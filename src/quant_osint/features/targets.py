"""Forward returns, stored separately from model-ready technical features."""

from __future__ import annotations

import pandas as pd


def build_targets(bars: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    result = bars[["date", "ticker", "close"]].sort_values(["ticker", "date"]).copy()
    grouped = result.groupby("ticker", group_keys=False)["close"]
    for horizon in horizons:
        result[f"forward_return_{horizon}d"] = grouped.shift(-horizon) / result["close"] - 1
    return result.drop(columns="close")
