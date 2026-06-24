# Feature Development Playbook

Use this when implementing product or platform behavior.

## Loop

1. Identify the story, bug, or contract that defines the change.
2. Read the smallest relevant area of the codebase and the nearest guidance file.
3. Check whether the change touches security, privacy, storage, auth, LLM behavior, jobs, or external providers.
4. Update or create the contract before implementation when boundaries change.
5. Implement the smallest vertical slice that satisfies acceptance criteria.
6. Add focused tests for success, failure, and important edge cases.
7. Update docs only where behavior or operations changed.
8. Run `make verify` and any package-specific checks.
9. Prepare PR notes with assumptions, verification, and security/privacy impact.

## Defaults

- Prefer explicit data models and typed schemas.
- Keep side effects behind services or adapters.
- Make background jobs idempotent and retry-safe.
- Make LLM calls structured and validated.
- Keep UI flows mobile-first and accessible.

