"""The telegram source: the preview parser on a hand-written page in the
service's class structure, the walk on a fake page function, `load telegram`
through the raw store on a mock transport, the live page under `network`."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from btm_finance import api
from btm_finance.data.posts import Post, Posts
from btm_finance.data.raw import Manifest, data_snapshot, read_manifest, store
from btm_finance.data.sources import telegram
from btm_finance.data.sources.telegram import (
    After,
    Before,
    Cursor,
    Newest,
    Page,
    Span,
    gather,
    parse,
    walk,
)
from btm_finance.data.tables import Loaded, Table
from btm_finance.models import Bound, TelegramConfig
from btm_finance.store import open_book

from btm_corekit import CommandError, UpstreamError, build_client

CHANNEL = "Example_Chan"


def message(post: str, body: str, meta: str = "", stamp: str | None = None) -> str:
    when = (
        ""
        if stamp is None
        else f'<a class="tgme_widget_message_date" href="#"><time '
        f'datetime="{stamp}" class="time">09:00</time></a>'
    )
    return f"""
<div class="tgme_widget_message_wrap js-widget_message_wrap">
 <div class="tgme_widget_message text_not_supported_wrap js-widget_message"
      data-post="{post}">
  <div class="tgme_widget_message_bubble">
   {body}
   <div class="tgme_widget_message_footer compact js-message_footer">
    <div class="tgme_widget_message_info short js-message_info">
     {meta}<span class="tgme_widget_message_meta">{when}</span>
    </div>
   </div>
  </div>
 </div>
</div>"""


def views(shown: str) -> str:
    return f'<span class="tgme_widget_message_views">{shown}</span>'


FIRST = message(
    f"{CHANNEL}/41",
    '<a class="tgme_widget_message_reply" href="https://t.me/Example_Chan/39">'
    '<div class="tgme_widget_message_text js-message_text">quoted</div></a>'
    '<div class="tgme_widget_message_text js-message_text" dir="auto">'
    "Rates <b>held</b> today.<br/>See "
    '<a href="https://example.org/a?x=1&amp;amp;y=2">the note</a> '
    '<a href="?q=%23rates">#rates</a></div>',
    views("1.2K") + '<span class="tgme_widget_message_meta">edited </span>',
    "2026-10-20T09:00:00+00:00",
)
SECOND = message(
    f"{CHANNEL}/42",
    '<div class="tgme_widget_message_forwarded_from accent_color">Forwarded '
    'from <span class="tgme_widget_message_forwarded_from_name">'
    "<span>Desk Wire</span></span></div>"
    '<a class="tgme_widget_message_photo_wrap" href="#"></a>'
    '<div class="media_supported_cont">'
    '<div class="tgme_widget_message_text js-message_text">Chart attached</div>'
    "</div>"
    '<a class="tgme_widget_message_link_preview" href="https://example.org/p?a=1&amp;amp;b=2">'
    '<div class="link_preview_site_name">Example Site</div>'
    '<div class="link_preview_title">A title</div></a>',
    views("5.28M"),
    "2026-10-20T10:30:00+02:00",
)
SERVICE = message(
    f"{CHANNEL}/43",
    '<div class="tgme_widget_message_service_wrap">'
    '<div class="service_message">Channel photo updated</div></div>',
    stamp="2026-10-20T11:00:00+00:00",
)
FOREIGN = message("other_chan/44", "x", stamp="2026-10-20T11:00:00+00:00")
DATELESS = message(f"{CHANNEL}/45", "no time")
NOT_DIGITS = message(f"{CHANNEL}/4a", "x", stamp="2026-10-20T11:00:00+00:00")
MEDIA = message(
    "example_chan/47",
    '<span class="tgme_widget_message_from_author">A. Writer</span>'
    '<div class="tgme_widget_message_poll"></div>'
    '<div class="tgme_widget_message_tgsticker"></div>'
    '<div class="tgme_widget_message_video_player"></div>'
    '<div class="tgme_widget_message_voice"></div>'
    '<div class="tgme_widget_message_document"></div>'
    '<div class="tgme_widget_message_location"></div>'
    '<div class="message_media_not_supported"></div>',
    views("3B"),
    "2026-10-21T08:00:00+00:00",
)


def page(*posts: str, before: int | None = None, after: int | None = None) -> bytes:
    older = (
        ""
        if before is None
        else f'<a href="/s/x?before={before}" class="tme_messages_more '
        f'js-messages_more" data-before="{before}"></a>'
    )
    newer = (
        ""
        if after is None
        else f'<a href="/s/x?after={after}" class="tme_messages_more '
        f'js-messages_more" data-after="{after}"></a>'
    )
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<header><div class="tgme_channel_info"><div>Example</div></div></header>
<main><section class="tgme_channel_history js-message_history">
<div class="tgme_widget_message_centered js-messages_more_wrap">{older}</div>
{"".join(posts)}
<div class="tgme_widget_message_centered js-messages_more_wrap">{newer}</div>
</section></main></body></html>""".encode()


