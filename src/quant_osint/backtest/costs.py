"""Trading-cost helpers. Values are expressed in basis points."""

from __future__ import annotations


def round_trip_cost_rate(costs: dict[str, object]) -> float:
    return (
        2 * (float(costs.get("commission_bps", 0)) + float(costs.get("slippage_bps", 0))) / 10_000
    )
