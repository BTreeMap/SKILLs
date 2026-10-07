# Caveman Refactor Verb

Rewrite a natural-language file (CLAUDE.md, notes, todos, preferences) in
caveman style in place to cut input-token cost. The agent compresses the
prose; the bundled guard script deterministically handles the rest:
classification, sensitive-file refusal, a verified out-of-tree backup,
structural validation, and atomic writes. The script never writes the target
file until validation passes.

## Script

Bind the guard command once per shell, and re-bind after a reset; `realpath`
is required:

<commands for="bind">
R="env -u VIRTUAL_ENV uv run --project $(realpath <skill-root>/scripts) btm-caveman"
</commands>

The command surface is `prepare`, `apply`, `restore`, and `clean`, used as
the steps below show. Invoke the script and read its output; read its
source only when the user instructs troubleshooting. Every subcommand
prints one JSON record on stdout; advisories arrive on stderr as `signal:`
lines.

## Procedure

1. Prepare:

<commands for="prepare">
$R prepare <absolute-filepath>
</commands>

   A refusal exits 1 with `error: <reason>` having changed nothing. Refusals
   are hard invariants: report the reason and stop; trust them and never
   bypass one with a manual write. The script refuses exact credential,
   key, and secret filenames; paths inside a known private directory;
   backup artifacts and any path inside the backup tree (backups live
   outside the tree so skill auto-loaders never re-ingest them); a file
   that already has a backup; empty files; files over 500KB; and non-UTF-8
   files.

   On success the record carries the `backup` and `body` paths,
   `frontmatter` saying whether one was split off (it is preserved
   verbatim), and the body's `chars`.

   `signal:` lines are advisory heuristics for you to weigh: content
   assessed as code, config, or inconclusive, with the observed ratios; a
   filename that merely reads sensitive. A signal saying code, config, or
   sensitive filename stops the run unless the user explicitly named this
   exact file; then proceed, since the verified backup makes it undoable.

2. Compress. Read the `body` file, rewrite its prose per the rules below,
   and write the result to a scratch file. Do not touch fenced code, inline
   code, URLs, or headings. In mixed prose and code, compress prose only:
   code blocks are read-only regions, and a span you cannot tell is code or
   prose stays unchanged. For non-Markdown prose (.rst, .tex, .typ) the
   script signals that its checks assume Markdown; those headings and code
   blocks are unprotected, so preserve structure manually.

3. Apply. The compressed body reaches the script through its own slot,
   never as an argument:

<commands for="apply">
$R apply <absolute-filepath> --body:file <compressed-body-file>
</commands>

   On pass it atomically writes the target and reports `chars_before`,
   `chars_after`, and `percent_smaller`. Exit 1 returns a rejection record
   instead: each entry under `rejected` names the failed check in `where`
   and the problem in `fix`, and `unchanged` confirms the target file was
   never written. Fix ONLY the listed problems in the scratch file by
   restoring the missing content from the backup (never recompress
   untouched sections) and re-apply. After two failed fix rounds, stop and
   report; the target file is still untouched.

4. To undo a completed compression: `$R restore <filepath>`.

## Cleanup

`$R clean` with no argument lists the backups held, with their sizes, and
writes nothing. Only when the user EXPLICITLY asks to clear compression
backups (never unprompted, never as routine tidying), run one of:

<commands for="clean">
$R clean <filepath>
$R clean --all
</commands>

The first removes one file's backup; the second removes every backup this
tool ever made. Each reports `removed` and `bytes_freed`. A removed backup
destroys the only undo for its compression, so confirm intent first when the
request is ambiguous.

## Compression Rules

Remove: articles (a/an/the); filler (just, really, basically, actually,
simply, essentially); pleasantries; hedging ("it might be worth", "you could
consider"); redundant phrasing ("in order to" becomes "to", "make sure to"
becomes "ensure"); connective fluff (however, furthermore, additionally).

Compress: short synonyms ("big" not "extensive", "use" not "utilize");
fragments OK ("Run tests before commit"); drop "you should" and state the
action; merge bullets that repeat one point; keep one example where several
show the same pattern.

Preserve EXACTLY, never modify: fenced and indented code blocks, inline
backtick spans, URLs and markdown links, file paths, commands, technical
terms, proper nouns, dates, versions, numbers, environment variables.

Preserve structure: every heading with its exact text, bullet hierarchy,
list numbering, table structure (compress cell text only), YAML frontmatter
(the script guards it, keep it out of the scratch body).
