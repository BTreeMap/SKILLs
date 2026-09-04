"""btm-setup-env: a typed, userspace, per-project dev-environment provisioner.

Layered one-directional: `model` (pure domain), `steps` (the plan-step ADT),
`catalog` (recipes), `plan` (Spec x Host -> Plan), `render` (EnvDelta ->
activate scripts), `effects` (the imperative shell), `cli` (arguments and
reporting). Everything above `effects` is pure and unit-testable without a
network.
"""
