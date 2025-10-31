"""Executable entrypoint for Super Download."""

from __future__ import annotations

import argparse
import sys

from .app import SuperDownloadApplication


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--debug", action="store_true", help="Ativa logs detalhados.")
    known, remaining = parser.parse_known_args(argv[1:])

    run_arguments = [argv[0], *remaining]
    app = SuperDownloadApplication(debug=known.debug)
    return app.run(run_arguments)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
