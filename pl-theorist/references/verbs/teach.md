# Verb: teach

Explain a design or refactor in PL terms calibrated to the audience: a human
learning FP taste, or a less capable model about to edit code.

## Pipeline

### 1. Read the artifact

Ground every claim in the actual code (or design) under discussion. Never
teach from a hypothetical version of the code.

### 2. Name the design

Explain by naming, in this order:

- The algebra at work: `map`, catamorphism/fold, sum type, applicative, monad,
  state transition, or effect interpretation.
- The invariant established or the invalid state eliminated.
- Why the result is total, or exactly where partiality remains and why.
- The complexity story: the bound, the structure that buys it, and what the
  naive shape would have cost.
- The loaded language constraint and the fallback it forced, if any.
- One tempting "more functional" form rejected on semantic or cost grounds.

Define specialized terminology on first use. Prefer one precise law or
contrast over broad theory; jargon never substitutes for tracing behavior
through the actual code.

### 3. Calibrate

For a human: connect the named concept to the concrete lines, then to the one
reusable distinction to keep for the next problem. One distinction
per session sticks; five wash out.

For a less capable model: load the target profile's teaching example to
calibrate taste, never as a template. Explain exactly three things: the invalid state
removed, the native algebra chosen, and the performance or production
constraint preventing a more abstract form. Then require the model to identify
those three properties in the actual code before it edits anything.

## Output Contract

A short teaching note: the named algebra, the invariant, the complexity story,
the rejected alternative, and one reusable distinction. Length proportional to
the artifact; no essays. Code snippets only from the real artifact.

## Completion Checks

<checklist for="verb">
  <item>Every named concept is anchored to specific lines of the real artifact.</item>
  <item>Terminology is defined on first use.</item>
  <item>Exactly one reusable distinction is called out for the learner to keep.</item>
  <item>A rejected more-abstract form is shown with its killing constraint.</item>
  <item>A model audience was made to restate the three properties before editing.</item>
</checklist>
