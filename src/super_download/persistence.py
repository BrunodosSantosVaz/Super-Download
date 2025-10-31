"""Persistência simples em JSON para o Super Download."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

from gi.repository import GLib

from .models import DownloadRecord

LOGGER = logging.getLogger(__name__)

CONFIG_DEFAULTS: Dict[str, Any] = {
    "default_path": str(Path.home() / "Downloads"),
    "max_concurrent": 3,
    "max_global_speed": 0,
    "theme": "system",
}


class PersistenceStore:
    """Gerencia leitura/escrita dos arquivos JSON persistentes."""

    def __init__(self, base_dir: Path | None = None) -> None:
        if base_dir is None:
            state_dir = Path(GLib.get_user_state_dir()) / "superdownload"
        else:
            state_dir = Path(base_dir)
        state_dir.mkdir(parents=True, exist_ok=True)
        self._history_path = state_dir / "history.json"
        self._config_path = state_dir / "config.json"
        self.config = self._load_config()
        self.history = self._load_history()

    # ------------------------------------------------------------------
    def save_downloads(self, downloads: Iterable[DownloadRecord]) -> None:
        serializable: List[Dict[str, Any]] = []
        for record in downloads:
            data = asdict(record)
            data["progress"] = round(record.progress, 4)
            # Convert Path objects to strings for JSON serialization
            if data.get("destination") and isinstance(data["destination"], Path):
                data["destination"] = str(data["destination"])
            serializable.append(data)
        self._write_json(self._history_path, serializable)

    def save_config(self, config: Dict[str, Any]) -> None:
        merged = CONFIG_DEFAULTS | config
        self._write_json(self._config_path, merged)
        self.config = merged

    # ------------------------------------------------------------------
    def _load_config(self) -> Dict[str, Any]:
        data = self._read_json(self._config_path, {})
        return CONFIG_DEFAULTS | data

    def _load_history(self) -> List[Dict[str, Any]]:
        return self._read_json(self._history_path, [])

    def _read_json(self, path: Path, fallback: Any) -> Any:
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as handle:
                    return json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            LOGGER.warning("Falha ao ler %s: %s", path, exc)
        return fallback

    def _write_json(self, path: Path, payload: Any) -> None:
        try:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            LOGGER.error("Falha ao gravar %s: %s", path, exc)
