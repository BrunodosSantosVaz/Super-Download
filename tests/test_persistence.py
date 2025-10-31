from __future__ import annotations

from pathlib import Path

from super_download.models import DownloadRecord
from super_download.persistence import CONFIG_DEFAULTS, PersistenceStore


def test_persistence_roundtrip(tmp_path: Path) -> None:
    store = PersistenceStore(base_dir=tmp_path)
    record = DownloadRecord(
        gid="test-gid",
        url="https://exemplo.com/arquivo.zip",
        filename="arquivo.zip",
        status="complete",
        progress=1.0,
    )

    store.save_downloads([record])

    reloaded = PersistenceStore(base_dir=tmp_path)
    assert reloaded.history
    entry = reloaded.history[0]
    assert entry["gid"] == record.gid
    assert entry["status"] == "complete"
    assert entry["filename"] == record.filename


def test_config_defaults_are_merged(tmp_path: Path) -> None:
    store = PersistenceStore(base_dir=tmp_path)
    custom = {"max_concurrent": 5}
    store.save_config(custom)

    reloaded = PersistenceStore(base_dir=tmp_path)
    assert reloaded.config["max_concurrent"] == 5
    for key, value in CONFIG_DEFAULTS.items():
        assert key in reloaded.config
        if key not in custom:
            assert reloaded.config[key] == value
