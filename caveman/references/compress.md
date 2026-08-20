# Caveman Compress Mode

Rewrite a natural-language file (CLAUDE.md, notes, todos, preferences) in
caveman style to cut its input-token cost. The agent compresses the prose;
the bundled guard script deterministically handles everything else:
classification, sensitive-file refusal, verified out-of-tree backup,
structural validation, and atomic writes. The target file is never written
until validation passes.

## Procedure

1. Prepare. Run the bundled script at its canonical path (uv caches script
   environments by path; do not copy it elsewhere):

<prepare_command>
uv run --script <skill-root>/scripts/compress_guard.py prepare <absolute-filepath>
</prepare_command>

   On REFUSED (sensitive name, empty, oversized, non-UTF-8, backup artifact,
   existing backup), report the reason and stop: refusals are hard
   invariants. On success it prints BACKUP and BODY paths; frontmatter is
   already split off and preserved verbatim. SIGNAL lines are advisory
   evidence from the script's heuristics (content assessed as code, config,
   or inconclusive, with the observed ratios): weigh them yourself. If
   signals say code or config and the user did not explicitly name this
   file for compression, stop and report instead of proceeding; if the user
   explicitly asked, proceed: the verified backup makes it undoable.

2. Compress. Read the BODY file and rewrite its prose per the rules below.
   Write the result to a scratch file. Do not touch fenced code, inline
   code, URLs, or headings.

3. Apply:

<apply_command>
uv run --script <skill-root>/scripts/compress_guard.py apply <absolute-filepath> <compressed-body-file>
</apply_command>

   On pass it atomically writes the target and reports honest character
   savings. On ERROR output, fix ONLY the listed errors in the scratch file
   by restoring the missing content from the backup (never recompress
   untouched sections) and re-apply. After two failed fix rounds, stop and
   report; the target file is still untouched.

4. To undo a completed compression:
   `uv run --script <skill-root>/scripts/compress_guard.py restore <filepath>`.

## Cleanup

Only when the user EXPLICITLY asks to clear compression backups (never
unprompted, never as routine tidying), run one of:

<clean_commands>
uv run --script <skill-root>/scripts/compress_guard.py clean <filepath>
uv run --script <skill-root>/scripts/compress_guard.py clean --all
</clean_commands>

The first removes one file's backup artifacts; the second removes every
backup this tool ever made. A removed backup destroys the only undo (and
the only restore path) for its compression, so confirm intent first when
the request is ambiguous.

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
- Non-Markdown prose (.rst, .tex, .typ): the script warns that structural validation assumes Markdown; their headings and code blocks are not protected by the checks, so preserve structure manually and with extra care.
- Backups live out-of-tree (XDG data dir, or LOCALAPPDATA on Windows) so skill auto-loaders never re-ingest them; the script refuses anything inside the backup tree.
- This mode is the sole exemption to the "no caveman in persisted files" boundary, and only for the file the user names.
- One-shot: the report ends the mode; the active intensity level is untouched.
