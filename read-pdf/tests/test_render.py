"""Document shape: metadata section, header, page markers, empty-page counting."""

from __future__ import annotations

import io
from dataclasses import dataclass, field

from btm_read_pdf.render import (
    format_header,
    format_metadata,
    write_extraction,
    write_pages,
)


@dataclass(frozen=True, slots=True)
class StubPage:
    text: str | None

    def extract_text(self) -> str | None:
        return self.text


@dataclass(frozen=True, slots=True)
class StubReader:
    """Stands in for a PdfReader across the surface the writers actually use."""

    pages: list[StubPage]
    metadata: dict[str, object] | None = field(default=None)


class TestFormatMetadata:
    def test_populated_fields_render_in_declared_order(self):
        rendered = format_metadata({"/Author": "Ada", "/Title": "Notes"})
        assert rendered.index("Title") < rendered.index("Author")

    def test_absent_fields_are_omitted(self):
        assert "Subject" not in format_metadata({"/Title": "Notes"})

    def test_empty_values_count_as_absent(self):
        assert "No standard document metadata found" in format_metadata({"/Title": ""})

    def test_no_metadata_states_so(self):
        assert "No standard document metadata found" in format_metadata({})

    def test_unknown_keys_are_ignored(self):
        assert "No standard document metadata found" in format_metadata({"/Odd": "x"})


class TestFormatHeader:
    def test_header_names_the_file_and_its_selection(self):
        header = format_header("paper.pdf", [1, 3])
        assert "paper.pdf" in header and "1, 3" in header


class TestWritePages:
    def test_each_page_gets_a_one_based_marker(self):
        sink = io.StringIO()
        write_pages(StubReader([StubPage("a"), StubPage("b")]), [1, 2], sink)
        assert "## PDF page 1" in sink.getvalue()
        assert "## PDF page 2" in sink.getvalue()

    def test_selection_order_drives_output_order(self):
        sink = io.StringIO()
        write_pages(StubReader([StubPage("a"), StubPage("b")]), [2, 1], sink)
        body = sink.getvalue()
        assert body.index("## PDF page 2") < body.index("## PDF page 1")

    def test_blank_pages_are_counted_and_marked(self):
        sink = io.StringIO()
        empty = write_pages(StubReader([StubPage("  "), StubPage("x")]), [1, 2], sink)
        assert empty == 1
        assert "[No extractable text on this page.]" in sink.getvalue()

    def test_none_text_counts_as_empty(self):
        sink = io.StringIO()
        assert write_pages(StubReader([StubPage(None)]), [1], sink) == 1

    def test_text_only_document_reports_no_empty_pages(self):
        sink = io.StringIO()
        assert write_pages(StubReader([StubPage("x")]), [1], sink) == 0


class TestWriteExtraction:
    def test_metadata_section_is_included_on_request(self):
        sink = io.StringIO()
        reader = StubReader([StubPage("x")], {"/Title": "Notes"})
        write_extraction(reader, "a.pdf", [1], include_metadata=True, output=sink)
        assert "## Document metadata" in sink.getvalue()

    def test_metadata_section_is_omitted_on_request(self):
        sink = io.StringIO()
        reader = StubReader([StubPage("x")], {"/Title": "Notes"})
        write_extraction(reader, "a.pdf", [1], include_metadata=False, output=sink)
        assert "## Document metadata" not in sink.getvalue()

    def test_absent_metadata_does_not_raise(self):
        sink = io.StringIO()
        write_extraction(
            StubReader([StubPage("x")]),
            "a.pdf",
            [1],
            include_metadata=True,
            output=sink,
        )
        assert "No standard document metadata found" in sink.getvalue()

    def test_header_precedes_metadata_and_pages(self):
        sink = io.StringIO()
        reader = StubReader([StubPage("x")], {"/Title": "Notes"})
        write_extraction(reader, "a.pdf", [1], include_metadata=True, output=sink)
        body = sink.getvalue()
        assert body.index("# Extracted from") < body.index("## Document metadata")
        assert body.index("## Document metadata") < body.index("## PDF page 1")
