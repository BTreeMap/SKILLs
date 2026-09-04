"""Repository convention gate for the SKILLs library.

Every convention in AGENTS.md that a program can decide lives here as one
rule: a pure function from a snapshot to findings. A finding with a repair
is mechanical and applied to a fixpoint; one without needs a person.

`conventions` fixes the constants, `repairs` the closed repair set, `snapshot`
reads the tree, `listings` holds the tables, `rules` the rule set, `cli` the shell.
"""
