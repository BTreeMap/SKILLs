---
name: authoring-skills
description: Triggered when the user asks to create, refactor, review, or distill a SKILL.md file from a task history or workflow. Converts execution history into a reproducible agent procedure.
---

# Authoring Skills

<system_directives>
  <skill_anatomy>
    <rule>Store the skill in a kebab-case directory containing a file named exactly `SKILL.md`.</rule>
    <rule>Begin the file with YAML frontmatter.</rule>
    <rule>Set `name` to a lowercase, hyphenated gerund or noun phrase matching the directory (e.g., `writing-runbooks`).</rule>
    <rule>Set `description` to state exact trigger conditions and actions for the orchestrator.</rule>
    <rule>Use Markdown `##` or `###` headings for internal structure.</rule>
    <rule>Wrap all examples, templates, and payloads strictly in XML tags to prevent instruction bleed.</rule>
  </skill_anatomy>

  <execution_constraints>
    <rule>Target this skill exclusively at agent-facing procedures.</rule>
    <rule>Extract only verified tool calls and successful commands from the execution history.</rule>
    <rule>Parameterize all project-specific values (paths, hostnames, IDs) or provide instructions to derive them dynamically.</rule>
    <rule>Express directives conditionally and explicitly (e.g., "If X, execute Y").</rule>
    <rule>Enforce token-economical language (Caveman formatting) in the generated skill, utilizing sentence fragments and eliminating conversational filler.</rule>
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
    <item>Frontmatter `name` matches the directory; `description` defines strict triggers.</item>
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
