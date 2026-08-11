import pandas as pd
import pytest

from quant_osint.backtest.engine import run_technical_backtest
from quant_osint.features.targets import build_targets
from quant_osint.features.technical import build_technical_features
from quant_osint.strategies.technical_v1 import generate_signals


def test_targets_are_forward_and_not_feature_columns() -> None:
    bars = pd.DataFrame(
        {
            "ticker": ["AAA"] * 60,
            "date": pd.date_range("2024-01-01", periods=60),
            "open": range(10, 70),
            "high": range(11, 71),
            "low": range(9, 69),
            "close": range(10, 70),
            "volume": [100] * 60,
        }
    )
    features = build_technical_features(bars)
    targets = build_targets(bars, [1, 3])
    assert "forward_return_1d" not in features.columns
    assert targets.loc[0, "forward_return_3d"] == pytest.approx(0.3)


def test_close_signal_uses_next_open_and_costs(tmp_path) -> None:
    signals = pd.DataFrame(
        {
            "ticker": ["AAA"] * 7,
            "date": pd.date_range("2024-01-01", periods=7),
            "open": [10, 12, 13, 14, 15, 16, 17],
            "close": [10, 12, 13, 14, 15, 16, 17],
            "selected": [True, False, False, False, False, False, False],
        }
    )
    metrics = run_technical_backtest(
        signals,
        {"strategy": {"holding_days": 3}, "costs": {"commission_bps": 10, "slippage_bps": 0}},
        tmp_path,
    )
    trade = pd.read_parquet(tmp_path / "trades.parquet").iloc[0]
    assert trade["entry_date"] == pd.Timestamp("2024-01-02")
    assert trade["exit_date"] == pd.Timestamp("2024-01-04")
    assert trade["gross_return"] == pytest.approx(14 / 12 - 1)
    assert trade["net_return"] < trade["gross_return"]
    assert metrics["trade_count"] == 1


def test_strategy_caps_daily_positions() -> None:
    features = pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-01")] * 3,
            "ticker": ["A", "B", "C"],
            "momentum_20": [0.3, 0.2, 0.1],
            "close": [3, 3, 3],
            "ma_20": [2, 2, 2],
            "ma_50": [1, 1, 1],
            "volume_z_20": [0, 0, 0],
        }
    )
    signals = generate_signals(features, {"max_positions": 2})
    assert signals["selected"].sum() == 2
