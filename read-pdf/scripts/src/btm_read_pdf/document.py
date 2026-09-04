"""Effects: decrypting a reader and opening the output sink."""

from __future__ import annotations

import os
import sys
from contextlib import AbstractContextManager as ContextManager
from contextlib import nullcontext
from pathlib import Path
from typing import TextIO

from pypdf import PdfReader

from btm_corekit import CommandError


def decrypt_if_needed(reader: PdfReader, password_env: str | None) -> None:
    """Decrypt the reader, trying the empty user password before requiring one.

    Many PDFs are owner-locked only: encrypted, but readable with the empty
    user password. That attempt is deterministic and free, so it is never the
    caller's problem; only a real user password gates on --password-env.
    """
    if not reader.is_encrypted:
        return
    if reader.decrypt(""):
        print(
            "note: PDF is owner-locked only; opened with the empty user password",
            file=sys.stderr,
        )
        return
    if not password_env:
        raise CommandError(
            "The PDF is encrypted. Set its password in an environment variable and "
            "pass that variable name with --password-env."
        )

    password = os.environ.get(password_env)
    if not password:
        raise CommandError(
            f"The environment variable {password_env!r} is empty or not set."
        )
    if not reader.decrypt(password):
        raise CommandError("The supplied password could not decrypt the PDF.")


def open_output(output_path: Path | None) -> ContextManager[TextIO]:
    """Open a UTF-8 output file or leave standard output owned by its caller."""
    if output_path:
        return output_path.open("w", encoding="utf-8", newline="\n")
    return nullcontext(sys.stdout)
