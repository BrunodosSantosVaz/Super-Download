# Super Download - Documentação Rápida para Claude

## Visão Geral
Gerenciador de downloads para Linux com GTK4 + libadwaita, usando aria2c como backend via JSON-RPC.

## Estrutura do Projeto
```
/home/brunovaz/projetos/super download/
├── src/super_download/
│   ├── main.py              # Ponto de entrada principal
│   ├── app.py               # Aplicação Gio.Application
│   ├── aria2_client.py      # Cliente RPC para aria2c
│   ├── download_manager.py  # Gerenciador de downloads
│   ├── models.py            # Modelos de dados (DownloadRecord)
│   ├── persistence.py       # Persistência em JSON
│   ├── tray.py             # Bandeja do sistema
│   └── ui/
│       └── main_window.py   # Interface GTK4
├── tests/
├── docs/
├── flatpak/
└── pyproject.toml
```

## Configuração do aria2c

### Inicialização do aria2c
O projeto usa aria2c com configuração padrão:
- Host: http://localhost
- Port: 6800
- Secret: None (sem autenticação)

Para iniciar o aria2c:
```bash
aria2c --enable-rpc --rpc-listen-all=false --daemon=true --dir=/home/brunovaz/Downloads
```

Para verificar se está rodando:
```bash
ps aux | grep aria2c | grep -v grep
```

Para parar o aria2c:
```bash
pkill aria2c
```

## Executando o Projeto

### Modo normal
```bash
cd "/home/brunovaz/projetos/super download"
python -m super_download.main
```

### Modo debug
```bash
cd "/home/brunovaz/projetos/super download"
python -m super_download.main --debug
```

### Adicionar downloads via linha de comando
```bash
cd "/home/brunovaz/projetos/super download"
python -m super_download.main "https://exemplo.com/arquivo.zip" "https://exemplo.com/outro.pdf"
```

## Características Importantes

1. **Instância única**: Usa Gio.Application - execuções subsequentes encaminham URLs para instância principal
2. **Persistência**: Salva histórico e configurações em JSON
3. **Suporte a torrents**: O aria2c suporta torrents nativamente (.torrent)
4. **Nomes únicos**: Adiciona (1), (2), etc. automaticamente se arquivo já existir

## Dependências Python
Definidas em `pyproject.toml`:
- aria2p (interface Python para aria2c)
- PyGObject (GTK4)
- libadwaita

Para instalar:
```bash
pip install -e .
```

## CLI Auxiliar
```bash
super-download-cli listar --json  # Listar downloads
super-download-cli config          # Ver configurações
```

## Diretório de Downloads Padrão
`/home/brunovaz/Downloads`

## Roadmap
1. Integrar bandeja Ayatana
2. Migrar persistência para SQLite
3. Expor CLI completa
4. Registrar serviço D-Bus
5. Empacotar Flatpak