def test_parser_reads_each_field_and_skips_what_is_no_post():
    found = parse(
        page(FIRST, SECOND, SERVICE, FOREIGN, DATELESS, NOT_DIGITS, MEDIA, before=41),
        CHANNEL,
        "fixture",
    )
    assert [p.id for p in found.posts] == [41, 42, 47]
    assert found.dateless == 1
    assert found.older and not found.newer
    first, second, media = found.posts
    assert first.text == "Rates held today.\nSee the note #rates"
    assert first.links == ("https://example.org/a?x=1&y=2",)
    assert (first.views, first.reply_to, first.edited) == (1200, 39, True)
    assert first.date == datetime(2026, 10, 20, 9, tzinfo=UTC)
    assert first.media == () and first.preview is None
    assert second.text == "Chart attached"
    assert second.date == datetime(2026, 10, 20, 8, 30, tzinfo=UTC)
    assert (second.views, second.forwarded_from) == (5_280_000, "Desk Wire")
    assert second.media == ("photo",) and not second.edited
    assert second.preview is not None
    assert second.preview.url == "https://example.org/p?a=1&b=2"
    assert (second.preview.site, second.preview.title) == ("Example Site", "A title")
    assert media.text == "" and media.author == "A. Writer"
    assert media.views == 3_000_000_000
    assert media.media == (
        "video",
        "voice",
        "document",
        "poll",
        "sticker",
        "location",
        "unsupported",
    )
    assert media.channel == CHANNEL and media.url == "https://t.me/Example_Chan/47"


def test_parser_tells_a_withheld_channel_from_changed_markup():
    with pytest.raises(CommandError, match="no public preview for Example_Chan"):
        parse(
            b"<html><body><div class='tgme_page'>Telegram</div></body></html>",
            CHANNEL,
            "u",
        )
    header_only = b'<html><body><div class="tgme_channel_info">x</div></body></html>'
    with pytest.raises(UpstreamError, match="u has no channel history"):
        parse(header_only, CHANNEL, "u")


def test_an_empty_history_page_has_no_posts_and_no_more_links():
    found = parse(page(), CHANNEL, "u")
    assert found == Page((), older=False, newer=False)


def test_views_read_every_suffix_and_refuse_noise():
    assert [telegram.views_of(s) for s in ("68", "1.2K", "5.28M", "3B")] == [
        68,
        1200,
        5_280_000,
        3_000_000_000,
    ]
    assert telegram.views_of("n/a") is None and telegram.views_of(None) is None


def test_cursors_map_to_the_preview_url():
    url = "https://t.me/s/Example_Chan"
    assert telegram.address(CHANNEL, Newest()) == (url, {})
    assert telegram.address(CHANNEL, After(7)) == (url, {"after": "7"})
    assert telegram.address(CHANNEL, Before(7)) == (url, {"before": "7"})


START = datetime(2026, 1, 1, tzinfo=UTC)


def post(number: int, channel: str = CHANNEL) -> Post:
    """Post `n` is dated `n` days after 2026-01-01."""
    return Post(
        channel=channel,
        id=number,
        date=START + timedelta(days=number),
        text=f"post {number}",
    )


