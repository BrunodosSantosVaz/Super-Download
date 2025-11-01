#!/usr/bin/env python3
"""Setup script to install icons and desktop file in system directories."""

import os
import shutil
from pathlib import Path
from setuptools import setup
from setuptools.command.install import install


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        install.run(self)

        # Determinar diretórios de instalação
        if os.environ.get("DESTDIR"):
            # Instalação em um diretório customizado (usado por empacotadores)
            prefix = Path(os.environ["DESTDIR"]) / "usr"
        elif self.prefix == "/usr/local" or self.prefix == "/usr":
            # Instalação do sistema
            prefix = Path(self.prefix)
        else:
            # Instalação local do usuário
            prefix = Path.home() / ".local"

        # Instalar ícone
        icon_src = Path(__file__).parent / "data" / "icons" / "hicolor" / "512x512" / "apps" / "com.superdownload.png"
        icon_dest = prefix / "share" / "icons" / "hicolor" / "512x512" / "apps"
        icon_dest.mkdir(parents=True, exist_ok=True)
        if icon_src.exists():
            shutil.copy2(icon_src, icon_dest / "com.superdownload.png")
            print(f"Installed icon to {icon_dest / 'com.superdownload.png'}")

        # Instalar arquivo .desktop
        desktop_src = Path(__file__).parent / "data" / "com.superdownload.desktop"
        desktop_dest = prefix / "share" / "applications"
        desktop_dest.mkdir(parents=True, exist_ok=True)
        if desktop_src.exists():
            shutil.copy2(desktop_src, desktop_dest / "com.superdownload.desktop")
            print(f"Installed desktop file to {desktop_dest / 'com.superdownload.desktop'}")

        # Atualizar cache de ícones se possível
        try:
            import subprocess
            icon_cache_path = prefix / "share" / "icons" / "hicolor"
            subprocess.run(
                ["gtk-update-icon-cache", "-f", "-t", str(icon_cache_path)],
                check=False,
                capture_output=True
            )
            print("Updated icon cache")
        except Exception:
            pass

        # Atualizar banco de dados de aplicações se possível
        try:
            import subprocess
            apps_path = prefix / "share" / "applications"
            subprocess.run(
                ["update-desktop-database", str(apps_path)],
                check=False,
                capture_output=True
            )
            print("Updated desktop database")
        except Exception:
            pass


if __name__ == "__main__":
    setup(
        cmdclass={
            'install': PostInstallCommand,
        }
    )
