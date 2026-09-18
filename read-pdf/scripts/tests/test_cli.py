"""End to end over a real PDF built by pypdf, plus the refusal paths."""

from __future__ import annotations

import json
import tempfile

import pytest
from pypdf import PdfWriter

from btm_corekit import cache_dir
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

    def test_a_corrupt_document_is_a_clean_refusal_not_a_traceback(
        self, tmp_path, capsys
    ):
        """pypdf's own error joins the exit contract at the one boundary that
        knows it means an unreadable file rather than an unreachable server."""
        broken = tmp_path / "not-really.pdf"
        broken.write_bytes(b"%PDF-1.7\nthis is not a pdf body")
        assert main([str(broken)]) == 1
        assert "error:" in capsys.readouterr().err

    def test_out_of_range_page_is_rejected(self, blank_pdf, capsys):
        assert main([str(blank_pdf), "--pages", "9"]) == 1
        assert "outside the document" in capsys.readouterr().err


class TestClean:
    @pytest.fixture
    def cache(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
        directory = cache_dir("read-pdf")
        directory.mkdir()
        (directory / "a.pdf").write_bytes(b"%PDF-1.4 tiny")
        return directory

    @pytest.mark.parametrize("argv", [["clean"], ["clean", "--all"]])
    def test_clean_removes_the_cache_and_emits_the_record(self, cache, argv, capsys):
        """`--all` is accepted for uniformity and removes the same one cache."""
        assert main(argv) == 0
        assert not cache.exists()
        assert json.loads(capsys.readouterr().out) == {
            "removed": str(cache),
            "bytes_freed": 13,
        }

    def test_clean_without_a_cache_names_nothing_removed(self, cache, capsys):
        main(["clean"])
        capsys.readouterr()
        assert main(["clean"]) == 0
        assert json.loads(capsys.readouterr().out) == {
            "removed": None,
            "bytes_freed": 0,
        }

    def test_a_document_named_clean_still_extracts(self, blank_pdf, tmp_path):
        """Dispatch is on the literal first argument, not on a path's stem."""
        named = tmp_path / "clean.pdf"
        named.write_bytes(blank_pdf.read_bytes())
        assert main([str(named)]) == 0


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
