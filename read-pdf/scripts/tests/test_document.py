"""The decrypt boundary: what opens for free, what demands a password, and
what each refusal tells the caller to do about it."""

from __future__ import annotations

import sys

import pytest
from pypdf import PdfReader, PdfWriter

from btm_corekit import CommandError
from btm_read_pdf.document import decrypt_if_needed, open_output


def written(path, **encryption) -> PdfReader:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    if encryption:
        writer.encrypt(**encryption)
    with path.open("wb") as handle:
        writer.write(handle)
    return PdfReader(path, strict=False)


class TestDecrypt:
    def test_an_unencrypted_reader_is_left_alone(self, tmp_path, capsys):
        decrypt_if_needed(written(tmp_path / "plain.pdf"), None)
        assert capsys.readouterr().err == ""

    def test_an_owner_locked_pdf_opens_without_a_password(self, tmp_path, capsys):
        """Encrypted but readable with the empty user password. That attempt is
        deterministic and free, so it never becomes the caller's problem."""
        reader = written(
            tmp_path / "owner.pdf", user_password="", owner_password="secret"
        )
        decrypt_if_needed(reader, None)
        assert "owner-locked only" in capsys.readouterr().err
        assert reader.pages[0] is not None

    def test_a_user_password_without_password_env_names_the_flag(self, tmp_path):
        reader = written(tmp_path / "locked.pdf", user_password="hunter2")
        with pytest.raises(CommandError, match="--password-env"):
            decrypt_if_needed(reader, None)

    def test_an_unset_variable_is_refused_by_name(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PDF_PW", raising=False)
        reader = written(tmp_path / "locked.pdf", user_password="hunter2")
        with pytest.raises(CommandError, match="'PDF_PW'"):
            decrypt_if_needed(reader, "PDF_PW")

    def test_an_empty_variable_reads_as_unset(self, tmp_path, monkeypatch):
        """An empty user password is already tried above, so a variable set to
        the empty string carries no information the caller has not had."""
        monkeypatch.setenv("PDF_PW", "")
        reader = written(tmp_path / "locked.pdf", user_password="hunter2")
        with pytest.raises(CommandError, match="empty or not set"):
            decrypt_if_needed(reader, "PDF_PW")

    def test_a_wrong_password_is_refused(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PDF_PW", "wrong")
        reader = written(tmp_path / "locked.pdf", user_password="hunter2")
        with pytest.raises(CommandError, match="could not decrypt"):
            decrypt_if_needed(reader, "PDF_PW")

    def test_the_right_password_opens_the_document(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PDF_PW", "hunter2")
        reader = written(tmp_path / "locked.pdf", user_password="hunter2")
        decrypt_if_needed(reader, "PDF_PW")
        assert len(reader.pages) == 1


class TestOutputSink:
    def test_a_path_opens_a_utf8_file(self, tmp_path):
        target = tmp_path / "out.txt"
        with open_output(target) as handle:
            handle.write("ünïcode\n")
        assert target.read_text(encoding="utf-8") == "ünïcode\n"

    def test_no_path_leaves_stdout_owned_by_its_caller(self, capsys):
        with open_output(None) as handle:
            assert handle is sys.stdout
        assert sys.stdout is not None  # the context manager closed nothing
