"""Public Telegram channels through the no-login preview `t.me/s/<channel>`:
each load takes every post newer than the store holds, then walks history
back until the channel's bound; the store is the checkpoint."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
import lxml.etree
import lxml.html

from btm_corekit import (
    CommandError,
    Pace,
    UpstreamError,
    get_bytes,
    is_digits,
    patient,
    signal,
)
from btm_finance.data.posts import Post, Posts, Preview, of_channel
from btm_finance.data.sources import client
from btm_finance.models import Bound, TelegramConfig

PREVIEW = "https://t.me/s/{channel}"
INTERVAL = 1.0
CAP = 4 * 1024 * 1024
SCALE = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
MEDIA = (
    ("photo", ("tgme_widget_message_photo_wrap",)),
    ("video", ("tgme_widget_message_video_player",)),
    ("voice", ("tgme_widget_message_voice",)),
    ("document", ("tgme_widget_message_document",)),
    ("poll", ("tgme_widget_message_poll",)),
    (
        "sticker",
        (
            "tgme_widget_message_sticker",
            "tgme_widget_message_tgsticker",
            "tgme_widget_message_videosticker",
        ),
    ),
    ("location", ("tgme_widget_message_location",)),
    ("unsupported", ("message_media_not_supported",)),
)
PARSER = lxml.html.HTMLParser(encoding="utf-8")


@dataclass(frozen=True, slots=True)
class Newest:
    pass


@dataclass(frozen=True, slots=True)
class After:
    id: int


@dataclass(frozen=True, slots=True)
class Before:
    id: int


Cursor = Newest | After | Before


def address(channel: str, cursor: Cursor) -> tuple[str, dict[str, str]]:
    url = PREVIEW.format(channel=channel)
    match cursor:
        case Newest():
            return url, {}
        case After(id=after):
            return url, {"after": str(after)}
        case Before(id=before):
            return url, {"before": str(before)}


@dataclass(frozen=True, slots=True)
class Page:
    """`older` and `newer`: the page's more links; `dateless` posts skipped."""

    posts: tuple[Post, ...]
    older: bool
    newer: bool
    dateless: int = 0


Fetch = Callable[[str, Cursor], Page]


def has(name: str) -> str:
    """XPath test: the node's class list holds `name` as a whole token."""
    return f"contains(concat(' ', normalize-space(@class), ' '), ' {name} ')"


def nodes(node: Any, path: str) -> list[Any]:
    return list(node.xpath(path))


def first_text(node: Any, path: str) -> str | None:
    found = nodes(node, path)
    shown = str(found[0].text_content()).strip() if found else ""
    return shown or None


def first_attr(node: Any, path: str) -> str | None:
    found = nodes(node, path)
    return str(found[0]) if found else None


def unescaped(href: str) -> str:
    """The preview escapes `&` twice in hrefs."""
    return href.replace("&amp;", "&")


def views_of(shown: str | None) -> int | None:
    """`68`, `1.2K`, `5.28M`, `3B` as a count, rounded; else None."""
    if shown is None:
        return None
    number, scale = shown, 1
    if shown[-1:].upper() in SCALE:
        number, scale = shown[:-1], SCALE[shown[-1].upper()]
    try:
        return round(float(number) * scale)
    except ValueError:
        return None


def text_of(node: Any) -> tuple[str, tuple[str, ...]]:
    """The post's text, `<br>` as newline, and its links, hashtag search out."""
    found = nodes(
        node,
        f".//*[{has('tgme_widget_message_bubble')}]"
        f"/*[{has('tgme_widget_message_text')}]",
    ) or nodes(
        node,
        f".//*[{has('media_supported_cont')}]/*[{has('tgme_widget_message_text')}]",
    )
    if not found:
        return "", ()
    body = found[0]
    for br in nodes(body, ".//br"):
        br.tail = "\n" + (br.tail or "")
    links = tuple(
        unescaped(str(href))
        for href in nodes(body, ".//a/@href")
        if not str(href).startswith("?q=")
    )
    return str(body.text_content()).strip(), links


def stamp_of(node: Any) -> datetime | None:
    raw = first_attr(node, f".//*[{has('tgme_widget_message_date')}]//time/@datetime")
    try:
        stamp = None if raw is None else datetime.fromisoformat(raw)
    except ValueError:
        return None
    return stamp if stamp is not None and stamp.tzinfo is not None else None


