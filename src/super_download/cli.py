"""CLI utilitário para histórico do Super Download."""

from __future__ import annotations

import argparse
import json
from typing import Iterable

from .models import DownloadRecord
from .persistence import PersistenceStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="super-download-cli",
        description="Ferramentas auxiliares para o Super Download.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("listar", help="Lista downloads conhecidos.")
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Exibe a saída em JSON.",
    )

    subparsers.add_parser("config", help="Mostra configurações persistidas.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = PersistenceStore()

    if args.command == "listar":
        return _cmd_listar(store.history, json_output=getattr(args, "json", False))
    if args.command == "config":
        print(json.dumps(store.config, indent=2, ensure_ascii=False))
        return 0

    parser.print_help()
    return 1


def _cmd_listar(entries: Iterable[dict], json_output: bool = False) -> int:
    if json_output:
        print(json.dumps(list(entries), indent=2, ensure_ascii=False))
        return 0

    if not entries:
        print("Nenhum download registrado.")
        return 0

    for entry in entries:
        record = DownloadRecord.from_dict(entry)
        print(
            f"{record.gid[:8]}  {record.status:<10}  "
            f"{record.progress * 100:>3.0f}%  {record.filename or record.url}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
