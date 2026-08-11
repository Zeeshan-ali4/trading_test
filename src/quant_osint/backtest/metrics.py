"""Metrics for daily equity curves."""

from __future__ import annotations

import math

import pandas as pd


def calculate_metrics(equity: pd.DataFrame, trades: pd.DataFrame) -> dict[str, float | int | None]:
    returns = equity["daily_return"].dropna()
    cumulative = (
        float(equity["equity"].iloc[-1] / equity["equity"].iloc[0] - 1) if len(equity) else 0.0
    )
    years = max(len(returns) / 252, 1 / 252)
    annualized = (1 + cumulative) ** (1 / years) - 1
    volatility = float(returns.std(ddof=0) * math.sqrt(252)) if len(returns) else 0.0
    sharpe = (
        float(returns.mean() / returns.std(ddof=0) * math.sqrt(252))
        if returns.std(ddof=0)
        else None
    )
    downside = returns.where(returns < 0, 0).std(ddof=0)
    sortino = float(returns.mean() / downside * math.sqrt(252)) if downside else None
    drawdown = equity["equity"] / equity["equity"].cummax() - 1
    return {
        "cumulative_return": cumulative,
        "annualized_return": annualized,
        "annualized_volatility": volatility,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": float(drawdown.min()),
        "trade_count": int(len(trades)),
        "hit_rate": float((trades["net_return"] > 0).mean()) if len(trades) else None,
        "mean_trade_return": float(trades["net_return"].mean()) if len(trades) else None,
        "turnover": float(trades["notional"].sum()) if len(trades) else 0.0,
    }
