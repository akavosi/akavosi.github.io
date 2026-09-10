#!/usr/bin/env bash
# Full reproduction: instance -> solvers -> figures -> verification.
#
# The Julia and C++ stages are skipped with a warning if their toolchains are
# absent, so the Python-only path still produces every figure. verify.py then
# checks whichever results exist.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== instance and exact DP ==="
cd "$ROOT/code/python"
python3 instance.py
python3 exact_dp.py
python3 export_policy.py

echo
echo "=== scenario-tree MIP, modelling layer A ==="
if command -v julia >/dev/null 2>&1; then
  cd "$ROOT/code/julia" && julia perishable_inventory.jl
else
  echo "julia not found — skipping" >&2
fi

echo
echo "=== scenario-tree MIP, modelling layer B ==="
if [[ -x "$ROOT/code/cpp/inventory_mip" ]]; then
  cd "$ROOT/code/cpp" && ./inventory_mip
elif [[ -n "${ORTOOLS_ROOT:-}" ]]; then
  cd "$ROOT/code/cpp" && ./build.sh && ./inventory_mip
else
  echo "OR-Tools build not found, set ORTOOLS_ROOT — skipping" >&2
fi

echo
echo "=== baselines, traces, scenario selection ==="
cd "$ROOT/code/python"
python3 baselines.py
python3 traces.py
python3 pick_scenario.py

echo
echo "=== figures ==="
cd "$ROOT/scripts"
python3 fig_flagship.py
python3 fig_convergence.py
python3 fig_filmstrip.py
python3 fig_hero_3d.py

echo
echo "=== verification ==="
python3 verify.py
