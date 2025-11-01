"""GTK UI components for Super Download."""

from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk, Pango, Gdk

if TYPE_CHECKING:  # pragma: no cover
    from ..app import SuperDownloadApplication
    from ..download_manager import DownloadManager, DownloadRecord
else:
    SuperDownloadApplication = "SuperDownloadApplication"
    DownloadManager = "DownloadManager"
    DownloadRecord = "DownloadRecord"


_STYLE_PROVIDER: Gtk.CssProvider | None = None


def _ensure_styles_loaded() -> None:
    """Register lightweight CSS tweaks shared across window widgets."""
    global _STYLE_PROVIDER
    if _STYLE_PROVIDER is not None:
        return

    css = """
    .super-download-search {
        min-height: 44px;
        border-radius: 12px;
        padding-left: 12px;
        padding-right: 12px;
    }

    .super-download-row {
        padding: 12px;
        border-radius: 14px;
    }

    .super-download-empty {
        font-size: 1.05em;
    }
    """

    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode("utf-8"))

    display = Gdk.Display.get_default()
    if display is not None:
        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
    _STYLE_PROVIDER = provider


class MainWindow(Adw.ApplicationWindow):
    """Primary window listing downloads and actions."""

    def __init__(self, app: SuperDownloadApplication) -> None:
        super().__init__(application=app)
        self.set_title("Super Download")
        self.set_default_size(960, 600)
        self.set_icon_name("com.superdownload")

        _ensure_styles_loaded()
        self._download_rows: dict[str, Gtk.ListBoxRow] = {}
        self._new_download_dialog: Adw.MessageDialog | None = None

        # Conectar handler para interceptar o fechamento da janela
        self.connect("close-request", self._on_close_request)

        self._build_ui()

        # Inscreve-se para atualizações automáticas da fila
        app.download_manager.subscribe(self._on_queue_change)

    # ------------------------------------------------------------------
    @classmethod
    def new(cls, app: SuperDownloadApplication) -> "MainWindow":
        return cls(app)

    def _build_ui(self) -> None:
        """Construct window chrome aligned with Super Web App visuals."""
        self._toolbar_view = Adw.ToolbarView()
        self.set_content(self._toolbar_view)

        self._header_bar = Adw.HeaderBar()
        self._toolbar_view.add_top_bar(self._header_bar)

        title_label = Gtk.Label(label="Super Download")
        title_label.add_css_class("title-4")
        title_label.set_hexpand(True)
        title_label.set_xalign(0.5)
        self._header_bar.set_title_widget(title_label)

        self._new_button = Gtk.Button(label="Novo download")
        self._new_button.add_css_class("suggested-action")
        self._new_button.connect("clicked", self._on_new_download_clicked)
        self._header_bar.pack_end(self._new_button)

        self._menu_button = Gtk.MenuButton()
        self._menu_button.set_icon_name("open-menu-symbolic")
        self._menu_button.set_menu_model(self._create_menu())
        self._header_bar.pack_end(self._menu_button)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content_box.set_hexpand(True)
        content_box.set_vexpand(True)
        self._toolbar_view.set_content(content_box)

        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        search_box.set_margin_top(12)
        search_box.set_margin_start(12)
        search_box.set_margin_end(12)
        search_box.set_margin_bottom(6)

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Pesquisar download...")
        self._search_entry.set_hexpand(True)
        self._search_entry.add_css_class("super-download-search")
        self._search_entry.connect("activate", self._on_add_url)

        search_box.append(self._search_entry)
        content_box.append(search_box)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)
        scroller.set_margin_start(12)
        scroller.set_margin_end(12)
        scroller.set_margin_bottom(12)

        self._list_box = Gtk.ListBox()
        self._list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list_box.add_css_class("boxed-list")
        scroller.set_child(self._list_box)

        self._info_label = Gtk.Label(label="Nenhum download no momento.")
        self._info_label.add_css_class("dim-label")
        self._info_label.add_css_class("super-download-empty")
        self._info_label.set_margin_top(48)
        self._info_label.set_margin_bottom(48)
        self._info_label.set_margin_start(24)
        self._info_label.set_margin_end(24)
        self._info_label.set_xalign(0.5)
        self._info_label.set_valign(Gtk.Align.CENTER)
        self._info_label.set_wrap(True)

        self._stack = Gtk.Stack()
        self._stack.set_hexpand(True)
        self._stack.set_vexpand(True)
        self._stack.add_named(scroller, "list")
        self._stack.add_named(self._info_label, "empty")
        self._stack.set_visible_child_name("empty")

        content_box.append(self._stack)

    def _create_menu(self) -> Gio.Menu:
        """Create the hamburger menu mirroring application-wide actions."""
        menu = Gio.Menu()
        menu.append("Alternar pausa geral", "app.toggle-pause-all")
        menu.append("Sair", "app.quit")
        return menu

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
        row.set_selectable(False)
        row.set_activatable(False)
        row.set_margin_top(4)
        row.set_margin_bottom(4)

        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        main_box.add_css_class("super-download-row")
        main_box.add_css_class("card")
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(8)
        main_box.set_margin_bottom(8)
        main_box.set_hexpand(True)
        row.set_child(main_box)

        icon_image = Gtk.Image.new_from_gicon(self._icon_for_record(record))
        icon_image.set_pixel_size(48)
        icon_image.set_valign(Gtk.Align.CENTER)
        main_box.append(icon_image)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        info_box.set_hexpand(True)
        main_box.append(info_box)

        name_label = Gtk.Label(xalign=0)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        name_label.add_css_class("title-4")
        info_box.append(name_label)

        status_label = Gtk.Label(xalign=0)
        status_label.add_css_class("dim-label")
        status_label.set_wrap(True)
        info_box.append(status_label)

        progress = Gtk.ProgressBar()
        progress.set_hexpand(True)
        progress.set_show_text(False)
        info_box.append(progress)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        action_box.set_valign(Gtk.Align.CENTER)
        main_box.append(action_box)

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
        remove_button.add_css_class("destructive-action")

        for button in (pause_button, resume_button, cancel_button, open_button, remove_button):
            button.set_valign(Gtk.Align.CENTER)
            action_box.append(button)

        row.icon_image = icon_image  # type: ignore[attr-defined]
        row.name_label = name_label  # type: ignore[attr-defined]
        row.status_label = status_label  # type: ignore[attr-defined]
        row.progress_bar = progress  # type: ignore[attr-defined]
        row.pause_button = pause_button  # type: ignore[attr-defined]
        row.resume_button = resume_button  # type: ignore[attr-defined]
        row.cancel_button = cancel_button  # type: ignore[attr-defined]
        row.open_button = open_button  # type: ignore[attr-defined]
        row.remove_button = remove_button  # type: ignore[attr-defined]
        return row

    def _icon_for_record(self, record: DownloadRecord) -> Gio.Icon:
        """Infer an icon representing the download target."""
        source = record.destination or record.filename or record.url
        if source:
            try:
                source_str = str(source)
                content_type, _ = Gio.content_type_guess(source_str, None)
            except (TypeError, ValueError):
                content_type = None
            if content_type:
                icon = Gio.content_type_get_icon(content_type)
                if icon is not None:
                    return icon
        return Gio.ThemedIcon.new("text-x-generic")

    def _update_row_content(self, row: Gtk.ListBoxRow, record: DownloadRecord) -> None:
        row.name_label.set_label(record.filename or record.url)  # type: ignore[attr-defined]

        status_label = row.status_label  # type: ignore[attr-defined]
        status_parts = [
            record.status.replace("_", " ").title(),
            f"{record.progress * 100:.0f}%",
        ]
        if record.speed:
            status_parts.append(f"{record.speed / 1024:.0f} KiB/s")
        status_label.set_label(" | ".join(status_parts))

        row.icon_image.set_from_gicon(self._icon_for_record(record))  # type: ignore[attr-defined]

        progress_bar = row.progress_bar  # type: ignore[attr-defined]
        progress_bar.set_fraction(record.progress)
        progress_bar.set_text(f"{record.progress * 100:.0f}%")

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

    def _on_new_download_clicked(self, _button: Gtk.Button) -> None:
        if self._new_download_dialog is not None:
            self._new_download_dialog.present()
            return

        dialog = Adw.MessageDialog.new(
            self,
            "Novo download",
            "Informe o link do download.",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("add", "Adicionar")
        dialog.set_default_response("add")
        dialog.set_close_response("cancel")
        dialog.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)

        entry = Gtk.Entry()
        entry.set_placeholder_text("https://exemplo.com/arquivo.iso")
        entry.set_hexpand(True)
        dialog.set_extra_child(entry)

        base_body = dialog.get_body() or ""

        def submit() -> None:
            url = entry.get_text().strip()
            if not url or not self._looks_like_url(url):
                entry.add_css_class("error")
                dialog.set_body("Forneça um link de download válido.")
                dialog.emit_stop_by_name("response")
                return

            entry.remove_css_class("error")
            dialog.set_body(base_body)
            app: SuperDownloadApplication = self.get_application()  # type: ignore[assignment]
            GLib.idle_add(app.add_downloads, [url])
            self._clear_new_download_dialog()
            dialog.destroy()

        def on_response(dlg: Adw.MessageDialog, response: str) -> None:
            if response == "add":
                submit()
            else:
                self._clear_new_download_dialog()
                dlg.destroy()

        entry.connect("activate", lambda *_: dialog.response("add"))
        def on_changed(_entry: Gtk.Entry) -> None:
            if entry.has_css_class("error"):
                entry.remove_css_class("error")
            if dialog.get_body() != base_body:
                dialog.set_body(base_body)

        entry.connect("changed", on_changed)
        dialog.connect("response", on_response)
        dialog.connect("destroy", lambda *_: self._clear_new_download_dialog())

        self._new_download_dialog = dialog
        dialog.present()

        def focus_entry() -> bool:
            entry.grab_focus()
            return False

        GLib.idle_add(focus_entry)

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

    def _clear_new_download_dialog(self) -> None:
        self._new_download_dialog = None

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
