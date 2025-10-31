"""Integração com bandeja via Ayatana AppIndicator."""

from __future__ import annotations

import logging
from typing import Iterable

import gi

try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator3
except (ValueError, ImportError):  # pragma: no cover - fallback em ambientes sem indicador
    AppIndicator3 = None  # type: ignore[assignment]

try:
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
except (ValueError, ImportError):  # pragma: no cover - Gtk3 indisponível ou em conflito
    Gtk = None  # type: ignore[assignment]

from gi.repository import GLib

from .models import DownloadRecord

LOGGER = logging.getLogger(__name__)


class TrayIndicator:
    """Gerencia ícone e menu de bandeja."""

    def __init__(self, app) -> None:
        self._app = app
        self._indicator = None
        self._menu = None
        if AppIndicator3 is None or Gtk is None:
            LOGGER.info("Bandeja desabilitada (AppIndicator ou Gtk3 indisponível).")
            return
        self._build_indicator()

    # ------------------------------------------------------------------
    def update_state(self, downloads: Iterable[DownloadRecord]) -> None:
        if self._indicator is None:
            return
        downloads = list(downloads)
        active = sum(1 for item in downloads if item.status in {"active", "waiting"})
        waiting = sum(1 for item in downloads if item.status == "queued")
        completed = sum(1 for item in downloads if item.status == "complete")

        if active:
            summary = f"{active} ativo(s)"
        elif waiting:
            summary = f"{waiting} na fila"
        elif completed:
            summary = f"{completed} concluído(s)"
        else:
            summary = "Nenhum download"

        tooltip = f"Super Download - {summary}"
        self._indicator.set_title(tooltip)
        self._indicator.set_menu(self._menu)

    # ------------------------------------------------------------------
    @property
    def available(self) -> bool:
        return self._indicator is not None

    def _build_indicator(self) -> None:
        icon_name = "network-receive-symbolic"
        self._indicator = AppIndicator3.Indicator.new(
            "com.superdownload",
            icon_name,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self._indicator.set_icon_full(icon_name, "Super Download")

        self._menu = Gtk.Menu()
        item_open = Gtk.MenuItem(label="Abrir Super Download")
        item_open.connect("activate", self._on_open)
        self._menu.append(item_open)

        item_queue = Gtk.MenuItem(label="Ver fila")
        item_queue.connect("activate", self._on_open_queue)
        self._menu.append(item_queue)

        self._menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem(label="Encerrar")
        item_quit.connect("activate", self._on_quit)
        self._menu.append(item_quit)

        self._menu.show_all()

    def _on_open(self, _menuitem) -> None:
        GLib.idle_add(self._app.activate)

    def _on_open_queue(self, _menuitem) -> None:
        GLib.idle_add(self._app.activate)

    def _on_quit(self, _menuitem) -> None:
        GLib.idle_add(self._app.activate)
        GLib.idle_add(lambda: self._app.lookup_action("quit").activate(None))
