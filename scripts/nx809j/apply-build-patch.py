#!/usr/bin/env python3
"""Apply the pinned BBG exception and reject any additional source changes."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def git(source_dir: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(source_dir), *args])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("apply", "verify"))
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("lock_file", type=Path)
    parser.add_argument("artifact_dir", type=Path)
    args = parser.parse_args()

    lock = json.loads(args.lock_file.read_text(encoding="utf-8"))
    commit = git(args.source_dir, "rev-parse", "HEAD").decode().strip()
    if commit != lock["kernel"]["commit"]:
        raise SystemExit(f"Kernel commit mismatch: {commit}")

    patch = lock["build_patch"]
    patch_path = args.lock_file.resolve().parent / patch["path"]
    digest = hashlib.sha256(patch_path.read_bytes()).hexdigest()
    if digest != patch["sha256"]:
        raise SystemExit(f"Build patch checksum mismatch: {patch_path}")

    record_path = args.artifact_dir / "applied-build-patch.json"
    diff_path = args.artifact_dir / "applied-source.patch"
    status_args = ("status", "--porcelain=v1", "--untracked-files=all")

    if args.command == "apply":
        if git(args.source_dir, *status_args):
            raise SystemExit("The kernel checkout must be clean before patching.")
        git(args.source_dir, "apply", "--check", str(patch_path))
        git(args.source_dir, "apply", str(patch_path))
        changed = git(args.source_dir, "diff", "--name-only", "HEAD").decode().splitlines()
        if sorted(changed) != sorted(patch["files"]):
            raise SystemExit(f"Unexpected files modified by build patch: {changed}")

        args.artifact_dir.mkdir(parents=True, exist_ok=True)
        diff_path.write_bytes(git(args.source_dir, "diff", "--binary", "HEAD"))
        record = {
            "kernel_commit": commit,
            "patch": patch,
            "source_status": git(args.source_dir, *status_args).decode(),
        }
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"Applied pinned BBG ABL/EFISP patch: {digest}")
    else:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record["kernel_commit"] != commit or record["patch"] != patch:
            raise SystemExit("The recorded build source or patch does not match the lock.")
        if git(args.source_dir, *status_args).decode() != record["source_status"]:
            raise SystemExit("The build unexpectedly changed the source checkout status.")
        if git(args.source_dir, "diff", "--binary", "HEAD") != diff_path.read_bytes():
            raise SystemExit("The build unexpectedly modified the patched kernel source.")
        print("Verified kernel source contains exactly the recorded build patch.")


if __name__ == "__main__":
    main()
