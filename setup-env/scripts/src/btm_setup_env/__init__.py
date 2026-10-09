"""btm-setup-env: a typed, userspace, per-project dev-environment installer.

Layered one-directional: `model` (pure domain), `steps` (the plan-step ADT),
`catalog` (recipes), `plan` (Spec x Host -> Plan), `render` (EnvDelta ->
activate scripts), `shell` (the imperative shell), `cli` (arguments and
reporting). Everything but `shell` is pure and unit-testable without a
network.
"""
