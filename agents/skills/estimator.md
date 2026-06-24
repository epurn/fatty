# Estimator Skill

Use for food, exercise, nutrition sources, LLM provider adapters, OCR, search, and estimation jobs.

## Principles

- The LLM is an untrusted analyst, not an authority.
- The backend owns orchestration, validation, deterministic math, storage, and memory mutation.
- Prefer evidence in this order:
  1. user-provided nutrition label or barcode/package data,
  2. official restaurant or manufacturer source,
  3. trusted nutrition database,
  4. ingredient-based recipe calculation,
  5. similar-dish reference estimate.
- Use one displayed calorie number, with source/status icons and editable assumptions.
- Ask follow-ups only when missing information materially changes the result.

## Security

- Sanitize search queries.
- Harden URL fetching against SSRF.
- Treat web/OCR/model output as untrusted.
- Validate all structured outputs.
- Store source evidence and assumptions without storing unnecessary raw content.

