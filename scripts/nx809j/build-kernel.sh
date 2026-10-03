#!/usr/bin/env bash
# Build committed source plus the pinned BBG exception. Keep output separate.
set -euo pipefail

if [[ $# -ne 4 ]]; then
    echo "Usage: $0 SOURCE_DIR TOOLCHAIN_DIR OUTPUT_DIR ARTIFACT_DIR" >&2
    exit 2
fi

source_dir=$(realpath "$1")
toolchain_dir=$(realpath "$2")
mkdir -p "$3" "$4"
output_dir=$(realpath "$3")
artifact_dir=$(realpath "$4")
recipe_dir=$(cd "$(dirname "$0")/../.." && pwd)

expected_commit=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["kernel"]["commit"])' "$recipe_dir/nx809j-source-lock.json")
actual_commit=$(git -C "$source_dir" rev-parse HEAD)
if [[ "$actual_commit" != "$expected_commit" ]]; then
    echo "Kernel commit mismatch: $actual_commit != $expected_commit" >&2
    exit 1
fi
if [[ -n $(git -C "$source_dir" status --porcelain) ]]; then
    echo "The kernel checkout must be clean before building." >&2
    exit 1
fi

python3 "$recipe_dir/scripts/nx809j/apply-build-patch.py" apply \
    "$source_dir" "$recipe_dir/nx809j-source-lock.json" "$artifact_dir"

clang_dir="$toolchain_dir/clang/host/linux-x86/clang-r547379"
rust_dir="$toolchain_dir/rust/linux-x86/1.82.0"
clang_tools_dir="$toolchain_dir/clang-tools/linux-x86"
build_tools_dir="$toolchain_dir/kernel-build-tools/linux-x86"
export PATH="$clang_dir/bin:$rust_dir/bin:$clang_tools_dir/bin:$build_tools_dir/bin:$PATH"
export ARCH=arm64 LLVM=1 LLVM_IAS=1 CROSS_COMPILE=aarch64-linux-gnu-
# Honor Android KABI rules when generating CRCs for the unchanged vendor drivers.
export KBUILD_GENDWARFKSYMS_STABLE=1
export RUSTC="$rust_dir/bin/rustc" BINDGEN="$clang_tools_dir/bin/bindgen"
export LIBCLANG_PATH="$clang_dir/lib" PAHOLE="$build_tools_dir/bin/pahole"
export KBUILD_BUILD_USER=Nattsu39 KBUILD_BUILD_HOST=github-actions KBUILD_BUILD_VERSION=1
export SOURCE_DATE_EPOCH
SOURCE_DATE_EPOCH=$(git -C "$source_dir" log -1 --format=%ct)
export KBUILD_BUILD_TIMESTAMP
KBUILD_BUILD_TIMESTAMP=$(date -u -d "@$SOURCE_DATE_EPOCH" '+%a %b %d %H:%M:%S UTC %Y')

prefix_flags="-fdebug-prefix-map=$source_dir=. -fmacro-prefix-map=$source_dir=. -ffile-prefix-map=$source_dir=."
export KCFLAGS="$prefix_flags -no-canonical-prefixes -fdiagnostics-color=never -Qunused-arguments -Wno-unused-command-line-argument -D__ANDROID_COMMON_KERNEL__ -Wno-error -pipe -mcpu=oryon-1 -O2"
export KCPPFLAGS="$prefix_flags -DCONFIG_OPTIMIZE_INLINING"
make_args=(-C "$source_dir" O="$output_dir" LOCALVERSION=)

{
    echo "Kernel source: $actual_commit"
    echo "KBUILD_GENDWARFKSYMS_STABLE=$KBUILD_GENDWARFKSYMS_STABLE"
    clang --version
    rustc --version
    bindgen --version
    "$PAHOLE" --version
} | tee "$artifact_dir/toolchain-versions.txt"

make "${make_args[@]}" rustavailable
make "${make_args[@]}" gki_defconfig
make "${make_args[@]}" olddefconfig
python3 "$recipe_dir/scripts/nx809j/verify-config.py" "$output_dir/.config"
cp "$output_dir/.config" "$artifact_dir/kernel.config"
cp "$source_dir/Documentation/nx809j/source-provenance.json" "$artifact_dir/source-provenance.json"
cp "$recipe_dir/nx809j-source-lock.json" "$artifact_dir/build-source-lock.json"
git -C "$source_dir" log --format=fuller -1 > "$artifact_dir/kernel-commit.txt"

make "${make_args[@]}" -j"$(nproc)" kernel/module/version.o 2>&1 | tee "$artifact_dir/module-layout-build.log"
python3 "$recipe_dir/scripts/nx809j/verify-module-layout.py" \
    "$recipe_dir/nx809j-source-lock.json" "$output_dir/kernel/module/.version.o.cmd"

make "${make_args[@]}" -j"$(nproc)" Image modules 2>&1 | tee "$artifact_dir/build.log"
python3 "$recipe_dir/scripts/nx809j/verify-module-layout.py" \
    "$recipe_dir/nx809j-source-lock.json" "$output_dir/Module.symvers"
for file in arch/arm64/boot/Image Module.symvers System.map vmlinux; do
    cp "$output_dir/$file" "$artifact_dir/$(basename "$file")"
done
make "${make_args[@]}" INSTALL_MOD_PATH="$artifact_dir/modules" modules_install 2>&1 | tee "$artifact_dir/modules-install.log"
find "$artifact_dir/modules" -type l -name build -delete

python3 "$recipe_dir/scripts/nx809j/apply-build-patch.py" verify \
    "$source_dir" "$recipe_dir/nx809j-source-lock.json" "$artifact_dir"
file "$artifact_dir/Image"
(
    cd "$artifact_dir"
    find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)
