"""Repository convention gate for the SKILLs library.

Every convention in AGENTS.md that a program can decide lives here as one
rule: a pure function from an immutable snapshot of the repository to
findings. A finding that carries a repair is mechanical and gets applied to a
fixpoint; a finding without one needs a person, and is the only thing that
fails a run.

`conventions` fixes the constants, `repairs` the closed repair set, `snapshot`
the reading of the tree, `listings` the generated tables, `rules` the rule set,
and `cli` the shell.
"""
