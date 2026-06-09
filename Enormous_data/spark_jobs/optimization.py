from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


OPTIMIZATION_CONTRACT_VERSION = "merchandising-optimization/v1"

DEFAULT_ACTIONS: list[dict[str, Any]] = [
    {"name": "feature_slot", "type": "slot", "lift": 0.18, "cost_rate": 0.0, "fixed_cost": 120.0},
    {"name": "promo_low", "type": "promo", "lift": 0.08, "cost_rate": 0.035, "fixed_cost": 20.0},
    {"name": "promo_mid", "type": "promo", "lift": 0.14, "cost_rate": 0.06, "fixed_cost": 35.0},
    {"name": "promo_high", "type": "promo", "lift": 0.22, "cost_rate": 0.1, "fixed_cost": 55.0},
]

DEFAULT_CONFIG: dict[str, Any] = {
    "candidate_limit": 100,
    "plan_limit": 30,
    "total_budget": 5000.0,
    "slot_count": 8,
    "category_cap": 12,
    "brand_cap": 6,
    "min_views": 20,
    "min_confidence": 0.03,
    "risk_lambda": 0.25,
    "time_limit_seconds": 10,
    "mip_gap": 0.02,
    "actions": DEFAULT_ACTIONS,
}


@dataclass(frozen=True)
class SolverResult:
    solver_status: str
    objective_value: float
    runtime_seconds: float
    optimality_gap: float | None
    selected: list[dict[str, Any]]
    message: str


def optimization_config(config: dict[str, Any] | None) -> dict[str, Any]:
    user_config = config or {}
    result = {**DEFAULT_CONFIG, **user_config}
    result["actions"] = user_config.get("actions") or DEFAULT_ACTIONS
    return result


def _safe_rate(numerator: float | int | None, denominator: float | int | None) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator or 0) / float(denominator), 6)


def _wilson_lower_bound(successes: float, total: float, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    phat = successes / total
    denominator = 1 + z * z / total
    centre = phat + z * z / (2 * total)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total)
    return max(0.0, (centre - margin) / denominator)


def build_optimization_candidates(
    cleaned_df: DataFrame,
    candidate_limit: int,
    global_purchase_rate: float,
) -> tuple[DataFrame, list[dict[str, Any]]]:
    view = F.col("event_type") == "view"
    cart = F.col("event_type") == "cart"
    purchase = F.col("event_type") == "purchase"
    product_sessions = (
        cleaned_df.groupBy("product_id", "brand", "category_level1", "user_session")
        .agg(
            F.min(F.when(view, F.col("event_timestamp"))).alias("first_view_ts"),
            F.min(F.when(cart, F.col("event_timestamp"))).alias("first_cart_ts"),
            F.min(F.when(purchase, F.col("event_timestamp"))).alias("first_purchase_ts"),
            F.round(F.sum(F.when(purchase, F.coalesce(F.col("price"), F.lit(0))).otherwise(F.lit(0))), 2).alias(
                "session_revenue"
            ),
            F.avg(F.when(purchase, F.col("price"))).alias("purchase_price"),
        )
        .withColumn("has_view", F.when(F.col("first_view_ts").isNotNull(), F.lit(1)).otherwise(F.lit(0)))
        .withColumn(
            "valid_cart_path",
            F.when(
                F.col("first_view_ts").isNotNull()
                & F.col("first_cart_ts").isNotNull()
                & (F.col("first_cart_ts") >= F.col("first_view_ts")),
                F.lit(1),
            ).otherwise(F.lit(0)),
        )
        .withColumn(
            "valid_purchase_path",
            F.when(
                F.col("first_view_ts").isNotNull()
                & F.col("first_purchase_ts").isNotNull()
                & (F.col("first_purchase_ts") >= F.col("first_view_ts")),
                F.lit(1),
            ).otherwise(F.lit(0)),
        )
        .withColumn(
            "valid_cart_purchase_path",
            F.when(
                F.col("first_view_ts").isNotNull()
                & F.col("first_cart_ts").isNotNull()
                & F.col("first_purchase_ts").isNotNull()
                & (F.col("first_cart_ts") >= F.col("first_view_ts"))
                & (F.col("first_purchase_ts") >= F.col("first_cart_ts")),
                F.lit(1),
            ).otherwise(F.lit(0)),
        )
    )
    candidates_df = (
        product_sessions.groupBy("product_id", "brand", "category_level1")
        .agg(
            F.sum("has_view").alias("views"),
            F.sum("valid_cart_path").alias("carts"),
            F.sum("valid_purchase_path").alias("purchases"),
            F.sum("valid_cart_purchase_path").alias("funnel_purchases"),
            F.round(F.sum("session_revenue"), 2).alias("revenue"),
            F.round(F.avg("purchase_price"), 2).alias("avg_price"),
        )
        .filter(F.col("views") > 0)
        .withColumn("view_to_cart_rate", F.round(F.col("carts") / F.col("views"), 6))
        .withColumn("view_to_purchase_rate", F.round(F.col("purchases") / F.col("views"), 6))
        .withColumn("cart_to_purchase_rate", F.round(F.col("funnel_purchases") / F.when(F.col("carts") == 0, None).otherwise(F.col("carts")), 6))
        .withColumn("revenue_per_view", F.round(F.col("revenue") / F.col("views"), 6))
        .orderBy(F.desc("revenue"), F.desc("purchases"), F.desc("views"))
        .limit(candidate_limit)
    )
    rows = candidates_df.collect()
    candidates = [_candidate_from_row(row.asDict(), global_purchase_rate) for row in rows]
    return candidates_df, candidates


