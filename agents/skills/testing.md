# Testing Skill

Use when adding or changing tests.

## Strategy

- Test behavior, not implementation trivia.
- Put fast deterministic tests closest to the code.
- Use integration tests for API, database, job, and provider boundaries.
- Add adversarial tests for LLM/tool behavior.
- Add regression tests for every bug fix.
- Keep fixtures synthetic; never use real user data.

## Minimum Expectations

- New calculators need exact examples and invalid-input tests.
- New contracts need serialization and validation tests.
- New auth/data access behavior needs positive and negative authorization tests.
- New UI flows need state coverage for loading, success, failure, and empty states.

