# Perishable inventory — implementation

Supporting code for the note *Perishable Inventory: Age-Tracked Dynamics Under
Non-Stationary Demand*. Implementation details live here rather than in the
post, which is about the model and its behaviour.

## The instance

Five-day shelf life, seven-day horizon, zero lead time, two-point demand each
day (128 scenarios, 255 tree nodes). A fixed ordering cost of 40 per
replenishment is what makes perishability bind — without it the optimal policy
orders near just-in-time and nothing ever expires.

`python/instance.py` is the single source of truth. Everything else reads the
JSON it emits, so no two solvers can disagree about the instance.

## Layout

| Path | Language | Role |
| --- | --- | --- |
| `python/instance.py` | Python | instance definition, emits `results/instance.json` |
| `python/exact_dp.py` | Python | exact backward stochastic DP over the age vector — ground truth |
| `python/export_policy.py` | Python | exports the DP policy as a MIP warm start |
| `python/baselines.py` | Python | grid-searched (s,S) + tabular Q-learning |
| `python/traces.py` | Python | per-day expected traces for every figure |
| `python/pick_scenario.py` | Python | searches all 128 paths for the filmstrip scenario |
| `python/sweep_*.py` | Python | the instance-design sweeps described in the post |
| `julia/perishable_inventory.jl` | Julia | scenario-tree MIP via JuMP + HiGHS |
| `cpp/inventory_mip.cc` | C++ | the same formulation, independently written, via OR-Tools + SCIP |
| `../scripts/fig_*.py` | Python | figure generation |
| `../scripts/verify.py` | Python | cross-checks every claim in the post |

## Why three solvers

The DP and the two MIPs are independent. They must return the same optimal
expected profit; if they do not, one of them is wrong. This caught a real bug:
the first scenario-tree model returned `238.445312`, below the DP's
`257.867188`, which is impossible for a correct deterministic equivalent. The
cause was an off-by-one in ageing the initial stock before day one, present in
both MIPs because the same mistaken assumption was made twice.

Both MIPs also leave issuing **free** — no FIFO constraint anywhere. Since their
feasible sets contain every oldest-first plan, matching the DP exactly proves
oldest-first is optimal here rather than assuming it.

## Running it

```bash
# Python-only pipeline (DP, baselines, traces, figures)
cd python
python3 instance.py
python3 exact_dp.py
python3 export_policy.py
python3 baselines.py
python3 traces.py
python3 pick_scenario.py

# Julia scenario-tree MIP
cd ../julia
julia --project -e 'using Pkg; Pkg.add(["JuMP","HiGHS","JSON3"])'
julia perishable_inventory.jl

# C++ scenario-tree MIP
cd ../cpp
export ORTOOLS_ROOT=/path/to/or-tools_cpp_distribution
./build.sh
./inventory_mip

# figures + verification
cd ../../scripts
python3 fig_flagship.py && python3 fig_convergence.py
python3 fig_filmstrip.py && python3 fig_hero_3d.py
python3 verify.py
```

`verify.py` prints `ALL CHECKS PASSED` when the three solvers agree and the
policy ranking holds.

## Results

| Policy | Expected profit | Gap to optimum | Spoiled | Short |
| --- | ---: | ---: | ---: | ---: |
| Exact optimum | 257.8672 | — | 1.3984 | 1.1016 |
| Learned (best of 5 seeds) | 243.3242 | 5.64% | 1.4141 | 1.1562 |
| Learned (mean of 5 seeds) | 227.6469 | 11.72% | — | — |
| Best (s,S) = (7,25) | 213.9531 | 17.03% | 0.9688 | 3.9375 |

The base-stock policy spoils *less* than optimal play and loses anyway, because
its only lever against spoilage is holding less stock.

## Environment notes

Solve times were measured on a 2-core machine with 2 GB of RAM. The Julia model
solves in ~7 s with the DP warm start; the C++ model solves cold in ~38 s. An
earlier three-point-support instance (2,187 scenarios, ~58k integer variables)
is a fine DP but does not fit in that memory budget well enough for
branch-and-bound to prove optimality, which is why the published instance uses
two-point support.