def _candidate_from_row(row: dict[str, Any], global_purchase_rate: float) -> dict[str, Any]:
    views = int(row.get("views") or 0)
    purchases = int(row.get("purchases") or 0)
    revenue = float(row.get("revenue") or 0)
    avg_price = float(row.get("avg_price") or (revenue / purchases if purchases else 0))
    prior_weight = 50
    shrunk_rate = (purchases + global_purchase_rate * prior_weight) / (views + prior_weight) if views else 0
    wilson = _wilson_lower_bound(purchases, views)
    confidence = min(1.0, math.sqrt(views / 500)) * (0.5 + 0.5 * min(1.0, wilson / max(global_purchase_rate, 0.0001)))
    baseline_gmv = views * shrunk_rate * avg_price
    risk_score = round(1 - confidence, 6)
    return {
        "product_id": str(row["product_id"]),
        "brand": row.get("brand") or "unknown",
        "category_level1": row.get("category_level1") or "unknown",
        "views": views,
        "carts": int(row.get("carts") or 0),
        "purchases": purchases,
        "funnel_purchases": int(row.get("funnel_purchases") or 0),
        "revenue": round(revenue, 2),
        "avg_price": round(avg_price, 2),
        "view_to_cart_rate": float(row.get("view_to_cart_rate") or 0),
        "cart_to_purchase_rate": float(row.get("cart_to_purchase_rate") or 0),
        "view_to_purchase_rate": float(row.get("view_to_purchase_rate") or 0),
        "revenue_per_view": float(row.get("revenue_per_view") or 0),
        "purchase_rate_shrunk": round(shrunk_rate, 6),
        "wilson_purchase_rate": round(wilson, 6),
        "confidence_weight": round(confidence, 6),
        "risk_score": risk_score,
        "baseline_gmv": round(baseline_gmv, 2),
    }


def solve_merchandising_plan(candidates: list[dict[str, Any]], config: dict[str, Any]) -> SolverResult:
    try:
        return solve_with_gurobi(candidates, config)
    except Exception as exc:  # noqa: BLE001 - solver availability/license failures must degrade cleanly.
        fallback = solve_with_greedy(candidates, config)
        return SolverResult(
            solver_status="degraded_greedy",
            objective_value=fallback.objective_value,
            runtime_seconds=fallback.runtime_seconds,
            optimality_gap=None,
            selected=fallback.selected,
            message=f"gurobi unavailable or failed; used greedy fallback: {exc}",
        )


