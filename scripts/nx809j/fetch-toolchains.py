#!/usr/bin/env python3
"""Download the pinned Android toolchains and verify every cache asset."""

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_toolchain(toolchain: dict, destination: Path, base_url: str) -> None:
    target = destination / toolchain["directory"]
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nx809j-toolchain-") as temporary:
        downloads = Path(temporary)
        parts = []
        for asset in toolchain["assets"]:
            path = downloads / asset["name"]
            print(f"Downloading {asset['name']}", flush=True)
            subprocess.run(
                ["curl", "--fail", "--location", "--silent", "--show-error",
                 "--retry", "5", "--retry-delay", "5", "--connect-timeout", "30",
                 "--output", str(path), f"{base_url}/{asset['name']}"],
                check=True,
            )
            if path.stat().st_size != asset["size"] or sha256(path) != asset["sha256"]:
                raise RuntimeError(f"Size or SHA256 mismatch: {asset['name']}")
            parts.append(path)
        archive = parts[0]
        if len(parts) > 1:
            archive = downloads / "combined.tar.gz"
            with archive.open("wb") as output:
                for part in parts:
                    with part.open("rb") as source:
                        shutil.copyfileobj(source, output, 1024 * 1024)
        print(f"Extracting {toolchain['name']}", flush=True)
        subprocess.run(
            ["tar", "--extract", "--gzip", "--file", str(archive),
             "--directory", str(target), "--strip-components=1", "--no-same-owner"],
            check=True,
        )
    for binary in toolchain["required_binaries"]:
        path = target / binary
        if not path.is_file():
            raise RuntimeError(f"Toolchain binary missing: {path}")
    print(f"Verified {toolchain['name']}@{toolchain['revision']}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lock", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    for toolchain in lock["toolchains"]:
        fetch_toolchain(toolchain, args.destination.resolve(), lock["toolchain_cache"])


if __name__ == "__main__":
    main()
