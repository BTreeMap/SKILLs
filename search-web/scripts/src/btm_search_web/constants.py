"""Endpoints, caps, and the defaults the verbs are built from. The scholarly
indexes are the kernel registry's, named there."""

from __future__ import annotations

INSTANT_ANSWER = "https://api.duckduckgo.com/"
WIKI_SEARCH = "https://en.wikipedia.org/w/rest.php/v1/search/page"
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"

APP = "btm-skills"  # the instant-answer API asks callers to name themselves
TIMEOUT_SECONDS = 30
RESPONSE_CAP_BYTES = 16 * 1024 * 1024
PAGE_CAP_BYTES = 8 * 1024 * 1024
RAW_CAP_BYTES = 512 * 1024 * 1024  # a data file pinned by digest, not read as a page
DEFAULT_RESULTS = 8
MAX_RESULTS = 50
SNIPPET_CHARS = 400  # enough to judge a hit, not enough to read the page
TITLE_CHARS = 300  # a title an index padded with a subtitle still fits
TOPIC_CHARS = 80  # a related term names itself; its text is the snippet


DEFAULT_PASSAGES = 4  # the index's own default; enough to judge a paper
ARXIV_REGISTRANT = "10.48550/"  # the DOI prefix arXiv registers its papers under
