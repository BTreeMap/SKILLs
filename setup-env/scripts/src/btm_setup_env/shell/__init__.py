"""The imperative shell: every effect a provision performs.

Idempotence is the governing law. Each executor checks its own
postcondition and skips completed work, so re-running provision is the
repair action rather than a reinstall. Only the *activation* environment is
fully hermetic: provisioning subprocesses still inherit the caller's HOME,
TMPDIR, and TLS roots.

The modules run one direction, no cycles: transfer and process perform the
raw effects, root holds what the environment records about itself, supply
ensures the two toolchain suppliers, execute runs one step, and commands
composes them into what a verb does.
"""
