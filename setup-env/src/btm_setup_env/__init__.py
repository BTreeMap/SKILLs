"""btm-setup-env: a typed, userspace, per-project dev-environment provisioner.

Layering, strictly one-directional:

    model    pure domain: hosts, platforms, tags, env deltas, emulation
    steps    the closed plan-step ADT
    catalog  the closed (family, flavor) -> recipe table
    plan     pure planner: Spec x Host -> Plan
    render   pure renderers: EnvDelta -> activate.sh / activate.ps1
    effects  the imperative shell: downloads, micromamba, step executors
    cli      argument parsing and reporting

Everything above `effects` is pure and unit-testable without a network.
"""
