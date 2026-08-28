"""Argument surface and the process boundary that turns failures into exit codes."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from btm_read_pdf.document import decrypt_if_needed, open_output
from btm_read_pdf.pages import parse_page_specification
from btm_read_pdf.render import write_extraction


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract analysis-ready text and metadata from a PDF using pypdf only."
        )
    )
    parser.add_argument(
        "input_pdf", type=Path, help="PDF file to read; it is never modified"
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


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input_pdf.is_file():
        raise ValueError(f"PDF file not found: {args.input_pdf}")
    if args.output and args.output.exists() and not args.overwrite:
        # Destroying existing bytes is decidable here; whether it is intended
        # is the caller's judgment, so demand it explicitly.
        raise ValueError(
            f"output file already exists: {args.output}; pass --overwrite to replace it"
        )

    reader = PdfReader(args.input_pdf, strict=False)
    decrypt_if_needed(reader, args.password_env)
    page_numbers = parse_page_specification(args.pages, len(reader.pages))

    with open_output(args.output) as output:
        empty_pages = write_extraction(
            reader,
            args.input_pdf.name,
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


def entrypoint() -> int:
    """Console-script boundary: expected failures become exit code 2."""
    try:
        return main()
    except (OSError, PdfReadError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
