"""Argument surface and the process boundary that turns failures into exit codes."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from btm_corekit import CommandError, Parser, dispatch
from btm_read_pdf.document import decrypt_if_needed, open_output
from btm_read_pdf.pages import parse_page_specification
from btm_read_pdf.render import write_extraction
from btm_read_pdf.source import DEFAULT_MAX_BYTES, materialize, parse_source


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(
        description=(
            "Extract analysis-ready text and metadata from a PDF using pypdf only."
        )
    )
    parser.add_argument(
        "input_pdf",
        help="PDF file or http(s) URL to read; the document is never modified",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help="download size cap for URL inputs (default 200 MB)",
    )
    parser.add_argument(
        "--pages",
        metavar="PAGE_SPEC",
        help="One-based pages/ranges to extract, such as 1-3,5,8-; default: all pages",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="UTF-8 text file to write; default: standard output",
    )
    parser.add_argument(
        "--password-env",
        metavar="VARIABLE",
        help="Environment-variable name containing a password for an encrypted PDF",
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Omit standard document metadata from the extraction",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the --output file if it already exists",
    )
    return parser


def _run(argv: Sequence[str] | None) -> int:
    args = build_parser().parse_args(argv)
    if args.output and args.output.exists() and not args.overwrite:
        # Destroying existing bytes needs the caller's explicit consent;
        # refuse before materialize, so a doomed run downloads nothing.
        raise CommandError(
            f"output file already exists: {args.output}; pass --overwrite to replace it"
        )
    local_path, display_name = materialize(parse_source(args.input_pdf), args.max_bytes)

    reader = PdfReader(local_path, strict=False)
    decrypt_if_needed(reader, args.password_env)
    page_numbers = parse_page_specification(args.pages, len(reader.pages))

    with open_output(args.output) as output:
        empty_pages = write_extraction(
            reader,
            display_name,
            page_numbers,
            include_metadata=not args.no_metadata,
            output=output,
        )

    if empty_pages:
        note = (
            f"note: {empty_pages} of {len(page_numbers)} selected pages "
            "had no extractable text"
        )
        if empty_pages == len(page_numbers):
            note += "; likely a scanned/image-based PDF (this tool has no OCR)"
        print(note, file=sys.stderr)

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Extraction under the shared exit contract: 0 done, 1 fix the input and
    resend, 2 the fetch failed and a retry may clear it.

    pypdf's and the OS's own exceptions join the contract here, at the one
    boundary that knows they mean an unreadable file rather than an
    unreachable server."""

    def run() -> int:
        try:
            return _run(argv)
        except (OSError, PdfReadError) as err:
            raise CommandError(str(err)) from err

    return dispatch(run)


def entrypoint() -> int:
    """Console-script boundary."""
    return main()
