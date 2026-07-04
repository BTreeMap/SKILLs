---
name: caveman-protocol
description: Compresses language model outputs for all coding, refactoring, and debugging tasks to maximize context window longevity. Use this skill whenever the user explicitly asks to apply caveman formatting, optimize tokens, or use the slash command /caveman-compress.
---

# Caveman Protocol

This protocol provides a deterministic token-optimization framework for frontier models. Because conversational turns accumulate in the context window, trimming natural language output extends usable memory and delays session resets.

## 1. When To Use

Use this protocol for coding, refactoring, and debugging workflows where token economy is required. This applies when the user explicitly triggers the protocol or when maximum context preservation is requested.

## 2. Procedure

Read and strictly execute the directives defined in the XML blocks below. 

<caveman_directives>
  <rule>Begin responses directly with the requested code blocks, standard diffs, or structural data.</rule>
  <rule>Express necessary architectural context or logic strictly as sentence fragments, direct imperatives, or comma-separated lists.</rule>
  <rule>Provide the exact, fully implemented code blocks required to solve the task to ensure absolute technical completeness.</rule>
  <rule>Terminate the response immediately after the final closing syntax of the required technical artifact.</rule>
</caveman_directives>

<output_contracts>
  <contract trigger="Information Retrieval (Searching/Tracing)">
    Format responses strictly as: `[File:Line] <Entity>: <State/Issue>`
  </contract>
  <contract trigger="Building (Code Generation/Fixing)">
    Output raw implementation details using standard diff formats or complete code blocks.
  </contract>
  <contract trigger="Reviewing (Audits/Critiques)">
    Identify defects and architectural flaws directly using the format: `[Location] <Severity>: <Problem> -> <Fix>`
  </contract>
</output_contracts>

<compress_directive>
  When the user invokes `/caveman-compress` on provided text, documentation, or configuration data:
  Rewrite the target text using compact key-value mappings and token-optimized semantic structures.
  Preserve exact technical instructions while discarding conversational phrasing.
</compress_directive>

## 3. Gotchas

*   Compression targets natural language prose exclusively. Compressing code syntax, URLs, or literal string values will break functionality.
*   Models frequently attempt to append a helpful summary after a large code block. Ensure the generation stops precisely at the end of the requested code block.

## 4. Example

<example type="protocol-application">
User request: "Can you help me find the bug in the authentication middleware, and then fix it so it returns a 401 instead of a 500?"

Correct Caveman Protocol Output:
`[src/middleware/auth.ts:42] ErrorHandler: Uncaught exception triggers 500.`

```typescript
if (!token.isValid()) {
  return res.status(401).json({ error: "Unauthorized" });
}
```
