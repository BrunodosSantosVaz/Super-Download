"""Integração com bandeja via StatusNotifierItem (DBus)."""

from __future__ import annotations

import logging
from typing import Iterable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib

from .models import DownloadRecord

LOGGER = logging.getLogger(__name__)

# StatusNotifierItem DBus specification
SNI_INTERFACE = "org.kde.StatusNotifierItem"
SNI_PATH = "/StatusNotifierItem"
DBUS_MENU_INTERFACE = "com.canonical.dbusmenu"


class TrayIndicator:
    """Gerencia ícone de bandeja via StatusNotifierItem (DBus)."""

    def __init__(self, app) -> None:
        self._app = app
        self._connection: Gio.DBusConnection | None = None
        self._registration_id: int | None = None
        self._menu_registration_id: int | None = None
        self._watcher_id: int | None = None
        self._available = False

        try:
            self._setup_dbus()
        except Exception as exc:
            LOGGER.warning("Bandeja desabilitada: %s", exc)

    def _setup_dbus(self) -> None:
        """Configura StatusNotifierItem via DBus."""
        # Conectar ao session bus
        self._connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)

        # Registrar StatusNotifierWatcher se necessário
        self._register_with_watcher()

        # Registrar StatusNotifierItem
        self._register_status_notifier()

        # Registrar DBusMenu
        self._register_menu()

        self._available = True
        LOGGER.info("Bandeja StatusNotifierItem registrada via DBus")

    def _register_with_watcher(self) -> None:
        """Registra com StatusNotifierWatcher."""
        try:
            # Tentar registrar com o watcher do KDE/GNOME
            proxy = Gio.DBusProxy.new_sync(
                self._connection,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.kde.StatusNotifierWatcher",
                "/StatusNotifierWatcher",
                "org.kde.StatusNotifierWatcher",
                None,
            )

            # Registrar nosso item
            bus_name = self._connection.get_unique_name()
            proxy.call_sync(
                "RegisterStatusNotifierItem",
                GLib.Variant("(s)", (bus_name,)),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
            LOGGER.debug("Registrado com StatusNotifierWatcher")
        except Exception as exc:
            LOGGER.debug("StatusNotifierWatcher não disponível: %s", exc)

    def _register_status_notifier(self) -> None:
        """Registra interface StatusNotifierItem."""
        introspection_xml = """
        <node>
          <interface name="org.kde.StatusNotifierItem">
            <property name="Category" type="s" access="read"/>
            <property name="Id" type="s" access="read"/>
            <property name="Title" type="s" access="read"/>
            <property name="Status" type="s" access="read"/>
            <property name="IconName" type="s" access="read"/>
            <property name="Menu" type="o" access="read"/>
            <method name="Activate">
              <arg name="x" type="i" direction="in"/>
              <arg name="y" type="i" direction="in"/>
            </method>
            <method name="ContextMenu">
              <arg name="x" type="i" direction="in"/>
              <arg name="y" type="i" direction="in"/>
            </method>
          </interface>
        </node>
        """

        node_info = Gio.DBusNodeInfo.new_for_xml(introspection_xml)
        interface_info = node_info.lookup_interface(SNI_INTERFACE)

        self._registration_id = self._connection.register_object(
            SNI_PATH,
            interface_info,
            self._handle_method_call,
            self._handle_get_property,
            None,
        )

    def _register_menu(self) -> None:
        """Registra interface DBusMenu."""
        introspection_xml = """
        <node>
          <interface name="com.canonical.dbusmenu">
            <method name="GetLayout">
              <arg name="parentId" type="i" direction="in"/>
              <arg name="recursionDepth" type="i" direction="in"/>
              <arg name="propertyNames" type="as" direction="in"/>
              <arg name="revision" type="u" direction="out"/>
              <arg name="layout" type="(ia{sv}av)" direction="out"/>
            </method>
            <method name="Event">
              <arg name="id" type="i" direction="in"/>
              <arg name="eventId" type="s" direction="in"/>
              <arg name="data" type="v" direction="in"/>
              <arg name="timestamp" type="u" direction="in"/>
            </method>
            <signal name="LayoutUpdated">
              <arg name="revision" type="u"/>
              <arg name="parent" type="i"/>
            </signal>
          </interface>
        </node>
        """

        node_info = Gio.DBusNodeInfo.new_for_xml(introspection_xml)
        interface_info = node_info.lookup_interface(DBUS_MENU_INTERFACE)

        self._menu_registration_id = self._connection.register_object(
            "/MenuBar",
            interface_info,
            self._handle_menu_method_call,
            None,
            None,
        )

    def _handle_method_call(
        self,
        connection: Gio.DBusConnection,
        sender: str,
        object_path: str,
        interface_name: str,
        method_name: str,
        parameters: GLib.Variant,
        invocation: Gio.DBusMethodInvocation,
    ) -> None:
        """Handle StatusNotifierItem method calls."""
        if method_name == "Activate":
            GLib.idle_add(self._app.activate)
            invocation.return_value(None)
        elif method_name == "ContextMenu":
            # Menu is shown automatically by the system
            invocation.return_value(None)

    def _handle_get_property(
        self,
        connection: Gio.DBusConnection,
        sender: str,
        object_path: str,
        interface_name: str,
        property_name: str,
    ) -> GLib.Variant:
        """Handle StatusNotifierItem property reads."""
        if property_name == "Category":
            return GLib.Variant("s", "ApplicationStatus")
        elif property_name == "Id":
            return GLib.Variant("s", "br.com.superdownload")
        elif property_name == "Title":
            return GLib.Variant("s", "Super Download")
        elif property_name == "Status":
            return GLib.Variant("s", "Active")
        elif property_name == "IconName":
            return GLib.Variant("s", "br.com.superdownload")
        elif property_name == "Menu":
            return GLib.Variant("o", "/MenuBar")

    def _handle_menu_method_call(
        self,
        connection: Gio.DBusConnection,
        sender: str,
        object_path: str,
        interface_name: str,
        method_name: str,
        parameters: GLib.Variant,
        invocation: Gio.DBusMethodInvocation,
    ) -> None:
        """Handle DBusMenu method calls."""
        LOGGER.debug(f"Menu method call: {method_name}, params: {parameters}")

        if method_name == "GetLayout":
            # Build complete menu structure with items
            # DBusMenu format: (uint revision, (int id, dict properties, variant[] children))
            revision = 1
            root_id = 0

            # Menu simplificado: apenas "Abrir" e "Sair"
            item1 = (
                1,  # ID
                {
                    "label": GLib.Variant("s", "Abrir"),
                    "enabled": GLib.Variant("b", True),
                    "visible": GLib.Variant("b", True),
                },
                [],  # No children
            )

            item2 = (
                2,
                {
                    "type": GLib.Variant("s", "separator"),
                    "visible": GLib.Variant("b", True),
                },
                [],
            )

            item3 = (
                3,
                {
                    "label": GLib.Variant("s", "Sair"),
                    "enabled": GLib.Variant("b", True),
                    "visible": GLib.Variant("b", True),
                },
                [],
            )

            # Root menu structure
            root_menu = (
                root_id,
                {"children-display": GLib.Variant("s", "submenu")},
                [
                    GLib.Variant("(ia{sv}av)", item1),
                    GLib.Variant("(ia{sv}av)", item2),
                    GLib.Variant("(ia{sv}av)", item3),
                ],
            )

            # Final result
            result = GLib.Variant("(u(ia{sv}av))", (revision, root_menu))
            invocation.return_value(result)

        elif method_name == "Event":
            item_id = parameters[0]
            event_id = parameters[1]

            LOGGER.info(f"Menu event: item_id={item_id}, event_id={event_id}")

            if event_id == "clicked":
                if item_id == 1:  # Abrir
                    LOGGER.info("Menu: Abrir clicked")
                    def activate_app():
                        LOGGER.info("Executing activate")
                        self._app.activate()
                        return False
                    GLib.idle_add(activate_app)
                elif item_id == 3:  # Sair
                    LOGGER.info("Menu: Sair clicked")
                    def quit_app():
                        LOGGER.info("Executing quit")
                        quit_action = self._app.lookup_action("quit")
                        if quit_action:
                            quit_action.activate(None)
                        return False
                    GLib.idle_add(quit_app)

            invocation.return_value(None)

    def update_state(self, downloads: Iterable[DownloadRecord]) -> None:
        """Atualiza estado da bandeja (placeholder for future enhancements)."""
        if not self._available:
            return
        # Could emit property changes here for dynamic title updates

    @property
    def available(self) -> bool:
        return self._available

    def destroy(self) -> None:
        """Clean up DBus registrations."""
        if self._connection:
            if self._registration_id:
                self._connection.unregister_object(self._registration_id)
            if self._menu_registration_id:
                self._connection.unregister_object(self._menu_registration_id)
