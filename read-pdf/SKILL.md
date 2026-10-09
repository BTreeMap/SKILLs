---
name: read-pdf
description: >-
  Extracts text and metadata from a PDF file or URL and answers questions
  about it with page-cited evidence. It only reads, writes nothing, and has
  no OCR, so a scanned page is reported as having no text. Use when asked to
  read, summarize, search, quote, or answer questions about a PDF.
license: MIT
compatibility: >-
  Requires uv, and a full SKILLs repository checkout. Network access is
  needed only for URL inputs. The first run builds the `.venv` at the
  checkout root that every skill's scripts share, about 225 MB.
metadata:
  argument-hint: "<pdf path or URL> [pages]"
---

# Read PDF

Extract text and metadata from PDFs and answer questions with page-cited
evidence.

## Boundaries

* Read only: the extractor writes plain text and never changes the PDF. If
  the reader cannot parse the document, report the read error and stop; do
  not repair, rewrite, or substitute the PDF.
* No OCR: the extractor reads the PDF text layer only; never claim OCR
  results.
* Run only the bundled extractor, through the binding below. Do not invoke a
  host `python` or `python3`, install packages manually, or use another PDF
  library, a command-line PDF utility, an OCR tool, or an image renderer.
* Preserve source-page provenance.

## The Extractor

Bind the command once per shell and re-bind after a reset; `realpath` is
required. Invoke it and read its output; source reading belongs to
user-instructed troubleshooting.

<commands for="bind">
R="env -u VIRTUAL_ENV uv run --project $(realpath <skill-root>/scripts) btm-read-pdf"
</commands>

`$R <document> [flags]` takes a local path or an http(s) URL.

* `--pages 1-3,5,8-`: one-based pages and ranges, open-ended allowed;
  default all.
* `--no-metadata`: omit standard metadata, printed by default when
  available.
* `--output <extraction.txt>`: write the text there, not to standard output;
  refuses to replace an existing file.
* `--overwrite`: let `--output` replace an existing file.
* `--password-env <PASSWORD_VARIABLE>`: environment variable holding an
  encrypted PDF's password.
* `--max-bytes`: raise the 200 MB URL download cap; a larger download is
  refused.

The extracted text is the whole of standard output; everything else,
including the note that selected pages have no extractable text (a likely
scanned document), is a `signal:` line on stderr. An owner-locked PDF
(empty user password) opens without asking.

<template for="extraction">
# Extracted from document.pdf

Selected PDF pages: 2, 3

## Document metadata

- Title: Example title

## PDF page 2

Extracted source text.

## PDF page 3

More extracted source text.
</template>

Read the exit code before acting:

* `0`: extracted.
* `1`: fix the argument or the file and resend. Causes: a missing path, an
  out-of-range page, a wrong password, an oversized download, a URL serving
  a paywall page.
* `2`: the download failed; the same call is worth retrying. Causes: a 5xx,
  a rate limit, a transport failure.

Pass a URL directly as the document argument; the extractor's own fetch
caches, caps, and cites it as provenance. A URL downloads once into a
digest-keyed file under the system temp directory's `btm-read-pdf/`; a
rerun reuses it and says so on stderr. A response without PDF magic bytes,
such as a paywall's HTML page, is refused and left uncached.

`$R clean` removes the cache and emits one JSON document,
`{"removed", "bytes_freed"}`, where `removed` is null when there was no
cache; the next run refetches. `clean --all` is the same call, since the
cache is this skill's only state.

## Procedure

1. Locate the requested PDF: confirm a file path exists; pass an http(s)
   URL as is.
2. Run the extractor. If it reports encryption, do
   not ask the user to disclose or paste a password into chat: instruct the
   user to set a local environment variable directly in their terminal,
   then rerun with `--password-env` and only that variable's name. If it
   cannot decrypt with the supplied variable, report that access was
   unavailable.
3. Keep the `## PDF page N` markers in the extracted text; they are the
   evidence anchors.
4. Inspect the extracted page text before answering. For a specific
   question, begin with the relevant pages; expand to referenced pages when
   context is missing. A `[No extractable text on this page.]` marker
   usually means the page is scanned, image-only, or has unusable text
   encoding; report that limitation.
5. Analyze by task, below. Multi-column layouts, tables, headers, footers,
   ligatures, and unusual fonts can scramble reading order; do not silently
   repair ambiguous values.
6. Report facts with their PDF page numbers. Label conclusions that combine
   multiple passages as inferences. If the document has no standard
   metadata, omit metadata-based conclusions.
7. State any extraction limitation that affects the answer, such as an
   image-only page or disrupted reading order.

## Analysis by Task

* **Summary or question answering:** Read all relevant sections. Retain
  qualifying language, dates, quantities, and exceptions. Cite every
  material claim with its PDF page number.
* **Comparison:** Extract the corresponding sections from every document.
  Compare only like-for-like fields. Report missing data as missing.
* **Table-like content:** Treat text order as a transcription. Reconstruct a
  row or column only when labels and values remain unambiguous; otherwise
  describe the ambiguity and cite the page.
* **Long documents:** First identify title, headings, contents pages, and
  relevant terms. Extract the target pages with their surrounding pages.
  Expand the selection when cross-references, definitions, or footnotes
  change the interpretation.
* **Exact quotations:** Copy from the extraction only after checking the
  page marker. Preserve wording, and identify the PDF page.

## Completion Checks

<checklist>
  <item>The requested PDF file remains unmodified.</item>
  <item>Every analyzed passage is traceable to a `PDF page N` marker.</item>
  <item>The response distinguishes extracted facts from interpretation.</item>
  <item>Empty or unreliable pages, encryption, and layout ambiguity are disclosed when relevant.</item>
  <item>No PDF package or tool other than the bundled extractor was used.</item>
</checklist>
