# Super Download - Arquitetura

## Visao geral

Super Download e composto por uma camada de interface GTK4/libadwaita que conversa com um `DownloadManager` em Python. O `DownloadManager` controla o ciclo de vida dos downloads, delegando o trabalho pesado ao aria2c por meio de JSON-RPC. Aplicacoes externas interagem com a instancia ativa via CLI, D-Bus e socket local.

```
Outros Apps (CLI / D-Bus / Socket)
          │ URLs
          ▼
 Super Download (Gtk Application)
 ├─ UI principal (MainWindow)
 ├─ Bandeja e notificacoes (planejado)
 └─ Integracao IPC
          │ JSON-RPC
          ▼
      aria2c daemon
```

## Componentes

- `SuperDownloadApplication`: instancia unica `Adw.Application` que registra acoes, integra com CLI e apresenta a janela principal.
- `DownloadManager`: gerencia fila, pooling de status, persistencia em JSON e operacoes de pausa/retomada.
- `Aria2Client`: encapsula `aria2p` com uma interface segura, permitindo fallback mock quando aria2p nao esta disponivel.
- `ui.MainWindow`: construtor da interface, exibindo lista de downloads e oferecendo botoes de acao.
- `TrayIndicator`: integra opcionalmente com Ayatana AppIndicator para menu de bandeja.
- `logs`: armazenados em `~/.local/state/superdownload/log.txt` conforme GLib.

## Fluxos principais

### Adicionar download

1. Usuario fornece URL (CLI ou UI).
2. `SuperDownloadApplication.add_downloads` delega ao `DownloadManager`.
3. `DownloadManager` cria registro, chama `Aria2Client.add_uri`.
4. Polling atualiza progresso, UI reflete alteracoes.

### Encerrar

1. Usuario solicita `app.quit` ou acao de bandeja.
2. `DownloadManager.can_quit` avalia se existem transferencias ativas.
3. Caso positivo, `MainWindow.ask_quit_confirmation` confirma com usuario.
4. Ao confirmar, `DownloadManager.shutdown` remove timers e o app finaliza.

## Persistencia e integracao

- Historico e configuracoes armazenados em JSON via `PersistenceStore`.
- Socket local planejado: `/run/user/<uid>/superdownload.sock`.
- Servico D-Bus: `com.superdownload.Manager` com metodos `AddDownload`, `PauseAll`, `ResumeAll`, `GetDownloads`.
- Modalidade Flatpak: manifest em `flatpak/com.superdownload.yml`.

## Roadmap tecnico

1. Expandir bandeja Ayatana com interacoes (pausar/retomar) e notificacoes.
2. Evoluir persistencia para SQLite e sincronizacao incremental.
3. Conectar CLI dedicada e socket local.
4. Expor D-Bus e notificacoes nativas.
5. Finalizar empacotamento Flatpak.
