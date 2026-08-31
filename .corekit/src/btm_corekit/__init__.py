"""btm-corekit: the shared symbolic kernel for SKILLs bundled scripts.

One module per algebra, each testable alone; this package re-exports the
whole surface, so consumers import from `btm_corekit` and never from a
submodule. Consumers declare this package as a workspace dependency, so a
skill runs from a full repository checkout and a script copied out alone
fails loudly at environment build.
"""

from __future__ import annotations

from btm_corekit.channels import emit, signal
from btm_corekit.cli import run_cli
from btm_corekit.clock import now_iso
from btm_corekit.errors import CommandError, UpstreamError
from btm_corekit.fsio import (
    append_jsonl,
    read_jsonl,
    state_root,
    tree_bytes,
    write_atomic,
)
from btm_corekit.identifiers import (
    KEYWORD_RANGE,
    Ambiguous,
    Exact,
    NoMatch,
    Recovered,
    Resolution,
    band_signal,
    eliminate,
    is_pathlike,
    keywords_of,
    mint,
    resolve,
    slugify,
    suffix,
)
from btm_corekit.origin import (
    Contact,
    CustomAgent,
    RequestIdentity,
    polite_params,
    request_identity,
    user_agent,
)
from btm_corekit.pad import jot, pad_body, pad_entries, pad_ids, recall
from btm_corekit.sessions import SessionStore
from btm_corekit.verdicts import Diagnostic

__all__ = [
    "KEYWORD_RANGE",
    "Ambiguous",
    "CommandError",
    "Contact",
    "CustomAgent",
    "Diagnostic",
    "Exact",
    "NoMatch",
    "Recovered",
    "RequestIdentity",
    "Resolution",
    "SessionStore",
    "UpstreamError",
    "append_jsonl",
    "band_signal",
    "eliminate",
    "emit",
    "is_pathlike",
    "jot",
    "keywords_of",
    "mint",
    "now_iso",
    "pad_body",
    "pad_entries",
    "pad_ids",
    "polite_params",
    "read_jsonl",
    "recall",
    "request_identity",
    "resolve",
    "run_cli",
    "signal",
    "slugify",
    "state_root",
    "suffix",
    "tree_bytes",
    "user_agent",
    "write_atomic",
]
