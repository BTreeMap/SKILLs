---
name: read-pdf
description: >-
  Extracts text and metadata from a PDF file or URL, answers questions about
  it with page-cited evidence. Only reads, writes nothing, no OCR: scanned
  page reported as having no text. Use when asked to read, summarize,
  search, quote, or answer questions about a PDF.
license: MIT
compatibility: >-
  Requires uv, and a full SKILLs repository checkout. Network access is
  needed only for URL inputs. The first run builds the `.venv` at the
  checkout root that every skill's scripts share, about 225 MB.
metadata:
  argument-hint: "<pdf path or URL> [pages]"
---

# Read PDF

Extract text and metadata from PDFs; answer questions with page-cited
evidence.

## Boundaries

* Read only: extractor writes plain text, never changes PDF. Reader cannot
  parse document: report read error and stop; do not repair, rewrite, or
  substitute PDF.
* No OCR: extractor reads PDF text layer only; never claim OCR results.
* Run only bundled extractor, through binding below. Do not invoke host
  `python` or `python3`, install packages manually, or use another PDF
  library, command-line PDF utility, OCR tool, or image renderer.
* Preserve source-page provenance.

## The Extractor

Bind command once per shell; re-bind after reset; `realpath` required.
Invoke it, read its output; source reading belongs to user-instructed
troubleshooting.

```bash
R="env -u VIRTUAL_ENV -u UV_PROJECT_ENVIRONMENT uv run --project $(realpath <skill-root>/scripts) btm-read-pdf"
```

`$R <document> [flags]` takes local path or http(s) URL.

* `--pages 1-3,5,8-`: one-based pages and ranges, open-ended allowed;
  default all.
* `--no-metadata`: omit standard metadata, printed by default when
  available.
* `--output <extraction.txt>`: write text there, not to standard output;
  refuses to replace existing file.
* `--overwrite`: let `--output` replace existing file.
* `--password-env <PASSWORD_VARIABLE>`: environment variable holding
  encrypted PDF's password.
* `--max-bytes`: raise 200 MB URL download cap; larger download refused.

Extracted text is whole of standard output; everything else, including note
that selected pages have no extractable text (likely scanned document), is
`signal:` line on stderr. Owner-locked PDF (empty user password) opens
without asking.

**Template: extraction**

```markdown
# Extracted from document.pdf

Selected PDF pages: 2, 3

## Document metadata

- Title: Example title

## PDF page 2

Extracted source text.

## PDF page 3

More extracted source text.
```

Read exit code before acting:

* `0`: extracted.
* `1`: fix argument or file and resend. Causes: missing path, out-of-range
  page, wrong password, oversized download, URL serving paywall page.
* `2`: download failed; same call worth retrying. Causes: 5xx, rate limit,
  transport failure.

Pass URL directly as document argument; extractor's own fetch caches, caps,
cites it as provenance. URL downloads once into digest-keyed file under
system temp directory's `btm-read-pdf/`; rerun reuses it and says so on
stderr. Response without PDF magic bytes, such as paywall's HTML page, is
refused and left uncached.

`$R clean` removes cache, emits one JSON document,
`{"removed", "bytes_freed"}`, where `removed` is null when there was no
cache; next run refetches. `clean --all` is same call, since cache is this
skill's only state.

## Procedure

1. Locate requested PDF: confirm file path exists; pass http(s) URL as is.
2. Run extractor. If it reports encryption, do not ask user to disclose or
   paste password into chat; instruct user to set local environment variable
   directly in their terminal, then rerun with `--password-env` and only
   that variable's name. Cannot decrypt with supplied variable: report
   access unavailable.
3. Keep `## PDF page N` markers in extracted text; they are evidence
   anchors.
4. Inspect extracted page text before answering. Specific question: begin
   with relevant pages; expand to referenced pages when context is missing.
   `[No extractable text on this page.]` marker usually means page is
   scanned, image-only, or has unusable text encoding; report that
   limitation.
5. Analyze by task, below. Multi-column layouts, tables, headers, footers,
   ligatures, unusual fonts can scramble reading order; do not silently
   repair ambiguous values.
6. Report facts with PDF page numbers. Label conclusions combining multiple
   passages as inferences. Document has no standard metadata: omit
   metadata-based conclusions.
7. State any extraction limitation affecting answer, such as image-only page
   or disrupted reading order.

## Analysis by Task

* **Summary or question answering:** Read all relevant sections. Retain
  qualifying language, dates, quantities, exceptions. Cite every material
  claim with PDF page number.
* **Comparison:** Extract corresponding sections from every document.
  Compare only like-for-like fields. Report missing data as missing.
* **Table-like content:** Treat text order as transcription. Reconstruct row
  or column only when labels and values stay unambiguous; otherwise describe
  ambiguity and cite page.
* **Long documents:** First identify title, headings, contents pages,
  relevant terms. Extract target pages with surrounding pages. Expand
  selection when cross-references, definitions, or footnotes change
  interpretation.
* **Exact quotations:** Copy from extraction only after checking page
  marker. Preserve wording; identify PDF page.

## Completion Checks

- Requested PDF file unmodified.
- Every analyzed passage traceable to `PDF page N` marker.
- Response distinguishes extracted facts from interpretation.
- Empty or unreliable pages, encryption, layout ambiguity disclosed when
  relevant.
- No PDF package or tool other than bundled extractor used.
