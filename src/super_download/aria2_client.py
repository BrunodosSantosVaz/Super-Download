"""Thin wrapper around aria2 RPC using aria2p when available."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlparse
from uuid import uuid4

try:
    import aria2p
except ImportError:  # pragma: no cover - aria2p optional at runtime
    aria2p = None  # type: ignore[assignment]


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Aria2DownloadStatus:
    gid: str
    status: str
    progress: float
    download_speed: int
    file_path: str


class Aria2Client:
    """Facade for communicating with aria2 daemon via JSON-RPC."""

    def __init__(
        self,
        host: str = "http://localhost",
        port: int = 6800,
        secret: str | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._secret = secret
        self._api: Optional["aria2p.API"] = None

    # ------------------------------------------------------------------
    def add_uri(self, url: str, options: Optional[dict] = None, download_dir: Optional[str] = None) -> tuple[str, str]:
        """Adiciona URI para download.

        Returns:
            Tupla (gid, filename) onde filename é o nome real que será usado (incluindo renomeações).
        """
        api = self._get_api()
        filename = self.guess_filename(url)

        if api is None:
            gid = _mock_gid()
            LOGGER.warning(
                "aria2p is not available; using mock download gid=%s for %s", gid, url
            )
            return gid, filename

        # Preparar opções com nome de arquivo único se necessário
        opts = options or {}
        if download_dir:
            opts["dir"] = download_dir
            # Gerar nome único se arquivo já existir
            unique_filename = self._get_unique_filename(download_dir, filename)
            if unique_filename != filename:
                opts["out"] = unique_filename
                filename = unique_filename  # Usar o nome único
                LOGGER.info("File exists, using unique name: %s", unique_filename)

        download = api.add_uris([url], options=opts)
        LOGGER.info("Queued download %s via aria2", download.gid)
        return download.gid, filename

    def tell_status(self, gid: str) -> Aria2DownloadStatus:
        api = self._get_api()
        if api is None:
            return Aria2DownloadStatus(
                gid=gid,
                status="mock",
                progress=0.0,
                download_speed=0,
                file_path="",
            )
        download = api.get_download(gid)
        completed = int(download.completed_length or 0)
        total = int(download.total_length or 1)
        progress = min(completed / total, 1.0) if total > 0 else 0.0
        return Aria2DownloadStatus(
            gid=download.gid,
            status=download.status,
            progress=progress,
            download_speed=download.download_speed,
            file_path=download.files[0].path if download.files else "",
        )

    def list_active(self) -> Iterable[Aria2DownloadStatus]:
        api = self._get_api()
        if api is None:
            return []
        for download in api.get_downloads():
            yield self.tell_status(download.gid)

    def pause(self, gid: str) -> None:
        api = self._get_api()
        if api is None:
            return
        try:
            download = api.get_download(gid)
            download.pause()
        except Exception as exc:
            LOGGER.warning("Failed to pause download %s: %s", gid, exc)

    def resume(self, gid: str) -> None:
        api = self._get_api()
        if api is None:
            return
        try:
            download = api.get_download(gid)
            download.resume()
        except Exception as exc:
            LOGGER.warning("Failed to resume download %s: %s", gid, exc)

    def pause_all(self) -> None:
        api = self._get_api()
        if api is None:
            return
        api.pause_all()

    def resume_all(self) -> None:
        api = self._get_api()
        if api is None:
            return
        api.resume_all()

    def remove(self, gid: str) -> None:
        """Remove download from aria2 (cancela se estiver ativo)."""
        api = self._get_api()
        if api is None:
            return
        try:
            api.remove([gid], force=True)
            LOGGER.info("Removed download %s from aria2", gid)
        except Exception as exc:
            LOGGER.warning("Failed to remove download %s: %s", gid, exc)

    @staticmethod
    def guess_filename(url: str) -> str:
        return urlparse(url).path.rsplit("/", 1)[-1] or "download"

    @staticmethod
    def _get_unique_filename(directory: str, filename: str) -> str:
        """Gera nome único para arquivo, adicionando (1), (2), etc. se necessário."""
        base_path = Path(directory)
        file_path = base_path / filename

        if not file_path.exists():
            return filename

        # Separar nome e extensão
        if "." in filename:
            name_parts = filename.rsplit(".", 1)
            name = name_parts[0]
            ext = f".{name_parts[1]}"
        else:
            name = filename
            ext = ""

        # Tentar (1), (2), (3), etc.
        counter = 1
        while True:
            new_filename = f"{name}({counter}){ext}"
            new_path = base_path / new_filename
            if not new_path.exists():
                return new_filename
            counter += 1
            if counter > 1000:  # Proteção contra loop infinito
                LOGGER.warning("Could not find unique filename after 1000 attempts")
                return filename

    # ------------------------------------------------------------------
    def _get_api(self) -> Optional["aria2p.API"]:
        if aria2p is None:
            return None
        if self._api:
            return self._api
        client = aria2p.Client(
            host=self._host,
            port=self._port,
            secret=self._secret,
        )
        self._api = aria2p.API(client)
        return self._api


def _mock_gid() -> str:
    return f"mock-{uuid4().hex}"
