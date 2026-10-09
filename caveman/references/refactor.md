# Caveman Refactor Verb

Rewrite natural-language file (CLAUDE.md, notes, todos, preferences) in
caveman style in place to cut input-token cost. Agent compresses prose;
bundled guard script deterministically handles rest: classification,
sensitive-file refusal, verified out-of-tree copy, structural validation,
atomic writes. Script never writes target file until validation passes.

## Script

Bind guard command once per shell; re-bind after reset; `realpath` required:

<commands for="bind">
R="env -u VIRTUAL_ENV -u UV_PROJECT_ENVIRONMENT uv run --project $(realpath <skill-root>/scripts) btm-caveman"
</commands>

Command surface: `prepare`, `apply`, `replace`, `clean`, used as steps below
show. Invoke script, read its output; read its source only when user
instructs troubleshooting. Every subcommand prints one JSON record on
stdout; advisories arrive on stderr as `signal:` lines.

## Procedure

1. Prepare:

<commands for="prepare">
$R prepare <absolute-filepath> [--project <name>]
</commands>

   Refusal exits 1 with `error: <reason>`, nothing changed. Refusals are
   hard invariants: report reason and stop; trust them, never bypass one
   with manual write. Script refuses exact credential, key, and secret
   filenames; paths inside known private directory; copy artifacts and any
   path inside copy tree (copies live outside tree so skill auto-loaders
   never re-ingest them); file already having copy; empty files; files over
   500KB; non-UTF-8 files.

   On success record carries `copy` and `body` paths, `frontmatter` saying
   whether one was split off (preserved verbatim), body's `chars`, `project`
   (`--project NAME` tags copy with free project name shared across skills).

   `signal:` lines are advisory heuristics for you to weigh: content
   assessed as code, config, or inconclusive, with observed ratios; filename
   that merely reads sensitive. Signal saying code, config, or sensitive
   filename stops run unless user explicitly named this exact file; then
   proceed, since verified copy makes it undoable.

2. Compress. Read `body` file, rewrite its prose per rules below, write
   result to scratch file. Do not touch fenced code, inline code, URLs, or
   headings. Mixed prose and code: compress prose only; code blocks are
   read-only regions; span you cannot tell is code or prose stays unchanged.
   Non-Markdown prose (.rst, .tex, .typ): script signals its checks assume
   Markdown; those headings and code blocks are unprotected, so preserve
   structure manually.

3. Apply. Compressed body reaches script through its own slot, never as
   argument:

<commands for="apply">
$R apply <absolute-filepath> --body:file <compressed-body-file>
</commands>

   On pass it atomically writes target, reports `chars_before`,
   `chars_after`, `percent_smaller`. Exit 1 returns rejection record
   instead: each entry under `rejected` names failed check in `where` and
   problem in `fix`; `unchanged` confirms target file never written. Fix
   ONLY listed problems in scratch file by putting back missing content from
   copy (never recompress untouched sections), re-apply. After two failed
   fix rounds, stop and report; target file still untouched.

4. To undo completed compression: `$R replace <filepath>`.

## Cleanup

`$R clean` with no argument lists copies held, with sizes and projects,
writes nothing; `--project NAME` keeps one project's. Only when user
EXPLICITLY asks to clear compression copies (never unprompted, never as
routine tidying), run one of:

<commands for="clean">
$R clean <filepath>
$R clean --all
</commands>

First removes one file's copy; second removes every copy this tool ever
made. Each reports `removed` and `bytes_freed`. Removed copy destroys only
undo for its compression: confirm intent first when request is ambiguous.

## Compression Rules

Remove: articles (a/an/the); filler (just, really, basically, actually,
simply, essentially); pleasantries; hedging ("it might be worth", "you could
consider"); redundant phrasing ("in order to" becomes "to", "make sure to"
becomes "ensure"); connective fluff (however, furthermore, additionally).

Compress: short synonyms ("big" not "extensive", "use" not "utilize");
fragments OK ("Run tests before commit"); drop "you should", state action;
merge bullets repeating one point; keep one example where several show same
pattern.

Preserve EXACTLY, never modify: fenced and indented code blocks, inline
backtick spans, URLs and markdown links, file paths, commands, technical
terms, proper nouns, dates, versions, numbers, environment variables.

Preserve structure: every heading with exact text, bullet hierarchy, list
numbering, table structure (compress cell text only), YAML frontmatter
(script guards it; keep it out of scratch body).
