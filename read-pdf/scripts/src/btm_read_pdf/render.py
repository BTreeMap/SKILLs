"""Document shape: pure formatters, plus writers parameterized over their sink."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Protocol, TextIO

METADATA_FIELDS = (
    ("/Title", "Title"),
    ("/Author", "Author"),
    ("/Subject", "Subject"),
    ("/Creator", "Creator"),
    ("/Producer", "Producer"),
    ("/CreationDate", "Creation date"),
    ("/ModDate", "Modified date"),
)


class Page(Protocol):
    def extract_text(self) -> str | None: ...


class Document(Protocol):
    """The surface these writers use, so a reader stands in for a PdfReader."""

    @property
    def metadata(self) -> Mapping[str, object] | None: ...

    @property
    def pages(self) -> Sequence[Page]: ...


def format_metadata(metadata: Mapping[str, object]) -> str:
    """Build the complete metadata section from populated standard fields."""
    lines = [
        f"- {label}: {value}\n"
        for key, label in METADATA_FIELDS
        if (value := metadata.get(key))
    ]
    body = "".join(lines) or "- No standard document metadata found.\n"
    return f"## Document metadata\n\n{body}\n"


def format_header(input_name: str, page_numbers: Sequence[int]) -> str:
    """Build the stable preamble for an extraction document."""
    selected_pages = ", ".join(map(str, page_numbers))
    return f"# Extracted from {input_name}\n\nSelected PDF pages: {selected_pages}\n\n"


def write_metadata(reader: Document, output: TextIO) -> None:
    """Write available document metadata without assuming optional fields exist."""
    output.write(format_metadata(reader.metadata or {}))


def write_pages(reader: Document, page_numbers: Iterable[int], output: TextIO) -> int:
    """Write text for each selected page with stable one-based page markers.

    Returns the count of pages that had no extractable text, so the caller
    can surface an aggregate signal instead of leaving the reader to infer a
    scanned document from a wall of empty page markers.
    """
    empty_pages = 0
    for page_number in page_numbers:
        text = reader.pages[page_number - 1].extract_text() or ""
        output.write(f"## PDF page {page_number}\n\n")
        output.write(text.strip() or "[No extractable text on this page.]\n")
        output.write("\n\n")
        if not text.strip():
            empty_pages += 1
    return empty_pages


def write_extraction(
    reader: Document,
    input_name: str,
    page_numbers: Sequence[int],
    include_metadata: bool,
    output: TextIO,
) -> int:
    """Interpret a validated extraction request at the output boundary.

    Returns the count of selected pages without extractable text."""
    output.write(format_header(input_name, page_numbers))
    if include_metadata:
        write_metadata(reader, output)
    return write_pages(reader, page_numbers, output)
