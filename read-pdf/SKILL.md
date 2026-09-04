---
name: read-pdf
description: >-
  Extracts text and metadata from a PDF and answers questions about it with
  page-cited evidence, working from a local file or an http(s) URL it
  fetches itself. It only reads. Nothing is written, created, merged, split,
  or rendered, and there is no OCR, so a scanned page reports as having no
  extractable text. Use when the user asks to inspect, summarize, search,
  quote, extract from, analyze, or answer questions about a PDF, including
  one behind a link.
license: MIT
compatibility: >-
  Requires uv, and a full SKILLs repository checkout. Network access is
  needed only for URL inputs.
metadata:
  argument-hint: "<pdf path or URL> [pages]"
---

# Read PDF

Extract text and metadata from PDFs and answer questions with page-cited
evidence. Never creates, modifies, or otherwise writes a PDF.

## Scope

Read PDF content for analysis. Extract text, page numbers, and standard metadata. Preserve source-page provenance.

Run the extractor through its console command with `uv run --project`; do not invoke a host `python` or `python3`, install packages manually, or use another PDF library, a command-line PDF utility, an OCR tool, or an image renderer.

Pass an http(s) URL directly as the document argument: the extractor's own fetch caches, caps, and cites the URL as provenance.

## Procedure

1. Locate the requested PDF: a file path (confirm it exists) or an http(s) URL (pass it as is).
2. Run the bundled extractor. It writes plain text only and never changes the PDF.
3. Keep the `## PDF page N` markers in the extracted text; they are the evidence anchors.
4. Inspect the extracted page text before answering. For a specific question, begin with the relevant pages; expand to referenced pages when context is missing.
5. Report facts with their PDF page numbers. Label conclusions that combine multiple passages as inferences.
6. State any extraction limitation that affects the answer, such as an image-only page or disrupted reading order.

## Extract with the Bundled Script

The extractor's console command `btm-read-pdf` accepts one-based page selections, including open-ended ranges. By default it prints all pages and available standard metadata to standard output. It refuses to replace an existing `--output` file unless `--overwrite` is passed, opens owner-locked PDFs (empty user password) without asking, and reports on stderr when selected pages have no extractable text (a likely scanned document).

Bind the command once per shell and re-bind after a reset; `realpath` is required. Invoke it and read its output; source reading belongs to user-instructed troubleshooting.

<commands for="all-pages">
R="env -u VIRTUAL_ENV uv run --project $(realpath <skill-root>/scripts) btm-read-pdf"
$R <document.pdf>
</commands>

<commands for="selected-pages">
$R <document.pdf> --pages 1-3,5,8- --output <extraction.txt>
</commands>

<commands for="text-only">
$R <document.pdf> --pages 4-6 --no-metadata
</commands>

<commands for="url">
$R https://<host>/<paper>.pdf --pages 1-3
</commands>

A URL downloads once into a digest-keyed file under the system temp
directory's `btm-read-pdf/`; a rerun reuses it, and deleting that file
forces a refetch. Downloads over 200 MB are refused
(`--max-bytes` raises the cap), and a response without PDF magic bytes, such
as a paywall's HTML page, is refused and left uncached.

For an encrypted PDF, do not ask the user to disclose or paste a password into chat. Instruct the user to set a local environment variable directly in their terminal, then pass only that variable's name to the script.

<commands for="encrypted-pdf">
$R <document.pdf> --password-env <PASSWORD_VARIABLE>
</commands>

Expected extraction shape:

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

## Analyze the Extraction

- **Summary or question answering:** Read all relevant sections. Retain qualifying language, dates, quantities, and exceptions. Cite every material claim with its PDF page number.
- **Comparison:** Extract the corresponding sections from every document. Compare only like-for-like fields. Report missing data as missing.
- **Table-like content:** Treat text order as a transcription. Reconstruct a row or column only when labels and values remain unambiguous; otherwise describe the ambiguity and cite the page.
- **Long documents:** First identify title, headings, contents pages, and relevant terms. Extract the target pages with their surrounding pages. Expand the selection when cross-references, definitions, or footnotes change the interpretation.
- **Exact quotations:** Copy from the extraction only after checking the page marker. Preserve wording, and identify the PDF page.

## Limitations and Recovery

- The extractor reads a PDF text layer. A `[No extractable text on this page.]` marker usually means the page is scanned, image-only, or has unusable text encoding. Report that limitation; do not claim OCR results.
- Multi-column layouts, tables, headers, footers, ligatures, and unusual fonts can scramble reading order. Do not silently repair ambiguous values.
- If the script reports encryption, use `--password-env`. If it cannot decrypt with the supplied variable, report that access was unavailable.
- If the reader cannot parse the document, report the read error and stop. Do not repair, rewrite, or substitute the PDF.
- If the document has no standard metadata, omit metadata-based conclusions.
- Read the exit code before acting: 0 extracted, 1 fix the argument or the file and resend, 2 the download failed and the same call is worth retrying. A missing path, an out-of-range page, a wrong password, an oversized download, and a URL serving a paywall page are all exit 1; a 5xx, a rate limit, and a transport failure are exit 2.

## Completion Checks

- The requested PDF file remains unmodified.
- Every analyzed passage is traceable to a `PDF page N` marker.
- The response distinguishes extracted facts from interpretation.
- Empty or unreliable pages, encryption, and layout ambiguity are disclosed when relevant.
- No PDF package or tool other than the bundled extractor was used.
