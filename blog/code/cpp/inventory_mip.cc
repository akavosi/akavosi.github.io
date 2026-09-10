// Age-tracked perishable inventory: independent MIP implementation.
//
// This solves the same deterministic-equivalent scenario-tree model as the
// sibling JuMP formulation, but builds it through a different modelling layer
// and hands it to a different solver. The point is corroboration: two
// independently written models, two solvers, and an exact stochastic DP must
// all return the same optimal expected profit, or one of them is wrong.
//
// Model recap
// -----------
//   decision nodes (stage < T)  place an order q, with setup binary z
//   outcome nodes  (stage >= 1) realise a demand and choose sales by age
//
//   avail[n][1] = q[parent(n)]                       arrivals are age 1
//   avail[n][a] = endinv[parent(n)][a-1]   (a >= 2)  yesterday's leftovers age
//   sum_a sales[n][a] + lost[n] = demand[n]
//   endinv[n][a] = avail[n][a] - sales[n][a]  (a < m)
//   waste[n]     = avail[n][m] - sales[n][m]         age-m stock is scrapped
//
// Issuing is left free: no FIFO constraint is written anywhere. Whether
// oldest-first is optimal is a question the solver answers, not one the model
// assumes.

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include "ortools/linear_solver/linear_solver.h"

namespace operations_research {

// ----------------------------------------------------------- tiny JSON reader
// The instance file is written by instance.py and has a flat, known shape, so
// a full JSON dependency would be more machinery than this needs.
namespace mini {

std::string Slurp(const std::string& path) {
  std::ifstream in(path);
  if (!in) {
    std::cerr << "cannot open " << path << "\n";
    std::exit(1);
  }
  std::stringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

double Number(const std::string& s, const std::string& key) {
  auto pos = s.find("\"" + key + "\"");
  if (pos == std::string::npos) {
    std::cerr << "missing key " << key << "\n";
    std::exit(1);
  }
  pos = s.find(':', pos) + 1;
  return std::strtod(s.c_str() + pos, nullptr);
}

// Reads a flat array of numbers, e.g. "initial_stock": [0, 0, 4, 5, 0]
std::vector<double> Array(const std::string& s, const std::string& key) {
  auto pos = s.find("\"" + key + "\"");
  if (pos == std::string::npos) {
    std::cerr << "missing key " << key << "\n";
    std::exit(1);
  }
  pos = s.find('[', pos) + 1;
  auto end = s.find(']', pos);
  std::vector<double> out;
  std::stringstream ss(s.substr(pos, end - pos));
  std::string tok;
  while (std::getline(ss, tok, ',')) out.push_back(std::strtod(tok.c_str(), nullptr));
  return out;
}

}  // namespace mini

struct Node {
  int stage;
  int parent;
  int demand;
  double prob;
};

int Main() {
  const std::string results = "../../results/";
  const std::string js = mini::Slurp(results + "instance.json");

  const int M = static_cast<int>(mini::Number(js, "shelf_life"));
  const int T = static_cast<int>(mini::Number(js, "horizon"));
  const int QMAX = static_cast<int>(mini::Number(js, "order_cap"));
  const double R = mini::Number(js, "price");
  const double C = mini::Number(js, "purchase");
  const double K = mini::Number(js, "setup");
  const double H = mini::Number(js, "holding");
  const double P = mini::Number(js, "shortage");
  const double W = mini::Number(js, "wastage");
  const std::vector<double> X0 = mini::Array(js, "initial_stock");
  const std::vector<double> DLO = mini::Array(js, "demand_low");
  const std::vector<double> DHI = mini::Array(js, "demand_high");

  // Two-point support per day, equiprobable.
  std::vector<std::vector<std::pair<int, double>>> SUP(T);
  for (int t = 0; t < T; ++t)
    SUP[t] = {{static_cast<int>(DLO[t]), 0.5}, {static_cast<int>(DHI[t]), 0.5}};

  // ------------------------------------------------------------- build tree
  std::vector<Node> nodes{{0, 0, -1, 1.0}};
  std::vector<int> frontier{0};
  for (int t = 0; t < T; ++t) {
    std::vector<int> next;
    for (int parent : frontier) {
      for (const auto& dp : SUP[t]) {
        nodes.push_back({t + 1, parent, dp.first, nodes[parent].prob * dp.second});
        next.push_back(static_cast<int>(nodes.size()) - 1);
      }
    }
    frontier = next;
  }
  const int N = static_cast<int>(nodes.size());
  int n_decision = 0;
  for (const auto& nd : nodes)
    if (nd.stage < T) ++n_decision;

  std::printf("scenario tree : %d nodes, %d order decisions, %d scenarios\n", N,
              n_decision, static_cast<int>(std::lround(std::pow(2, T))));

  // ------------------------------------------------------------ build model
  std::unique_ptr<MPSolver> solver(MPSolver::CreateSolver("SCIP"));
  if (!solver) {
    std::cerr << "SCIP backend unavailable\n";
    return 1;
  }
  const double inf = solver->infinity();

  // Tightened big-M: an order can never usefully exceed the maximum total
  // demand still reachable downstream of the node that places it.
  std::vector<int> max_dem_from(T + 2, 0);
  for (int t = T - 1; t >= 0; --t) {
    int mx = 0;
    for (const auto& dp : SUP[t]) mx = std::max(mx, dp.first);
    max_dem_from[t] = max_dem_from[t + 1] + mx;
  }

  std::vector<MPVariable*> q(N, nullptr), z(N, nullptr), lost(N, nullptr),
      waste(N, nullptr);
  std::vector<std::vector<MPVariable*>> avail(N), sales(N), endinv(N);

  for (int n = 0; n < N; ++n) {
    if (nodes[n].stage < T) {
      q[n] = solver->MakeIntVar(0, QMAX, "q" + std::to_string(n));
      z[n] = solver->MakeBoolVar("z" + std::to_string(n));
      const double bound = std::min(QMAX, max_dem_from[nodes[n].stage]);
      MPConstraint* link = solver->MakeRowConstraint(-inf, 0.0);  // q <= bound*z
      link->SetCoefficient(q[n], 1.0);
      link->SetCoefficient(z[n], -bound);
    }
    if (nodes[n].stage >= 1) {
      avail[n].resize(M);
      sales[n].resize(M);
      endinv[n].resize(M);
      for (int a = 0; a < M; ++a) {
        avail[n][a] = solver->MakeIntVar(0, inf, "");
        sales[n][a] = solver->MakeIntVar(0, inf, "");
        endinv[n][a] = solver->MakeIntVar(0, inf, "");
      }
      lost[n] = solver->MakeIntVar(0, inf, "");
      waste[n] = solver->MakeIntVar(0, inf, "");
    }
  }

  for (int n = 0; n < N; ++n) {
    if (nodes[n].stage < 1) continue;
    const Node& nd = nodes[n];
    const int par = nd.parent;

    for (int a = 0; a < M; ++a) {
      if (a == 0) {
        MPConstraint* c = solver->MakeRowConstraint(0.0, 0.0);  // avail0 = q[par]
        c->SetCoefficient(avail[n][0], 1.0);
        c->SetCoefficient(q[par], -1.0);
      } else if (nd.stage == 1) {
        // First day: the given initial stock, indexed by age directly.
        // Ageing happens at the END of a day, so there is no shift here.
        MPConstraint* c = solver->MakeRowConstraint(X0[a], X0[a]);
        c->SetCoefficient(avail[n][a], 1.0);
      } else {
        MPConstraint* c = solver->MakeRowConstraint(0.0, 0.0);
        c->SetCoefficient(avail[n][a], 1.0);
        c->SetCoefficient(endinv[par][a - 1], -1.0);
      }
    }

    for (int a = 0; a < M; ++a) {  // sales <= avail
      MPConstraint* c = solver->MakeRowConstraint(-inf, 0.0);
      c->SetCoefficient(sales[n][a], 1.0);
      c->SetCoefficient(avail[n][a], -1.0);
    }

    {  // sum sales + lost = demand
      MPConstraint* c = solver->MakeRowConstraint(nd.demand, nd.demand);
      for (int a = 0; a < M; ++a) c->SetCoefficient(sales[n][a], 1.0);
      c->SetCoefficient(lost[n], 1.0);
    }

    for (int a = 0; a < M - 1; ++a) {  // endinv = avail - sales
      MPConstraint* c = solver->MakeRowConstraint(0.0, 0.0);
      c->SetCoefficient(endinv[n][a], 1.0);
      c->SetCoefficient(avail[n][a], -1.0);
      c->SetCoefficient(sales[n][a], 1.0);
    }
    {  // age-m stock cannot be carried
      MPConstraint* c = solver->MakeRowConstraint(0.0, 0.0);
      c->SetCoefficient(endinv[n][M - 1], 1.0);
    }
    {  // waste = avail[m] - sales[m]
      MPConstraint* c = solver->MakeRowConstraint(0.0, 0.0);
      c->SetCoefficient(waste[n], 1.0);
      c->SetCoefficient(avail[n][M - 1], -1.0);
      c->SetCoefficient(sales[n][M - 1], 1.0);
    }
  }

  // -------------------------------------------------------------- objective
  MPObjective* obj = solver->MutableObjective();
  for (int n = 0; n < N; ++n) {
    if (nodes[n].stage < 1) continue;
    const double w = nodes[n].prob;
    const int par = nodes[n].parent;
    for (int a = 0; a < M; ++a) obj->SetCoefficient(sales[n][a], R * w);
    obj->SetCoefficient(q[par], obj->GetCoefficient(q[par]) - C * w);
    obj->SetCoefficient(z[par], obj->GetCoefficient(z[par]) - K * w);
    for (int a = 0; a < M - 1; ++a)
      obj->SetCoefficient(endinv[n][a], obj->GetCoefficient(endinv[n][a]) - H * w);
    obj->SetCoefficient(lost[n], -P * w);
    obj->SetCoefficient(waste[n], -W * w);
  }
  obj->SetMaximization();

  std::printf("variables     : %d\n", solver->NumVariables());
  std::printf("constraints   : %d\n", solver->NumConstraints());

  solver->SetNumThreads(1);

  const absl::Time t0 = absl::Now();
  const MPSolver::ResultStatus status = solver->Solve();
  const double secs = absl::ToDoubleSeconds(absl::Now() - t0);

  if (status != MPSolver::OPTIMAL) {
    std::cerr << "not solved to optimality, status " << status << "\n";
    return 2;
  }

  // ------------------------------------- audit: did free issuing pick FIFO?
  int fifo_violations = 0;
  for (int n = 0; n < N; ++n) {
    if (nodes[n].stage < 1) continue;
    for (int a = 0; a < M - 1; ++a) {
      if (sales[n][a]->solution_value() < 0.5) continue;
      for (int b = a + 1; b < M; ++b) {
        const double leftover = (b == M - 1) ? waste[n]->solution_value()
                                             : endinv[n][b]->solution_value();
        if (leftover > 0.5) ++fifo_violations;
      }
    }
  }

  double e_waste = 0, e_lost = 0, e_setup = 0;
  for (int n = 0; n < N; ++n) {
    if (nodes[n].stage < 1) continue;
    const double w = nodes[n].prob;
    e_waste += w * waste[n]->solution_value();
    e_lost += w * lost[n]->solution_value();
    e_setup += w * z[nodes[n].parent]->solution_value();
  }

  std::printf("----------------------------------------------------------\n");
  std::printf("OR-Tools MIP optimum      : %.6f\n", obj->Value());
  std::printf("first-day order           : %.0f\n", q[0]->solution_value());
  std::printf("solve time                : %.3f s\n", secs);
  std::printf("FIFO violations (free)    : %d\n", fifo_violations);
  std::printf("expected units wasted     : %.4f\n", e_waste);
  std::printf("expected units short      : %.4f\n", e_lost);
  std::printf("expected order days       : %.4f\n", e_setup);

  std::ofstream out(results + "mip_cpp.json");
  out.setf(std::ios::fixed);
  out.precision(6);
  out << "{\n"
      << "  \"method\": \"scenario-tree-MIP-ortools-scip\",\n"
      << "  \"optimal_expected_profit\": " << obj->Value() << ",\n"
      << "  \"first_order\": " << q[0]->solution_value() << ",\n"
      << "  \"nodes\": " << N << ",\n"
      << "  \"order_decisions\": " << n_decision << ",\n"
      << "  \"variables\": " << solver->NumVariables() << ",\n"
      << "  \"constraints\": " << solver->NumConstraints() << ",\n"
      << "  \"solve_seconds\": " << secs << ",\n"
      << "  \"fifo_violations_under_free_issuing\": " << fifo_violations << ",\n"
      << "  \"expected_units_wasted\": " << e_waste << ",\n"
      << "  \"expected_units_lost\": " << e_lost << ",\n"
      << "  \"expected_order_days\": " << e_setup << "\n"
      << "}\n";
  return 0;
}

}  // namespace operations_research

int main() { return operations_research::Main(); }
