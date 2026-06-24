# Security and Privacy Playbook

Use this when a change touches authentication, authorization, personal data, secrets, encryption, logging, telemetry, LLM context, external providers, file uploads, web fetches, or background jobs.

## Required Questions

- What data is collected, processed, stored, logged, sent to an external provider, or deleted?
- Is each field necessary for the user-visible behavior?
- What is the retention rule?
- Who can read or mutate it?
- Is it encrypted in transit and at rest where appropriate?
- Could untrusted content influence tools, memory, storage, or user-visible decisions?
- Does the change need a threat-model update?
- What negative tests prove the control works?

## Agent and LLM Controls

- Treat prompts, OCR, fetched pages, nutrition labels, user input, and tool output as untrusted data.
- Do not put secrets, broad user history, or unnecessary profile fields into model context.
- Validate structured model output before persistence.
- Keep tool calls allowlisted and parameter-validated.
- Keep web search queries sanitized and free of personal context.
- Reject or quarantine memory writes that come from untrusted external content.

## PR Requirement

Every security/privacy-impacting PR must include:

- data touched,
- controls added or preserved,
- tests run,
- residual risk,
- retention/logging impact.

