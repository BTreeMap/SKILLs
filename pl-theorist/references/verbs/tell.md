# Verb: tell

Explain design or refactor in PL terms calibrated to audience: human
learning FP taste, or less capable model about to edit code.

## Pipeline

### 1. Read the artifact

Ground every claim in actual code (or design) under discussion.

### 2. Name the design

Explain by naming, in this order:

- Algebra at work: `map`, catamorphism/fold, sum type, applicative, monad,
  state transition, or effect interpretation.
- Invariant established or invalid state eliminated.
- Why result is total, or exactly where partiality remains and why.
- Complexity story: bound, structure that buys it, what naive shape would
  have cost.
- Loaded language constraint and fallback it forced, if any.
- One tempting "more functional" form rejected on semantic or cost grounds.

Define specialized terminology on first use. Prefer one precise law or
contrast over broad theory; jargon never substitutes for tracing behavior
through actual code.

### 3. Calibrate

Human: connect named concept to concrete lines, then to one reusable
distinction to keep for next problem.

Less capable model: use loaded profile's Teaching Example to calibrate
taste, never as template. Explain exactly three things: invalid state
removed, native algebra chosen, performance or production constraint
preventing more abstract form. Then require model to identify those three
properties in actual code before it edits anything.

## Output Contract

Short teaching note: named algebra, invariant, complexity story, rejected
alternative, one reusable distinction. Length proportional to artifact. Code
snippets only from real artifact.

## Completion Checks

- Every named concept anchored to specific lines of real artifact.
- Terminology defined on first use.
- Exactly one reusable distinction called out for learner to keep.
- Rejected more-abstract form shown with its killing constraint.
- Model audience made to restate three properties before editing.
