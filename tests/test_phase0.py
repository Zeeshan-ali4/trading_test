from pathlib import Path

from quant_osint.cli import create_run
from quant_osint.config.settings import ProjectPaths, config_hash
from quant_osint.data.storage import canonical_event_schema


def test_config_hash_is_stable() -> None:
    assert config_hash({"b": 2, "a": 1}) == config_hash({"a": 1, "b": 2})


def test_run_writes_immutable_lineage_bundle(tmp_path: Path) -> None:
    config_path = tmp_path / "example.toml"
    config_path.write_text("[data_versions]\nmarket = 'snapshot-1'\n")
    run_dir = create_run(config_path, tmp_path)
    assert (run_dir / "config.toml").read_bytes() == config_path.read_bytes()
    metadata = (run_dir / "metadata.json").read_text()
    assert '"market": "snapshot-1"' in metadata
    assert ProjectPaths(tmp_path).output_backtests in run_dir.parents


def test_canonical_event_schema_preserves_publication_timing() -> None:
    fields = canonical_event_schema()
    assert "event_occurred_at" in fields
    assert "source_published_at" in fields
    assert "effective_signal_at" in fields
