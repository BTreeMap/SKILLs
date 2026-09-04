"""Parse, do not validate: the one place a file becomes a Plan or a Refusal."""

from __future__ import annotations

from pathlib import Path

from btm_caveman.classify import assess
from btm_caveman.markdown import split_frontmatter
from btm_caveman.model import MAX_FILE_SIZE, Admission, FileKind, Plan, Refusal
from btm_caveman.sensitive import is_sensitive
from btm_caveman.store import backup_base, read_utf8

# Guidance the agent receives alongside a non-prose assessment. Advisory:
# the agent weighs it against user intent; the backup keeps either call safe.
KIND_GUIDANCE = {
    FileKind.CODE: (
        "assessed as CODE: compress only when the user named this exact file"
    ),
    FileKind.CONFIG: ("assessed as CONFIG/DATA: compress only on explicit user intent"),
    FileKind.UNKNOWN: ("assessment inconclusive: read the file, judge prose yourself"),
}


def admit(path: Path) -> Admission:  # noqa: PLR0911
    """Parse, don't validate: every refusal reason lives here, once.

    Refusals are exact invariants only; heuristic judgment becomes advisory
    notes on the Plan instead.
    """
    # Preserve distinct refusal reasons and exit statuses.
    path = path.resolve()
    if not path.is_file():
        return Refusal(f"Not a file: {path}")
    if is_sensitive(path):
        return Refusal(
            f"Refusing {path.name}: filename looks sensitive (credentials, keys,"
            " secrets, or known private paths). Rename it if this is a false positive."
        )
    if path.name.endswith(".original.md") or backup_base().resolve() in path.parents:
        return Refusal("Refusing to compress a backup file")
    if path.stat().st_size > MAX_FILE_SIZE:
        return Refusal(f"File exceeds {MAX_FILE_SIZE // 1000}KB; split it first")
    text = read_utf8(path)
    if text is None:
        return Refusal("File is not valid UTF-8")
    if not text.strip():
        return Refusal("File is empty or whitespace-only")
    frontmatter, body = split_frontmatter(text)
    if not body.strip():
        return Refusal("Body is empty after frontmatter removal")
    assessment = assess(path, text)
    notes = assessment.signals
    if assessment.kind is not FileKind.NATURAL_LANGUAGE:
        notes = (KIND_GUIDANCE[assessment.kind], *notes)
    return Plan(path=path, frontmatter=frontmatter, body=body, notes=notes)
