#
# Age-tracked perishable inventory: deterministic-equivalent scenario-tree MIP.
#
# The stochastic program is written out in full on the demand tree. Every day
# has three-point demand support, so a 7-day horizon is a ternary tree with
# 3 + 9 + ... + 3^7 = 3279 outcome nodes plus a root: 3280 nodes exactly.
#
# Non-anticipativity is structural, not a constraint block: the order placed
# for day t is a variable attached to the *parent* node, so every scenario
# that shares a demand history up to day t-1 is forced to share one order
# decision. There is nothing to relax and nothing to penalise.
#
# Issuing is deliberately left FREE. Sales are decided per age class by the
# solver, with no FIFO constraint anywhere in the model. If oldest-first
# issuing is optimal, the solver has to discover it. It does.
#
# Solved with HiGHS. The C++ sibling model solves the identical formulation
# through a different solver stack, and the exact stochastic DP solves the
# same instance by backward recursion. All three must agree.
#

using JuMP
using HiGHS
using JSON3

const RESULTS = normpath(joinpath(@__DIR__, "..", "..", "results"))

inst = JSON3.read(read(joinpath(RESULTS, "instance.json"), String))

const M     = inst.shelf_life
const T     = inst.horizon
const QMAX  = inst.order_cap
const R     = inst.price
const C     = inst.purchase
const K     = inst.setup
const H     = inst.holding
const P     = inst.shortage
const W     = inst.wastage
const X0    = collect(inst.initial_stock)
const SUP   = [[(Int(p[1]), Float64(p[2])) for p in day] for day in inst.demand_support]

# ---------------------------------------------------------------- build tree

struct Node
    stage::Int          # 0 = root, 1..T = after that day's demand is known
    parent::Int         # 0 for root
    demand::Int         # demand realised at this node (-1 at root)
    prob::Float64       # unconditional probability of reaching this node
end

function build_tree()
    nodes = [Node(0, 0, -1, 1.0)]
    frontier = [1]
    for t in 1:T
        nxt = Int[]
        for parent in frontier
            for (d, pr) in SUP[t]
                push!(nodes, Node(t, parent, d, nodes[parent].prob * pr))
                push!(nxt, length(nodes))
            end
        end
        frontier = nxt
    end
    return nodes
end

nodes = build_tree()
N = length(nodes)
decision_nodes = [n for n in 1:N if nodes[n].stage < T]   # nodes that place an order
outcome_nodes  = [n for n in 1:N if nodes[n].stage >= 1]  # nodes with a demand

println("scenario tree : $N nodes, $(length(decision_nodes)) order decisions, " *
        "$(2^T) scenarios")

# --------------------------------------------------------------- build model

model = Model(HiGHS.Optimizer)
set_silent(model)

# order placed AT a decision node, delivered on the following day
@variable(model, 0 <= q[decision_nodes] <= QMAX, Int)

# setup binary: 1 iff an order is placed at that node. This is what makes the
# model a fixed-charge MIP rather than a pure integer transportation problem,
# and it is the reason replenishment is lumpy enough for stock to expire.
@variable(model, z[decision_nodes], Bin)

# Tightened linking bound. The generic big-M here is QMAX, but no order can
# usefully exceed the maximum total demand still reachable from that node, so
# the coefficient is shrunk to the smaller of the two. A tighter big-M gives a
# stronger LP relaxation and a much smaller branch-and-bound tree.
maxdem_from = zeros(Int, T + 1)
for t in T:-1:1
    maxdem_from[t] = maxdem_from[t + 1] + maximum(d for (d, _) in SUP[t])
end
for n in decision_nodes
    bound = min(QMAX, maxdem_from[nodes[n].stage + 1])
    @constraint(model, q[n] <= bound * z[n])
end

# per outcome node: stock available by age, sales by age, leftovers
@variable(model, avail[outcome_nodes, 1:M] >= 0, Int)
@variable(model, sales[outcome_nodes, 1:M] >= 0, Int)
@variable(model, endinv[outcome_nodes, 1:M] >= 0, Int)
@variable(model, lost[outcome_nodes] >= 0, Int)
@variable(model, waste[outcome_nodes] >= 0, Int)

for n in outcome_nodes
    nd = nodes[n]
    par = nd.parent

    # ---- age dynamics: what is on the shelf this morning
    for a in 1:M
        if a == 1
            # age-1 stock is exactly today's arriving order
            @constraint(model, avail[n, 1] == q[par])
        elseif nd.stage == 1
            # first day: the given initial stock, already stated by age.
            # X0 is indexed by age directly, so no shift here -- the ageing
            # step happens at the END of each day, not before day 1.
            @constraint(model, avail[n, a] == X0[a])
        else
            # age a today is what survived unsold at age a-1 yesterday
            @constraint(model, avail[n, a] == endinv[par, a - 1])
        end
    end

    # ---- issuing: free choice of age class, capped by stock and by demand
    for a in 1:M
        @constraint(model, sales[n, a] <= avail[n, a])
    end
    @constraint(model, sum(sales[n, a] for a in 1:M) + lost[n] == nd.demand)

    # ---- leftovers: age M cannot be carried, it is scrapped
    for a in 1:(M - 1)
        @constraint(model, endinv[n, a] == avail[n, a] - sales[n, a])
    end
    @constraint(model, endinv[n, M] == 0)
    @constraint(model, waste[n] == avail[n, M] - sales[n, M])
