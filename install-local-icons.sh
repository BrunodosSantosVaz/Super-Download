#!/bin/bash
# Script para instalar ícones e .desktop localmente para desenvolvimento

# Instalar ícone
mkdir -p ~/.local/share/icons/hicolor/512x512/apps
cp data/icons/hicolor/512x512/apps/com.superdownload.png ~/.local/share/icons/hicolor/512x512/apps/

# Instalar .desktop
mkdir -p ~/.local/share/applications
cp data/com.superdownload.desktop ~/.local/share/applications/

# Atualizar cache de ícones
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor
fi

# Atualizar banco de dados de aplicações
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database ~/.local/share/applications
fi

echo "Ícones e arquivo .desktop instalados em ~/.local/share/"
echo "O ícone será usado em:"
echo "  - Janela principal"
echo "  - Bandeja do sistema"
echo "  - Atalhos do menu de aplicativos"
echo "  - Barra de tarefas"
