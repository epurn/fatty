# fatop (Fatty agent monitor)

Read-only observability tooling for the command centre. A single Go binary that
renders agent state — services, runs in flight, PRs — as a live TUI, and exposes
scriptable `status` / `logs` / `inspect` / `doctor` subcommands.

## Rules

- **Read-only.** fatop never starts, stops, reloads, or mutates agents or PRs.
  Operating the services stays in the `agents-control` skill.
- **Private boundary.** fatop only reads local automation state. Nothing here —
  source, telemetry, or machine paths — belongs in the public `fatty` repo.
- **Telemetry is additive.** fatop consumes the JSONL event logs described in
  `../docs/agent-event-log.md`. It must tolerate missing files and malformed
  lines without crashing.

## Structure

- `internal/state` is the only place that touches the filesystem / `gh`. Keep it
  pure and unit-tested (`make test`); the CLI and TUI render its output.
- `internal/cli` and `internal/tui` share the palette in `internal/ui`.
- Add a new event type? Update `../docs/agent-event-log.md` first, then the
  producing agent, then any rendering here.

## Build & test

```sh
make build    # go mod tidy + go build
make test     # go test ./...
make vet
```
