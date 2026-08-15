#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pypdf>=6,<7",
# ]
# ///

"""Extract analysis-ready text and metadata from a PDF using pypdf only."""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from contextlib import AbstractContextManager as ContextManager
from contextlib import nullcontext
from functools import partial
from itertools import chain
from pathlib import Path
from typing import TextIO, TypeGuard

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


def parse_page_token(page_count: int, token: str) -> range:
    """Parse one validated page token into its selected one-based range."""
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

    return range(start, end + 1)


def parse_page_specification(specification: str | None, page_count: int) -> list[int]:
    """Return unique one-based page numbers selected by a user page specification."""
    if specification is None:
        return list(range(1, page_count + 1))

    page_ranges = map(
        partial(parse_page_token, page_count), map(str.strip, specification.split(","))
    )
    # `dict` is an insertion-ordered set in Python 3.11+, preserving first selection.
    return list(dict.fromkeys(chain.from_iterable(page_ranges)))


def decrypt_if_needed(reader: PdfReader, password_env: str | None) -> None:
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


def format_metadata_field(
    metadata: Mapping[str, object], field: tuple[str, str]
) -> str | None:
    """Format one populated metadata field, or return explicit absence."""
    key, label = field
    value = metadata.get(key)
    return f"- {label}: {value}\n" if value else None


def is_present(value: str | None) -> TypeGuard[str]:
    """Narrow optional formatted output to text that should be emitted."""
    return value is not None


def format_metadata(metadata: Mapping[str, object]) -> str:
    """Build the complete metadata section from available standard fields."""
    lines = tuple(
        filter(
            is_present, map(partial(format_metadata_field, metadata), METADATA_FIELDS)
        )
    )
    body = "".join(lines) or "- No standard document metadata found.\n"
    return f"## Document metadata\n\n{body}\n"


def write_metadata(reader: PdfReader, output: TextIO) -> None:
    """Write available document metadata without assuming optional fields exist."""
    output.write(format_metadata(reader.metadata or {}))


def write_pages(reader: PdfReader, page_numbers: Iterable[int], output: TextIO) -> None:
    """Write text for each selected page with stable one-based page markers."""
    for page_number in page_numbers:
        text = reader.pages[page_number - 1].extract_text() or ""
        output.write(f"## PDF page {page_number}\n\n")
        output.write(text.strip() or "[No extractable text on this page.]\n")
        output.write("\n\n")


def format_header(input_name: str, page_numbers: Sequence[int]) -> str:
    """Build the stable preamble for an extraction document."""
    selected_pages = ", ".join(map(str, page_numbers))
    return f"# Extracted from {input_name}\n\nSelected PDF pages: {selected_pages}\n\n"


def write_extraction(
    reader: PdfReader,
    input_name: str,
    page_numbers: Sequence[int],
    include_metadata: bool,
    output: TextIO,
) -> None:
    """Interpret a validated extraction request at the output boundary."""
    output.write(format_header(input_name, page_numbers))
    if include_metadata:
        write_metadata(reader, output)
    write_pages(reader, page_numbers, output)


def open_output(output_path: Path | None) -> ContextManager[TextIO]:
    """Open a UTF-8 output file or leave standard output owned by its caller."""
    if output_path:
        return output_path.open("w", encoding="utf-8", newline="\n")
    return nullcontext(sys.stdout)


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input_pdf.is_file():
        raise ValueError(f"PDF file not found: {args.input_pdf}")

    reader = PdfReader(args.input_pdf, strict=False)
    decrypt_if_needed(reader, args.password_env)
    page_numbers = parse_page_specification(args.pages, len(reader.pages))

    with open_output(args.output) as output:
        write_extraction(
            reader,
            args.input_pdf.name,
            page_numbers,
            include_metadata=not args.no_metadata,
            output=output,
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, PdfReadError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
