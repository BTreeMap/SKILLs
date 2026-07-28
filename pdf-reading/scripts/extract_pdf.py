#!/usr/bin/env python3
"""Extract analysis-ready text and metadata from a PDF using pypdf only."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence, TextIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


PAGE_TOKEN = re.compile(r"^(?P<start>\d+)(?:-(?P<end>\d*)?)?$")
METADATA_FIELDS = (
    ("/Title", "Title"),
    ("/Author", "Author"),
    ("/Subject", "Subject"),
    ("/Creator", "Creator"),
    ("/Producer", "Producer"),
    ("/CreationDate", "Creation date"),
    ("/ModDate", "Modified date"),
)


def parse_page_specification(specification: Optional[str], page_count: int) -> list[int]:
    """Return unique one-based page numbers selected by a user page specification."""
    if specification is None:
        return list(range(1, page_count + 1))

    selected: list[int] = []
    seen: set[int] = set()
    for raw_token in specification.split(","):
        token = raw_token.strip()
        match = PAGE_TOKEN.fullmatch(token)
        if not match:
            raise ValueError(
                "Invalid page selection. Use one-based page numbers and ranges, "
                "for example: 1-3,5,8-."
            )

        start = int(match.group("start"))
        raw_end = match.group("end")
        end = start if raw_end is None else page_count if raw_end == "" else int(raw_end)
        if start < 1 or end < start or end > page_count:
            raise ValueError(
                f"Page selection {token!r} is outside the document's 1-{page_count} range."
            )

        for page_number in range(start, end + 1):
            if page_number not in seen:
                selected.append(page_number)
                seen.add(page_number)

    return selected


def decrypt_if_needed(reader: PdfReader, password_env: Optional[str]) -> None:
    """Decrypt the reader from an environment variable when the PDF requires it."""
    if not reader.is_encrypted:
        return
    if not password_env:
        raise ValueError(
            "The PDF is encrypted. Set its password in an environment variable and "
            "pass that variable name with --password-env."
        )

    password = os.environ.get(password_env)
    if not password:
        raise ValueError(
            f"The environment variable {password_env!r} is empty or not set."
        )
    if not reader.decrypt(password):
        raise ValueError("The supplied password could not decrypt the PDF.")


def write_metadata(reader: PdfReader, output: TextIO) -> None:
    """Write available document metadata without assuming optional fields exist."""
    metadata = reader.metadata or {}
    output.write("## Document metadata\n\n")
    wrote_value = False
    for key, label in METADATA_FIELDS:
        value = metadata.get(key)
        if value:
            output.write(f"- {label}: {value}\n")
            wrote_value = True
    if not wrote_value:
        output.write("- No standard document metadata found.\n")
    output.write("\n")


def write_pages(reader: PdfReader, page_numbers: Iterable[int], output: TextIO) -> None:
    """Write text for each selected page with stable one-based page markers."""
    for page_number in page_numbers:
        text = reader.pages[page_number - 1].extract_text() or ""
        output.write(f"## PDF page {page_number}\n\n")
        output.write(text.strip() or "[No extractable text on this page.]\n")
        output.write("\n\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract analysis-ready text and metadata from a PDF using pypdf only."
    )
    parser.add_argument("input_pdf", type=Path, help="PDF file to read; it is never modified")
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
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input_pdf.is_file():
        raise ValueError(f"PDF file not found: {args.input_pdf}")

    reader = PdfReader(args.input_pdf, strict=False)
    decrypt_if_needed(reader, args.password_env)
    page_numbers = parse_page_specification(args.pages, len(reader.pages))

    if args.output:
        with args.output.open("w", encoding="utf-8", newline="\n") as output:
            output.write(f"# Extracted from {args.input_pdf.name}\n\n")
            output.write(f"Selected PDF pages: {', '.join(map(str, page_numbers))}\n\n")
            if not args.no_metadata:
                write_metadata(reader, output)
            write_pages(reader, page_numbers, output)
    else:
        output = sys.stdout
        output.write(f"# Extracted from {args.input_pdf.name}\n\n")
        output.write(f"Selected PDF pages: {', '.join(map(str, page_numbers))}\n\n")
        if not args.no_metadata:
            write_metadata(reader, output)
        write_pages(reader, page_numbers, output)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, PdfReadError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
