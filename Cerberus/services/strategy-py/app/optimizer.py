from __future__ import annotations

from typing import Any

import gurobipy as gp
from gurobipy import GRB

from app.config import settings
from app.schemas import OptimizeRequest, OptimizeResponse


def _license_env() -> dict[str, Any]:
    env: dict[str, Any] = {}
    if settings.grb_licenseid:
        env["LICENSEID"] = int(settings.grb_licenseid)
    if settings.grb_wlsaccessid:
        env["WLSACCESSID"] = settings.grb_wlsaccessid
    if settings.grb_wlssecret:
        env["WLSSECRET"] = settings.grb_wlssecret
    return env


def optimize_portfolio(req: OptimizeRequest) -> OptimizeResponse:
    n_assets = len(req.asset_names)
    if n_assets == 0:
        raise ValueError("asset_names cannot be empty")
    if len(req.expected_returns) != n_assets:
        raise ValueError("expected_returns length mismatch")
    if len(req.covariance) != n_assets or any(len(row) != n_assets for row in req.covariance):
        raise ValueError("covariance shape mismatch")

    params = _license_env()
    env = gp.Env(params=params) if params else gp.Env()

    with gp.Model(env=env) as model:
        w = model.addVars(n_assets, lb=0.0, ub=1.0, name="w")

        return_expr = gp.quicksum(req.expected_returns[i] * w[i] for i in range(n_assets))
        risk_expr = gp.quicksum(
            req.covariance[i][j] * w[i] * w[j] for i in range(n_assets) for j in range(n_assets)
        )

        model.addConstr(gp.quicksum(w[i] for i in range(n_assets)) == 1.0, name="budget")
        model.setObjective(return_expr - req.risk_aversion * risk_expr, GRB.MAXIMIZE)
        model.optimize()

        if model.status != GRB.OPTIMAL:
            raise RuntimeError(f"optimization failed with status={model.status}")

        weights = {req.asset_names[i]: float(w[i].X) for i in range(n_assets)}
        return OptimizeResponse(objective=float(model.objVal), weights=weights)
