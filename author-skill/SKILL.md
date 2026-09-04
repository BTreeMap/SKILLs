---
name: author-skill
description: >-
  Distills a completed task history, workflow, or procedure into a
  reproducible SKILL.md that a fresh agent can execute without external
  memory. Also reviews existing skills against the Agent Skills standard.
  Use when the user asks to create, refactor, review, or distill a skill, or
  when a repeated procedure should become one.
license: MIT
metadata:
  argument-hint: "[skill name or path]"
---

# Author Skill

<system-directives>

  <skill-anatomy>
    <rule>Store the skill in a kebab-case directory containing a file named exactly `SKILL.md`.</rule>
    <rule>Begin the file with YAML frontmatter restricted to Agent Skills spec fields (agentskills.io), in this order: `name`, `description`, then only as needed `license`, `compatibility`, `metadata`, `allowed-tools`. Never emit agent-specific extension fields such as `argument-hint` or `when_to_use`; record such hints as quoted string values under `metadata`.</rule>
    <rule>Set `name` equal to the directory name: 1-64 characters; lowercase letters, numbers, and hyphens; no leading, trailing, or consecutive hyphens. Name a task skill with an imperative verb phrase, the command a user would speak (e.g., `fact-check`, `read-pdf`, `git-commit`); name a persona or stance skill with a single noun (e.g., `caveman`, `ponytail`). Never append filler nouns like `-protocol`, `-helper`, or `-skills`.</rule>
    <rule>Write `description` as a `>-` folded block scalar, 1-1024 characters, third person, in two movements: first a capability statement carrying the skill's key search terms, then trigger conditions starting "Use when"; append a "Do not use for ..." exclusion when misfires are likely.</rule>
    <rule>Set `license: MIT` so a skill vendored out of this repository retains its terms.</rule>
    <rule>Add `compatibility` (max 500 characters) only when the skill requires specific runtimes, system packages, or network access; most skills omit it.</rule>
    <rule>Use Markdown `##` or `###` headings for internal structure.</rule>
    <rule>Address bundled files by registered name, never by path. Declare every path exactly once, in a `## Registry` table that is the first `##` section of `SKILL.md` and maps each name to its path, so names are declared before the body uses them. A name is the basename without `.md`, backticked so it reads as an identifier rather than the ordinary word. Reference files cite siblings by name only and never link: references stay one level deep from `SKILL.md`.</rule>
    <rule>Define each topic in exactly one file. Where a value, threshold, or enumeration is restated in a second file, replace the copy with an attribution naming its owner, so the two can never disagree. Attribute only toward a file guaranteed to be in context when the copy is read (the spine, or a kernel co-loaded with it); a file the skill loads alone keeps its own copies.</rule>
    <rule>Wrap all examples, templates, and payloads strictly in XML tags to prevent instruction bleed. Name every tag in kebab-case, leave a blank line before an opening tag, and put `<![CDATA[` on its own line. CommonMark's tag name admits letters, digits and hyphens but never an underscore, and an HTML block opens only on a line beginning with `<![CDATA[` or on a complete tag that no paragraph runs into. Satisfy all three and the payload is opaque to every markdown tool; miss one and it is paragraph text, which a formatter will rewrap into unparseable code.</rule>
  </skill-anatomy>

  <execution-constraints>
    <rule>Target this skill exclusively at agent-facing procedures.</rule>
    <rule>Extract only verified tool calls and successful commands from the execution history.</rule>
    <rule>Parameterize all project-specific values (paths, hostnames, IDs) or instruct how to derive them dynamically.</rule>
    <rule>Express directives conditionally and explicitly (e.g., "If X, execute Y").</rule>
    <rule>Enforce token-economical language in the generated skill: sentence fragments, no conversational filler; `/caveman` defines that register in full.</rule>
    <rule>Write every sentence to carry a rule, a condition, an input, or an example; delete narration about the document, restated headings, and repeated rationale. Keep rationale only where it changes a judgment call.</rule>
    <rule>State each directive as the pattern to follow; a prohibition spells out the unwanted pattern and raises its salience. Reserve negation for hard boundaries where the banned form must be named to be recognized.</rule>
    <rule>Exclude inflation vocabulary (comprehensive, seamless, robust, powerful, leverage, delve, cutting-edge) and wind-ups (in order to, it is important to note); sweep the finished draft with `/humanize` before finalizing.</rule>
    <rule>Write for a follower model less capable than the author: leave no step implied and no assumption unstated. When brevity and sufficiency conflict, sufficiency wins.</rule>
    <rule>Never emit em-dash characters (U+2014); use a hyphen, a comma, a colon, or restructure the sentence.</rule>
  </execution-constraints>

  <script-design>
    <directive>A bundled script and the agent invoking it form a neuro-symbolic pair. Design the script as the symbolic half; the skill text tells the agent, the neuro half, how to consume its output.</directive>
    <rule>The script owns exact, decidable checks: invariants (existence, size, encoding, identity), structural equality, digests, atomic writes, backups. It hard-fails (nonzero exit) only on an invariant violation.</rule>
    <rule>A heuristic never holds refusal authority. Emit heuristic judgments as advisory signal lines that state their evidence (ratios, matched rules, best-guess classification); the skill text instructs the agent to weigh signals against user intent.</rule>
    <rule>Gate destructive or hard-to-reverse effects on an exact witness: a marker file, an identity record, or an explicit flag the caller must pass. Provide an undo path (verified backup) where the agent's judgment could be wrong.</rule>
    <rule>Never decide trust silently: when a check is skipped or vacuous, the script states so in its output.</rule>
    <rule>Document the script's full command surface and output conventions in SKILL.md; that interface is the handoff point, and a production run rides on it alone. Source reading belongs to user-instructed troubleshooting; state this gate in one line beside the commands.</rule>
    <rule>The script mints unique identifiers: the agent supplies two or three keywords, the script returns the lowercase dash-joined slug plus a 128-bit entropy suffix (b32hexencode(os.urandom(16)).decode().rstrip("=").lower()) and echoes it in every output. The agent supplies the full identifier in later calls; keyword-subset resolution is the recovery path for an identifier lost to context compression, signaled and re-echoed on use, with ambiguity erroring and listing candidates. Identifiers with a natural key (DOI, path) keep it.</rule>
    <rule>Keep the command surface uniform: one record is a batch of one, sibling record kinds share one plural-array container schema, every subcommand addresses its subject the same way, and each effect has exactly one spelling. Each asymmetry costs the consuming agent a re-read of help text.</rule>
    <rule>Configuration travels as command-line parameters; free-form content travels on stdin. Closed vocabularies, counts, booleans, paths, and minted identifiers are shell-safe and stay flags; prose, queries, regexes, and any JSON body are not, so a subcommand with a required free-form field reads one JSON object from stdin or `--file` and offers no inline spelling for it. An optional positional beside flags is argparse's ambiguous shape and a quoted argument is rewritten before the process sees it; both cost a whole tool call to discover. argv is untrusted input like any other: a malformed argument line is a bounded, located rejection in the exit-1 column, never a payload echoed back and never the exit code that invites a retry. Every call names its subject: several agents may share one state root, so the script holds no ambient current-subject state. Keep identifiers cheap by instructing the agent to bind the command path and session identifier to shell variables (reused while the shell persists, re-bound after a reset) and to chain a round's calls in one shell invocation.</rule>
    <rule>A skill that bundles Python is a member of the repository's uv workspace, and the member is the skill's `scripts/` directory: it holds `scripts/pyproject.toml`, a `scripts/src/btm_<skill>/` package, and `scripts/tests/`, is listed in the root `pyproject.toml`, and keeps every coding element inside `scripts/` so the skill directory stays documentation. The member's `[project.scripts]` console command `btm-<skill>` is the one entry point; skills document its invocation as one shell binding, `R="env -u VIRTUAL_ENV uv run --project $(realpath <skill-root>/scripts) btm-<skill>"`, where `realpath` is required because uv resolves the project path lexically and an alias path such as `.claude/skills/<skill>/` has no workspace root among its lexical ancestors. Logic shared across members lives once in the kernel package `btm-corekit` under `.corekit/`, declared as `dependencies = ["btm-corekit"]` with the source `btm-corekit = { workspace = true }`. The kernel already carries the gate mechanics a session-keeping script repeats (`SessionStore` creation and meta, `EventLog`, `Admission` with `Pool`, `read_batch` and `rejection`, `wire_pad` and `wire_clean`); a new member composes them and adds only its record semantics. Members never redefine kernel symbols; such a skill's `compatibility` notes that it runs from a full repository checkout.</rule>
    <rule>Keep mechanical, idempotent repairs in the script (e.g., delete a corrupt artifact on digest mismatch); leave judgment calls to the agent, informed by the script's diagnostics.</rule>
    <rule>A script that talks to the network marks its request origin by one shared convention, first defined wins: `BTM_USER_AGENT`, sent verbatim as the User-Agent; else `BTM_CONTACT`, else the constant `skills@oss.joefang.org`, in the derived header `btm-skills/1.0 (<skill-name>; mailto:<contact>)`. Only a contact-derived identity may also disclose the contact through polite request pools (e.g. an OpenAlex or Crossref `mailto` parameter); a verbatim override marks the request with nothing else. The script alone reads the variables; the skill text never mentions them.</rule>
  </script-design>

  <distillation-pipeline>
    <phase name="extraction">
      <step>Reconstruct the verified path exclusively from executed tool calls.</step>
      <step>Isolate points of failure, surprises, and backtracks for the Gotchas section.</step>
    </phase>
    <phase name="generalization">
      <step>Retain only the verified, successful path.</step>
      <step>Document the structural reasoning (the "what" and "why") for non-obvious choices.</step>
      <step>Specify exact tools, flags, branches, and expected results for every step.</step>
      <step>Limit length to approximately 500 lines.</step>
      <step>Offload bulky reference data to sibling files.</step>
    </phase>
  </distillation-pipeline>

  <validation-checklist>
    <directive>Silently verify these conditions before finalizing the skill.</directive>
    <item>Directory is kebab-case; file is exactly `SKILL.md`.</item>
    <item>Frontmatter contains only Agent Skills spec fields in canonical order; `name` matches the directory; `description` is a `>-` folded block within 1024 characters following the capability-then-"Use when" form.</item>
    <item>Procedure strictly reflects the verified path with zero abandoned attempts.</item>
    <item>Project-specific values are parameterized or dynamically derived.</item>
    <item>Every step specifies exact tools, flags, and expected outputs.</item>
    <item>Examples and templates reside exclusively within XML blocks.</item>
    <item>Any bundled script hard-fails only on exact invariants; heuristic judgments surface as advisory signals, and no trust decision is silent.</item>
    <item>Any network-touching script resolves its request origin by the `BTM_USER_AGENT` / `BTM_CONTACT` / project-contact chain, and no `SKILL.md` mentions those variables.</item>
    <item>Every sentence carries a rule, condition, input, or example; a `/humanize` sweep finds no inflation vocabulary, wind-ups, or filler.</item>
    <item>Gotchas section contains non-obvious traps.</item>
    <item>No placeholder text remains outside intentional templates.</item>
    <item>Reproduction Test: the document text alone lets a fresh agent execute the procedure without external memory or clarifying questions.</item>
  </validation-checklist>

  <output-contract>
    <rule>Output the finalized SKILL.md file directly into the codebase or as a raw Markdown block.</rule>
    <rule>Omit all conversational filler, preambles, summaries, and concluding remarks.</rule>
  </output-contract>
