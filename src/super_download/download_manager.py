"""Download queue orchestration on top of aria2."""

from __future__ import annotations

import logging
from typing import Callable, Dict, Iterable, List, Optional

from gi.repository import GLib

from .aria2_client import Aria2Client, Aria2DownloadStatus
from .models import DownloadRecord
from .persistence import PersistenceStore

LOGGER = logging.getLogger(__name__)


class DownloadManager:
    """Maintains download queue state and bridges to aria2."""

    POLL_INTERVAL_SECONDS = 1

    def __init__(self, persistence: Optional[PersistenceStore] = None) -> None:
        self._client = Aria2Client()
        self._downloads: Dict[str, DownloadRecord] = {}
        self._observers: List[Callable[[List[DownloadRecord]], None]] = []
        self._persistence = persistence or PersistenceStore()
        self._dirty = False

        for item in self._persistence.history:
            record = DownloadRecord.from_dict(item)
            if record.gid:
                self._downloads[record.gid] = record

        self._poll_id = GLib.timeout_add_seconds(self.POLL_INTERVAL_SECONDS, self._poll)
        self._flush_changes()

    # ------------------------------------------------------------------
    def enqueue_urls(self, urls: Iterable[str]) -> None:
        download_dir = self._persistence.config.get("default_path")
        for url in urls:
            gid = self._client.add_uri(url, download_dir=download_dir)
            record = DownloadRecord(
                gid=gid,
                url=url,
                filename=self._client.guess_filename(url),
                status="queued",
            )
            LOGGER.info("Enqueued download %s (%s)", gid, url)
            self._downloads[gid] = record
            self._dirty = True
        self._flush_changes()

    def pause_all(self) -> None:
        LOGGER.info("Pausing all downloads")
        self._client.pause_all()
        for record in self._downloads.values():
            if record.status in {"active", "waiting"}:
                record.status = "paused"
                self._dirty = True
        self._flush_changes()

    def resume_all(self) -> None:
        LOGGER.info("Resuming all downloads")
        self._client.resume_all()

    def pause(self, gid: str) -> None:
        LOGGER.debug("Pausing download %s", gid)
        self._client.pause(gid)
        if gid in self._downloads:
            self._downloads[gid].status = "paused"
            self._dirty = True
            self._flush_changes()

    def resume(self, gid: str) -> None:
        LOGGER.debug("Resuming download %s", gid)
        self._client.resume(gid)
        if gid in self._downloads:
            self._downloads[gid].status = "active"
            self._dirty = True
            self._flush_changes()

    def remove(self, gid: str) -> None:
        """Remove download da lista (não cancela no aria2)."""
        LOGGER.info("Removing download %s from manager", gid)
        if gid in self._downloads:
            self._downloads.pop(gid, None)
            self._dirty = True
            self._flush_changes()

    def cancel(self, gid: str) -> None:
        """Cancela download no aria2 e remove da lista."""
        LOGGER.info("Cancelling download %s", gid)
        self._client.remove(gid)
        self.remove(gid)

    def can_quit(self) -> bool:
        return not self.has_active_downloads

    @property
    def has_active_downloads(self) -> bool:
        return any(
            record.status in {"active", "waiting", "queued"}
            for record in self._downloads.values()
        )

    # ------------------------------------------------------------------
    def snapshot(self) -> List[DownloadRecord]:
        """Return current download state for UI consumption."""
        return sorted(
            self._downloads.values(),
            key=lambda record: record.gid,
        )

    def shutdown(self) -> None:
        if self._poll_id:
            GLib.source_remove(self._poll_id)
            self._poll_id = 0
        self._flush_changes(force=True)

    def subscribe(self, callback: Callable[[List[DownloadRecord]], None]) -> None:
        self._observers.append(callback)
        callback(self.snapshot())

    # ------------------------------------------------------------------
    def _poll(self) -> bool:
        changed = False
        for gid, record in list(self._downloads.items()):
            status = self._safe_status(gid)
            if status is None:
                continue
            if record.status != status.status:
                record.status = status.status
                changed = True
            if abs(record.progress - status.progress) > 0.0001:
                record.progress = status.progress
                changed = True
            if record.speed != status.download_speed:
                record.speed = status.download_speed
                changed = True
            destination = status.file_path or record.destination
            if record.destination != destination:
                record.destination = destination
                changed = True
        if changed:
            self._dirty = True
            self._flush_changes()
        return True

    def _safe_status(self, gid: str) -> Aria2DownloadStatus | None:
        try:
            return self._client.tell_status(gid)
        except Exception as exc:  # pragma: no cover - defensive guard
            LOGGER.exception("Failed to poll status for %s: %s", gid, exc)
            return None

    def _flush_changes(self, force: bool = False) -> None:
        if not self._dirty and not force:
            return
        self._persistence.save_downloads(self._downloads.values())
        self._notify_observers()
        self._dirty = False

    def _notify_observers(self) -> None:
        if not self._observers:
            return
        snapshot = self.snapshot()
        for callback in self._observers:
            callback(snapshot)
