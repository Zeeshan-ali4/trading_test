"""Daily market-data ingestion and normalisation for local Parquet snapshots."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {"Date", "Open", "High", "Low", "Close", "Volume", "Adjusted Close"}


def raw_data_version(raw_dir: Path, tickers: list[str]) -> str:
    """Hash filenames and contents so every run identifies its exact input snapshot."""
    digest = hashlib.sha256()
    for ticker in sorted(tickers):
        path = raw_dir / f"{ticker}.parquet"
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def load_daily_bars(raw_dir: Path, tickers: list[str] | None = None) -> pd.DataFrame:
    """Load source files into a canonical, adjusted daily OHLCV frame.

    Raw close is retained for lineage.  OHLC prices are adjusted by the same
    close adjustment factor, making returns continuous across splits/dividends.
    """
    paths = (
        sorted(raw_dir.glob("*.parquet"))
        if tickers is None
        else [raw_dir / f"{t}.parquet" for t in tickers]
    )
    if not paths:
        raise ValueError(f"No Parquet files found in {raw_dir}")
    frames: list[pd.DataFrame] = []
    for path in paths:
        if not path.is_file():
            raise ValueError(f"Missing market data file: {path}")
        source = pd.read_parquet(path)
        missing = REQUIRED_COLUMNS - set(source.columns)
        if missing:
            raise ValueError(f"{path} is missing columns: {sorted(missing)}")
        frame = source.copy()
        frame["date"] = pd.to_datetime(frame["Date"], utc=True).dt.tz_convert(None).dt.normalize()
        factor = frame["Adjusted Close"] / frame["Close"]
        for source_name, destination in (
            ("Open", "open"),
            ("High", "high"),
            ("Low", "low"),
            ("Close", "close"),
        ):
            frame[destination] = frame[source_name].astype(float) * factor
        frame["volume"] = frame["Volume"].astype(float)
        frame["ticker"] = path.stem.upper()
        frames.append(frame[["date", "ticker", "open", "high", "low", "close", "volume"]])
    bars = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "ticker"])
    return bars.sort_values(["ticker", "date"], ignore_index=True)
