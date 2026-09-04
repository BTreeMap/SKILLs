"""Search the web, reference works, and the scholarly record without a key.

Five backends, one result shape: `web` for a general search, `instant` for a
definition, `wiki` for an encyclopedia summary, `scholar` for papers, and
`fetch` for the readable text of one page. Every row carries where it came
from, so a caller can weigh it.
"""
