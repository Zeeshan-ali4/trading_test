"""Deliberately simple cross-sectional long-only technical baseline."""

from __future__ import annotations

import pandas as pd


def generate_signals(
    features: pd.DataFrame, settings: dict[str, object] | None = None
) -> pd.DataFrame:
    settings = settings or {}
    max_positions = int(settings.get("max_positions", 5))
    min_momentum = float(settings.get("min_momentum_20", 0.0))
    min_volume_z = float(settings.get("min_volume_z", -10.0))
    result = features.copy()
    eligible = (
        result["momentum_20"].gt(min_momentum)
        & result["close"].gt(result["ma_20"])
        & result["ma_20"].gt(result["ma_50"])
        & result["volume_z_20"].gt(min_volume_z)
    )
    result["signal"] = eligible
    result["rank"] = (
        result["momentum_20"]
        .where(eligible)
        .groupby(result["date"])
        .rank(ascending=False, method="first")
    )
    result["selected"] = result["rank"].le(max_positions)
    return result
