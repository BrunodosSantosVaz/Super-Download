# Super Download

Super Download é um gerenciador de downloads centralizado para ambientes Linux modernos. Ele oferece uma interface unificada para fila, pausa, retomada e monitoramento de downloads, comunicando-se com o aria2c via JSON-RPC.

## Origem do Projeto

O Super Download nasceu durante o desenvolvimento do **Super Web App**. Ao perceber a necessidade de um gerenciador de downloads, optei por criar um **sistema independente e reutilizável**, capaz de atender não apenas o Super Web App, mas outras aplicações e casos de uso também. Assim, o Super Download pode ser usado tanto como aplicação standalone quanto integrado a outros projetos.

## Funcionalidades principais

- Instância única com detecção automática de execuções duplicadas (Gio.Application)
- Interface GTK4 + libadwaita com lista de downloads, barra de progresso e ações rápidas
- Orquestrador Python integrando-se ao aria2 via `aria2p`
- Persistência em JSON para histórico e configurações (sincronizada a cada alteração)
- **Bandeja do sistema via StatusNotifierItem (DBus)** ✅:
  - Protocolo nativo do FreeDesktop.org
  - Ícone único na bandeja (nunca duplicado)
  - Minimiza para bandeja ao fechar janela
  - Menu contextual simplificado: **Abrir** e **Sair**
  - Confirmação ao sair com downloads ativos
  - Funciona nativamente em KDE Plasma, XFCE, Cinnamon, MATE
  - Requer extensão no GNOME Shell
- CLI utilitária (`super-download-cli`) para inspecionar histórico e configurações
- Gerenciamento automático de nomes de arquivos duplicados
- Suporte a downloads HTTP, HTTPS, FTP e BitTorrent (.torrent)

## Requisitos

### Sistema
- Python 3.12+
- GTK4 e libadwaita (para interface principal)
- aria2c (daemon de downloads)
- **GNOME Shell**: Extensão "AppIndicator Support" para bandeja (opcional)

### Instalação no Manjaro/Arch
```bash
sudo pacman -S python gtk4 libadwaita aria2
```

### Instalação no Ubuntu/Debian
```bash
sudo apt install python3 gir1.2-gtk-4.0 gir1.2-adw-1 aria2
```

### Extensão GNOME (opcional)
Para usar a bandeja no GNOME Shell, instale a extensão:
- **Nome**: AppIndicator and KStatusNotifierItem Support
- **Link**: https://extensions.gnome.org/extension/615/appindicator-support/
- **Nota**: KDE Plasma, XFCE, Cinnamon e MATE têm suporte nativo (não precisa extensão)

### Dependências Python
Declaradas em `pyproject.toml` e podem ser instaladas com:

```bash
pip install -e .
```

### Iniciar daemon aria2c
```bash
aria2c --enable-rpc --rpc-listen-all=false --rpc-listen-port=6800 --daemon=true
```

## Estrutura do projeto

```
super download/
├─ pyproject.toml
├─ README.md
├─ docs/
│  └─ ARCHITECTURE.md
├─ flatpak/
│  └─ com.superdownload.yml
├─ src/super_download/
│  ├─ __init__.py
│  ├─ app.py
│  ├─ aria2_client.py
│  ├─ cli.py
│  ├─ download_manager.py
│  ├─ main.py
│  ├─ models.py
│  ├─ persistence.py
│  ├─ tray.py
│  └─ ui/
│     ├─ __init__.py
│     └─ main_window.py
└─ tests/
   └─ test_persistence.py
```

## Executando

```bash
python -m super_download.main
```

Para habilitar logs detalhados:

```bash
python -m super_download.main --debug
```

Ao executar com URLs:

```bash
python -m super_download.main https://exemplo.com/arquivo.zip
```

Execucoes subsequentes encaminham as URLs para a instancia principal em execucao.

CLI auxiliar para consultar dados persistidos:

```bash
super-download-cli listar --json
super-download-cli config
```

## Comportamento da Bandeja do Sistema

A bandeja do sistema oferece acesso rápido ao aplicativo:

- **Fechar janela (X)**: Minimiza para bandeja (não encerra o aplicativo)
- **Ícone na bandeja**: Sempre único, nunca duplicado
- **Menu "Abrir"**: Abre e dá foco à janela principal
- **Menu "Sair"**:
  - Se há downloads ativos/em fila: pede confirmação
  - Se não há downloads: encerra imediatamente

**Implementação**: StatusNotifierItem via DBus (protocolo nativo do FreeDesktop.org)

**Nota para GNOME**: A bandeja só aparecerá se você tiver a extensão [AppIndicator Support](https://extensions.gnome.org/extension/615/appindicator-support/) instalada. Em outros ambientes (KDE Plasma, XFCE, Cinnamon, MATE), a bandeja funciona nativamente sem configuração adicional.

## Logs

Logs são salvos em: `~/.local/state/superdownload/log.txt`

Para executar com logs detalhados:
```bash
python -m super_download.main --debug
```

## Roadmap

- [x] Bandeja do sistema totalmente funcional (StatusNotifierItem via DBus)
- [x] Menu contextual da bandeja com "Abrir" e "Sair"
- [x] Confirmação ao sair com downloads ativos
- [ ] Integração com Super Web App
- [ ] Adicionar pausa/retomada global de downloads
- [ ] Evoluir persistência para SQLite
- [ ] Limpeza automática de downloads antigos
- [ ] Expor API D-Bus `com.superdownload.Manager` para IPC
- [ ] Suporte a agendamento de downloads
- [ ] Limite de velocidade por download
- [ ] Categorização e filtros de downloads
- [ ] Atualização dinâmica de título/tooltip na bandeja