def preview_of(node: Any) -> Preview | None:
    found = nodes(node, f".//a[{has('tgme_widget_message_link_preview')}][@href]")
    if not found:
        return None
    return Preview(
        url=unescaped(str(found[0].get("href"))),
        site=first_text(found[0], f".//*[{has('link_preview_site_name')}]"),
        title=first_text(found[0], f".//*[{has('link_preview_title')}]"),
    )


def reply_of(node: Any) -> int | None:
    href = first_attr(node, f".//a[{has('tgme_widget_message_reply')}]/@href")
    tail = (href or "").split("?", 1)[0].rstrip("/").rpartition("/")[2]
    return int(tail) if is_digits(tail) else None


def media_of(node: Any) -> tuple[str, ...]:
    return tuple(
        kind
        for kind, names in MEDIA
        if nodes(node, ".//*[" + " or ".join(has(name) for name in names) + "]")
    )


def post_of(node: Any, channel: str, number: int, stamp: datetime) -> Post:
    text, links = text_of(node)
    meta = first_text(node, f".//*[{has('tgme_widget_message_meta')}]") or ""
    return Post(
        channel=channel,
        id=number,
        date=stamp,
        text=text,
        links=links,
        media=media_of(node),
        views=views_of(first_text(node, f".//*[{has('tgme_widget_message_views')}]")),
        author=first_text(node, f".//*[{has('tgme_widget_message_from_author')}]"),
        forwarded_from=first_text(
            node, f".//*[{has('tgme_widget_message_forwarded_from_name')}]"
        ),
        reply_to=reply_of(node),
        preview=preview_of(node),
        edited="edited" in meta,
    )


def parse(data: bytes, channel: str, where: str) -> Page:
    """One preview page of `channel`. A page that is no channel preview is the
    input's fault (exit 1); a preview without its history, the markup's (2)."""
    try:
        root = lxml.html.fromstring(data, parser=PARSER)
    except (lxml.etree.ParserError, ValueError) as err:
        raise UpstreamError(f"{where} sent no HTML: {err}") from err
    history = nodes(root, f"//*[{has('tgme_channel_history')}]")
    if not history:
        if not nodes(root, f"//*[{has('tgme_channel_info')}]"):
            raise CommandError(
                f"no public preview for {channel}: check the username, or drop "
                "the channel"
            )
        raise UpstreamError(f"{where} has no channel history: markup changed")
    more = f"//a[{has('tme_messages_more')}]"
    posts: list[Post] = []
    dateless = 0
    for node in nodes(root, f"//div[{has('tgme_widget_message')}][@data-post]"):
        owner, _, number = str(node.get("data-post")).partition("/")
        if owner.casefold() != channel.casefold() or not is_digits(number):
            continue
        if nodes(node, f"descendant-or-self::*[{has('service_message')}]"):
            continue
        stamp = stamp_of(node)
        if stamp is None:
            dateless += 1
            continue
        posts.append(post_of(node, channel, int(number), stamp))
    return Page(
        tuple(posts),
        older=bool(nodes(root, f"{more}[@data-before]")),
        newer=bool(nodes(root, f"{more}[@data-after]")),
        dateless=dateless,
    )


@dataclass(frozen=True, slots=True)
class Span:
    """What the store holds of one channel."""

    count: int
    low: int | None
    high: int | None

    @classmethod
    def of(cls, held: Sequence[Post]) -> Span:
        ids = [post.id for post in held]
        return cls(len(ids), min(ids, default=None), max(ids, default=None))


@dataclass(frozen=True, slots=True)
class Walked:
    """One channel's new posts, ascending by id; `open` while its bound is."""

    posts: tuple[Post, ...]
    requests: int
    open: bool
    dateless: int


