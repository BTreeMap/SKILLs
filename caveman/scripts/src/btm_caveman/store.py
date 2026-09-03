"""Filesystem effects: identified backup slots."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from btm_caveman.model import Refusal
from btm_corekit import state_root

SAFE_NAME_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
)


def backup_base() -> Path:
    """Out-of-tree backup root so skill auto-loaders never re-ingest backups.

    Durable state lands in the library's unified namespace, whose location the
    kernel owns, so every skill agrees on where its state lives.
    """
    return state_root("caveman") / "backups"


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
        return self.directory / "meta.json"


def slot_for(target: Path) -> BackupSlot:
    """Derive the backup slot for a resolved path.

    The rule: slug(name) + "-" + first 16 hex of sha256(fsencode(path)).
    Deterministic (a pure function of the path) and total (os.fsencode hashes
    any representable filename, including non-UTF-8 surrogates). The digest
    makes accidental collision ~n^2/2^65; `load_slot` then proves identity
    against meta.json, so even a collision refuses instead of touching another
    file's backup. The component is ASCII, <= 81 bytes, and separator-free.
    """
    digest = hashlib.sha256(os.fsencode(target)).hexdigest()[:16]
    slug = (
        "".join(c if c in SAFE_NAME_CHARS else "_" for c in target.name[:64]) or "file"
    )
    return BackupSlot(directory=backup_base() / f"{slug}-{digest}", source=target)


def recorded_source(slot: BackupSlot) -> str | None:
    """The source path a slot's meta.json claims, or None if absent/corrupt."""
    raw = read_utf8(slot.meta_path) if slot.meta_path.is_file() else None
    if raw is None:
        return None
    try:
        meta = json.loads(raw)
    except ValueError:
        return None
    source = meta.get("source") if isinstance(meta, dict) else None
    return source if isinstance(source, str) else None


def load_slot(target: Path) -> BackupSlot | Refusal:
    """The one trusted way to reach an existing backup: prove identity first."""
    slot = slot_for(target)
    if not slot.backup_path.is_file():
        return Refusal(f"no backup found at {slot.backup_path}; run prepare first")
    recorded = recorded_source(slot)
    if recorded is None:
        return Refusal(
            f"backup metadata missing or unreadable: {slot.meta_path}; refusing to"
            " touch this slot (clean <file> removes it)"
        )
    if recorded != str(target):
        return Refusal(
            f"backup identity mismatch: {slot.directory} records {recorded};"
            " refusing to touch another file's backup"
        )
    return slot


def read_utf8(path: Path) -> str | None:
    """Strict UTF-8 read; None means undecodable, never silent corruption."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


# Guidance the agent receives alongside a non-prose assessment. Advisory:
