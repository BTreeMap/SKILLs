#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""Session engine for literature reviews over OpenAlex, arXiv, and Crossref.

The script owns the exact half of a review: session state, search logging,
identity resolution across DOI, arXiv id, and title, deduplication, decision
bookkeeping, and citation resolution checks. The invoking agent owns every
judgment call: criteria, screening, reading, synthesis. Subcommands print one
JSON document to stdout; advisory `signal:` lines go to stderr and never
block; failures print `error:` to stderr and exit 1.
"""

from __future__ import annotations

import argparse
import base64
import difflib
import hashlib
import http.client
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, fields, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OPENALEX_WORKS = "https://api.openalex.org/works"
ARXIV_QUERY = "https://export.arxiv.org/api/query"
CROSSREF_WORKS = "https://api.crossref.org/works"
DOI_HOST = "doi.org"
USER_AGENT_ENV = "BTM_USER_AGENT"
CONTACT_ENV = "BTM_CONTACT"
DEFAULT_CONTACT = "skills@oss.joefang.org"
TIMEOUT_SECONDS = 30
DEFAULT_LIMIT = 25
MAX_LIMIT = 100
ID_BATCH_SIZE = 50
COURTESY_PAUSE_SECONDS = 0.2
TITLE_MATCH_FLOOR = 0.6
ABSTRACT_SHOW_LIMIT = 1500
AUTHOR_SHOW_LIMIT = 6
HTTP_OK = 200
HTTP_BAD_REQUEST = 400

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"

STATUSES = ("candidate", "included", "excluded")
READ_LEVELS = ("none", "abstract", "full-text")
SOURCES = ("openalex", "arxiv", "crossref")
DIRECTIONS = ("backward", "forward")
DECISION_FIELDS = frozenset({"status", "reason", "read_level"})
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

ARXIV_ID = re.compile(r"(\d{4}\.\d{4,5})(?:v\d+)?$")
JATS_TAG = re.compile(r"<[^>]+>")
WHITESPACE = re.compile(r"\s+")
NON_ALNUM = re.compile(r"[^a-z0-9]+")


class CommandError(Exception):
    """Failure that ends the command with a clean message and exit code 1."""


# --- pure core: domain model ---


@dataclass(frozen=True, slots=True)
class Paper:
    """One deduplicated bibliographic record in the session corpus."""

    key: str
    title: str
    year: int | None
    authors: tuple[str, ...]
    venue: str | None
    doi: str | None
    arxiv_id: str | None
    openalex_id: str | None
    cited_by_count: int | None
    abstract: str | None
    pdf_url: str | None
    landing_url: str | None
    found_by: tuple[str, ...]
    status: str
    decision_reason: str | None
    read_level: str


def clean_text(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    collapsed = WHITESPACE.sub(" ", raw).strip()
    return collapsed or None


def normalize_doi(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    doi = raw.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        doi = doi.removeprefix(prefix)
    return doi if doi.startswith("10.") else None


def normalize_arxiv_id(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = ARXIV_ID.search(raw.strip())
    return match.group(1) if match else None


def normalize_title(title: str) -> str:
    return NON_ALNUM.sub(" ", title.lower()).strip()


def paper_key(doi: str | None, arxiv_id: str | None, title: str) -> str:
    if doi:
        return f"doi:{doi}"
    if arxiv_id:
        return f"arxiv:{arxiv_id}"
    return f"title:{normalize_title(title)}"


def paper_aliases(paper: Paper) -> Iterator[str]:
    if paper.doi:
        yield f"doi:{paper.doi}"
    if paper.arxiv_id:
        yield f"arxiv:{paper.arxiv_id}"
    yield f"title:{normalize_title(paper.title)}"


def candidate(**bibliographic: Any) -> Paper:
    """Smart constructor: derive the key, start unscreened."""
    doi = bibliographic.get("doi")
    arxiv_id = bibliographic.get("arxiv_id")
    title = bibliographic["title"]
    return Paper(
        key=paper_key(doi, arxiv_id, title),
        found_by=(),
        status="candidate",
        decision_reason=None,
        read_level="none",
        **bibliographic,
    )


def merge_papers(existing: Paper, incoming: Paper) -> Paper:
    """Bibliographic fields fill gaps; agent-owned decisions never move."""
    updates: dict[str, Any] = {}
    for name in (
        "year",
        "venue",
        "doi",
        "arxiv_id",
        "openalex_id",
        "abstract",
        "pdf_url",
        "landing_url",
    ):
        if getattr(existing, name) is None:
            updates[name] = getattr(incoming, name)
    counts = (existing.cited_by_count, incoming.cited_by_count)
    known_counts = [count for count in counts if count is not None]
    updates["cited_by_count"] = max(known_counts) if known_counts else None
    fresh = tuple(x for x in incoming.found_by if x not in existing.found_by)
    updates["found_by"] = existing.found_by + fresh
    return replace(existing, **updates)


def absorb(
    papers: dict[str, Paper], fetched: Iterable[Paper]
) -> tuple[dict[str, Paper], int]:
    """Fold fetched papers into the corpus; O(corpus + fetched)."""
    index = {
        alias: key for key, paper in papers.items() for alias in paper_aliases(paper)
    }
    result = dict(papers)
    new_count = 0
    for paper in fetched:
        hit = next((index[a] for a in paper_aliases(paper) if a in index), None)
        if hit is None:
            result[paper.key] = paper
            new_count += 1
            hit = paper.key
        else:
            result[hit] = merge_papers(result[hit], paper)
        for alias in paper_aliases(result[hit]):
            index.setdefault(alias, hit)
    return result, new_count


PAPER_FIELDS = frozenset(f.name for f in fields(Paper))


def paper_from_json(row: Mapping[str, Any]) -> Paper:
    """Parse boundary for state on disk; total: rejects corrupt records."""
    if set(row) != PAPER_FIELDS:
        unknown = sorted(set(row) - PAPER_FIELDS)
        missing = sorted(PAPER_FIELDS - set(row))
        raise CommandError(
            f"corrupt paper record for key {row.get('key')!r}: "
            f"unknown fields {unknown}, missing fields {missing}"
        )
    if row["status"] not in STATUSES or row["read_level"] not in READ_LEVELS:
        raise CommandError(f"corrupt paper record for key {row.get('key')!r}")
    data = dict(row)
    data["authors"] = tuple(data.get("authors") or ())
    data["found_by"] = tuple(data.get("found_by") or ())
    return Paper(**data)


# --- pure core: upstream record normalization ---


def reconstruct_abstract(inverted: Mapping[str, Sequence[int]] | None) -> str | None:
    if not inverted:
        return None
    positions = sorted(
        (position, word) for word, places in inverted.items() for position in places
    )
    return " ".join(word for _, word in positions) or None


def paper_from_openalex(work: Mapping[str, Any]) -> Paper:
    ids = work.get("ids") or {}
    source = (work.get("primary_location") or {}).get("source") or {}
    openalex_url = work.get("id") or ""
    return candidate(
        title=clean_text(work.get("display_name")) or "(untitled)",
        year=work.get("publication_year"),
        authors=tuple(
            name
            for name in (
                clean_text((entry.get("author") or {}).get("display_name"))
                for entry in work.get("authorships") or []
            )
            if name
        ),
        venue=clean_text(source.get("display_name")),
        doi=normalize_doi(work.get("doi")),
        arxiv_id=normalize_arxiv_id(str(ids.get("arxiv") or "")),
        openalex_id=openalex_url.rsplit("/", 1)[-1] or None,
        cited_by_count=work.get("cited_by_count"),
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        pdf_url=(work.get("open_access") or {}).get("oa_url"),
        landing_url=work.get("doi") or openalex_url or None,
    )


def paper_from_arxiv(entry: ET.Element) -> Paper:
    def text(tag: str) -> str | None:
        node = entry.find(ATOM + tag)
        return clean_text(node.text) if node is not None else None

    pdf_url = next(
        (
            link.get("href")
            for link in entry.findall(ATOM + "link")
            if link.get("title") == "pdf"
        ),
        None,
    )
    doi_node = entry.find(ARXIV_NS + "doi")
    published = text("published") or ""
    return candidate(
        title=text("title") or "(untitled)",
        year=int(published[:4]) if published[:4].isdigit() else None,
        authors=tuple(
            clean_text(node.text) or ""
            for node in entry.findall(f"{ATOM}author/{ATOM}name")
            if clean_text(node.text)
        ),
        venue=text("journal_ref"),
        doi=normalize_doi(doi_node.text if doi_node is not None else None),
        arxiv_id=normalize_arxiv_id(text("id") or ""),
        openalex_id=None,
        cited_by_count=None,
        abstract=text("summary"),
        pdf_url=pdf_url,
        landing_url=text("id"),
    )


def paper_from_crossref(item: Mapping[str, Any]) -> Paper:
    authors = tuple(
        name
        for name in (
            clean_text(f"{a.get('given', '')} {a.get('family', '')}")
            for a in item.get("author") or []
        )
        if name
    )
    issued = (item.get("issued") or {}).get("date-parts") or [[None]]
    abstract_raw = item.get("abstract")
    abstract = clean_text(JATS_TAG.sub(" ", abstract_raw)) if abstract_raw else None
    return candidate(
        title=clean_text(" ".join(item.get("title") or [])) or "(untitled)",
        year=issued[0][0] if issued[0] else None,
        authors=authors,
        venue=clean_text(" ".join(item.get("container-title") or [])),
        doi=normalize_doi(item.get("DOI")),
        arxiv_id=None,
        openalex_id=None,
        cited_by_count=item.get("is-referenced-by-count"),
        abstract=abstract,
        pdf_url=None,
        landing_url=item.get("URL"),
    )


# --- pure core: identifiers ---

NON_SLUG = re.compile(r"[^a-z0-9]+")
KEYWORD_RANGE = (2, 3)  # advisory band for minting keywords


def keywords_of(text: str) -> list[str]:
    return [part for part in NON_SLUG.sub("-", text.lower()).split("-") if part]


def slugify(words: Iterable[str]) -> str:
    cleaned = [part for word in words for part in keywords_of(str(word))]
    if not cleaned:
        raise CommandError("identifier keywords must contain letters or digits")
    return "-".join(cleaned)


def band_signal(stem: str) -> str | None:
    """Advisory for a stem outside the keyword band; None inside it."""
    low, high = KEYWORD_RANGE
    if low <= stem.count("-") + 1 <= high:
        return None
    return f"'{stem}': two or three keywords resolve best"


@dataclass(frozen=True, slots=True)
class Exact:
    id: str


@dataclass(frozen=True, slots=True)
class Recovered:
    id: str


@dataclass(frozen=True, slots=True)
class Ambiguous:
    candidates: tuple[str, ...]  # sorted


@dataclass(frozen=True, slots=True)
class NoMatch:
    pass


Resolution = Exact | Recovered | Ambiguous | NoMatch


def resolve(ref: str, ids: Iterable[str]) -> Resolution:
    """Total resolution: exact id, else the id containing every keyword.

    O(ids x keywords); pools stay in the low hundreds.
    """
    pool = list(ids)
    if ref in pool:
        return Exact(ref)
    keywords = keywords_of(ref)
    matches = [
        candidate
        for candidate in pool
        if keywords and all(keyword in candidate for keyword in keywords)
    ]
    if not matches:
        return NoMatch()
    if len(matches) > 1:
        return Ambiguous(tuple(sorted(matches)))
    return Recovered(matches[0])


# --- effect shell: HTTP ---


@dataclass(frozen=True, slots=True)
class CustomAgent:
    header: str


@dataclass(frozen=True, slots=True)
class Contact:
    address: str


def request_identity() -> CustomAgent | Contact:
    custom = os.environ.get(USER_AGENT_ENV)
    if custom:
        return CustomAgent(custom)
    return Contact(os.environ.get(CONTACT_ENV) or DEFAULT_CONTACT)


def user_agent() -> str:
    match request_identity():
        case CustomAgent(header):
            return header
        case Contact(address):
            return f"btm-skills/1.0 (lit-review; mailto:{address})"


def polite_params() -> dict[str, str]:
    """The `mailto` pool parameter OpenAlex and Crossref honor. Empty under a
    User-Agent override: the override owns identity, so nothing else marks
    the request."""
    match request_identity():
        case CustomAgent():
            return {}
        case Contact(address):
            return {"mailto": address}


def http_get(url: str, params: Mapping[str, str] | None = None) -> bytes:
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    request = urllib.request.Request(full, headers={"User-Agent": user_agent()})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except urllib.error.HTTPError as err:
        raise CommandError(f"HTTP {err.code} from {full}") from err
    except (urllib.error.URLError, TimeoutError) as err:
        raise CommandError(f"cannot reach {full}: {err}") from err


def http_get_json(url: str, params: Mapping[str, str] | None = None) -> Any:
    payload = http_get(url, params)
    try:
        return json.loads(payload)
    except json.JSONDecodeError as err:
        raise CommandError(f"non-JSON response from {url}") from err


def doi_resolution_status(doi: str) -> int:
    """HEAD https://doi.org/<doi> without following the redirect."""
    connection = http.client.HTTPSConnection(DOI_HOST, timeout=TIMEOUT_SECONDS)
    try:
        path = "/" + urllib.parse.quote(doi)
        connection.request("HEAD", path, headers={"User-Agent": user_agent()})
        return connection.getresponse().status
    except OSError as err:
        raise CommandError(f"cannot reach {DOI_HOST}: {err}") from err
    finally:
        connection.close()


