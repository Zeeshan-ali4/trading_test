"""Immutable local dataset and experiment-output conventions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class DatasetMetadata:
    dataset: str
    source: str
    source_version: str
    ingested_at: str
    row_count: int | None = None


def write_dataset_metadata(dataset_path: Path, metadata: DatasetMetadata) -> Path:
    """Persist lineage next to immutable Parquet data, without modifying the data file."""
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = dataset_path.with_suffix(dataset_path.suffix + ".metadata.json")
    metadata_path.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n")
    return metadata_path


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def canonical_event_schema() -> tuple[str, ...]:
    """Fields every future alternative-data adapter must preserve."""
    return (
        "event_id",
        "source",
        "event_type",
        "entity_ids",
        "tickers",
        "region",
        "lat",
        "lon",
        "event_occurred_at",
        "source_published_at",
        "first_observed_at",
        "ingested_at",
        "effective_signal_at",
        "source_version",
        "payload",
    )
