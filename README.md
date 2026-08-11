# Quant-OSINT

A reproducible, point-in-time quantitative research application. Phase 1 consumes local daily
OHLCV Parquet files and runs a technical baseline; it does not download market data.

## Quick start

```bash
uv sync --all-groups
uv run quant ingest market --config configs/market-us-liquid.toml
uv run quant features build --set technical-v1
uv run quant backtest configs/technical-v1.toml
```

Every backtest creates an immutable result bundle in `output/backtests/<run-id>/` containing the
resolved config, lineage metadata, `trades.parquet`, `equity.parquet`, `metrics.json`, and `report.html`.
Signals use the market close and enter at the following session's adjusted open.

## Commands

```text
quant ingest market --config configs/market-us-liquid.toml
quant features build --set technical-v1
quant backtest configs/technical-v1.toml
quant report latest
```

`data/raw/` contains one Parquet file per ticker with `Date`, OHLCV and `Adjusted Close`. Ingestion
normalises these into adjusted bars; feature and forward-target tables are materialised separately.
