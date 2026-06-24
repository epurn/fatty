# Security Skill

Use for auth, secrets, encryption, logs, privacy, abuse, agent safety, dependency risk, and deployment hardening.

## Standards

- Follow data minimization by default.
- Use least privilege for users, services, agents, tools, and CI tokens.
- Store secrets only in secret managers or environment variables; never in source.
- Use modern password hashing if password auth is implemented.
- Encrypt sensitive data at rest where feasible and always protect data in transit.
- Build explicit retention and deletion behavior.
- Add negative tests for access control, prompt injection, SSRF, unsafe file upload, and sensitive logging.

## References

- `docs/security/security-baseline.md`
- `docs/security/threat-model.md`
- `docs/security/data-retention.md`

