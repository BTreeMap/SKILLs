"""Build the evidence-first fact-check report from `factcheck-state.json`.

The agent writes the state file; this member decodes it, refuses a report
the verdict rules forbid, and returns the report as one JSON document.
"""
