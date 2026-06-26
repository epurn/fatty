# backend

The Fatty backend package (FastAPI, Python).

## Owns

- The FastAPI application, settings, and request/response boundary models.
- Service-layer domain behavior (deterministic calorie, macro, and target math).
- Database access, migrations, and background job entrypoints (added in later stories).
- Provider adapters for evidence retrieval and LLM estimation (added in later stories).

## Toolchain

- **uv** manages the Python environment and locks dependencies in `uv.lock`.
  This lockfile convention is shared by all later backend stories.
- **ruff** lints and formats; **mypy** (strict) typechecks; **pytest** runs tests.

```sh
uv sync --dev        # create the environment from uv.lock
uv run python -m app # run the app (uvicorn) on FATTY_HOST:FATTY_PORT
uv run pytest        # run the tests
```

## Layout

- `app/main.py` — `create_app()` application factory (validates settings,
  configures logging, wires routers).
- `app/settings.py` — typed Pydantic settings loaded from environment variables.
- `app/logging.py` — structured JSON logging with sensitive-field redaction.
- `app/routers/` — thin HTTP boundary; handlers delegate to `app/services/`.
- `app/services/` — domain behavior.
- `app/schemas/` — Pydantic request/response models.
- `tests/` — pytest harness.

## Contracts

- `GET /healthz` returns `200 {"status": "ok"}` (consumed by the FTY-011 Docker
  Compose healthcheck and later infra).
- Settings are read from `FATTY_`-prefixed environment variables:

  | Variable | Default | Notes |
  | --- | --- | --- |
  | `FATTY_APP_NAME` | `fatty-backend` | Application title. |
  | `FATTY_ENVIRONMENT` | `development` | One of `development`, `test`, `production`. |
  | `FATTY_LOG_LEVEL` | `INFO` | Standard Python log level. |
  | `FATTY_HOST` | `127.0.0.1` | Bind address; deployments override to expose. |
  | `FATTY_PORT` | `8000` | Bind port (1–65535). |

  Invalid or out-of-range values fail fast at startup with a `ValidationError`.

## Logging and privacy

Logs are single-line JSON. A redaction filter scrubs any field whose name looks
sensitive (tokens, secrets, keys, passwords, authorization, cookies). Never
attach raw prompts, provider keys, or personal nutrition data to log records;
prefer request/event IDs over personal values.

## Root verification

`backend/verify.sh` is the package hook run by root `make verify` (via
`scripts/package-verify.sh`). It runs `uv sync --frozen`, ruff lint + format
check, mypy, and pytest, and exits non-zero on the first failure. See
[`docs/architecture/repo-layout.md`](../docs/architecture/repo-layout.md).
