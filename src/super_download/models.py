"""Modelos de dados compartilhados pela aplicação."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class DownloadRecord:
    gid: str
    url: str
    filename: str
    status: str = "queued"
    progress: float = 0.0
    speed: int = 0
    error: str | None = None
    destination: str | None = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadRecord":
        return cls(
            gid=data.get("gid", ""),
            url=data.get("url", ""),
            filename=data.get("filename", ""),
            status=data.get("status", "queued"),
            progress=float(data.get("progress", 0.0)),
            speed=int(data.get("speed", 0)),
            error=data.get("error"),
            destination=data.get("destination"),
            extra=data.get("extra") or {},
        )
