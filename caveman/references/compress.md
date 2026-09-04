# Caveman Compress Mode

Rewrite a natural-language file (CLAUDE.md, notes, todos, preferences) in
caveman style to cut input-token cost. Agent compresses the prose; the
bundled guard script deterministically handles the rest: classification,
sensitive-file refusal, verified out-of-tree backup, structural validation,
atomic writes. Target file is never written until validation passes.

## Procedure

1. Prepare. Bind the guard command once per shell (re-bind after a reset;
   `realpath` is required), then run prepare:

<prepare-command>
R="env -u VIRTUAL_ENV uv run --project $(realpath <skill-root>/scripts) btm-caveman"
$R prepare <absolute-filepath>
</prepare-command>

   On REFUSED (sensitive name, empty, oversized, non-UTF-8, backup artifact,
   existing backup), report the reason and stop: refusals are hard
   invariants. On success it prints BACKUP and BODY paths; frontmatter is
   already split off and preserved verbatim. SIGNAL lines are advisory
   heuristics (content assessed as code, config, or inconclusive, with the
   observed ratios): weigh them yourself. Signals saying code or config stop
   the run unless the user explicitly named this file; then proceed, since
   the verified backup makes it undoable.

2. Compress. Read the BODY file and rewrite its prose per the rules below.
   Write the result to a scratch file. Do not touch fenced code, inline
   code, URLs, or headings.

3. Apply:

<apply-command>
$R apply <absolute-filepath> <compressed-body-file>
</apply-command>

   On pass it atomically writes the target and reports character savings.
   On ERROR output, fix ONLY the listed errors in the scratch file by
   restoring the missing content from the backup (never recompress untouched
   sections) and re-apply. After two failed fix rounds, stop and report; the
   target file is still untouched.

4. To undo a completed compression: `$R restore <filepath>`.

## Cleanup

Only when the user EXPLICITLY asks to clear compression backups (never
unprompted, never as routine tidying), run one of:

<clean-commands>
$R clean <filepath>
$R clean --all
</clean-commands>

The first removes one file's backup artifacts; the second removes every
backup this tool ever made. A removed backup destroys the only undo for its
compression, so confirm intent first when the request is ambiguous.

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

## Boundaries

- The script hard-refuses only invariants: secrets-like names, backup artifacts, files over 500KB, non-UTF-8, empty files. Trust refusals; never bypass with a manual write. Content-type judgment arrives as SIGNAL lines for you to weigh: code or config signals mean stop unless the user explicitly asked for that exact file.
- Mixed prose and code: compress prose only; code blocks are read-only regions. When unsure whether a span is code or prose, leave it unchanged.
- Non-Markdown prose (.rst, .tex, .typ): the script warns that its checks assume Markdown; those headings and code blocks are unprotected, so preserve structure manually.
- Backups live outside the tree so skill auto-loaders never re-ingest them; the script refuses any path inside the backup tree.
- This mode is the sole exemption to the "no caveman in persisted files" boundary, and only for the file the user names.
- One-shot: the report ends the mode; the active intensity level is untouched.
