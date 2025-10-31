# Super Download

Super Download e um gerenciador de downloads centralizado para ambientes Linux modernos. Ele oferece uma interface unificada para fila, pausa, retomada e monitoramento de downloads, comunicando-se com o aria2c via JSON-RPC e disponibilizando integracoes por CLI, D-Bus e socket local.

## Funcionalidades principais

- Instancia unica com detecao automatica de execucoes duplicadas (Gio.Application)
- Interface GTK4 + libadwaita com lista de downloads, barra de progresso e acoes rapidas
- Orquestrador Python integrando-se ao aria2 via `aria2p`
- Persistencia em JSON para historico e configuracoes (sincronizada a cada alteracao)
- Bandeja opcional via Ayatana AppIndicator, exibindo resumo dos downloads
- CLI utilitaria (`super-download-cli`) para inspecionar historico e configuracoes
- Hooks planejados para D-Bus, socket local (`/run/user/<uid>/superdownload.sock`) e API HTTP

## Requisitos

- Python 3.11+
- GTK4 e libadwaita
- aria2c executando com RPC habilitado (`aria2c --enable-rpc --rpc-listen-all=false --rpc-secret=<token>`)

Dependencias Python sao declaradas em `pyproject.toml` e podem ser instaladas com:

```bash
pip install -e .
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

## Roadmap imediato

1. Integrar bandeja Ayatana com operacoes de pausa/retomada diretas
2. Evoluir persistencia para SQLite e adicionar limpeza automatica
3. Expor CLI completa para adicionar downloads e consultar progresso em tempo real
4. Registrar servico D-Bus `com.superdownload.Manager`
5. Empacotar Flatpak (ver `flatpak/com.superdownload.yml`)
