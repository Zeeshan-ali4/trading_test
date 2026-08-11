"""Point-in-time technical features computed independently for each ticker."""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_technical_features(
    bars: pd.DataFrame, settings: dict[str, object] | None = None
) -> pd.DataFrame:
    settings = settings or {}
    fast_momentum = int(settings.get("momentum_fast_days", 5))
    slow_momentum = int(settings.get("momentum_slow_days", 20))
    ma_fast = int(settings.get("ma_fast_days", 20))
    ma_slow = int(settings.get("ma_slow_days", 50))
    rsi_window = int(settings.get("rsi_days", 14))
    atr_window = int(settings.get("atr_days", 14))
    vol_window = int(settings.get("volatility_days", 20))
    volume_window = int(settings.get("volume_z_days", 20))
    result = bars.sort_values(["ticker", "date"]).copy()
    grouped = result.groupby("ticker", group_keys=False)
    result["return_1"] = grouped["close"].pct_change(fill_method=None)
    result["momentum_5"] = grouped["close"].pct_change(fast_momentum, fill_method=None)
    result["momentum_20"] = grouped["close"].pct_change(slow_momentum, fill_method=None)
    result["ma_20"] = grouped["close"].transform(
        lambda x: x.rolling(ma_fast, min_periods=ma_fast).mean()
    )
    result["ma_50"] = grouped["close"].transform(
        lambda x: x.rolling(ma_slow, min_periods=ma_slow).mean()
    )
    delta = grouped["close"].diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    average_gain = gain.groupby(result["ticker"]).transform(
        lambda x: x.rolling(rsi_window, min_periods=rsi_window).mean()
    )
    average_loss = loss.groupby(result["ticker"]).transform(
        lambda x: x.rolling(rsi_window, min_periods=rsi_window).mean()
    )
    result["rsi_14"] = 100 - 100 / (1 + average_gain / average_loss.replace(0, np.nan))
    previous_close = grouped["close"].shift(1)
    true_range = pd.concat(
        [
            result["high"] - result["low"],
            (result["high"] - previous_close).abs(),
            (result["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    result["atr_14"] = true_range.groupby(result["ticker"]).transform(
        lambda x: x.rolling(atr_window, min_periods=atr_window).mean()
    )
    result["volatility_20"] = (
        result["return_1"]
        .groupby(result["ticker"])
        .transform(lambda x: x.rolling(vol_window, min_periods=vol_window).std())
    )
    volume_mean = grouped["volume"].transform(
        lambda x: x.rolling(volume_window, min_periods=volume_window).mean()
    )
    volume_std = grouped["volume"].transform(
        lambda x: x.rolling(volume_window, min_periods=volume_window).std()
    )
    result["volume_z_20"] = (result["volume"] - volume_mean) / volume_std.replace(0, np.nan)
    return result
