---
name: author-skill
description: >-
  Distills a completed task history, workflow, or procedure into a
  reproducible SKILL.md that a fresh agent can execute without external
  memory, and reviews existing skills for conformance to the Agent Skills
  standard. Use when the user asks to create, refactor, review, or distill a
  skill, or when a repeated procedure should become one.
license: MIT
---

# Author Skill

<system_directives>
  <skill_anatomy>
    <rule>Store the skill in a kebab-case directory containing a file named exactly `SKILL.md`.</rule>
    <rule>Begin the file with YAML frontmatter restricted to Agent Skills spec fields (agentskills.io), in this order: `name`, `description`, then only as needed `license`, `compatibility`, `metadata`, `allowed-tools`. Never emit agent-specific extension fields such as `argument-hint` or `when_to_use`; record such hints as quoted string values under `metadata`.</rule>
    <rule>Set `name` equal to the directory name: 1-64 characters; lowercase letters, numbers, and hyphens; no leading, trailing, or consecutive hyphens. Name a task skill with an imperative verb phrase, the command a user would speak (e.g., `fact-check`, `read-pdf`, `git-commit`); name a persona or stance skill with a single noun (e.g., `caveman`, `ponytail`). Never append filler nouns like `-protocol`, `-helper`, or `-skills`.</rule>
    <rule>Write `description` as a `>-` folded block scalar, 1-1024 characters, third person, in two movements: first a capability statement of what the skill does carrying its key search terms, then trigger conditions starting "Use when"; append a "Do not use for ..." exclusion when misfires are likely.</rule>
    <rule>Set `license: MIT` so a skill vendored out of this repository retains its terms.</rule>
    <rule>Add `compatibility` (max 500 characters) only when the skill requires specific runtimes, system packages, or network access; most skills omit it.</rule>
    <rule>Use Markdown `##` or `###` headings for internal structure.</rule>
    <rule>Address bundled files by registered name, never by path. Declare every path exactly once, in a `## Registry` table that is the final section of `SKILL.md` and maps each name to its path. A name is the basename without `.md`, written in backticks so it reads as an identifier rather than the ordinary word. Reference files cite siblings by name only and never link, since references stay one level deep from `SKILL.md`.</rule>
    <rule>Define each topic in exactly one file. Where a value, threshold, or enumeration is restated in a second file, replace the copy with an attribution naming its owner, so the two can never disagree.</rule>
    <rule>Wrap all examples, templates, and payloads strictly in XML tags to prevent instruction bleed.</rule>
  </skill_anatomy>

  <execution_constraints>
    <rule>Target this skill exclusively at agent-facing procedures.</rule>
    <rule>Extract only verified tool calls and successful commands from the execution history.</rule>
    <rule>Parameterize all project-specific values (paths, hostnames, IDs) or provide instructions to derive them dynamically.</rule>
    <rule>Express directives conditionally and explicitly (e.g., "If X, execute Y").</rule>
    <rule>Enforce token-economical language (Caveman formatting) in the generated skill, utilizing sentence fragments and eliminating conversational filler.</rule>
    <rule>Never emit em-dash characters (U+2014); use a hyphen, a comma, a colon, or restructure the sentence.</rule>
  </execution_constraints>

  <distillation_pipeline>
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
  </distillation_pipeline>

  <validation_checklist>
    <directive>Silently verify these conditions before finalizing the skill.</directive>
    <item>Directory is kebab-case; file is exactly `SKILL.md`.</item>
    <item>Frontmatter contains only Agent Skills spec fields in canonical order; `name` matches the directory; `description` is a `>-` folded block within 1024 characters following the capability-then-"Use when" form.</item>
    <item>Procedure strictly reflects the verified path with zero abandoned attempts.</item>
    <item>Project-specific values are parameterized or dynamically derived.</item>
    <item>Every step specifies exact tools, flags, and expected outputs.</item>
    <item>Examples and templates reside exclusively within XML blocks.</item>
    <item>Gotchas section contains non-obvious traps.</item>
    <item>No placeholder text remains outside intentional templates.</item>
    <item>Reproduction Test: The procedure relies exclusively on the document text, guaranteeing that a fresh agent can execute it without external memory or clarifying questions.</item>
  </validation_checklist>

  <output_contract>
    <rule>Output the finalized SKILL.md file directly into the codebase or as a raw Markdown block.</rule>
    <rule>Omit all conversational filler, preambles, summaries, and concluding remarks.</rule>
  </output_contract>
</system_directives>

## Examples

<examples>
  <example type="distillation">
    <context>Converting raw history into a reproducible step.</context>
    <raw_history>I tried bumping the dependency directly, the lockfile drifted and CI failed, then I realized this repo regenerates the lock via `make lock`, so I ran that and CI passed.</raw_history>
    <distilled_procedure>
      <step>Regenerate the lockfile using the repository's native command: `make lock`.</step>
      <step>Commit both the manifest and the lockfile together.</step>
    </distilled_procedure>
    <gotcha>Editing the lockfile manually causes CI drift. Always regenerate it via the build tool.</gotcha>
  </example>

  <example type="frontmatter-routing">
    <context>Writing trigger-based descriptions instead of passive summaries.</context>
    <invalid_description>This skill helps format python code using black and flake8.</invalid_description>
    <valid_description>Triggered when the user asks to format Python code, lint a file, or run Black and Flake8.</valid_description>
  </example>

  <example type="parameterization">
    <context>Removing incidental project specifics.</context>
    <invalid_hardcoded_step>Run the build script located at `/users/joe/projects/manifold/scripts/build.sh`.</invalid_hardcoded_step>
    <valid_parameterized_step>Execute the build script located at `<repository_root>/scripts/build.sh`.</valid_parameterized_step>
  </example>

  <example type="xml-isolation">
    <context>Fencing reference material to prevent instruction bleed.</context>
    <invalid_format>
      Your config file should look like this:
      { "port": 8080 }
    </invalid_format>
    <valid_format>
      Create the configuration file using this schema:
      <config_template>
      { "port": 8080 }
      </config_template>
    </valid_format>
  </example>
</examples>