class Channel:
    """A fake preview over ids 1..`newest`, `size` per page, logging cursors."""

    def __init__(self, newest: int, size: int = 5) -> None:
        self.ids = list(range(1, newest + 1))
        self.size = size
        self.asked: list[Cursor] = []

    def __call__(self, channel: str, cursor: Cursor) -> Page:
        self.asked.append(cursor)
        match cursor:
            case Newest():
                ids = self.ids[-self.size :]
            case After(id=low):
                ids = [i for i in self.ids if i > low][: self.size]
            case Before(id=high):
                ids = [i for i in self.ids if i < high][-self.size :]
        return Page(
            tuple(post(i, channel) for i in ids),
            older=bool(ids) and ids[0] > self.ids[0],
            newer=bool(ids) and ids[-1] < self.ids[-1],
        )


def day(number: int) -> date:
    return (START + timedelta(days=number)).date()


def test_a_fresh_channel_takes_the_newest_page_then_backfills_to_since():
    fake = Channel(30)
    walked = walk(CHANNEL, Bound(since=day(18)), Span.of([]), fake, 100)
    assert [p.id for p in walked.posts] == list(range(18, 31))
    assert fake.asked == [Newest(), Before(26), Before(21)]
    assert (walked.requests, walked.open) == (3, False)


def test_a_held_span_updates_forward_then_backfills_to_limit():
    fake = Channel(30)
    held = [post(i) for i in range(20, 23)]
    walked = walk(CHANNEL, Bound(limit=15), Span.of(held), fake, 100)
    assert fake.asked == [After(22), After(27), Before(20)]
    assert [p.id for p in walked.posts] == [*range(15, 20), *range(23, 31)]
    assert not walked.open


def test_limit_never_cuts_the_update():
    fake = Channel(30)
    held = [post(i) for i in range(1, 11)]
    walked = walk(CHANNEL, Bound(limit=3), Span.of(held), fake, 100)
    assert [p.id for p in walked.posts] == list(range(11, 31))
    assert Before(1) not in fake.asked


def test_backfill_stops_at_the_channel_start():
    fake = Channel(8)
    walked = walk(CHANNEL, Bound(limit=1000), Span.of([]), fake, 100)
    assert [p.id for p in walked.posts] == list(range(1, 9))
    assert fake.asked == [Newest(), Before(4)]
    assert not walked.open


def test_no_admitted_id_closes_the_bound_when_more_links_lie():
    def lying(channel: str, cursor: Cursor) -> Page:
        return Page((post(5, channel),), older=True, newer=True)

    walked = walk(CHANNEL, Bound(limit=1000), Span.of([]), lying, 100)
    assert [p.id for p in walked.posts] == [5] and walked.requests == 3
    assert not walked.open


def test_a_spent_budget_leaves_the_bound_open_and_the_next_call_resumes():
    fake = Channel(30)
    first = walk(CHANNEL, Bound(since=day(3)), Span.of([]), fake, 3)
    assert [p.id for p in first.posts] == list(range(16, 31))
    assert first.open
    resumed = Channel(30)
    second = walk(CHANNEL, Bound(since=day(3)), Span.of(first.posts), resumed, 100)
    assert resumed.asked == [After(30), Before(16), Before(11), Before(6)]
    assert [p.id for p in second.posts] == list(range(3, 16))
    assert not second.open


def test_both_bounds_stop_at_whichever_comes_first():
    by_since = walk(
        CHANNEL, Bound(since=day(24), limit=20), Span.of([]), Channel(30), 99
    )
    assert [p.id for p in by_since.posts] == list(range(24, 31))
    by_limit = walk(CHANNEL, Bound(since=day(2), limit=8), Span.of([]), Channel(30), 99)
    assert [p.id for p in by_limit.posts] == list(range(21, 31))


def test_two_channels_share_one_budget_in_config_order():
    fake = Channel(30)
    config = TelegramConfig(
        channels={"first_one": Bound(limit=12), "second_one": Bound(limit=50)},
        requests=5,
    )
    gathered = gather(config, [post(30, "second_one")], fake)
    assert gathered.requests == 5
    assert gathered.report["first_one"] == {
        "new": 15,
        "held": 15,
        "first": day(16).isoformat(),
        "last": day(30).isoformat(),
        "bound": "reached",
    }
    second = gathered.report["second_one"]
    assert (second["new"], second["held"], second["bound"]) == (5, 6, "open")
    [note] = gathered.notes
    assert "second_one" in note and "id 25 of" in note
    assert len(gathered.posts) == 20