def solve_with_gurobi(candidates: list[dict[str, Any]], config: dict[str, Any]) -> SolverResult:
    started = time.perf_counter()
    import gurobipy as gp
    from gurobipy import GRB

    actions = config["actions"]
    eligible = _eligible_candidates(candidates, config)
    model = gp.Model("merchandising_optimization")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = float(config["time_limit_seconds"])
    model.Params.MIPGap = float(config["mip_gap"])

    variables = {
        (candidate["product_id"], action["name"]): model.addVar(
            vtype=GRB.BINARY,
            name=_safe_gurobi_name(f"x_{candidate['product_id']}_{action['name']}"),
        )
        for candidate in eligible
        for action in actions
    }
    for candidate in eligible:
        model.addConstr(
            gp.quicksum(variables[(candidate["product_id"], action["name"])] for action in actions) <= 1,
            name=_safe_gurobi_name(f"one_action_{candidate['product_id']}"),
        )
    model.addConstr(
        gp.quicksum(
            variables[(candidate["product_id"], action["name"])] * _action_cost(candidate, action)
            for candidate in eligible
            for action in actions
        )
        <= float(config["total_budget"]),
        name="budget",
    )
    slot_actions = [action for action in actions if action["type"] == "slot"]
    if slot_actions:
        model.addConstr(
            gp.quicksum(
                variables[(candidate["product_id"], action["name"])]
                for candidate in eligible
                for action in slot_actions
            )
            <= int(config["slot_count"]),
            name="slot_count",
        )
    for key, cap_name in (("category_level1", "category_cap"), ("brand", "brand_cap")):
        groups = sorted({candidate[key] for candidate in eligible})
        for group in groups:
            model.addConstr(
                gp.quicksum(
                    variables[(candidate["product_id"], action["name"])]
                    for candidate in eligible
                    if candidate[key] == group
                    for action in actions
                )
                <= int(config[cap_name]),
                name=_safe_gurobi_name(f"{cap_name}_{group}"),
            )

    model.setObjective(
        gp.quicksum(
            variables[(candidate["product_id"], action["name"])] * _action_value(candidate, action, config)
            for candidate in eligible
            for action in actions
        ),
        GRB.MAXIMIZE,
    )
    model.optimize()
    if model.SolCount == 0:
        raise RuntimeError(f"gurobi did not find feasible solution, status={model.Status}")
    selected = [
        _selected_action(candidate, action, config)
        for candidate in eligible
        for action in actions
        if variables[(candidate["product_id"], action["name"])].X > 0.5
    ]
    status = "optimal" if model.Status == GRB.OPTIMAL else "time_limited_feasible"
    return SolverResult(
        solver_status=status,
        objective_value=round(float(model.ObjVal), 4),
        runtime_seconds=round(time.perf_counter() - started, 3),
        optimality_gap=round(float(model.MIPGap), 6) if model.IsMIP else 0.0,
        selected=selected,
        message="gurobi milp solved",
    )


def solve_with_greedy(candidates: list[dict[str, Any]], config: dict[str, Any]) -> SolverResult:
    started = time.perf_counter()
    actions = config["actions"]
    remaining_budget = float(config["total_budget"])
    remaining_slots = int(config["slot_count"])
    category_counts: dict[str, int] = {}
    brand_counts: dict[str, int] = {}
    selected_products: set[str] = set()
    selected: list[dict[str, Any]] = []
    scored = []
    for candidate in _eligible_candidates(candidates, config):
        for action in actions:
            cost = _action_cost(candidate, action)
            value = _action_value(candidate, action, config)
            scored.append((value / max(cost, 1), value, candidate, action))
    for _, value, candidate, action in sorted(scored, key=lambda item: (item[0], item[1]), reverse=True):
        if candidate["product_id"] in selected_products:
            continue
        cost = _action_cost(candidate, action)
        if cost > remaining_budget:
            continue
        if action["type"] == "slot" and remaining_slots <= 0:
            continue
        category = candidate["category_level1"]
        brand = candidate["brand"]
        if category_counts.get(category, 0) >= int(config["category_cap"]):
            continue
        if brand_counts.get(brand, 0) >= int(config["brand_cap"]):
            continue
        selected_products.add(candidate["product_id"])
        remaining_budget -= cost
        if action["type"] == "slot":
            remaining_slots -= 1
        category_counts[category] = category_counts.get(category, 0) + 1
        brand_counts[brand] = brand_counts.get(brand, 0) + 1
        selected.append(_selected_action(candidate, action, config))
        if len(selected) >= int(config["plan_limit"]):
            break
    return SolverResult(
        solver_status="degraded_greedy",
        objective_value=round(sum(item["objective_contribution"] for item in selected), 4),
        runtime_seconds=round(time.perf_counter() - started, 3),
        optimality_gap=None,
        selected=selected,
        message="deterministic greedy fallback solved",
    )


