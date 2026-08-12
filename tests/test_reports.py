import pandas as pd

from quant_osint.reports.html import build_report


def test_html_report_embeds_the_core_charts() -> None:
    equity = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3),
            "daily_return": [0.0, 0.1, -0.05],
            "equity": [1.0, 1.1, 1.045],
        }
    )
    trades = pd.DataFrame({"net_return": [0.1, -0.05, 0.02]})
    report = build_report("run-1", {}, {"trade_count": 3}, equity, trades)
    assert "id='equity-chart'" in report
    assert "id='drawdown-chart'" in report
    assert "id='monthly-chart'" in report
    assert "id='trade-chart'" in report
    assert "const label=element('text'" in report
    assert ".append(element('text'" not in report
