# Harness and access

"Not documented" means vendor documentation surveyed does not state it:
probe it, never assume it.

## Inheritance

| Harness | Primitive | Delegate inherits | Skill access | Caps and limits | Output |
| --- | --- | --- | --- | --- | --- |
| Claude Code | `Agent` tool; `isolation` for a fork | project instruction hierarchy, git status, working directory; no parent conversation. A fork inherits system prompt, tools, model, and history | skill tool present by default, so the delegate can discover and load; the definition's `skills:` field preloads bodies at definition time; blocked by omitting the skill tool or listing it as disallowed | 20 concurrent, and the 21st spawn fails rather than queuing; nesting depth 3 by default; 15,000 tokens across all agent descriptions | final text only, never intermediate tool calls; scanned and marked when instruction-shaped |
| GitHub Copilot | `runSubagent`; `/fleet` for parallel, `/delegate` to the cloud agent | workspace, permission and tool scope; no parent conversation | instruction files auto-attach by `applyTo` glob and stack without override; an agent's `skills:` array is injected in full at agent start; prompt and chat-mode files need explicit attachment | 30,000 characters per agent prompt; about 1,000 lines per instruction file, beyond which the vendor states quality degrades | not documented |
| Google Antigravity | `invoke_subagent` | terminal prefixes, file scopes, sandbox settings; clean slate on conversation history | rules load by glob, always-on, model decision, or manual; skills auto-load by description match | 12,000 characters per rules file; nesting depth 10 | not documented |
| OpenAI Codex | opt-in only: a plain request for parallel agents, or an `[agents]` entry in config.toml or `.codex/agents/*.toml` | model, reasoning effort, sandbox policy, permission mode, tool set, working directory | skills auto-discovered from `.agents/skills` with progressive disclosure, metadata first and body on selection; whether a delegate re-reads AGENTS.md or inherits the parent's discovered skills is not documented | AGENTS.md concatenated root-down, capped by `project_doc_max_bytes`, 32 KiB by default; about 8,000 characters of skill metadata | the parent waits for every requested result, then outputs one consolidated response |
| DeepSeek Harness (dsh) | `dsh-tool-subagent`, plus `dsh-tool-subagent-control` for send_message, interrupt_agent, list_agents | nothing by default: each child gets a new flat tool scope, and the caller passes an optional `toolFilter`. A fork provider inherits a completed-turn prefix of the parent log; spawn and ACP providers inherit nothing | the Agent Skills SKILL.md contract with six-tier non-recursive discovery; whether a spawned child auto-loads skills is not documented | not documented | typed: `SubagentStartRequest` carries an optional `outputSchema` (JSON Schema) for the result; otherwise the child's last non-empty assistant message |
| OpenAI Agents SDK | `handoff` transfers control with the full history; `as_tool` calls a sub-agent with generated input and leaves the answer with the orchestrator | handoff: everything. as_tool: only the generated input | not documented | not documented | handoff: the delegate owns the conversation from then on. as_tool: a tool result the orchestrator keeps |

OpenAI Agents SDK handoff prompts carry SDK's recommended prefix, telling
delegate it is part of multi-agent system.

## Access

Take first variant that holds, reading top down. Order is reliability of
text being read, not cost: preloading spends tokens up front whether or not
skill is needed, buys certainty that body is present.

| Variant | Holds when | What the brief does | Standing |
| --- | --- | --- | --- |
| Preloaded | the agent definition names the skill under `skills:`, so the body is injected at start | names the skill only | documented |
| Invocable | the delegate has a skill-loading tool | commands the skill by name in slash form; the delegate loads the body itself | measured |
| Readable | no skill tool, but the file is reachable on disk | gives the absolute path and says to read it before starting | measured |
| Definable | no preload exists, and the harness hot-reloads agent definitions | mints an agent definition naming the skill under `skills:`, then sends to that type | documented, untested: the agents directory must exist at session start, since the docs require a restart to pick one up |
| Sealed | none of the above holds | excerpts the binding rules into the brief's rules field | documented, not observed |

Sealed arises when skill tool is omitted from delegate's tools or listed
among disallowed tools, when skill is marked not model-invocable, or on
harness with no skill loading at all.

Harness preloading skills does so at agent-definition time; prompt is only
call-time channel. Point, not paste, wherever delegate can load skill
itself. Excerpting is Sealed branch alone, under excerpting law in `send`.

## Probe

Unfamiliar harness, or agent definition with restricted tool list: send one
probe delegate before first real brief; it settles access for every later
delegation.

<template for="probe">
TASK
Report what you start with. Do no other work.

CONTRACT
Output exactly these five lines:
tools: <every tool name available to you>
skill-listing: <present with N entries | absent>
skill-load: <the first line returned by loading skill "<name>" | the exact error>
project-instructions: <the first line of any project instruction file in your context | absent>
cwd: <your working directory>

LIMIT
Three tool calls. On hitting it, output the lines you have settled.
</template>

Read probe against access table. Skill-load succeeding puts delegate at
Invocable, reachable file with no skill tool at Readable, neither at Sealed.
Absent project instructions mean every repository convention task depends on
travels in brief's evidence field.
