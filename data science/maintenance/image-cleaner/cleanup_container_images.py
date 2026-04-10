#!/usr/bin/env python3
"""Weekly maintenance cleanup for App Engine, GCR images, and build artifacts.

Workflow:
1. Delete zero-traffic App Engine versions beyond the retention policy.
2. Delete stale Container Registry digests not referenced by live Cloud Run revisions.
3. Delete old Cloud Build source archives from the Cloud Build staging bucket.

Default mode is dry-run. Use --delete to apply the cleanup.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from typing import Iterable


UTC = dt.timezone.utc
_ACCESS_TOKEN_FILE: pathlib.Path | None = None
_ACCESS_TOKEN_VALUE: str | None = None


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


@dataclasses.dataclass(frozen=True)
class AppVersion:
    service: str
    version_id: str
    created_at: dt.datetime
    traffic_split: float
    serving_status: str


@dataclasses.dataclass(frozen=True)
class StorageObject:
    bucket: str
    name: str
    created_at: dt.datetime
    size_bytes: int


DEFAULT_IMAGE_TARGETS = (
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
    command = ["gcloud", *access_token_args(), *args]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "gcloud command failed\n"
            f"command={' '.join(command)}\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    return completed.stdout


def project_from_context() -> str:
    configured = os.environ.get("PROJECT_ID")
    if configured:
        return configured
    return run_gcloud(["config", "get-value", "project"]).strip()


def access_token_args() -> list[str]:
    token_file = metadata_access_token_file()
    if token_file is None:
        return []
    return [f"--access-token-file={token_file}"]


def metadata_access_token_file() -> pathlib.Path | None:
    global _ACCESS_TOKEN_FILE
    token = metadata_access_token_value()
    if not token:
        return None
    if _ACCESS_TOKEN_FILE is not None:
        return _ACCESS_TOKEN_FILE
    tmp = tempfile.NamedTemporaryFile(mode="w", prefix="gcloud-token-", delete=False)
    tmp.write(token)
    tmp.flush()
    tmp.close()
    _ACCESS_TOKEN_FILE = pathlib.Path(tmp.name)
    return _ACCESS_TOKEN_FILE


def metadata_access_token_value() -> str | None:
    global _ACCESS_TOKEN_VALUE
    if _ACCESS_TOKEN_VALUE is not None:
        return _ACCESS_TOKEN_VALUE
    token: str | None = None
    request = urllib.request.Request(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
        headers={"Metadata-Flavor": "Google"},
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        token = payload.get("access_token")
    except Exception:
        token = None
    if token:
        _ACCESS_TOKEN_VALUE = token
        return token
    try:
        _ACCESS_TOKEN_VALUE = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except Exception:
        return None
    return _ACCESS_TOKEN_VALUE or None


def auth_header() -> dict[str, str]:
    token = metadata_access_token_value()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def parse_timestamp(raw: str) -> dt.datetime:
    raw = raw.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return dt.datetime.fromisoformat(raw).astimezone(UTC)


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    expected: Iterable[int] = (200,),
    extra_headers: dict[str, str] | None = None,
) -> dict:
    headers = {"Accept": "application/json", **auth_header()}
    if extra_headers:
        headers.update(extra_headers)
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.getcode()
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code not in expected:
            raise RuntimeError(f"HTTP {exc.code} for {method} {url}: {body}") from exc
        if not body:
            return {}
        return json.loads(body)
    if status not in expected:
        raise RuntimeError(f"HTTP {status} for {method} {url}: {body}")
    if not body:
        return {}
    return json.loads(body)


def request_empty(
    url: str,
    *,
    method: str,
    expected: Iterable[int],
) -> None:
    headers = auth_header()
    request = urllib.request.Request(url, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.getcode()
            _ = response.read()
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code not in expected:
            raise RuntimeError(f"HTTP {exc.code} for {method} {url}: {body}") from exc
        return
    if status not in expected:
        raise RuntimeError(f"HTTP {status} for {method} {url}")


def list_app_services(project: str) -> list[str]:
    url = f"https://appengine.googleapis.com/v1/apps/{project}/services"
    payload = request_json(url)
    services = payload.get("services", [])
    return [service["id"] for service in services if service.get("id")]


def list_app_versions(project: str, service: str) -> list[AppVersion]:
    url = (
        f"https://appengine.googleapis.com/v1/apps/{project}/services/"
        f"{service}/versions"
    )
    payload = request_json(url)
    versions: list[AppVersion] = []
    for item in payload.get("versions", []):
        versions.append(
            AppVersion(
                service=service,
                version_id=item["id"],
                created_at=parse_timestamp(item["createTime"]),
                traffic_split=float(item.get("traffic_split", item.get("trafficSplit", 0.0)) or 0.0),
                serving_status=item.get("servingStatus", ""),
            )
        )
    versions.sort(key=lambda version: version.created_at, reverse=True)
    return versions


def delete_app_version(project: str, version: AppVersion) -> None:
    url = (
        f"https://appengine.googleapis.com/v1/apps/{project}/services/"
        f"{version.service}/versions/{version.version_id}"
    )
    operation = request_json(url, method="DELETE", expected=(200,))
    wait_google_operation(operation.get("name"))


def wait_google_operation(operation_name: str | None, timeout_seconds: int = 600) -> None:
    if not operation_name:
        return
    deadline = dt.datetime.now(tz=UTC) + dt.timedelta(seconds=timeout_seconds)
    while dt.datetime.now(tz=UTC) < deadline:
        payload = request_json(f"https://appengine.googleapis.com/v1/{operation_name}")
        if payload.get("done"):
            if "error" in payload:
                raise RuntimeError(f"Operation failed: {payload['error']}")
            return
        subprocess.run(["sleep", "2"], check=True)
    raise RuntimeError(f"Timed out waiting for operation {operation_name}")


def select_app_version_candidates(
    versions: list[AppVersion],
    *,
    keep_zero_traffic: int,
    keep_days: int,
    now: dt.datetime,
) -> tuple[list[AppVersion], list[AppVersion]]:
    protected_ids: set[str] = {version.version_id for version in versions if version.traffic_split > 0}
    zero_traffic = [version for version in versions if version.traffic_split == 0]
    for version in zero_traffic[:keep_zero_traffic]:
        protected_ids.add(version.version_id)
    cutoff = now - dt.timedelta(days=keep_days)
    kept: list[AppVersion] = []
    candidates: list[AppVersion] = []
    for version in versions:
        if version.version_id in protected_ids or version.created_at >= cutoff:
            kept.append(version)
        elif version.serving_status == "SERVING":
            candidates.append(version)
        else:
            kept.append(version)
    return kept, candidates


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
        if ref and "@sha256:" in ref:
            digests.add(ref.split("@sha256:", 1)[1])
    return digests


def parse_gcr_name(image: str) -> str:
    prefix = "gcr.io/"
    if not image.startswith(prefix):
        raise ValueError(f"Only gcr.io images are supported, got {image}")
    return image[len(prefix):]


def list_image_digests(image: str) -> list[ImageDigest]:
    name = parse_gcr_name(image)
    payload = request_json(f"https://gcr.io/v2/{name}/tags/list")
    manifests = payload.get("manifest", {})
    digests: list[ImageDigest] = []
    for digest, meta in manifests.items():
        created_ms = meta.get("timeUploadedMs") or meta.get("timeCreatedMs")
        if not created_ms:
            continue
        created_at = dt.datetime.fromtimestamp(int(created_ms) / 1000, tz=UTC)
        digests.append(
            ImageDigest(
                image=image,
                digest=digest.removeprefix("sha256:"),
                created_at=created_at,
            )
        )
    digests.sort(key=lambda digest: digest.created_at, reverse=True)
    return digests


def select_image_candidates(
    digests: list[ImageDigest],
    *,
    protected_live: set[str],
    keep_last: int,
    keep_days: int,
    now: dt.datetime,
) -> tuple[list[ImageDigest], list[ImageDigest]]:
    protected: set[str] = set(protected_live)
    cutoff = now - dt.timedelta(days=keep_days)
    for digest in digests[:keep_last]:
        protected.add(digest.digest)
    kept: list[ImageDigest] = []
    candidates: list[ImageDigest] = []
    for digest in digests:
        if digest.digest in protected or digest.created_at >= cutoff:
            kept.append(digest)
        else:
            candidates.append(digest)
    return kept, candidates


def delete_digest(image: str, digest: str) -> None:
    name = parse_gcr_name(image)
    request_empty(
        f"https://gcr.io/v2/{name}/manifests/sha256:{digest}",
        method="DELETE",
        expected=(202,),
    )


def list_storage_objects(bucket: str, prefix: str) -> list[StorageObject]:
    encoded_prefix = urllib.parse.quote(prefix, safe="")
    page_token = ""
    objects: list[StorageObject] = []
    while True:
        url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o?prefix={encoded_prefix}"
        if page_token:
            url += f"&pageToken={urllib.parse.quote(page_token, safe='')}"
        payload = request_json(url)
        for item in payload.get("items", []):
            objects.append(
                StorageObject(
                    bucket=bucket,
                    name=item["name"],
                    created_at=parse_timestamp(item["timeCreated"]),
                    size_bytes=int(item.get("size", 0)),
                )
            )
        page_token = payload.get("nextPageToken", "")
        if not page_token:
            break
    objects.sort(key=lambda obj: obj.created_at, reverse=True)
    return objects


def select_storage_candidates(
    objects: list[StorageObject],
    *,
    keep_days: int,
    now: dt.datetime,
) -> tuple[list[StorageObject], list[StorageObject]]:
    cutoff = now - dt.timedelta(days=keep_days)
    kept: list[StorageObject] = []
    candidates: list[StorageObject] = []
    for obj in objects:
        if obj.created_at >= cutoff:
            kept.append(obj)
        else:
            candidates.append(obj)
    return kept, candidates


def delete_storage_object(obj: StorageObject) -> None:
    encoded_name = urllib.parse.quote(obj.name, safe="")
    request_empty(
        f"https://storage.googleapis.com/storage/v1/b/{obj.bucket}/o/{encoded_name}",
        method="DELETE",
        expected=(204,),
    )


def format_age(now: dt.datetime, created_at: dt.datetime) -> str:
    delta = now - created_at
    days = delta.days
    hours = delta.seconds // 3600
    if days > 0:
        return f"{days}d {hours}h"
    minutes = (delta.seconds % 3600) // 60
    return f"{hours}h {minutes}m"


def emit_app_report(
    service: str,
    kept: list[AppVersion],
    candidates: list[AppVersion],
    now: dt.datetime,
) -> None:
    print(f"\n## App Engine service={service}")
    print(f"kept={len(kept)} candidates={len(candidates)}")
    for version in candidates:
        print(
            f"  DELETE version={version.version_id} created={version.created_at.isoformat()} "
            f"age={format_age(now, version.created_at)} traffic={version.traffic_split:.2f}"
        )
    if not candidates:
        print("  no deletion candidates")


def emit_image_report(image: str, kept: list[ImageDigest], candidates: list[ImageDigest], now: dt.datetime) -> None:
    print(f"\n## {image}")
    print(f"kept={len(kept)} candidates={len(candidates)}")
    for digest in candidates:
        print(
            f"  DELETE sha256:{digest.digest} created={digest.created_at.isoformat()} "
            f"age={format_age(now, digest.created_at)}"
        )
    if not candidates:
        print("  no deletion candidates")


def emit_storage_report(bucket: str, kept: list[StorageObject], candidates: list[StorageObject], now: dt.datetime) -> None:
    print(f"\n## gs://{bucket}/source/")
    print(f"kept={len(kept)} candidates={len(candidates)}")
    for obj in candidates[:20]:
        print(
            f"  DELETE {obj.name} created={obj.created_at.isoformat()} "
            f"age={format_age(now, obj.created_at)} size={obj.size_bytes}"
        )
    if len(candidates) > 20:
        print(f"  ... {len(candidates) - 20} more objects")
    if not candidates:
        print("  no deletion candidates")


def build_image_targets(project: str, include_backend: bool) -> list[ServiceTarget]:
    targets = [
        ServiceTarget(
            image=target.image.format(project=project),
            region=target.region,
            service=target.service,
        )
        for target in DEFAULT_IMAGE_TARGETS
    ]
    if include_backend:
        targets.append(ServiceTarget(image=f"gcr.io/{project}/backend", region="", service=""))
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly maintenance cleanup for deployed resources.")
    parser.add_argument("--project", help="GCP project id. Defaults to current project context.")
    parser.add_argument("--delete", action="store_true", help="Apply deletions. Default is dry-run.")
    parser.add_argument("--include-backend", action="store_true", help="Also inspect gcr.io/<project>/backend.")
    parser.add_argument("--app-keep-zero-traffic", type=int, default=2)
    parser.add_argument("--app-keep-days", type=int, default=2)
    parser.add_argument("--image-keep-last", type=int, default=3)
    parser.add_argument("--image-keep-days", type=int, default=7)
    parser.add_argument("--build-source-keep-days", type=int, default=7)
    args = parser.parse_args()

    project = args.project or project_from_context()
    now = dt.datetime.now(tz=UTC)
    build_bucket = f"{project}_cloudbuild"

    print(
        "project={project} dry_run={dry_run} app_keep_zero_traffic={app_keep} "
        "app_keep_days={app_days} image_keep_last={image_keep_last} image_keep_days={image_days} "
        "build_source_keep_days={build_days}".format(
            project=project,
            dry_run=not args.delete,
            app_keep=args.app_keep_zero_traffic,
            app_days=args.app_keep_days,
            image_keep_last=args.image_keep_last,
            image_days=args.image_keep_days,
            build_days=args.build_source_keep_days,
        )
    )

    app_candidates: list[AppVersion] = []
    for service in list_app_services(project):
        versions = list_app_versions(project, service)
        kept, candidates = select_app_version_candidates(
            versions,
            keep_zero_traffic=args.app_keep_zero_traffic,
            keep_days=args.app_keep_days,
            now=now,
        )
        emit_app_report(service, kept, candidates, now)
        app_candidates.extend(candidates)

    image_candidates: list[ImageDigest] = []
    for target in build_image_targets(project, include_backend=args.include_backend):
        digests = list_image_digests(target.image)
        protected_live = list_live_digests(target) if target.service else set()
        kept, candidates = select_image_candidates(
            digests,
            protected_live=protected_live,
            keep_last=args.image_keep_last,
            keep_days=args.image_keep_days,
            now=now,
        )
        emit_image_report(target.image, kept, candidates, now)
        image_candidates.extend(candidates)

    storage_objects = list_storage_objects(build_bucket, "source/")
    kept_objects, storage_candidates = select_storage_candidates(
        storage_objects,
        keep_days=args.build_source_keep_days,
        now=now,
    )
    emit_storage_report(build_bucket, kept_objects, storage_candidates, now)

    if not args.delete:
        print("\nDry-run only. Re-run with --delete to apply cleanup.")
        return 0

    print("\nApplying cleanup...")
    for version in app_candidates:
        print(f"  deleting App Engine version {version.service}/{version.version_id}")
        delete_app_version(project, version)

    for digest in image_candidates:
        print(f"  deleting image {digest.full_ref}")
        delete_digest(digest.image, digest.digest)

    for obj in storage_candidates:
        print(f"  deleting storage object gs://{obj.bucket}/{obj.name}")
        delete_storage_object(obj)

    print("Cleanup complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
