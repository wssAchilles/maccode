#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


# Directory names that are safe to remove as cache/build artifacts.
TARGET_DIR_NAMES = {
    ".cache",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
    ".nox",
    ".tox",
    ".ipynb_checkpoints",
    "node_modules",
    "dist",
    ".vite",
    ".parcel-cache",
    ".sass-cache",
    ".turbo",
    ".npm",
    ".pnpm-store",
    ".yarn",
    "target",
    "build",
    "CMakeFiles",
    "Testing",
    ".terraform",
}

# Name patterns for cache/build directories.
TARGET_DIR_GLOBS = [
    "build-*",
    "cmake-build-*",
]

# File patterns that are safe to remove as cache/build artifacts.
TARGET_FILE_GLOBS = [
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.tsbuildinfo",
    "*.cache",
]

# Default protected directory names; we do not clean inside these unless overridden.
PROTECTED_DIR_NAMES = {
    ".git",
    ".venv",
}


@dataclass(frozen=True)
class Candidate:
    path: Path
    is_dir: bool
    bytes_size: int


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Scan and remove cache/build artifacts in this repository.",
    )
    parser.add_argument(
        "--root",
        default=str(default_root),
        help="Repository root path to scan (default: parent of scripts/).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete matched paths. Without this flag, only dry-run output is shown.",
    )
    parser.add_argument(
        "--include-venv",
        action="store_true",
        help="Also scan and clean inside .venv directories.",
    )
    parser.add_argument(
        "--extra-dir-pattern",
        action="append",
        default=[],
        metavar="GLOB",
        help="Additional directory-name glob pattern to clean (repeatable).",
    )
    parser.add_argument(
        "--extra-file-pattern",
        action="append",
        default=[],
        metavar="GLOB",
        help="Additional file-name glob pattern to clean (repeatable).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each matched path.",
    )
    return parser.parse_args()


def is_protected(path: Path, root: Path, include_venv: bool) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return True

    protected = set(PROTECTED_DIR_NAMES)
    if include_venv:
        protected.discard(".venv")
    return any(part in protected for part in rel_parts)


def match_dir_name(name: str, extra_patterns: list[str]) -> bool:
    if name in TARGET_DIR_NAMES:
        return True
    patterns = TARGET_DIR_GLOBS + extra_patterns
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def match_file_name(name: str, extra_patterns: list[str]) -> bool:
    patterns = TARGET_FILE_GLOBS + extra_patterns
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def safe_path_size(path: Path, is_dir: bool) -> int:
    if not path.exists() and not path.is_symlink():
        return 0
    if not is_dir:
        try:
            return path.stat(follow_symlinks=False).st_size
        except OSError:
            return 0

    total = 0
    try:
        for child in path.rglob("*"):
            try:
                if child.is_file() and not child.is_symlink():
                    total += child.stat().st_size
            except OSError:
                continue
    except OSError:
        return 0
    return total


def collect_candidates(
    root: Path,
    include_venv: bool,
    extra_dir_patterns: list[str],
    extra_file_patterns: list[str],
) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[Path] = set()

    for current_root_str, dirs, files in os.walk(root, topdown=True):
        current_root = Path(current_root_str)
        if is_protected(current_root, root, include_venv):
            dirs[:] = []
            continue

        for dirname in list(dirs):
            candidate_path = current_root / dirname

            if is_protected(candidate_path, root, include_venv):
                dirs.remove(dirname)
                continue

            if match_dir_name(dirname, extra_dir_patterns):
                dirs.remove(dirname)
                if candidate_path not in seen:
                    seen.add(candidate_path)
                    size = safe_path_size(candidate_path, is_dir=True)
                    candidates.append(Candidate(path=candidate_path, is_dir=True, bytes_size=size))

        for filename in files:
            candidate_path = current_root / filename
            if is_protected(candidate_path, root, include_venv):
                continue
            if match_file_name(filename, extra_file_patterns) and candidate_path not in seen:
                seen.add(candidate_path)
                size = safe_path_size(candidate_path, is_dir=False)
                candidates.append(Candidate(path=candidate_path, is_dir=False, bytes_size=size))

    return sorted(candidates, key=lambda item: str(item.path))


def format_bytes(total: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(total)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{total} B"


def delete_candidate(candidate: Candidate) -> tuple[bool, str | None]:
    try:
        if candidate.is_dir and candidate.path.exists():
            shutil.rmtree(candidate.path)
        elif not candidate.is_dir and candidate.path.exists():
            candidate.path.unlink()
        return True, None
    except OSError as exc:
        return False, str(exc)


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()

    if not root.exists() or not root.is_dir():
        print(f"Invalid --root directory: {root}", file=sys.stderr)
        return 2

    candidates = collect_candidates(
        root=root,
        include_venv=args.include_venv,
        extra_dir_patterns=args.extra_dir_pattern,
        extra_file_patterns=args.extra_file_pattern,
    )

    total_bytes = sum(item.bytes_size for item in candidates)
    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"[{mode}] Root: {root}")
    print(f"Matched paths: {len(candidates)}")
    print(f"Estimated reclaimable size: {format_bytes(total_bytes)}")

    if args.verbose:
        for item in candidates:
            rel = item.path.relative_to(root)
            kind = "DIR" if item.is_dir else "FILE"
            print(f"  - {kind:4} {rel} ({format_bytes(item.bytes_size)})")

    if not args.execute:
        print("No files were deleted. Re-run with --execute to remove matched paths.")
        return 0

    deleted = 0
    failed = 0
    for item in candidates:
        ok, error = delete_candidate(item)
        if ok:
            deleted += 1
        else:
            failed += 1
            print(f"Failed to delete {item.path}: {error}", file=sys.stderr)

    print(f"Deleted: {deleted}")
    if failed:
        print(f"Failed: {failed}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())