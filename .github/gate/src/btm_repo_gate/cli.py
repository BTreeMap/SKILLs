"""The imperative shell: snapshot, audit, repair to a fixpoint, report."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from btm_repo_gate.conventions import FIXPOINT_ROUNDS, MARKETPLACE
from btm_repo_gate.repairs import Finding
from btm_repo_gate.rules import audit
from btm_repo_gate.snapshot import snapshot


def repair_to_fixpoint(root: Path) -> tuple[list[Finding], list[Finding]]:
    """Apply repairs until none remain, re-auditing between rounds so the
    verdict describes the tree as it now stands rather than as it was."""
    applied: list[Finding] = []
    findings = audit(snapshot(root))
    for _ in range(FIXPOINT_ROUNDS):
        pending = [(f, f.repair) for f in findings if f.repair is not None]
        if not pending:
            break
        # One writer per path per round: a repair deferred here re-derives
        # from the next round's fresh snapshot, so no update is ever lost.
        claimed: set[Path] = set()
        for finding, repair in pending:
            if repair.path in claimed:
                continue
            claimed.add(repair.path)
            repair.apply(root)
            applied.append(finding)
        findings = audit(snapshot(root))
    return applied, findings


def report(applied: Sequence[Finding], findings: Sequence[Finding]) -> int:
    """Print what was repaired and what remains, then fail if anything remains.

    The two remaining classes are reported separately because they ask for
    different actions: a mechanical finding asks for `fix`, and only a finding
    without a repair asks for a person. After `fix` the first class is empty
    unless a repair failed to settle, which is why it is still worth naming.
    """
    for finding in applied:
        print(f"repaired {finding.rule:<14} {finding.path}", file=sys.stderr)
    for finding in sorted(findings, key=lambda f: (f.repair is None, f.rule, f.path)):
        print(finding.render(), file=sys.stderr)
    mechanical = sum(f.repair is not None for f in findings)
    blocking = len(findings) - mechanical
    if mechanical:
        print(
            f"\n{mechanical} finding(s) are mechanical; run repo_gate.py fix.",
            file=sys.stderr,
        )
    if blocking:
        print(f"\n{blocking} finding(s) need a human.", file=sys.stderr)
    if findings:
        return 1
    print("repository conventions hold.", file=sys.stderr)
    return 0


def find_root(start: Path) -> Path:
    """Walk up to the repository the marketplace manifest marks.

    Derived from the working directory rather than from this file's depth, so
    moving a module cannot silently change which tree gets audited.
    """
    for candidate in (start, *start.parents):
        if (candidate / MARKETPLACE).is_file():
            return candidate
    raise SystemExit(f"not a skills repository: no {MARKETPLACE} above {start}")


def main(argv: Sequence[str]) -> int:
    mode = argv[0] if argv else "check"
    root = find_root(Path.cwd().resolve())
    match mode:
        case "check":
            return report((), audit(snapshot(root)))
        case "fix":
            return report(*repair_to_fixpoint(root))
        case _:
            print("usage: repo_gate.py [check | fix]", file=sys.stderr)
            return 2


def entrypoint() -> int:
    """Console-script boundary: argv selects the mode, cwd is the repository."""
    return main(sys.argv[1:])
