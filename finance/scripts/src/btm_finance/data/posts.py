"""Channel posts as the raw store keeps them: one JSON object per line in
`data/raw/telegram/<stem>.posts.jsonl`, sorted keys, UTF-8."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Annotated

from pydantic import AwareDatetime, Field

from btm_corekit import CommandError, Model, dump, parse_model


class Preview(Model):
    url: str
    site: str | None = None
    title: str | None = None


class Post(Model):
    """One post as the public preview showed it on first fetch; `channel`
    as configured, `media` the kinds attached, never their files."""

    channel: str
    id: Annotated[int, Field(ge=1)]
    date: AwareDatetime
    text: str
    links: tuple[str, ...] = ()
    media: tuple[str, ...] = ()
    views: int | None = None
    author: str | None = None
    forwarded_from: str | None = None
    reply_to: int | None = None
    preview: Preview | None = None
    edited: bool = False

    @property
    def url(self) -> str:
        return f"https://t.me/{self.channel}/{self.id}"

    @property
    def day(self) -> dt.date:
        """The UTC date of `date`."""
        return self.date.astimezone(dt.UTC).date()

    @property
    def key(self) -> tuple[str, int]:
        """Telegram usernames ignore case, so one channel is one key."""
        return self.channel.casefold(), self.id


@dataclass(frozen=True, slots=True)
class Posts:
    rows: tuple[Post, ...]

    def __len__(self) -> int:
        return len(self.rows)

    @property
    def first(self) -> dt.date:
        """The oldest UTC day; the rows must be non-empty."""
        return min(post.day for post in self.rows)

    @property
    def last(self) -> dt.date:
        return max(post.day for post in self.rows)

    def jsonl(self) -> bytes:
        return "".join(
            json.dumps(dump(post), ensure_ascii=False, sort_keys=True) + "\n"
            for post in self.rows
        ).encode("utf-8")

    @classmethod
    def of(cls, data: bytes, where: str) -> Posts:
        """Decode verified bytes; a bad line names file and line."""
        rows: list[Post] = []
        for number, line in enumerate(data.decode("utf-8").splitlines(), start=1):
            try:
                raw = json.loads(line)
            except ValueError as err:
                raise CommandError(f"{where} line {number}: {err}") from err
            rows.append(parse_model(Post, raw, f"{where} line {number}"))
        return cls(tuple(rows))


def current(parts: Sequence[tuple[int, Posts]]) -> list[Post]:
    """Newest-wins per `Post.key` by load rank, ascending by key. O(n log n)."""
    held: dict[tuple[str, int], Post] = {}
    for _, part in sorted(parts, key=lambda pair: pair[0]):
        for post in part.rows:
            held[post.key] = post
    return [held[key] for key in sorted(held)]


def of_channel(posts: Iterable[Post], channel: str) -> list[Post]:
    folded = channel.casefold()
    return [post for post in posts if post.channel.casefold() == folded]
