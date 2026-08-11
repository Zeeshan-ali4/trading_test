"""Config and filesystem settings for deterministic research runs."""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def data_raw(self) -> Path:
        return self.root / "data" / "raw"

    @property
    def data_processed(self) -> Path:
        return self.root / "data" / "processed"

    @property
    def data_features(self) -> Path:
        return self.root / "data" / "features"

    @property
    def output_backtests(self) -> Path:
        return self.root / "output" / "backtests"

    @property
    def output_reports(self) -> Path:
        return self.root / "output" / "reports"

    def ensure_directories(self) -> None:
        for directory in (
            self.data_raw,
            self.data_processed,
            self.data_features,
            self.output_backtests,
            self.output_reports,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML experiment configuration with a useful error at the boundary."""
    with path.open("rb") as config_file:
        return tomllib.load(config_file)


def config_hash(config: dict[str, Any]) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
