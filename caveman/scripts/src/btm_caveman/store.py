"""Filesystem effects: identified backup slots."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

from btm_corekit import CommandError, Model, SessionStore

UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")
"""Everything a directory component may not carry, replaced in one C pass."""

STORE = SessionStore("caveman", marker="meta.json", hint="run prepare first")
"""One slot per target file, under the skill's state root."""


class SlotMeta(Model):
    """The identity a slot records: the one file its backup belongs to."""

    source: str


def backup_base() -> Path:
    """Out-of-tree backup root, so skill auto-loaders never re-ingest backups."""
    return STORE.root()


@dataclass(frozen=True, slots=True)
class BackupSlot:
    """One target's backup directory plus the source path it must belong to."""

    directory: Path
    source: Path

    @property
    def backup_path(self) -> Path:
        return self.directory / "original.md"

    @property
    def body_path(self) -> Path:
        return self.directory / "body.md"

    @property
    def meta_path(self) -> Path:
        return STORE.meta_path(self.directory)


def slot_for(target: Path) -> BackupSlot:
    """Derive the backup slot for a resolved path: `slug(name)-16hex(sha256(path))`.

    Deterministic and total over any representable filename. A hash collision
    is still safe: `load_slot` proves identity against meta.json before use.
    """
    digest = hashlib.sha256(os.fsencode(target)).hexdigest()[:16]
    slug = UNSAFE_NAME.sub("_", target.name[:64]) or "file"
    return BackupSlot(directory=STORE.root() / f"{slug}-{digest}", source=target)


def read_meta(slot: BackupSlot) -> SlotMeta | None:
    """The identity a slot records, or None when no meta.json is there: an
    absent marker means unprepared, and a malformed one is a rejection."""
    if not slot.meta_path.is_file():
        return None
    return STORE.read_meta(slot.directory, SlotMeta)


def load_slot(target: Path) -> BackupSlot:
    """The one trusted way to reach an existing backup: prove identity first."""
    slot = slot_for(target)
    if not slot.backup_path.is_file():
        raise CommandError(f"no backup found at {slot.backup_path}; run prepare first")
    meta = read_meta(slot)
    if meta is None:
        raise CommandError(
            f"backup metadata missing: {slot.meta_path}; refusing to touch this"
            " slot (clean <file> removes it)"
        )
    if meta.source != str(target):
        raise CommandError(
            f"backup identity mismatch: {slot.directory} records {meta.source};"
            " refusing to touch another file's backup"
        )
    return slot


def read_utf8(path: Path) -> str:
    """Strict UTF-8 read; undecodable bytes reject, never silent corruption."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise CommandError(f"not valid UTF-8: {path}") from None
