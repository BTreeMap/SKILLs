"""End to end over a real PDF built by pypdf, plus the refusal paths."""

from __future__ import annotations

import pytest
from pypdf import PdfWriter

from btm_read_pdf.cli import entrypoint, main


@pytest.fixture
def blank_pdf(tmp_path):
    """A real two-page PDF; blank pages carry no extractable text."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    path = tmp_path / "blank.pdf"
    with path.open("wb") as handle:
        writer.write(handle)
    return path


class TestExtraction:
    def test_writes_every_page_to_the_output_file(self, blank_pdf, tmp_path):
        out = tmp_path / "out.txt"
        assert main([str(blank_pdf), "--output", str(out)]) == 0
        body = out.read_text(encoding="utf-8")
        assert "## PDF page 1" in body and "## PDF page 2" in body

    def test_page_selection_narrows_the_output(self, blank_pdf, tmp_path):
        out = tmp_path / "out.txt"
        main([str(blank_pdf), "--pages", "2", "--output", str(out)])
        body = out.read_text(encoding="utf-8")
        assert "## PDF page 2" in body and "## PDF page 1" not in body

    def test_blank_document_reports_a_scanned_pdf_note(
        self, blank_pdf, tmp_path, capsys
    ):
        main([str(blank_pdf), "--output", str(tmp_path / "out.txt")])
        assert "no extractable text" in capsys.readouterr().err

    def test_no_metadata_omits_the_section(self, blank_pdf, tmp_path):
        out = tmp_path / "out.txt"
        main([str(blank_pdf), "--no-metadata", "--output", str(out)])
        assert "## Document metadata" not in out.read_text(encoding="utf-8")

    def test_stdout_is_the_default_sink(self, blank_pdf, capsys):
        assert main([str(blank_pdf)]) == 0
        assert "## PDF page 1" in capsys.readouterr().out


class TestRefusals:
    def test_missing_input_is_rejected(self, tmp_path, capsys):
        assert main([str(tmp_path / "absent.pdf")]) == 1
        assert "PDF file not found" in capsys.readouterr().err

    def test_existing_output_is_protected(self, blank_pdf, tmp_path, capsys):
        out = tmp_path / "out.txt"
        out.write_text("prior", encoding="utf-8")
        assert main([str(blank_pdf), "--output", str(out)]) == 1
        assert "pass --overwrite" in capsys.readouterr().err

    def test_overwrite_releases_the_protection(self, blank_pdf, tmp_path):
        out = tmp_path / "out.txt"
        out.write_text("prior", encoding="utf-8")
        assert main([str(blank_pdf), "--output", str(out), "--overwrite"]) == 0
        assert "prior" not in out.read_text(encoding="utf-8")

    def test_out_of_range_page_is_rejected(self, blank_pdf, capsys):
        assert main([str(blank_pdf), "--pages", "9"]) == 1
        assert "outside the document" in capsys.readouterr().err


class TestEntrypoint:
    def test_a_bad_input_is_exit_one_not_a_retry(self, tmp_path, monkeypatch, capsys):
        """A missing path can never be fixed by retrying, so it belongs in the
        exit-1 column; this command used to answer 2 for every failure."""
        monkeypatch.setattr("sys.argv", ["btm-read-pdf", str(tmp_path / "absent.pdf")])
        assert entrypoint() == 1
        assert "error: PDF file not found" in capsys.readouterr().err

    def test_a_malformed_argument_line_is_exit_one(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["btm-read-pdf", "--nope"])
        assert entrypoint() == 1
        assert "error:" in capsys.readouterr().err

    def test_success_returns_zero(self, blank_pdf, monkeypatch):
        monkeypatch.setattr("sys.argv", ["btm-read-pdf", str(blank_pdf)])
        assert entrypoint() == 0