end

# ------------------------------------------------------------------ objective
# Purchase cost is charged at the child nodes: the children of a decision node
# have probabilities summing to that node's probability, so this is exactly
# prob(parent) * C * q(parent), with no double counting.

@objective(model, Max,
    sum(nodes[n].prob * (
            R * sum(sales[n, a] for a in 1:M)
          - C * q[nodes[n].parent]
          - K * z[nodes[n].parent]
          - H * sum(endinv[n, a] for a in 1:(M - 1))
          - P * lost[n]
          - W * waste[n]
        ) for n in outcome_nodes)
)

println("variables     : $(num_variables(model))")
println("constraints   : $(sum(num_constraints(model, F, S)
                               for (F, S) in list_of_constraint_types(model)))")

# ------------------------------------------------------------- warm start
# Load the exact DP policy as an incumbent so branch-and-bound spends its
# time proving optimality rather than searching for the optimum.
warmfile = joinpath(RESULTS, "dp_policy_tree.json")
if isfile(warmfile)
    warm = JSON3.read(read(warmfile, String))
    wq = collect(warm.orders_by_decision_node)
    if length(wq) == length(decision_nodes)
        for (k, n) in enumerate(decision_nodes)
            set_start_value(q[n], wq[k])
            set_start_value(z[n], wq[k] > 0 ? 1 : 0)
        end
        println("warm start    : loaded DP incumbent (", warm.dp_optimal, ")")
    end
end

set_optimizer_attribute(model, "mip_rel_gap", 0.0)
set_optimizer_attribute(model, "threads", 2)

elapsed = @elapsed optimize!(model)
@assert termination_status(model) == MOI.OPTIMAL "MIP did not solve to optimality"

obj = objective_value(model)
root_order = value(q[1])

# --------------------------------------- did free issuing choose oldest-first?
# For each node, check no younger unit was sold while an older unit sat unsold.
function count_fifo_violations()
    v = 0
    for n in outcome_nodes
        for a in 1:(M - 1)          # a is the younger age class
            value(sales[n, a]) > 0.5 || continue
            for b in (a + 1):M      # b is strictly older
                leftover_b = b == M ? value(waste[n]) : value(endinv[n, b])
                if leftover_b > 0.5
                    v += 1          # sold young while older stock went unsold
                end
            end
        end
    end
    return v
end

fifo_violations = count_fifo_violations()

# --------------------------------------------------- expected cost components
exp_rev   = sum(nodes[n].prob * R * sum(value(sales[n, a]) for a in 1:M) for n in outcome_nodes)
exp_buy   = sum(nodes[n].prob * C * value(q[nodes[n].parent]) for n in outcome_nodes)
exp_setup = sum(nodes[n].prob * K * value(z[nodes[n].parent]) for n in outcome_nodes)
exp_orders = sum(nodes[n].prob * value(z[nodes[n].parent]) for n in outcome_nodes)
exp_hold  = sum(nodes[n].prob * H * sum(value(endinv[n, a]) for a in 1:(M - 1)) for n in outcome_nodes)
exp_short = sum(nodes[n].prob * P * value(lost[n]) for n in outcome_nodes)
exp_waste = sum(nodes[n].prob * W * value(waste[n]) for n in outcome_nodes)
exp_units_wasted = sum(nodes[n].prob * value(waste[n]) for n in outcome_nodes)
exp_units_lost   = sum(nodes[n].prob * value(lost[n]) for n in outcome_nodes)
exp_units_sold   = sum(nodes[n].prob * sum(value(sales[n, a]) for a in 1:M) for n in outcome_nodes)

result = Dict(
    "method" => "scenario-tree-MIP",
    "optimal_expected_profit" => round(obj, digits = 6),
    "first_order" => round(Int, root_order),
    "nodes" => N,
    "scenarios" => 2^T,
    "order_decisions" => length(decision_nodes),
    "variables" => num_variables(model),
    "solve_seconds" => round(elapsed, digits = 3),
    "fifo_violations_under_free_issuing" => fifo_violations,
    "expected_revenue" => round(exp_rev, digits = 4),
    "expected_purchase" => round(exp_buy, digits = 4),
    "expected_setup" => round(exp_setup, digits = 4),
    "expected_order_days" => round(exp_orders, digits = 4),
    "expected_holding" => round(exp_hold, digits = 4),
    "expected_shortage" => round(exp_short, digits = 4),
    "expected_wastage" => round(exp_waste, digits = 4),
    "expected_units_wasted" => round(exp_units_wasted, digits = 4),
    "expected_units_lost" => round(exp_units_lost, digits = 4),
    "expected_units_sold" => round(exp_units_sold, digits = 4),
)

open(joinpath(RESULTS, "mip_julia.json"), "w") do io
    JSON3.pretty(io, result)
end

println("-"^58)
println("scenario-tree MIP optimum : ", round(obj, digits = 6))
println("first-day order           : ", round(Int, root_order))
println("solve time                : ", round(elapsed, digits = 3), " s")
println("FIFO violations (free)    : ", fifo_violations)
println("expected units wasted     : ", round(exp_units_wasted, digits = 4))
println("expected units short      : ", round(exp_units_lost, digits = 4))
println("expected order days       : ", round(exp_orders, digits = 4))
