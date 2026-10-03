#!/usr/bin/env python3
"""Check module_layout's CRC against the validated NX809J driver baseline."""

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lock_file", type=Path)
    parser.add_argument("symbol_versions", type=Path)
    args = parser.parse_args()
    expected = int(json.loads(args.lock_file.read_text())["abi"]["module_layout_crc"], 16)
    actual = set()
    for line in args.symbol_versions.read_text().splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[:2] == ["#SYMVER", "module_layout"]:
            actual.add(int(fields[2], 16))
        elif len(fields) >= 3 and fields[1:3] == ["module_layout", "vmlinux"]:
            actual.add(int(fields[0], 16))
    if actual != {expected}:
        values = ", ".join(f"0x{value:08x}" for value in sorted(actual)) or "missing"
        raise SystemExit(f"module_layout CRC mismatch: expected 0x{expected:08x}, got {values}")
    print(f"Verified NX809J module_layout CRC: 0x{expected:08x}")


if __name__ == "__main__":
    main()
