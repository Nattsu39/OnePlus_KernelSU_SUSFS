#!/usr/bin/env python3
"""Fail if Kconfig drops an option required by the NX809J real-38 port."""

import re
import sys
from pathlib import Path


REQUIRED = {
    "CONFIG_LOCALVERSION": '"-android16-OP-WILD"',
    "CONFIG_MODVERSIONS": "y",
    "CONFIG_GENDWARFKSYMS": "y",
    "CONFIG_EXTENDED_MODVERSIONS": "y",
    "CONFIG_LTO_NONE": "y",
    "CONFIG_CC_OPTIMIZE_FOR_PERFORMANCE": "y",
    "CONFIG_KSU": "y",
    "CONFIG_KSU_MULTI_MANAGER_SUPPORT": "y",
    "CONFIG_KSU_SUSFS": "y",
    "CONFIG_KSU_SUSFS_SUS_PATH": "y",
    "CONFIG_KSU_SUSFS_SUS_MOUNT": "y",
    "CONFIG_KSU_SUSFS_SUS_KSTAT": "y",
    "CONFIG_KSU_SUSFS_SPOOF_UNAME": "y",
    "CONFIG_KSU_SUSFS_ENABLE_LOG": "y",
    "CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS": "y",
    "CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG": "y",
    "CONFIG_KSU_SUSFS_OPEN_REDIRECT": "y",
    "CONFIG_KSU_SUSFS_SUS_MAP": "y",
    "CONFIG_BBG": "y",
    "CONFIG_RUST": "y",
    "CONFIG_ANDROID_BINDER_IPC_RUST": "m",
    "CONFIG_SYSVIPC": "y",
    "CONFIG_PID_NS": "y",
    "CONFIG_POSIX_MQUEUE": "y",
    "CONFIG_TMPFS_XATTR": "y",
    "CONFIG_TMPFS_POSIX_ACL": "y",
    "CONFIG_TCP_CONG_BBR": "y",
    "CONFIG_IP_SET": "y",
    "CONFIG_IP_NF_TARGET_TTL": "y",
    "CONFIG_IP6_NF_TARGET_HL": "y",
    "CONFIG_NTSYNC": "y",
    "CONFIG_MODULE_SIG_FORCE": "n",
    "CONFIG_MODULE_SIG_ALL": "n",
    "CONFIG_LOCALVERSION_AUTO": "n",
    "CONFIG_USER_NS": "n",
    "CONFIG_KSU_TRACEPOINT_HOOK": "n",
    "CONFIG_KSU_MANUAL_HOOK": "n",
}


def main() -> None:
    values = {}
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
        if line.startswith("CONFIG_"):
            name, value = line.split("=", 1)
            values[name] = value
        else:
            match = re.fullmatch(r"# (CONFIG_\w+) is not set", line)
            if match:
                values[match.group(1)] = "n"
    failures = []
    for name, expected in REQUIRED.items():
        actual = values.get(name, "n")
        if actual != expected:
            failures.append(f"{name}: expected {expected}, got {actual}")
    if "baseband_guard" not in values.get("CONFIG_LSM", "").strip('"').split(","):
        failures.append("CONFIG_LSM does not enable baseband_guard")
    if failures:
        raise SystemExit("Invalid NX809J config:\n" + "\n".join(failures))
    print(f"Verified {len(REQUIRED)} required kernel options and the BBG LSM order.")


if __name__ == "__main__":
    main()
