# Contract-First Change Playbook

Use this when changing boundaries between systems.

Contract-first applies to:

- HTTP APIs,
- database schema and migrations,
- background job payloads,
- estimator tool inputs and outputs,
- LLM structured output schemas,
- mobile/backend DTOs,
- external provider adapters,
- event names and status state machines.

## Steps

1. Define the contract in `docs/contracts/` or the package-local contract file.
2. Include examples for success, validation failure, and authorization failure where relevant.
3. Name versioning or migration behavior.
4. Implement validation at the boundary.
5. Add tests that prove incompatible data fails closed.
6. Update callers and documentation in the same PR.

## Defaults

- Contracts should be explicit, typed, and stable.
- Prefer additive changes over breaking changes.
- Store units canonically: kcal, grams, milliliters, seconds, meters, kilograms.
- Keep user-visible display units separate from stored units.