def test_dateless_and_textless_pages_raise_markup_notes():
    def bare(channel: str, cursor: Cursor) -> Page:
        return Page((post(3).with_(text=""),), older=False, newer=False, dateless=2)

    config = TelegramConfig(channels={CHANNEL: Bound(limit=10)})
    notes = gather(config, [], bare).notes
    assert len(notes) == 2
    assert "4 post(s) without a date" in notes[0]
    assert "no new post carried text" in notes[1]


def stamp(number: int) -> str:
    return (START + timedelta(days=number)).isoformat()


def preview(newest: int, size: int = 5, asked: list[str] | None = None):
    """A transport serving ids 1..`newest` by the URL's `before`/`after`."""

    def handler(request: httpx.Request) -> httpx.Response:
        if asked is not None:
            asked.append(str(request.url))
        query = request.url.params
        ids = list(range(1, newest + 1))
        if "after" in query:
            chosen = [i for i in ids if i > int(query["after"])][:size]
        elif "before" in query:
            chosen = [i for i in ids if i < int(query["before"])][-size:]
        else:
            chosen = ids[-size:]
        text = '<div class="tgme_widget_message_text">post {}</div>'
        body = page(
            *(
                message(f"{CHANNEL}/{i}", text.format(i), stamp=stamp(i))
                for i in chosen
            ),
            before=chosen[0] if chosen and chosen[0] > 1 else None,
            after=chosen[-1] if chosen and chosen[-1] < newest else None,
        )
        return httpx.Response(200, content=body)

    return httpx.MockTransport(handler)


@pytest.fixture
def serve(monkeypatch: pytest.MonkeyPatch):
    def install(transport: httpx.MockTransport) -> None:
        monkeypatch.setattr(telegram, "INTERVAL", 0.0)
        monkeypatch.setattr(
            telegram, "client", lambda: build_client("finance", transport=transport)
        )

    return install


def channels(tmp_path: Path, **bound: object) -> Path:
    target = tmp_path / "tg.json"
    target.write_text(json.dumps({"channels": {CHANNEL: bound}}))
    return target


def load_posts(run, book: Path, cfg: Path | None = None):
    given = [] if cfg is None else ["--config:file", str(cfg)]
    return run(["load", str(book), "telegram", *given])


def manifest_of(book: Path) -> Manifest:
    return read_manifest(open_book(str(book)))


def test_load_writes_posts_jsonl_and_leaves_the_snapshot(tmp_path, book, run, serve):
    serve(preview(12))
    before = data_snapshot(manifest_of(book))
    code, receipt, err = load_posts(run, book, channels(tmp_path, since=stamp(4)[:10]))
    assert code == 0, err
    [stored] = receipt["files"]
    assert stored["path"].startswith("data/raw/telegram/")
    assert stored["path"].endswith(".posts.jsonl")
    assert receipt["rows"] == {"bars": 0, "events": 0, "posts": 9}
    assert receipt["channels"][CHANNEL] == {
        "new": 9,
        "held": 9,
        "first": stamp(4)[:10],
        "last": stamp(12)[:10],
        "bound": "reached",
    }
    assert receipt["requests"] == 2
    assert receipt["data_snapshot"] == before
    [entry] = manifest_of(book).files
    assert (entry.source, entry.table, entry.rows) == ("telegram", Table.POSTS, 9)
    assert (entry.since, entry.through) == (day(4), day(12))
    lines = (book / stored["path"]).read_bytes().decode().splitlines()
    assert len(lines) == 9
    assert json.loads(lines[0]) == {
        "channel": CHANNEL,
        "date": stamp(4).replace("+00:00", "Z"),
        "edited": False,
        "id": 4,
        "links": [],
        "media": [],
        "text": "post 4",
    }
    assert lines[0] == json.dumps(json.loads(lines[0]), sort_keys=True)