def walk(channel: str, bound: Bound, span: Span, fetch: Fetch, budget: int) -> Walked:
    """Update past `span.high`, then backfill below the least id until the
    bound closes or `budget` pages are spent. O(pages)."""
    new: dict[int, Post] = {}
    used = dateless = 0

    def page(cursor: Cursor) -> Page:
        nonlocal used, dateless
        used += 1
        found = fetch(channel, cursor)
        dateless += found.dateless
        return found

    cursor: Cursor = Newest() if span.high is None else After(span.high)
    updated = False
    while used < budget:
        found = page(cursor)
        floor = cursor.id if isinstance(cursor, After) else 0
        kept = [post for post in found.posts if post.id > floor]
        new.update((post.id, post) for post in kept)
        if not kept or not found.newer:
            updated = True
            break
        cursor = After(max(post.id for post in kept))

    def admitted(post: Post) -> bool:
        return bound.since is None or post.day >= bound.since

    low = min([*new, *([] if span.low is None else [span.low])], default=None)
    closed = any(not admitted(post) for post in new.values())
    new = {key: post for key, post in new.items() if admitted(post)}
    count = span.count + len(new)
    closed = closed or low is None or (bound.limit is not None and count >= bound.limit)
    while updated and not closed and low is not None and used < budget:
        found = page(Before(low))
        kept = [post for post in found.posts if post.id < low]
        if not kept:
            closed = True
            break
        low = min(post.id for post in kept)
        inside = [post for post in kept if admitted(post)]
        new.update((post.id, post) for post in inside)
        count += len(inside)
        closed = (
            len(inside) < len(kept)
            or not found.older
            or (bound.limit is not None and count >= bound.limit)
        )
    rows = tuple(new[key] for key in sorted(new))
    return Walked(rows, used, not (updated and closed), dateless)


@dataclass(frozen=True, slots=True)
class Gathered:
    posts: Posts
    report: dict[str, dict[str, Any]]
    requests: int
    notes: tuple[str, ...]
    """`signal:` lines: a bound left open, or signs the markup changed."""


def gather(config: TelegramConfig, held: Sequence[Post], fetch: Fetch) -> Gathered:
    """Walk each channel in config order on one shared page budget."""
    rows: list[Post] = []
    report: dict[str, dict[str, Any]] = {}
    notes: list[str] = []
    budget = config.requests
    for channel, bound in config.channels.items():
        before = of_channel(held, channel)
        walked = walk(channel, bound, Span.of(before), fetch, budget)
        budget -= walked.requests
        rows.extend(walked.posts)
        every = [*before, *walked.posts]
        report[channel] = {
            "new": len(walked.posts),
            "held": len(every),
            "first": min((p.day.isoformat() for p in every), default=None),
            "last": max((p.day.isoformat() for p in every), default=None),
            "bound": "open" if walked.open else "reached",
        }
        if walked.dateless:
            notes.append(
                f"telegram: {channel}: {walked.dateless} post(s) without a date "
                "skipped; the preview markup may have changed"
            )
        if walked.posts and not any(post.text for post in walked.posts):
            notes.append(
                f"telegram: {channel}: no new post carried text; the preview "
                "markup may have changed"
            )
        if walked.open:
            oldest = min(every, key=lambda post: post.id, default=None)
            reached = (
                "nothing yet"
                if oldest is None
                else f"id {oldest.id} of {oldest.day.isoformat()}"
            )
            notes.append(
                f"telegram: {channel}: request budget spent with its bound open at "
                f"{reached}; the next load telegram continues"
            )
    return Gathered(Posts(tuple(rows)), report, config.requests - budget, tuple(notes))


def pager(pace: Pace) -> Fetch:
    """Pages from the network at the pace, 429 backed off."""

    def fetch(channel: str, cursor: Cursor) -> Page:
        url, params = address(channel, cursor)
        data = patient(lambda: get_bytes(client(), url, CAP, params), pace)
        return parse(data, channel, str(httpx.URL(url, params=params)))

    return fetch


def fetch(config: TelegramConfig, held: Sequence[Post]) -> Gathered:
    gathered = gather(config, held, pager(Pace(INTERVAL)))
    for note in gathered.notes:
        signal(note)
    return gathered


def channels_of(
    given: TelegramConfig | None, preferences: TelegramConfig | None
) -> TelegramConfig:
    """`--config:file` replaces the preferences value whole."""
    chosen = given if given is not None else preferences
    if chosen is None or not chosen.channels:
        raise CommandError(
            "load telegram needs channels: add a telegram key to preferences.json "
            "on the operator's word, or pass --config:file "
            '{"channels": {"<username>": {"since": "YYYY-MM-DD"}}}'
        )
    return chosen
