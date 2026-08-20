---
name: read-pdf
description: >-
  Reads PDFs with pypdf to extract text and metadata and answer questions
  with page-cited evidence; never creates, modifies, merges, splits, renders,
  OCRs, or otherwise writes PDF files. Use when the user asks to inspect,
  summarize, search, quote, extract from, analyze, or answer questions about
  a PDF.
license: MIT
compatibility: Requires uv to run the bundled PEP 723 extractor script
---

# Read PDF

Extract text and metadata from PDFs with pypdf and answer questions with
page-cited evidence. Never creates, modifies, or otherwise writes a PDF.

## Registry

| Name | Path |
| --- | --- |
| `extract_pdf` | [scripts/extract_pdf.py](scripts/extract_pdf.py) |

## Scope

Read PDF content for analysis. Extract text, page numbers, and standard metadata. Preserve source-page provenance.

Use only `pypdf`, resolved by `uv` from the bundled script's PEP 723 metadata. Run the script with `uv run --script`; do not invoke a host `python` or `python3`, install packages manually, or use another PDF library, a command-line PDF utility, an OCR tool, or an image renderer. Do not create or modify any PDF file.

## Procedure

1. Locate the requested PDF. Confirm the file exists before reading it.
2. Run the bundled extractor. It reads the input PDF and writes plain text only; it never changes the PDF.
3. Keep the `## PDF page N` markers in the extracted text. They are the evidence anchors for the analysis.
4. Inspect the extracted page text before answering. For a specific question, begin with the relevant pages and expand to referenced pages when context is missing.
5. Report facts with their PDF page numbers. Label conclusions that combine multiple passages as inferences.
6. State any extraction limitation that affects the answer, such as an image-only page or disrupted reading order.

## Extract with the Bundled Script

The bundled script is registered as `extract_pdf`. It accepts one-based page selections, including open-ended ranges. By default, it prints all pages and available standard metadata to standard output. It refuses to replace an existing `--output` file unless `--overwrite` is passed, opens owner-locked PDFs (empty user password) without asking, and reports on stderr when selected pages have no extractable text (a likely scanned document). Its PEP 723 metadata is the source of truth for the required dependency.

Run the canonical bundled path rather than copying the script into document directories: uv caches script environments by script path. Pass each document path as an argument instead.

<all_pages_command>
uv run --script <skill-root>/scripts/extract_pdf.py <document.pdf>
</all_pages_command>

<selected_pages_command>
uv run --script <skill-root>/scripts/extract_pdf.py <document.pdf> --pages 1-3,5,8- --output <extraction.txt>
</selected_pages_command>

<text_only_command>
uv run --script <skill-root>/scripts/extract_pdf.py <document.pdf> --pages 4-6 --no-metadata
</text_only_command>

For an encrypted PDF, do not ask the user to disclose or paste a password into chat. Instruct the user to set a local environment variable directly in their terminal, then pass only that variable's name to the script.

<encrypted_pdf_command>
uv run --script <skill-root>/scripts/extract_pdf.py <document.pdf> --password-env <PASSWORD_VARIABLE>
</encrypted_pdf_command>

Expected extraction shape:

<extraction_shape>
# Extracted from document.pdf

Selected PDF pages: 2, 3

## Document metadata

- Title: Example title

## PDF page 2

Extracted source text.

## PDF page 3

More extracted source text.
</extraction_shape>

## Analyze the Extraction

- **Summary or question answering:** Read all relevant sections. Retain qualifying language, dates, quantities, and exceptions. Cite every material claim with its PDF page number.
- **Comparison:** Extract the corresponding sections from every document. Compare only like-for-like fields. Identify missing data instead of inferring it.
- **Table-like content:** Treat text order as a transcription, not a validated table. Reconstruct a row or column only when labels and values remain unambiguous; otherwise describe the ambiguity and cite the page.
- **Long documents:** First identify title, headings, contents pages, and relevant terms. Extract the target pages with their surrounding pages. Expand the selection when cross-references, definitions, or footnotes change the interpretation.
- **Exact quotations:** Copy from the extraction only after checking the page marker. Preserve wording, and identify the PDF page.

## Limitations and Recovery

- `pypdf` reads a PDF text layer. A `[No extractable text on this page.]` marker usually means the page is scanned, image-only, or has unusable text encoding. Report that limitation; do not claim OCR results.
- Multi-column layouts, tables, headers, footers, ligatures, and unusual fonts can scramble reading order. Do not silently repair ambiguous values.
- If the script reports encryption, use `--password-env`. If it cannot decrypt with the supplied variable, report that access was unavailable.
- If the reader cannot parse the document, report the read error and stop. Do not repair, rewrite, or substitute the PDF.
- If the document has no standard metadata, omit metadata-based conclusions rather than inventing it.

## Completion Checks

- The requested PDF file remains unmodified.
- Every analyzed passage is traceable to a `PDF page N` marker.
- The response distinguishes extracted facts from interpretation.
- Empty or unreliable pages, encryption, and layout ambiguity are disclosed when relevant.
- No PDF package or tool other than `pypdf` was used.