def test_a_second_load_continues_from_the_stored_span(tmp_path, book, run, serve):
    cfg = tmp_path / "tg.json"
    cfg.write_text(json.dumps({"channels": {CHANNEL: {"limit": 100}}, "requests": 2}))
    serve(preview(20))
    code, receipt, err = load_posts(run, book, cfg)
    assert code == 0, err
    assert receipt["channels"][CHANNEL]["bound"] == "open"
    assert "next load telegram continues" in err
    asked: list[str] = []
    serve(preview(23, asked=asked))
    code, receipt, err = load_posts(run, book, cfg)
    assert code == 0, err
    assert asked == [
        "https://t.me/s/Example_Chan?after=20",
        "https://t.me/s/Example_Chan?before=11",
    ]
    assert receipt["channels"][CHANNEL]["new"] == 8
    assert receipt["channels"][CHANNEL]["held"] == 18
    assert Path(receipt["files"][0]["path"]).name.split(".")[0].endswith("-2")
    held = [p.id for p in api.posts(open_book(str(book)))]
    assert held == list(range(6, 24))


def test_load_reads_preferences_and_refuses_since_or_no_channels(
    tmp_path, book, run, serve
):
    code, _, err = load_posts(run, book)
    assert code == 1 and "preferences.json" in err and "--config:file" in err
    cfg = str(channels(tmp_path, limit=5))
    code, _, err = run(
        ["load", str(book), "telegram", "--since", "2026-01-01", "--config:file", cfg]
    )
    assert code == 1 and "takes no --since" in err
    path = book / "preferences.json"
    preferences = json.loads(path.read_text())
    preferences["telegram"] = {"channels": {CHANNEL: {"limit": 5}}}
    path.write_text(json.dumps(preferences))
    serve(preview(12))
    code, receipt, err = load_posts(run, book)
    assert code == 0, err
    assert receipt["rows"]["posts"] == 5


def test_a_bad_username_or_empty_bound_is_refused_at_parse(tmp_path, book, run):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"channels": {"a/b?x": {"limit": 1}, "ok_name": {}}}))
    code, _, err = load_posts(run, book, bad)
    assert code == 1
    assert "a/b?x" in err and "give since" in err


def test_a_withheld_channel_exits_1_and_a_5xx_exits_2(tmp_path, book, run, serve):
    def redirect(request: httpx.Request) -> httpx.Response:
        if request.url.host == "t.me":
            return httpx.Response(302, headers={"Location": "https://telegram.org/"})
        return httpx.Response(200, content=b"<html><body>Telegram</body></html>")

    serve(httpx.MockTransport(redirect))
    code, _, err = load_posts(run, book, channels(tmp_path, limit=5))
    assert code == 1 and "no public preview for Example_Chan" in err
    serve(httpx.MockTransport(lambda request: httpx.Response(503)))
    code, _, err = load_posts(run, book, channels(tmp_path, limit=5))
    assert code == 2 and "HTTP 503" in err
    assert manifest_of(book).files == ()


def stored(book: Path, *rows: Post) -> None:
    store(
        open_book(str(book)),
        "telegram",
        Loaded(None, None, Posts(rows)),
        since=date(2026, 1, 1),
        today=date(2026, 10, 23),
    )


def test_api_posts_takes_the_newest_load_and_cuts_on_since(book):
    stored(book, post(2), post(1), post(3, "other_chan"))
    stored(book, post(2).with_(text="corrected"))
    opened = open_book(str(book))
    assert [(p.channel, p.id, p.text) for p in api.posts(opened)] == [
        (CHANNEL, 1, "post 1"),
        (CHANNEL, 2, "corrected"),
        ("other_chan", 3, "post 3"),
    ]
    assert [p.id for p in api.posts(opened, channel="example_chan")] == [1, 2]
    assert [p.id for p in api.posts(opened, since=day(2))] == [2, 3]


def test_a_tampered_posts_file_halts_load_and_api(tmp_path, book, run):
    stored(book, post(1))
    [entry] = manifest_of(book).files
    target = book / entry.path
    target.write_bytes(target.read_bytes().replace(b"Example", b"Exampel"))
    code, _, err = load_posts(run, book, channels(tmp_path, limit=5))
    assert code == 1 and entry.path in err
    with pytest.raises(CommandError, match="sha256 differs"):
        api.posts(open_book(str(book)))


@pytest.mark.network
def test_live_preview_answers_in_the_parsed_shape():
    found = telegram.pager(telegram.Pace(1.0))("telegram", After(100))
    assert found.posts and all(p.id > 100 for p in found.posts)
    assert all(p.date.tzinfo is not None for p in found.posts)
