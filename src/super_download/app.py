"""Core Gio.Application for Super Download."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib

from .download_manager import DownloadManager
from .persistence import PersistenceStore
from .tray import TrayIndicator
from .ui.main_window import MainWindow


APP_ID = "com.superdownload"


class SuperDownloadApplication(Adw.Application):
    """Main application entrypoint managing lifecycle and IPC."""

    def __init__(self, debug: bool = False) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
            | Gio.ApplicationFlags.SEND_ENVIRONMENT,
        )
        self._window: MainWindow | None = None
        self._debug = debug
        self._persistence = PersistenceStore()
        self.download_manager = DownloadManager()
        self.tray = TrayIndicator(self)
        self.download_manager.subscribe(self._on_downloads_update)
        self._configure_logging()

    def do_startup(self) -> None:  # noqa: N802 (PyGObject naming)
        logging.debug("Super Download starting up")
        Adw.Application.do_startup(self)
        self._configure_theme()
        self._register_actions()

    def do_activate(self) -> None:  # noqa: N802
        logging.debug("Super Download activate request")
        if self._window is None:
            self._window = MainWindow.new(self)
        # Sempre mostra a janela (mesmo se estava oculta)
        self._window.set_visible(True)
        self._window.present()

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:  # noqa: N802
        """Handle subsequent invocations forwarding URLs to primary instance."""
        arguments = command_line.get_arguments()[1:]
        urls = [arg for arg in arguments if self._looks_like_url(arg)]
        logging.debug("Received command line with urls=%s", urls)

        # Sempre ativa a janela (seja com ou sem URLs)
        self.activate()

        # Se há URLs, enfileira para download
        if urls:
            GLib.idle_add(self._enqueue_from_cli, urls)

        return 0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _enqueue_from_cli(self, urls: Sequence[str]) -> bool:
        self.download_manager.enqueue_urls(urls)
        return False

    def _register_actions(self) -> None:
        def _simple_action(name: str, callback) -> None:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

        _simple_action("quit", self._on_quit)
        _simple_action("toggle-pause-all", self._on_toggle_pause_all)
        self.set_accels_for_action("app.quit", ["<Primary>q"])

    def _on_quit(self, _action: Gio.SimpleAction, _param: Gio.Variant | None) -> None:
        logging.info("Quit requested via action")
        if self.download_manager.can_quit():
            self.quit()
        else:
            # Precisa mostrar confirmação - garantir que a janela existe e está visível
            if self._window is None:
                self._window = MainWindow.new(self)
            self._window.set_visible(True)
            self._window.present()
            self._window.ask_quit_confirmation()

    def _on_toggle_pause_all(
        self, _action: Gio.SimpleAction, _param: Gio.Variant | None
    ) -> None:
        logging.info("Toggle pause/resume all downloads via action")
        if self.download_manager.has_active_downloads:
            self.download_manager.pause_all()
        else:
            self.download_manager.resume_all()

    @staticmethod
    def _looks_like_url(candidate: str) -> bool:
        return candidate.startswith(("http://", "https://", "ftp://", "sftp://"))

    def _configure_logging(self) -> None:
        log_dir = Path(GLib.get_user_state_dir()) / "superdownload"
        log_dir.mkdir(parents=True, exist_ok=True)
        logfile = log_dir / "log.txt"
        logging.basicConfig(
            level=logging.DEBUG if self._debug else logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.FileHandler(logfile, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )
        logging.debug("Logging configured with file %s", logfile)

    def _configure_theme(self) -> None:
        """Configure application theme using AdwStyleManager."""
        style_manager = Adw.StyleManager.get_default()
        theme_pref = self._persistence.config.get("theme", "system")

        if theme_pref == "dark":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        elif theme_pref == "light":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        else:  # "system" or default
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

        logging.debug("Theme configured: %s", theme_pref)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add_downloads(self, urls: Iterable[str]) -> None:
        """Add new downloads originating from UI."""
        self.download_manager.enqueue_urls(urls)

    # ------------------------------------------------------------------
    def _on_downloads_update(self, records) -> None:
        if self.tray and self.tray.available:
            self.tray.update_state(records)
