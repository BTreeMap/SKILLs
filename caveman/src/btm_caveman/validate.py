"""Structural equality between the original body and its compression."""

from __future__ import annotations

from itertools import chain

from btm_caveman.markdown import (
    BULLET_REGEX,
    extract_headings,
    extract_inline_codes,
    extract_paths,
    extract_urls,
    partition_fences,
    partition_indented,
)
from btm_caveman.model import Verdict


def _check_headings(original: str, compressed: str) -> Verdict:
    orig, comp = extract_headings(original), extract_headings(compressed)
    if orig != comp:
        return Verdict(
            errors=(f"Headings not preserved exactly: {len(orig)} vs {len(comp)}",)
        )
    return Verdict()


def _check_code_blocks(original: str, compressed: str) -> Verdict:
    orig_fences, orig_rest = partition_fences(original)
    comp_fences, comp_rest = partition_fences(compressed)
    errors = []
    if orig_fences != comp_fences:
        errors.append("Fenced code blocks not preserved exactly (content, order)")
    if partition_indented(orig_rest)[0] != partition_indented(comp_rest)[0]:
        errors.append("Indented code blocks not preserved exactly (content, order)")
    return Verdict(errors=tuple(errors))


def _check_urls(original: str, compressed: str) -> Verdict:
    orig, comp = extract_urls(original), extract_urls(compressed)
    if orig != comp:
        return Verdict(
            errors=(f"URL mismatch: lost={set(orig - comp)}, added={set(comp - orig)}",)
        )
    return Verdict()


def _check_inline_codes(original: str, compressed: str) -> Verdict:
    orig, comp = extract_inline_codes(original), extract_inline_codes(compressed)
    lost, added = orig - comp, comp - orig
    return Verdict(
        errors=(f"Inline code lost: {sorted(lost)}",) if lost else (),
        warnings=(f"Inline code added: {sorted(added)}",) if added else (),
    )


def _check_paths(original: str, compressed: str) -> Verdict:
    orig, comp = extract_paths(original), extract_paths(compressed)
    if orig != comp:
        return Verdict(
            warnings=(
                f"Path mismatch: lost={set(orig - comp)}, added={set(comp - orig)}",
            )
        )
    return Verdict()


def _check_bullets(original: str, compressed: str) -> Verdict:
    orig = len(BULLET_REGEX.findall(original))
    comp = len(BULLET_REGEX.findall(compressed))
    # Allow 15% bullet-count drift.
    if orig and abs(orig - comp) / orig > 0.15:  # noqa: PLR2004
        return Verdict(warnings=(f"Bullet count drifted: {orig} -> {comp}",))
    return Verdict()


CHECKS = (
    _check_headings,
    _check_code_blocks,
    _check_urls,
    _check_inline_codes,
    _check_paths,
    _check_bullets,
)


def validate(original: str, compressed: str) -> Verdict:
    """Concatenate the independent checks' findings, in CHECKS order."""
    results = [check(original, compressed) for check in CHECKS]
    return Verdict(
        errors=tuple(chain.from_iterable(v.errors for v in results)),
        warnings=tuple(chain.from_iterable(v.warnings for v in results)),
    )