def fetch_openalex(
    query: str, limit: int, from_year: int | None, to_year: int | None
) -> tuple[list[Paper], int]:
    params = {"search": query, "per-page": str(limit)}
    filters = []
    if from_year:
        filters.append(f"from_publication_date:{from_year}-01-01")
    if to_year:
        filters.append(f"to_publication_date:{to_year}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    params |= polite_params()
    body = http_get_json(OPENALEX_WORKS, params)
    total = (body.get("meta") or {}).get("count") or 0
    return [paper_from_openalex(work) for work in body.get("results") or []], total


def fetch_openalex_by_ids(openalex_ids: Sequence[str]) -> list[Paper]:
    papers: list[Paper] = []
    for start in range(0, len(openalex_ids), ID_BATCH_SIZE):
        batch = openalex_ids[start : start + ID_BATCH_SIZE]
        params = {
            "filter": "openalex_id:" + "|".join(batch),
            "per-page": str(ID_BATCH_SIZE),
        }
        body = http_get_json(OPENALEX_WORKS, params)
        papers.extend(paper_from_openalex(w) for w in body.get("results") or [])
        time.sleep(COURTESY_PAUSE_SECONDS)
    return papers


def fetch_arxiv(query: str, limit: int) -> tuple[list[Paper], int]:
    search_query = query if ":" in query else f'all:"{query}"'
    params = {"search_query": search_query, "max_results": str(limit)}
    root = ET.fromstring(http_get(ARXIV_QUERY, params))
    total_node = root.find(OPENSEARCH + "totalResults")
    total = int(total_node.text) if total_node is not None and total_node.text else 0
    return [paper_from_arxiv(entry) for entry in root.findall(ATOM + "entry")], total


def fetch_crossref(
    query: str, limit: int, from_year: int | None, to_year: int | None
) -> tuple[list[Paper], int]:
    params = {"query": query, "rows": str(limit)}
    filters = []
    if from_year:
        filters.append(f"from-pub-date:{from_year}-01-01")
    if to_year:
        filters.append(f"until-pub-date:{to_year}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    params |= polite_params()
    message = http_get_json(CROSSREF_WORKS, params).get("message") or {}
    total = message.get("total-results") or 0
    return [paper_from_crossref(item) for item in message.get("items") or []], total


# --- effect shell: session state ---


@dataclass(frozen=True, slots=True)
class Session:
    root: Path

    @property
    def protocol_path(self) -> Path:
        return self.root / "protocol.json"

    @property
    def papers_path(self) -> Path:
        return self.root / "papers.jsonl"

    @property
    def log_path(self) -> Path:
        return self.root / "search_log.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def state_root() -> Path:
    """Durable-state home for this skill, per repository convention."""
    if os.name == "nt":
        base = Path(
            os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        )
    else:
        base = Path(
            os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
        )
    return base / "btm-skills" / "lit-review"


def sessions_root() -> Path:
    return state_root() / "sessions"


def suffix() -> str:
    """128 bits of entropy, base32hex, lowercase: uniqueness is the script's job."""
    return base64.b32hexencode(os.urandom(16)).decode().rstrip("=").lower()


def mint(words: Iterable[str]) -> str:
    return f"{slugify(words)}-{suffix()}"


def session_ids() -> list[str]:
    root = sessions_root()
    if not root.exists():
        return []
    return sorted(entry.name for entry in root.iterdir() if entry.is_dir())


def is_pathlike(argument: str) -> bool:
    return (
        os.sep in argument
        or (os.altsep is not None and os.altsep in argument)
        or argument.startswith(("~", "."))
    )


def resolved_session(ref: str) -> Path:
    """Eliminate a session Resolution at the shell, rendering its signal."""
    match resolve(ref, session_ids()):
        case Exact(sid):
            return sessions_root() / sid
        case Recovered(sid):
            signal(f"recovered session '{ref}' -> {sid}; use the full identifier")
            return sessions_root() / sid
        case Ambiguous(candidates):
            raise CommandError(
                f"'{ref}' is ambiguous across sessions: {', '.join(candidates)}"
            )
        case NoMatch():
            raise CommandError(f"no session matches '{ref}'; run init first")
    raise AssertionError("unreachable: Resolution is a closed union")


def session_path(argument: str) -> Path:
    if is_pathlike(argument):
        return Path(argument).expanduser()
    return resolved_session(argument)


def tree_bytes(path: Path) -> int:
    """Total size of the regular files under a directory."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def open_session(root: str) -> Session:
    session = Session(session_path(root))
    if not session.protocol_path.is_file():
        raise CommandError(f"no session at {session.root}: run init first")
    return session


def load_protocol(session: Session) -> dict[str, Any]:
    try:
        protocol = json.loads(session.protocol_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise CommandError(f"unreadable protocol.json: {err}") from err
    if not isinstance(protocol, dict):
        raise CommandError("protocol.json must hold a JSON object")
    return protocol


def criteria_hash(protocol: Mapping[str, Any]) -> str:
    canonical = json.dumps(protocol.get("criteria"), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def require_criteria(protocol: Mapping[str, Any]) -> None:
    criteria = protocol.get("criteria") or {}
    if not criteria.get("include") or not criteria.get("exclude"):
        raise CommandError(
            "protocol.json has empty inclusion or exclusion criteria; "
            "fill both lists before searching (criteria precede search)"
        )


def load_papers(session: Session) -> dict[str, Paper]:
    papers: dict[str, Paper] = {}
    for line in session.papers_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            paper = paper_from_json(json.loads(line))
            papers[paper.key] = paper
    return papers


def atomic_write(path: Path, content: str) -> None:
    scratch = path.with_suffix(path.suffix + ".tmp")
    scratch.write_text(content, encoding="utf-8")
    os.replace(scratch, path)


def save_papers(session: Session, papers: Mapping[str, Paper]) -> None:
    lines = [json.dumps(asdict(paper), ensure_ascii=False) for paper in papers.values()]
    atomic_write(session.papers_path, "\n".join(lines) + ("\n" if lines else ""))


def read_log(session: Session) -> list[dict[str, Any]]:
    lines = session.log_path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def append_log(session: Session, entry: Mapping[str, Any]) -> None:
    with session.log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def emit(document: Mapping[str, Any]) -> None:
    print(json.dumps(document, indent=2, ensure_ascii=False))


def signal(message: str) -> None:
    print(f"signal: {message}", file=sys.stderr)


# --- subcommands ---


def record_fetch(
    session: Session,
    entry: dict[str, Any],
    fetched: list[Paper],
    total: int,
    limit: int,
) -> None:
    """Shared tail of search and snowball: absorb, log, report."""
    log_id = f"s{len(read_log(session)) + 1}"
    papers = load_papers(session)
    stamped = [replace(paper, found_by=(log_id,)) for paper in fetched]
    papers, new_count = absorb(papers, stamped)
    save_papers(session, papers)
    truncated = total > len(fetched)
    entry.update(
        {
            "id": log_id,
            "time": now_iso(),
            "fetched": len(fetched),
            "new": new_count,
            "total_matches": total,
            "truncated": truncated,
        }
    )
    append_log(session, entry)
    if truncated:
        signal(
            f"{total} matches upstream but only {len(fetched)} fetched; "
            f"narrow the query or raise --limit (cap {MAX_LIMIT})"
        )
    emit({**entry, "corpus_size": len(papers)})


def cmd_init(args: argparse.Namespace) -> int:
    if is_pathlike(args.session):
        root = Path(args.session).expanduser()
        name = str(root)
    else:
        name = mint(args.session.split())
        if advice := band_signal(name.rsplit("-", 1)[0]):
            signal(advice)
        root = sessions_root() / name
    session = Session(root)
    if session.protocol_path.exists():
        raise CommandError(f"session already exists at {root}; refusing to overwrite")
    root.mkdir(parents=True, exist_ok=True)
    protocol = {
        "question": args.question,
        "level": args.level,
        "criteria": {"include": [], "exclude": []},
        "created": now_iso(),
        "amendments": [],
    }
    atomic_write(session.protocol_path, json.dumps(protocol, indent=2) + "\n")
    session.papers_path.touch()
    session.log_path.touch()
    emit({"session": name, "next": "fill criteria lists in protocol.json"})
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    protocol = load_protocol(session)
    require_criteria(protocol)
    limit = min(args.limit, MAX_LIMIT)
    if args.source == "openalex":
        fetched, total = fetch_openalex(args.query, limit, args.from_year, args.to_year)
    elif args.source == "arxiv":
        if args.from_year or args.to_year:
            signal("arxiv source ignores year bounds; filter after fetching")
        fetched, total = fetch_arxiv(args.query, limit)
    else:
        fetched, total = fetch_crossref(args.query, limit, args.from_year, args.to_year)
    entry = {
        "command": "search",
        "source": args.source,
        "query": args.query,
        "from_year": args.from_year,
        "to_year": args.to_year,
        "limit": limit,
        "criteria_hash": criteria_hash(protocol),
    }
    record_fetch(session, entry, fetched, total, limit)
    return 0


def resolve_openalex_id(papers: Mapping[str, Paper], token: str) -> tuple[str, str]:
    """Return (paper key, OpenAlex work id) for a key, DOI, or arXiv id."""
    index = {
        alias: key for key, paper in papers.items() for alias in paper_aliases(paper)
    }
    key = token if token in papers else index.get(token)
    if key is None:
        doi = normalize_doi(token)
        arxiv_id = normalize_arxiv_id(token)
        key = index.get(f"doi:{doi}") or index.get(f"arxiv:{arxiv_id}")
    if key is None:
        raise CommandError(f"no corpus paper matches {token!r}; search for it first")
    paper = papers[key]
    if paper.openalex_id:
        return key, paper.openalex_id
    if paper.doi:
        work = http_get_json(f"{OPENALEX_WORKS}/doi:{paper.doi}")
        openalex_id = str(work.get("id") or "").rsplit("/", 1)[-1]
        if openalex_id:
            return key, openalex_id
    raise CommandError(
        f"paper {key} has no OpenAlex id or DOI; snowball needs one of them"
    )


def cmd_snowball(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    protocol = load_protocol(session)
    require_criteria(protocol)
    limit = min(args.limit, MAX_LIMIT)
    papers = load_papers(session)
    seed_key, work_id = resolve_openalex_id(papers, args.seed)
    if args.direction == "backward":
        work = http_get_json(f"{OPENALEX_WORKS}/{work_id}")
        referenced = [
            url.rsplit("/", 1)[-1] for url in work.get("referenced_works") or []
        ]
        total = len(referenced)
        if not referenced:
            signal(
                f"OpenAlex lists no references for {seed_key}: upstream metadata "
                "gap; snowball another seed or read the paper's own reference list"
            )
        fetched = fetch_openalex_by_ids(referenced[:limit])
    else:
        params = {"filter": f"cites:{work_id}", "per-page": str(limit)}
        body = http_get_json(OPENALEX_WORKS, params)
        total = (body.get("meta") or {}).get("count") or 0
        fetched = [paper_from_openalex(w) for w in body.get("results") or []]
    entry = {
        "command": "snowball",
        "seed": seed_key,
        "direction": args.direction,
        "limit": limit,
        "criteria_hash": criteria_hash(protocol),
    }
    record_fetch(session, entry, fetched, total, limit)
    return 0


def validate_decision(
    key: str, decision: Mapping[str, Any], papers: Mapping[str, Paper]
) -> None:
    if key not in papers:
        raise CommandError(f"decision names unknown paper key {key!r}")
    unknown = set(decision) - DECISION_FIELDS
    if unknown:
        raise CommandError(f"decision for {key} has unknown fields {sorted(unknown)}")
    status = decision.get("status")
    if status is not None and status not in STATUSES:
        raise CommandError(f"decision for {key} has invalid status {status!r}")
    if status == "excluded" and not clean_text(decision.get("reason")):
        raise CommandError(f"exclusion of {key} needs a non-empty reason")
    read_level = decision.get("read_level")
    if read_level is not None and read_level not in READ_LEVELS:
        raise CommandError(f"decision for {key} has invalid read_level {read_level!r}")


def cmd_update(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    raw = sys.stdin.read()
    if not raw.strip():
        raise CommandError("update reads the decisions JSON from stdin")
    try:
        decisions = json.loads(raw)
    except json.JSONDecodeError as err:
        raise CommandError(f"unreadable decisions JSON on stdin: {err}") from err
    if not isinstance(decisions, dict):
        raise CommandError("decisions must map paper keys to decision objects")
    papers = load_papers(session)
    for key, decision in decisions.items():
        validate_decision(key, decision, papers)
    changed = Counter()
    for key, decision in decisions.items():
        updates: dict[str, Any] = {}
        if "status" in decision:
            updates["status"] = decision["status"]
            changed[decision["status"]] += 1
        if "reason" in decision:
            updates["decision_reason"] = clean_text(decision["reason"])
        if "read_level" in decision:
            updates["read_level"] = decision["read_level"]
            changed[f"read:{decision['read_level']}"] += 1
        papers[key] = replace(papers[key], **updates)
    save_papers(session, papers)
    emit({"applied": len(decisions), "changes": dict(changed)})
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    matching = [
        paper for paper in load_papers(session).values() if paper.status == args.status
    ]
    matching.sort(key=lambda paper: -(paper.cited_by_count or 0))
    shown = []
    for paper in matching[: args.limit]:
        abstract = paper.abstract
        if abstract and len(abstract) > ABSTRACT_SHOW_LIMIT:
            abstract = abstract[:ABSTRACT_SHOW_LIMIT] + " [truncated]"
        shown.append(
            {
                "key": paper.key,
                "title": paper.title,
                "year": paper.year,
                "authors": list(paper.authors[:AUTHOR_SHOW_LIMIT]),
                "author_count": len(paper.authors),
                "venue": paper.venue,
                "citations": paper.cited_by_count,
                "read_level": paper.read_level,
                "abstract": abstract,
            }
        )
    if len(matching) > args.limit:
        signal(f"{len(matching) - args.limit} more {args.status} papers not shown")
    emit({"status": args.status, "total": len(matching), "papers": shown})
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    protocol = load_protocol(session)
    papers = load_papers(session)
    log = read_log(session)
    by_status = Counter(paper.status for paper in papers.values())
    by_read = Counter(
        paper.read_level for paper in papers.values() if paper.status == "included"
    )
    current_hash = criteria_hash(protocol)
    logged_hashes = {entry.get("criteria_hash") for entry in log}
    if logged_hashes and logged_hashes != {current_hash}:
        signal(
            "criteria changed after searches ran; record the change in "
            "protocol.json amendments"
        )
    criteria = protocol.get("criteria") or {}
    emit(
        {
            "question": protocol.get("question"),
            "level": protocol.get("level"),
            "criteria_ready": bool(criteria.get("include"))
            and bool(criteria.get("exclude")),
            "criteria_hash": current_hash,
            "searches": len(log),
            "papers": dict(by_status),
            "included_read_levels": dict(by_read),
            "undecided": by_status.get("candidate", 0),
        }
    )
    return 0


def verify_one(paper: Paper) -> dict[str, Any]:
    result: dict[str, Any] = {"key": paper.key, "title": paper.title}
    if paper.doi:
        status = doi_resolution_status(paper.doi)
        result["doi_resolves"] = status in REDIRECT_STATUSES or status == HTTP_OK
        result["doi_http_status"] = status
        try:
            message = http_get_json(f"{CROSSREF_WORKS}/{paper.doi}").get("message")
        except CommandError:
            message = None
        if message and message.get("title"):
            registered = clean_text(" ".join(message["title"])) or ""
            ratio = difflib.SequenceMatcher(
                None, normalize_title(paper.title), normalize_title(registered)
            ).ratio()
            result["crossref_title_match"] = round(ratio, 2)
            if ratio < TITLE_MATCH_FLOOR:
                signal(
                    f"{paper.key}: corpus title diverges from Crossref record "
                    f"({registered!r}); check for a mangled citation"
                )
        else:
            result["crossref_title_match"] = None
            signal(
                f"{paper.key}: no Crossref metadata (DataCite DOIs such as "
                "arXiv resolve but are not title-checked here)"
            )
    elif paper.arxiv_id:
        result["doi_resolves"] = None
        result["identity"] = f"arXiv:{paper.arxiv_id} (no DOI; not registrar-checked)"
    else:
        result["doi_resolves"] = None
        result["identity"] = "title-only record; verify against the source by hand"
    time.sleep(COURTESY_PAUSE_SECONDS)
    return result


def cmd_clean(args: argparse.Namespace) -> int:
    root = sessions_root()
    if args.all and args.session:
        raise CommandError("pass a session or --all, one of the two")
    if args.all:
        if not root.is_dir():
            emit({"removed": None, "bytes_freed": 0})
            return 0
        freed = tree_bytes(root)
        shutil.rmtree(root)
        emit({"removed": str(root), "bytes_freed": freed})
        return 0
    if args.session is None:
        listing = (
            [
                {"session": entry.name, "bytes": tree_bytes(entry)}
                for entry in sorted(root.iterdir())
                if entry.is_dir()
            ]
            if root.is_dir()
            else []
        )
        emit(
            {
                "sessions_root": str(root),
                "sessions": listing,
                "next": "pass a session identifier or --all to remove and free space",
            }
        )
        return 0
    target = session_path(args.session)
    if not (target / "protocol.json").is_file():
        raise CommandError(
            f"{target} holds no session (protocol.json absent); refusing to remove"
        )
    freed = tree_bytes(target)
    shutil.rmtree(target)
    emit({"removed": str(target), "bytes_freed": freed})
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    included = [
        paper for paper in load_papers(session).values() if paper.status == "included"
    ]
    if not included:
        raise CommandError("no included papers to verify; screen the corpus first")
    unread = [paper.key for paper in included if paper.read_level == "none"]
    if unread:
        signal(f"included but unread (read_level none): {', '.join(unread)}")
    results = [verify_one(paper) for paper in included]
    broken = [r["key"] for r in results if r.get("doi_resolves") is False]
    emit(
        {
            "checked": len(results),
            "broken_dois": broken,
            "results": results,
        }
    )
    return 0


# --- CLI ---


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "session",
        help="session identifier (kept under the XDG state root) or directory",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lit_review.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create a review session")
    add_common(init)
    init.add_argument("--question", required=True, help="the research question")
    init.add_argument("--level", choices=("lite", "full", "ultra"), default="full")
    init.set_defaults(func=cmd_init)

    search = commands.add_parser("search", help="run one logged search")
    add_common(search)
    search.add_argument("--source", choices=SOURCES, required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    search.add_argument("--from-year", type=int, default=None)
    search.add_argument("--to-year", type=int, default=None)
    search.set_defaults(func=cmd_search)

    snowball = commands.add_parser(
        "snowball", help="follow citations of a corpus paper via OpenAlex"
    )
    add_common(snowball)
    snowball.add_argument("--seed", required=True, help="paper key, DOI, or arXiv id")
    snowball.add_argument("--direction", choices=DIRECTIONS, required=True)
    snowball.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    snowball.set_defaults(func=cmd_snowball)

    show = commands.add_parser("show", help="print papers for screening")
    add_common(show)
    show.add_argument("--status", choices=STATUSES, default="candidate")
    show.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    show.set_defaults(func=cmd_show)

    update = commands.add_parser(
        "update",
        help='apply screening decisions; stdin JSON: {"<key>": {"status": ...,'
        ' "reason": ..., "read_level": ...}}',
    )
    add_common(update)
    update.set_defaults(func=cmd_update)

    status = commands.add_parser("status", help="session counts and advisories")
    add_common(status)
    status.set_defaults(func=cmd_status)

    verify = commands.add_parser("verify", help="check DOIs of included papers")
    add_common(verify)
    verify.set_defaults(func=cmd_verify)

    clean = commands.add_parser(
        "clean", help="list sessions, or remove one (or --all) and free the space"
    )
    clean.add_argument("session", nargs="?", help="session name or directory")
    clean.add_argument("--all", action="store_true")
    clean.set_defaults(func=cmd_clean)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CommandError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
