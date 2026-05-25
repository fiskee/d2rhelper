#!/usr/bin/env bash
set -euo pipefail

CASCLIB_REPO="https://github.com/ladislav-zezula/CascLib.git"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$(mktemp -d)"
OUTPUT_DIR="$PROJECT_DIR/src/d2rhelper"

TARGET="${1:-native}"

echo "=== Building CascLib shared library ($TARGET) ==="
echo "Build dir: $BUILD_DIR"
echo "Output dir: $OUTPUT_DIR"

git clone --depth 1 "$CASCLIB_REPO" "$BUILD_DIR"

cd "$BUILD_DIR"

sed -i 's/cmake_minimum_required(VERSION 3.2)/cmake_minimum_required(VERSION 3.2...4.0)/' CMakeLists.txt
    sed -i 's/list(APPEND LINK_LIBS wininet)/list(APPEND LINK_LIBS wininet ws2_32)/' CMakeLists.txt

if [[ "$TARGET" == "windows" ]]; then
    cat > "$BUILD_DIR/toolchain.cmake" << 'EOF'
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)
set(CMAKE_C_COMPILER x86_64-w64-mingw32-gcc)
set(CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++)
set(CMAKE_RC_COMPILER x86_64-w64-mingw32-windres)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
EOF
    cmake -DCMAKE_BUILD_TYPE=Release \
          -DCMAKE_TOOLCHAIN_FILE="$BUILD_DIR/toolchain.cmake" \
          -B build
    cmake --build build -j"$(nproc)"
    if [[ -f build/CascLib.dll ]]; then
        cp build/CascLib.dll "$OUTPUT_DIR/"
    elif [[ -f build/libCascLib.dll ]]; then
        cp build/libCascLib.dll "$OUTPUT_DIR/Casclib.dll"
    fi
    echo "Built: $OUTPUT_DIR/Casclib.dll"
else
    cmake -DCMAKE_BUILD_TYPE=Release -B build
    cmake --build build -j"$(nproc)"

    if [[ "$(uname -s)" == "Linux" ]]; then
        cp build/libcasc.so.1 "$OUTPUT_DIR/"
        ln -sf libcasc.so.1 "$OUTPUT_DIR/libcasc.so"
        echo "Built: $OUTPUT_DIR/libcasc.so.1"
    elif [[ "$(uname -s)" == "Darwin" ]]; then
        cp build/libcasc.dylib "$OUTPUT_DIR/"
        echo "Built: $OUTPUT_DIR/libcasc.dylib"
    fi
fi

rm -rf "$BUILD_DIR"
echo "=== Build complete ==="