</system-directives>

## Examples

<examples>

  <example type="distillation">
    <context>Converting raw history into a reproducible step.</context>
    <raw-history>I tried bumping the dependency directly, the lockfile drifted and CI failed, then I realized this repo regenerates the lock via `make lock`, so I ran that and CI passed.</raw-history>
    <distilled-procedure>
      <step>Regenerate the lockfile using the repository's native command: `make lock`.</step>
      <step>Commit both the manifest and the lockfile together.</step>
    </distilled-procedure>
    <gotcha>Editing the lockfile manually causes CI drift. Always regenerate it via the build tool.</gotcha>
  </example>

  <example type="frontmatter-routing">
    <context>Writing trigger-based descriptions.</context>
    <invalid-description>This skill helps format python code using black and flake8.</invalid-description>
    <valid-description>Triggered when the user asks to format Python code, lint a file, or run Black and Flake8.</valid-description>
  </example>

  <example type="parameterization">
    <context>Removing incidental project specifics.</context>
    <invalid-hardcoded-step>Run the build script located at `/users/joe/projects/manifold/scripts/build.sh`.</invalid-hardcoded-step>
    <valid-parameterized-step>Execute the build script located at `<repository-root>/scripts/build.sh`.</valid-parameterized-step>
  </example>

  <example type="xml-isolation">
    <context>Fencing reference material to prevent instruction bleed.</context>
    <invalid-format>
      Your config file should look like this:
      { "port": 8080 }
    </invalid-format>
    <valid-format>
      Create the configuration file using this schema:
      <config-template>
      { "port": 8080 }
      </config-template>
    </valid-format>
  </example>
</examples>
