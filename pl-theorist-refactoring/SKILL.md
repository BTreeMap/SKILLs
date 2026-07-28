---
name: pl-theorist-refactoring
description: "Use when refactoring Python, JavaScript, TypeScript, Rust, Go, Haskell, or C# toward functional style while preserving behavior, stack safety, runtime cost, and local conventions. Progressively loads the target language's cost constraints and selects a lower-level idiom when an FP abstraction would be inefficient."
argument-hint: "Code or files to refactor; state the target language when it cannot be inferred"
---

# PL Theorist Functional Refactoring

## Purpose

Transform imperative, stateful code into the simplest compositional form that
preserves observable behavior and its performance envelope. Prefer declarative
data flow, total domain models, immutable boundaries, and explicit effects;
do not treat point-free syntax or recursion as goals.

## Core Laws

- Preserve public API, ordering, error semantics, evaluation timing, resource
  ownership, cancellation, logging, and mutation observed by callers.
- Separate pure transformations from I/O, mutation, and exception boundaries.
  Do not conceal required effects in a pipeline.
- Prefer named functions over clever anonymous composition when names explain
  an invariant or preserve debuggability.
- Make invalid state unrepresentable only when the language can enforce it
  without disproportionate runtime machinery.
- Make performance claims only from a relevant language profile, an existing
  benchmark, profiler evidence, or an explicitly stated assumption.

## Progressive Constraint Dispatch

1. Determine the language from the requested target, file extension, and
   project configuration. An explicit target wins.
2. For a single-language refactor, read **only** its linked runtime profile.
   For a boundary between languages, read each involved profile separately.
3. If the target is not listed, inspect local compiler/runtime guidance and
   existing hot-path conventions. Do not import a constraint from a different
   language by analogy.

| Target | Load only this profile |
| --- | --- |
| Python | [Python](./references/python.md) |
| JavaScript (ES6+) | [JavaScript](./references/javascript.md) |
| TypeScript | [TypeScript](./references/typescript.md) |
| Rust | [Rust](./references/rust.md) |
| Go | [Go](./references/go.md) |
| Haskell | [Haskell](./references/haskell.md) |
| C# | [C#](./references/csharp.md) |

## Refactoring Procedure

1. **Establish the contract.** Read the requested code, adjacent types, direct
   callers, and focused tests. Record inputs, outputs, state transitions,
   effects, error paths, ordering, and performance sensitivity. If neither a
   language nor a source file/code block is available, request one.
2. **Model the source.** Identify the accumulator, loop invariant, mutation
   boundary, and terminal result. Distinguish a collection transformation from
   a state machine, a resource lifetime, and an effectful workflow.
3. **Load one profile.** Apply only the matching profile's constraints before
   choosing a representation. Treat its cost signals as guards, not blanket
   bans on functional techniques.
4. **Construct a semantic candidate.** Prefer a pure helper plus native
   `map`/`filter`/`fold`, iterator, pattern-match, algebraic data type, or
   immutable value when it makes the invariant clearer and preserves cost.
5. **Run the cost guard.** Evaluate stack growth, allocation/escape behavior,
   JIT or compiler optimization barriers, deferred-vs-eager timing, and
   repeated traversal. If a guard fails, descend exactly one abstraction level:
   recursive composition → iteration; wrapper pipeline → native iterator;
   intermediate collections → fused pass; higher-order hot path → explicit
   loop with pure helper functions.
6. **Reject cosmetic conversions.** Keep a direct loop when it is clearer,
   owns a resource, requires early exit, or is the proven efficient shape. A
   loop can remain functionally disciplined: local state, one purpose, pure
   helper functions, and no externally visible partial mutation.
7. **Implement narrowly.** Preserve established public types and project
   idioms. Do not add FP frameworks, custom monad hierarchies, or pipeline
   wrappers unless the repository already relies on them and they solve a
   demonstrated problem.
8. **Validate.** Run the repository's narrowest relevant formatter, typecheck,
   linter, and focused tests. For a hot path, use an existing benchmark or
   profiler when available; otherwise identify the unmeasured cost risk rather
   than claiming an improvement.

## Decision Rules

| Source shape | Preferred result | Cost-aware fallback |
| --- | --- | --- |
| Recursive traversal | Native lazy iterator or iterator adapter | Iterative loop with pure step |
| Filter then transform | Native fused or idiomatic pipeline | One-pass loop/reducer |
| Flag-driven state | Closed sum type plus exhaustive matching | Explicit transition function |
| Mutable configuration | Immutable value construction | Native functional-options/configuration pattern |
| Nested wrapper objects | Flat value/object layout | Native collection APIs or direct loop |

## Validation Checklist

- The transformed code preserves the established contract and effect order.
- The selected profile was the only profile disclosed for that language.
- Recursion, allocation, and optimization risks have an explicit resolution.
- The result is more legible or more maintainable than the source; otherwise
  retain the original structure.
- Relevant automated checks pass, or any unavailable check and remaining
  performance uncertainty are stated precisely.

## Gotchas

- Lazy and eager pipelines have different error timing, memory retention, and
  side-effect order. Preserve the original contract deliberately.
- A chain of native collection calls can still allocate intermediate results;
  do not equate FP syntax with a single pass.
- Immutability does not make nested reference values immutable. Protect the
  required boundary, not merely the outer container.
- Exhaustive type-level models still require runtime validation for untrusted
  input.
- Do not replace exceptions, sentinels, or error values unless every caller's
  contract and the target language's conventions permit it.

## Report

After completing the refactor, state the language profile used, the invariant
made explicit, the cost guard outcome, and validation performed. State any
unmeasured performance risk without speculation.
