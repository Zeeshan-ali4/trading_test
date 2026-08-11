"""Command-line interface for reproducible research operations."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from quant_osint.backtest.engine import run_technical_backtest
from quant_osint.config.settings import ProjectPaths, config_hash, load_toml
from quant_osint.data.market import load_daily_bars, raw_data_version
from quant_osint.data.storage import DatasetMetadata, utc_now, write_dataset_metadata
from quant_osint.features.targets import build_targets
from quant_osint.features.technical import build_technical_features
from quant_osint.reports.html import build_report
from quant_osint.strategies.technical_v1 import generate_signals


def project_root() -> Path:
    return Path.cwd()


def git_commit(root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def create_run(config_path: Path, root: Path) -> Path:
    config = load_toml(config_path)
    paths = ProjectPaths(root)
    paths.ensure_directories()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + config_hash(config)[:8]
    run_dir = paths.output_backtests / run_id
    run_dir.mkdir()  # Never reuse a run directory: outputs are immutable.
    (run_dir / "config.toml").write_bytes(config_path.read_bytes())
    metadata = {
        "run_id": run_id,
        "run_timestamp": utc_now(),
        "git_commit": git_commit(root),
        "config_path": str(config_path),
        "config_hash": config_hash(config),
        "input_data_versions": config.get("data_versions", {}),
        "status": "initialized",
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return run_dir


def command_run(args: argparse.Namespace) -> int:
    run_dir = create_run(Path(args.config), project_root())
    print(run_dir)
    return 0


def market_config(config: dict[str, object]) -> tuple[list[str] | None, str]:
    market = config.get("market", {})
    if not isinstance(market, dict):
        raise ValueError("[market] must be a TOML table")
    universe = market.get("universe")
    return (
        list(universe) if isinstance(universe, list) else None,
        str(market.get("raw_directory", "data/raw")),
    )


def materialize_features(config: dict[str, object], root: Path) -> Path:
    paths = ProjectPaths(root)
    paths.ensure_directories()
    tickers, relative_raw = market_config(config)
    raw_dir = root / relative_raw
    bars = load_daily_bars(raw_dir, tickers)
    features = build_technical_features(
        bars, config.get("features") if isinstance(config.get("features"), dict) else None
    )
    targets = build_targets(bars, list(config.get("experiment", {}).get("horizons", [1, 3, 5])))  # type: ignore[union-attr]
    features_path, targets_path = (
        paths.data_features / "technical-v1.parquet",
        paths.data_features / "technical-v1-targets.parquet",
    )
    features.to_parquet(features_path, index=False)
    targets.to_parquet(targets_path, index=False)
    version = raw_data_version(
        raw_dir, tickers or [path.stem for path in raw_dir.glob("*.parquet")]
    )
    write_dataset_metadata(
        features_path,
        DatasetMetadata("technical-v1", "local-parquet", version, utc_now(), len(features)),
    )
    return features_path


def command_features(args: argparse.Namespace) -> int:
    config_path = project_root() / "configs" / f"{args.set}.toml"
    if not config_path.is_file():
        raise SystemExit(f"Unknown feature set: {args.set}")
    print(materialize_features(load_toml(config_path), project_root()))
    return 0


def command_ingest(args: argparse.Namespace) -> int:
    config = load_toml(Path(args.config))
    tickers, relative_raw = market_config(config)
    bars = load_daily_bars(project_root() / relative_raw, tickers)
    destination = ProjectPaths(project_root()).data_processed / "market-daily.parquet"
    destination.parent.mkdir(parents=True, exist_ok=True)
    bars.to_parquet(destination, index=False)
    write_dataset_metadata(
        destination,
        DatasetMetadata(
            "market-daily",
            "local-parquet",
            raw_data_version(project_root() / relative_raw, tickers or []),
            utc_now(),
            len(bars),
        ),
    )
    print(destination)
    return 0


def command_backtest(args: argparse.Namespace) -> int:
    config_path, root = Path(args.config), project_root()
    config = load_toml(config_path)
    run_dir = create_run(config_path, root)
    features_path = materialize_features(config, root)
    features = pd.read_parquet(features_path)
    signals = generate_signals(
        features, config.get("strategy") if isinstance(config.get("strategy"), dict) else None
    )
    metrics = run_technical_backtest(signals, config, run_dir)
    metadata_path = run_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata.update(
        {"status": "completed", "features_path": str(features_path), "execution_time": "next_open"}
    )
    metadata["input_data_versions"] = {
        "market": raw_data_version(root / market_config(config)[1], market_config(config)[0] or [])
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    equity = pd.read_parquet(run_dir / "equity.parquet")
    trades = pd.read_parquet(run_dir / "trades.parquet")
    (run_dir / "report.html").write_text(
        build_report(metadata["run_id"], metadata, metrics, equity, trades)
    )
    print(run_dir)
    return 0


def command_report(args: argparse.Namespace) -> int:
    runs = sorted((project_root() / "output" / "backtests").glob("*"))
    if args.run_id == "latest":
        if not runs:
            raise SystemExit("No experiment runs found.")
        run_dir = runs[-1]
    else:
        run_dir = project_root() / "output" / "backtests" / args.run_id
    metadata_path = run_dir / "metadata.json"
    if not metadata_path.is_file():
        raise SystemExit(f"Unknown run: {args.run_id}")
    metadata = json.loads(metadata_path.read_text())
    report = run_dir / "report.html"
    metrics_path = run_dir / "metrics.json"
    metrics = json.loads(metrics_path.read_text()) if metrics_path.is_file() else {}
    equity_path, trades_path = run_dir / "equity.parquet", run_dir / "trades.parquet"
    equity = pd.read_parquet(equity_path) if equity_path.is_file() else pd.DataFrame()
    trades = pd.read_parquet(trades_path) if trades_path.is_file() else pd.DataFrame()
    report.write_text(build_report(metadata["run_id"], metadata, metrics, equity, trades))
    print(report)
    return 0


def phase_one_placeholder(_: argparse.Namespace) -> int:
    raise SystemExit(
        "This command is reserved for Phase 1; use 'quant run CONFIG' to validate Phase 0."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quant", description="Quant-OSINT research platform")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="create an immutable config-driven experiment bundle")
    run.add_argument("config")
    run.set_defaults(handler=command_run)
    report = subparsers.add_parser("report", help="write an HTML report for a saved experiment")
    report.add_argument("run_id", nargs="?", default="latest")
    report.set_defaults(handler=command_report)
    ingest = subparsers.add_parser("ingest", help="data ingestion (Phase 1)")
    ingest.add_argument("source", choices=["market"])
    ingest.add_argument("--config", required=True)
    ingest.set_defaults(handler=command_ingest)
    features = subparsers.add_parser("features", help="feature materialisation (Phase 1)")
    features.add_argument("action", choices=["build"])
    features.add_argument("--set", required=True)
    features.set_defaults(handler=command_features)
    backtest = subparsers.add_parser("backtest", help="backtesting (Phase 1)")
    backtest.add_argument("config")
    backtest.set_defaults(handler=command_backtest)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