def build_optimization_outputs(
    candidates: list[dict[str, Any]],
    solver_result: SolverResult,
    config: dict[str, Any],
) -> dict[str, Any]:
    total_cost = round(sum(row["cost"] for row in solver_result.selected), 2)
    expected_incremental_gmv = round(sum(row["expected_incremental_gmv"] for row in solver_result.selected), 2)
    expected_incremental_purchases = round(sum(row["expected_incremental_purchases"] for row in solver_result.selected), 4)
    category_allocation: dict[str, int] = {}
    action_allocation: dict[str, int] = {}
    for row in solver_result.selected:
        category_allocation[row["category_level1"]] = category_allocation.get(row["category_level1"], 0) + 1
        action_allocation[row["action"]] = action_allocation.get(row["action"], 0) + 1
    summary = {
        "contract_version": OPTIMIZATION_CONTRACT_VERSION,
        "solver_status": solver_result.solver_status,
        "message": solver_result.message,
        "objective_value": solver_result.objective_value,
        "runtime_seconds": solver_result.runtime_seconds,
        "optimality_gap": solver_result.optimality_gap,
        "candidate_count": len(candidates),
        "selected_count": len(solver_result.selected),
        "total_budget": float(config["total_budget"]),
        "used_budget": total_cost,
        "budget_utilization": _safe_rate(total_cost, float(config["total_budget"])),
        "slot_count": int(config["slot_count"]),
        "used_slots": sum(1 for row in solver_result.selected if row["action_type"] == "slot"),
        "slot_utilization": _safe_rate(sum(1 for row in solver_result.selected if row["action_type"] == "slot"), int(config["slot_count"])),
        "expected_incremental_gmv": expected_incremental_gmv,
        "expected_incremental_purchases": expected_incremental_purchases,
        "average_risk_score": round(sum(row["risk_score"] for row in solver_result.selected) / len(solver_result.selected), 6)
        if solver_result.selected
        else 0,
        "category_allocation": category_allocation,
        "action_allocation": action_allocation,
        "causal_caveat": "Observational ecommerce behavior data supports constrained opportunity ranking, not causal ROI claims.",
    }
    quality = {
        "contract_version": OPTIMIZATION_CONTRACT_VERSION,
        "candidate_count": len(candidates),
        "selected_count": len(solver_result.selected),
        "eligible_count": len(_eligible_candidates(candidates, config)),
        "solver_status": solver_result.solver_status,
        "budget_feasible": total_cost <= float(config["total_budget"]) + 1e-6,
        "slot_feasible": summary["used_slots"] <= int(config["slot_count"]),
        "category_cap": int(config["category_cap"]),
        "brand_cap": int(config["brand_cap"]),
        "min_views": int(config["min_views"]),
        "min_confidence": float(config["min_confidence"]),
    }
    return {
        "optimization_summary": summary,
        "optimization_plan": solver_result.selected,
        "optimization_candidates": candidates,
        "optimization_quality": quality,
    }


def _eligible_candidates(candidates: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        candidate
        for candidate in candidates
        if candidate["views"] >= int(config["min_views"])
        and candidate["confidence_weight"] >= float(config["min_confidence"])
        and candidate["avg_price"] > 0
    ]


def _action_cost(candidate: dict[str, Any], action: dict[str, Any]) -> float:
    return round(float(action.get("fixed_cost", 0)) + candidate["baseline_gmv"] * float(action.get("cost_rate", 0)), 4)


def _action_value(candidate: dict[str, Any], action: dict[str, Any], config: dict[str, Any]) -> float:
    incremental_gmv = candidate["baseline_gmv"] * float(action["lift"]) * candidate["confidence_weight"]
    risk_penalty = float(config["risk_lambda"]) * candidate["risk_score"] * incremental_gmv
    return round(incremental_gmv - risk_penalty, 6)


def _selected_action(candidate: dict[str, Any], action: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    cost = _action_cost(candidate, action)
    expected_incremental_gmv = round(candidate["baseline_gmv"] * float(action["lift"]) * candidate["confidence_weight"], 2)
    return {
        "product_id": candidate["product_id"],
        "brand": candidate["brand"],
        "category_level1": candidate["category_level1"],
        "action": action["name"],
        "action_type": action["type"],
        "cost": cost,
        "expected_incremental_gmv": expected_incremental_gmv,
        "expected_incremental_purchases": round(expected_incremental_gmv / candidate["avg_price"], 4) if candidate["avg_price"] else 0,
        "objective_contribution": _action_value(candidate, action, config),
        "confidence_weight": candidate["confidence_weight"],
        "risk_score": candidate["risk_score"],
        "views": candidate["views"],
        "purchases": candidate["purchases"],
        "baseline_gmv": candidate["baseline_gmv"],
        "avg_price": candidate["avg_price"],
    }


def _safe_gurobi_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value)
    return cleaned[:120]
