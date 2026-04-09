#!/usr/bin/env python3
"""Safely clean stale Container Registry images for this project.

Default behavior is dry-run. The script protects:
1. Digests currently referenced by Cloud Run revisions.
2. The newest N digests per image.
3. Digests newer than the configured retention window.

It intentionally ignores the App Engine `backend` image unless explicitly asked,
because that rollback surface is more sensitive than the Cloud Run services.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import subprocess
import sys
from typing import Iterable


UTC = dt.timezone.utc


@dataclasses.dataclass(frozen=True)
class ServiceTarget:
    image: str
    region: str
    service: str


@dataclasses.dataclass(frozen=True)
class ImageDigest:
    image: str
    digest: str
    created_at: dt.datetime

    @property
    def full_ref(self) -> str:
        return f"{self.image}@sha256:{self.digest}"


DEFAULT_TARGETS = (
    ServiceTarget(
        image="gcr.io/{project}/sentinel-backend-cloudrun",
        region="us-central1",
        service="sentinel-backend-cloudrun",
    ),
    ServiceTarget(
        image="gcr.io/{project}/sentinel-orchestrator",
        region="asia-northeast1",
        service="sentinel-orchestrator",
    ),
)


def run_gcloud(args: list[str]) -> str:
    command = ["gcloud", *args]
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def project_from_gcloud() -> str:
    return run_gcloud(["config", "get-value", "project"]).strip()


def parse_timestamp(raw: str) -> dt.datetime:
    raw = raw.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return dt.datetime.fromisoformat(raw).astimezone(UTC)


def list_image_digests(image: str) -> list[ImageDigest]:
    output = run_gcloud(
        [
            "container",
            "images",
            "list-tags",
            image,
            "--format=json",
            "--limit=999999",
            "--sort-by=~TIMESTAMP",
        ]
    )
    rows = json.loads(output or "[]")
    digests: list[ImageDigest] = []
    for row in rows:
        digest = row.get("digest")
        timestamp = row.get("timestamp", {}).get("datetime")
        if not digest or not timestamp:
            continue
        normalized_digest = digest.removeprefix("sha256:")
        digests.append(
            ImageDigest(
                image=image,
                digest=normalized_digest,
                created_at=parse_timestamp(timestamp),
            )
        )
    return digests


def list_live_digests(target: ServiceTarget) -> set[str]:
    output = run_gcloud(
        [
            "run",
            "revisions",
            "list",
            "--region",
            target.region,
            f"--service={target.service}",
            "--format=json",
        ]
    )
    rows = json.loads(output or "[]")
    digests: set[str] = set()
    for row in rows:
        ref = row.get("status", {}).get("imageDigest")
        if not ref:
            continue
        if "@sha256:" in ref:
            digests.add(ref.split("@sha256:", 1)[1])
    return digests


def select_candidates(
    digests: list[ImageDigest],
    protected_live: set[str],
    keep_last: int,
    keep_days: int,
    now: dt.datetime,
) -> tuple[list[ImageDigest], list[ImageDigest]]:
    protected: set[str] = set(protected_live)
    recent_cutoff = now - dt.timedelta(days=keep_days)

    for digest in digests[:keep_last]:
        protected.add(digest.digest)

    kept: list[ImageDigest] = []
    candidates: list[ImageDigest] = []
    for digest in digests:
        if digest.digest in protected or digest.created_at >= recent_cutoff:
            kept.append(digest)
        else:
            candidates.append(digest)
    return kept, candidates


def delete_digest(ref: str) -> None:
    subprocess.run(
        [
            "gcloud",
            "container",
            "images",
            "delete",
            ref,
            "--force-delete-tags",
            "--quiet",
        ],
        check=True,
    )


def format_age(now: dt.datetime, created_at: dt.datetime) -> str:
    delta = now - created_at
    days = delta.days
    hours = delta.seconds // 3600
    if days > 0:
        return f"{days}d {hours}h"
    minutes = (delta.seconds % 3600) // 60
    return f"{hours}h {minutes}m"


def emit_report(
    image: str,
    kept: Iterable[ImageDigest],
    candidates: Iterable[ImageDigest],
    now: dt.datetime,
) -> None:
    print(f"\n## {image}")
    kept = list(kept)
    candidates = list(candidates)
    print(f"kept={len(kept)} candidates={len(candidates)}")
    if candidates:
        for digest in candidates:
            print(
                f"  DELETE sha256:{digest.digest}  "
                f"created={digest.created_at.isoformat()}  age={format_age(now, digest.created_at)}"
            )
    else:
        print("  no deletion candidates")


def build_targets(project: str, include_backend: bool) -> list[ServiceTarget]:
    targets = [
        ServiceTarget(
            image=target.image.format(project=project),
            region=target.region,
            service=target.service,
        )
        for target in DEFAULT_TARGETS
    ]
    if include_backend:
        targets.append(
            ServiceTarget(
                image=f"gcr.io/{project}/backend",
                region="",
                service="",
            )
        )
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean stale Container Registry images with Cloud Run revision protection."
    )
    parser.add_argument("--project", help="GCP project id. Defaults to current gcloud project.")
    parser.add_argument(
        "--keep-last",
        type=int,
        default=3,
        help="Always keep the newest N digests per image. Default: 3",
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=7,
        help="Always keep digests newer than this many days. Default: 7",
    )
    parser.add_argument(
        "--include-backend",
        action="store_true",
        help="Also inspect gcr.io/<project>/backend. Off by default for App Engine safety.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete candidates. Default is dry-run.",
    )
    args = parser.parse_args()

    project = args.project or project_from_gcloud()
    now = dt.datetime.now(tz=UTC)
    targets = build_targets(project, include_backend=args.include_backend)

    all_candidates: list[ImageDigest] = []
    print(
        f"project={project} dry_run={not args.delete} keep_last={args.keep_last} keep_days={args.keep_days}"
    )

    for target in targets:
        digests = list_image_digests(target.image)
        protected_live = list_live_digests(target) if target.service else set()
        kept, candidates = select_candidates(
            digests=digests,
            protected_live=protected_live,
            keep_last=args.keep_last,
            keep_days=args.keep_days,
            now=now,
        )
        emit_report(target.image, kept, candidates, now)
        all_candidates.extend(candidates)

    if not args.delete:
        print("\nDry-run only. Re-run with --delete to remove the candidates above.")
        return 0

    if not all_candidates:
        print("\nNothing to delete.")
        return 0

    print(f"\nDeleting {len(all_candidates)} image digests...")
    for digest in all_candidates:
        print(f"  deleting {digest.full_ref}")
        delete_digest(digest.full_ref)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
