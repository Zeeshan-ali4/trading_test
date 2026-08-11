"""Stable backtest boundary and a transparent daily-bar implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd

from quant_osint.backtest.costs import round_trip_cost_rate
from quant_osint.backtest.metrics import calculate_metrics


class BacktestEngine(Protocol):
    """Engine contract independent from any third-party backtesting library."""

    def run(self, config: dict[str, object], output_dir: Path) -> None:
        """Execute one fully specified run and write outputs into an empty directory."""


def run_technical_backtest(
    signals: pd.DataFrame, config: dict[str, object], output_dir: Path
) -> dict[str, object]:
    """Trade next session's adjusted open and close after a fixed holding period.

    The decision is made only from the close on ``signal_date``.  An entry is
    never priced at that close, which keeps close-based indicators feasible.
    """
    holding_days = int(config.get("strategy", {}).get("holding_days", 5))  # type: ignore[union-attr]
    max_positions = int(config.get("strategy", {}).get("max_positions", 5))  # type: ignore[union-attr]
    costs = config.get("costs", {})
    cost_rate = round_trip_cost_rate(costs if isinstance(costs, dict) else {})
    candidates: list[dict[str, object]] = []
    for ticker, group in signals.sort_values("date").groupby("ticker"):
        group = group.reset_index(drop=True)
        for index in group.index[group["selected"].fillna(False)]:
            entry_index, exit_index = index + 1, index + holding_days
            if exit_index >= len(group):
                continue
            entry, exit_ = group.iloc[entry_index], group.iloc[exit_index]
            entry_price, exit_price = float(entry["open"]), float(exit_["close"])
            gross_return = exit_price / entry_price - 1
            candidates.append(
                {
                    "ticker": ticker,
                    "signal_date": group.iloc[index]["date"],
                    "entry_date": entry["date"],
                    "exit_date": exit_["date"],
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "gross_return": gross_return,
                    "cost_rate": cost_rate,
                    "net_return": (1 + gross_return) * (1 - cost_rate) - 1,
                    "notional": 1.0,
                }
            )
    candidates.sort(key=lambda row: (row["entry_date"], row["ticker"]))
    rows: list[dict[str, object]] = []
    active_exits: list[object] = []
    for candidate in candidates:
        # Entries occur at the open, so a same-day close exit cannot fund a new
        # position until the following session. This enforces the portfolio cap.
        active_exits = [
            exit_date for exit_date in active_exits if exit_date >= candidate["entry_date"]
        ]
        if len(active_exits) < max_positions:
            rows.append(candidate)
            active_exits.append(candidate["exit_date"])
    trades = pd.DataFrame(rows)
    if trades.empty:
        trades = pd.DataFrame(
            columns=[
                "ticker",
                "signal_date",
                "entry_date",
                "exit_date",
                "entry_price",
                "exit_price",
                "gross_return",
                "cost_rate",
                "net_return",
                "notional",
            ]
        )
        equity = pd.DataFrame(columns=["date", "daily_return", "equity", "active_positions"])
    else:
        daily = (
            trades.groupby("exit_date", as_index=False)["net_return"]
            .mean()
            .rename(columns={"exit_date": "date", "net_return": "daily_return"})
        )
        daily["equity"] = (1 + daily["daily_return"]).cumprod()
        daily["active_positions"] = trades.groupby("exit_date").size().to_numpy()
        equity = daily
    trades.to_parquet(output_dir / "trades.parquet", index=False)
    equity.to_parquet(output_dir / "equity.parquet", index=False)
    return (
        calculate_metrics(equity, trades)
        if not equity.empty
        else {"trade_count": 0, "cumulative_return": 0.0}
    )
