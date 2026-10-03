# NX809J real-38 source build

This branch builds the NX809J Android 16 kernel from committed Linux source.
The kernel revision and Android Clang/Rust toolchains are fixed in
[`nx809j-source-lock.json`](nx809j-source-lock.json).

The source includes the camera shared-GPIO reference counting and DP virtual
display modes from the 6.12.38 base, ReSukiSU, SUSFS 2.3.0, Baseband Guard,
NTSync, Droidspaces IPC changes, memory/filesystem tuning and networking options.
The kernel repository records these as separate commits. Its
`Documentation/nx809j/source-provenance.json` identifies all imported revisions.

The former build action's setup scripts and configuration edits have been
replaced by committed source. The action verifies cache asset hashes, checks out
the fixed kernel commit and builds with a separate output directory. It rejects
missing required configuration or unexpected changes to the source checkout.

The OnePlus-specific BBG ABL/EFISP exception is retained as the sole build-time
patch, following the upstream recipe. Its origin, hash and two affected files
are fixed in `nx809j-source-lock.json`. Only the source paths and a whitespace
context line were adapted for the committed BBG layout. The original behavior
is preserved: standard BBG protection is the default; the additional `abl` and
`efisp` entries are used when `oplusboot.secure_user_mode=0` (or `false`) appears
on the kernel command line. This recipe does not inject that boot parameter.
The exception remains a patch file rather than a kernel source commit.

Run **Build NX809J ReSukiSU 6.12.38** on `nx809j-resukisu-real-38` in GitHub Actions.
The artifact contains `Image`, built modules, the effective configuration,
`Module.symvers`, `System.map`, `vmlinux`, source/toolchain provenance, build logs
and checksums. `source-provenance.json` describes the committed base;
`applied-build-patch.json` and `applied-source.patch` record the applied exception.
The build checks that this recorded diff is unchanged after compilation.
It is a kernel build artifact, not an AnyKernel installer or a
complete ROM. Existing ROM firmware inputs and DTBO pairing checks remain in
the separate NX809J ROM build project.

The local ROM build script's kernel integration is also committed in the
`nx809j-avium-16.2` branches of `Nattsu39/android_vendor_lineage` (prebuilt kernel
configuration) and `Nattsu39/android_kernel_nubia_NX809J` (display UAPI). The device
tree fork removes the duplicate kernel hunk from its ROM patch bundle. The ROM
script checks these pinned commits without editing kernel integration source;
its other ROM patches and verified 6.12.23 firmware inputs remain available.

To reproduce the kernel build on Linux with the usual kernel build dependencies:

```sh
git clone https://github.com/Nattsu39/OnePlus_KernelSU_SUSFS.git recipe
cd recipe
git checkout nx809j-resukisu-real-38
kernel_commit=$(python3 -c 'import json; print(json.load(open("nx809j-source-lock.json"))["kernel"]["commit"])')
git clone https://github.com/Nattsu39/android_kernel_common_oneplus_sm8850.git kernel
git -C kernel checkout "$kernel_commit"
python3 scripts/nx809j/fetch-toolchains.py nx809j-source-lock.json ../toolchains
bash scripts/nx809j/build-kernel.sh kernel ../toolchains ../kernel-out ../artifacts
```

Linux 6.12.38 has not yet been booted on this project's current NX809J ROM.
Module CRC compatibility, runtime GPIO numbering and camera operation still need
to be verified against the device before adopting it as the ROM's kernel input.
