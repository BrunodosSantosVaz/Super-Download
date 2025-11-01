"""GTK UI components for Super Download."""

from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk, Pango

if TYPE_CHECKING:  # pragma: no cover
    from ..app import SuperDownloadApplication
    from ..download_manager import DownloadManager, DownloadRecord
else:
    SuperDownloadApplication = "SuperDownloadApplication"
    DownloadManager = "DownloadManager"
    DownloadRecord = "DownloadRecord"


class MainWindow(Adw.ApplicationWindow):
    """Primary window listing downloads and actions."""

    def __init__(self, app: SuperDownloadApplication) -> None:
        super().__init__(application=app)
        self.set_title("Super Download")
        self.set_default_size(960, 600)
        self.set_icon_name("com.superdownload")

        self._download_rows: dict[str, Gtk.ListBoxRow] = {}

        # Conectar handler para interceptar o fechamento da janela
        self.connect("close-request", self._on_close_request)

        self._toolbar_view = Adw.ToolbarView()
        self.set_content(self._toolbar_view)

        self._header_bar = Adw.HeaderBar()
        self._toolbar_view.add_top_bar(self._header_bar)

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Adicionar download por URL...")
        self._search_entry.connect("activate", self._on_add_url)

        self._header_bar.pack_start(self._search_entry)

        # ScrolledWindow que ocupa todo o espaço disponível
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        scroller.set_hexpand(True)

        self._list_box = Gtk.ListBox()
        self._list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scroller.set_child(self._list_box)

        self._info_label = Gtk.Label(label="Nenhum download no momento.")
        self._info_label.set_margin_top(24)
        self._info_label.get_style_context().add_class("dim-label")
        self._info_label.set_xalign(0.5)
        self._info_label.set_vexpand(True)
        self._info_label.set_valign(Gtk.Align.CENTER)

        # Stack para alternar entre lista e mensagem vazia
        self._stack = Gtk.Stack()
        self._stack.add_named(scroller, "list")
        self._stack.add_named(self._info_label, "empty")
        self._stack.set_visible_child_name("empty")

        self._toolbar_view.set_content(self._stack)

        # Inscreve-se para atualizações automáticas da fila
        app.download_manager.subscribe(self._on_queue_change)

    # ------------------------------------------------------------------
    @classmethod
    def new(cls, app: SuperDownloadApplication) -> "MainWindow":
        return cls(app)

    def refresh_queue(self) -> None:
        manager: DownloadManager = self.get_application().download_manager  # type: ignore[assignment]
        self._on_queue_change(manager.snapshot())

    def ask_quit_confirmation(self) -> None:
        dialog = Adw.MessageDialog.new(
            self,
            "Downloads em andamento",
            "Existem downloads ativos. Deseja encerrar mesmo assim?",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("quit", "Encerrar")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_quit_response)
        dialog.present()

    # ------------------------------------------------------------------
    def _update_rows(self, records: Iterable[DownloadRecord]) -> None:
        seen = set()
        for record in records:
            row = self._download_rows.get(record.gid)
            if row is None:
                row = self._create_row(record)
                self._download_rows[record.gid] = row
                self._list_box.append(row)
            self._update_row_content(row, record)
            seen.add(record.gid)

        # Remove rows no longer present
        for gid in list(self._download_rows.keys()):
            if gid not in seen:
                row = self._download_rows.pop(gid)
                self._list_box.remove(row)

    def _create_row(self, record: DownloadRecord) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()

        # Container principal horizontal
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        main_box.set_margin_top(8)
        main_box.set_margin_bottom(8)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        row.set_child(main_box)

        # Seção de informações (esquerda - expande)
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_hexpand(True)

        # Nome do arquivo
        name_label = Gtk.Label(xalign=0)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        info_box.append(name_label)

        # Status e velocidade
        status_label = Gtk.Label(xalign=0)
        status_label.get_style_context().add_class("dim-label")
        info_box.append(status_label)

        # Barra de progresso
        progress = Gtk.ProgressBar()
        progress.set_hexpand(True)
        progress.set_show_text(False)
        info_box.append(progress)

        main_box.append(info_box)

        # Seção de botões (direita - compactos)
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        action_box.set_valign(Gtk.Align.CENTER)

        # Botões com ícones apenas
        pause_button = Gtk.Button(icon_name="media-playback-pause-symbolic")
        pause_button.set_tooltip_text("Pausar")
        pause_button.connect("clicked", self._on_pause_clicked, record.gid)

        resume_button = Gtk.Button(icon_name="media-playback-start-symbolic")
        resume_button.set_tooltip_text("Retomar")
        resume_button.connect("clicked", self._on_resume_clicked, record.gid)

        cancel_button = Gtk.Button(icon_name="process-stop-symbolic")
        cancel_button.set_tooltip_text("Cancelar download")
        cancel_button.connect("clicked", self._on_cancel_clicked, record.gid)

        open_button = Gtk.Button(icon_name="folder-open-symbolic")
        open_button.set_tooltip_text("Abrir pasta")
        open_button.connect("clicked", self._on_open_folder, record.gid)

        remove_button = Gtk.Button(icon_name="user-trash-symbolic")
        remove_button.set_tooltip_text("Remover da lista")
        remove_button.connect("clicked", self._on_remove_clicked, record.gid)

        for button in (pause_button, resume_button, cancel_button, open_button, remove_button):
            action_box.append(button)

        main_box.append(action_box)

        row.name_label = name_label  # type: ignore[attr-defined]
        row.status_label = status_label  # type: ignore[attr-defined]
        row.progress_bar = progress  # type: ignore[attr-defined]
        row.pause_button = pause_button  # type: ignore[attr-defined]
        row.resume_button = resume_button  # type: ignore[attr-defined]
        row.cancel_button = cancel_button  # type: ignore[attr-defined]
        row.open_button = open_button  # type: ignore[attr-defined]
        row.remove_button = remove_button  # type: ignore[attr-defined]
        return row

    def _update_row_content(self, row: Gtk.ListBoxRow, record: DownloadRecord) -> None:
        row.name_label.set_label(record.filename or record.url)  # type: ignore[attr-defined]
        status_text = f"{record.status} - {record.progress * 100:.0f}%"
        if record.speed:
            status_text += f" - {record.speed / 1024:.0f} KiB/s"
        row.status_label.set_label(status_text)  # type: ignore[attr-defined]
        row.progress_bar.set_fraction(record.progress)  # type: ignore[attr-defined]
        row.progress_bar.set_text(f"{record.progress * 100:.0f}%")

        # Mostrar/ocultar botões baseado no status
        is_active = record.status in {"active", "waiting", "queued"}
        is_paused = record.status == "paused"
        is_complete = record.status == "complete"
        is_error = record.status == "error"
        can_cancel = is_active or is_paused

        row.pause_button.set_visible(is_active)  # type: ignore[attr-defined]
        row.resume_button.set_visible(is_paused)  # type: ignore[attr-defined]
        row.cancel_button.set_visible(can_cancel)  # type: ignore[attr-defined]
        row.open_button.set_visible(is_complete)  # type: ignore[attr-defined]
        # Botão remover sempre visível para downloads completos/cancelados/com erro
        row.remove_button.set_visible(is_complete or is_error or record.status == "removed")  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    def _on_queue_change(self, records: Iterable[DownloadRecord]) -> None:
        list_records = list(records)
        self._update_rows(list_records)
        if len(list_records) == 0:
            self._stack.set_visible_child_name("empty")
        else:
            self._stack.set_visible_child_name("list")

    def _on_add_url(self, entry: Gtk.SearchEntry) -> None:
        text = entry.get_text().strip()
        if not text:
            return
        urls = [part for part in text.split() if self._looks_like_url(part)]
        if not urls:
            entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "dialog-error-symbolic")
            return
        entry.set_text("")
        entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, None)

        app: SuperDownloadApplication = self.get_application()  # type: ignore[assignment]
        GLib.idle_add(app.add_downloads, urls)

    def _on_pause_clicked(self, _button: Gtk.Button, gid: str) -> None:
        self.get_application().download_manager.pause(gid)  # type: ignore[attr-defined]

    def _on_resume_clicked(self, _button: Gtk.Button, gid: str) -> None:
        self.get_application().download_manager.resume(gid)  # type: ignore[attr-defined]

    def _on_cancel_clicked(self, _button: Gtk.Button, gid: str) -> None:
        """Cancela download no aria2 e remove da lista."""
        self.get_application().download_manager.cancel(gid)  # type: ignore[attr-defined]

    def _on_remove_clicked(self, _button: Gtk.Button, gid: str) -> None:
        """Remove download da lista sem cancelar (apenas limpa a lista)."""
        self.get_application().download_manager.remove(gid)  # type: ignore[attr-defined]

    def _on_open_folder(self, _button: Gtk.Button, gid: str) -> None:
        from pathlib import Path

        record = next(
            (item for item in self.get_application().download_manager.snapshot() if item.gid == gid),  # type: ignore[attr-defined]
            None,
        )
        if not record or not record.destination:
            return

        # Obter o diretório pai do arquivo
        file_path = Path(record.destination)
        if file_path.is_file():
            folder_path = str(file_path.parent)
        else:
            folder_path = str(file_path)

        # Abrir pasta no gerenciador de arquivos
        Gio.AppInfo.launch_default_for_uri(
            GLib.filename_to_uri(folder_path, None), None
        )

    def _on_quit_response(self, dialog: Adw.MessageDialog, response: str) -> None:
        if response == "quit":
            app: SuperDownloadApplication = self.get_application()  # type: ignore[assignment]
            # Pausar todos os downloads antes de encerrar
            app.download_manager.pause_all()
            # Encerrar aplicativo
            app.quit()
        dialog.destroy()

    def _on_close_request(self, _window: Gtk.Window) -> bool:
        """Intercepta o fechamento da janela.

        Se a bandeja estiver disponível, apenas oculta a janela.
        Retorna True para prevenir o fechamento padrão.
        """
        app: SuperDownloadApplication = self.get_application()  # type: ignore[assignment]
        if app.tray and app.tray.available:
            # Se a bandeja está disponível, apenas oculta a janela
            self.set_visible(False)
            return True  # Previne o fechamento padrão
        # Se não há bandeja, permite o fechamento normal (que acionará quit)
        return False

    @staticmethod
    def _looks_like_url(candidate: str) -> bool:
        return candidate.startswith(("http://", "https://", "ftp://", "sftp://"))
