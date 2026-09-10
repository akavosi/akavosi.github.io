#!/usr/bin/env bash
# Build the OR-Tools scenario-tree MIP.
#
# Expects an extracted OR-Tools C++ binary distribution. Override the location
# with ORTOOLS_ROOT if it lives somewhere else.
set -euo pipefail

ORTOOLS_ROOT="${ORTOOLS_ROOT:-$HOME/.local/toolchains/or-tools_x86_64_Ubuntu-22.04_cpp_v9.11.4210}"

if [[ ! -d "$ORTOOLS_ROOT/include" ]]; then
  echo "OR-Tools not found at $ORTOOLS_ROOT" >&2
  echo "set ORTOOLS_ROOT to the extracted distribution" >&2
  exit 1
fi

cd "$(dirname "$0")"

# libortools.so carries the solver itself. ProtoEnumToString is a header
# template that reaches into protobuf's descriptor API, so the static
# protobuf archive is linked after it to resolve that symbol.
g++ -std=c++17 -O2 -o inventory_mip inventory_mip.cc \
  -I"$ORTOOLS_ROOT/include" \
  -L"$ORTOOLS_ROOT/lib" \
  -lortools \
  -Wl,--start-group \
    "$ORTOOLS_ROOT/lib/libprotobuf.a" \
    "$ORTOOLS_ROOT"/lib/libabsl_*.a \
    "$ORTOOLS_ROOT/lib/libutf8_validity.a" \
  -Wl,--end-group \
  -lz -lpthread \
  -Wl,-rpath,"$ORTOOLS_ROOT/lib"

echo "built ./inventory_mip"
