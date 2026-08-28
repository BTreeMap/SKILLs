"""The process boundary shared by argparse-driven members."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from btm_corekit.errors import CommandError


def run_cli(parser: argparse.ArgumentParser, argv: Sequence[str] | None = None) -> int:
    """Dispatch to the parsed `func`, turning CommandError into exit 1."""
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CommandError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
