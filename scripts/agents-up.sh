#!/usr/bin/env bash
# Command-centre orchestration: bring the Fatty agents up.
# Each agent owns its own launch-agent installer; this only coordinates them.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AUTHOR="$ROOT/fatty-author-agent"
REVIEWER="$ROOT/fatty-reviewer-agent"
STEWARD="$ROOT/fatty-steward-agent"

echo "== verifying agents =="
( cd "$AUTHOR"   && make doctor )
( cd "$REVIEWER" && make doctor )
( cd "$STEWARD"  && make doctor )

mkdir -p "$REVIEWER/logs" "$STEWARD/logs"
touch "$REVIEWER/logs/reviewer.out.log" "$REVIEWER/logs/reviewer.err.log" \
      "$STEWARD/logs/steward.out.log"   "$STEWARD/logs/steward.err.log"

echo "== installing launch agents (reviewer + steward) =="
( cd "$REVIEWER" && ./scripts/install-launch-agent.sh )   # reviewer runs with --enable-auto-merge
( cd "$STEWARD"  && ./scripts/install-launch-agent.sh )

echo "== active agent processes =="
pgrep -af 'reviewer_agent/runner.py|steward_agent/runner.py|author_agent/runner.py' 2>/dev/null || true

echo
echo "Agents are running as launchd services. Tailing logs; Ctrl-C stops the tail"
echo "only — the agents keep running. Stop them with: scripts/agents-down.sh"
echo
exec tail -n 0 -F \
  "$REVIEWER/logs/reviewer.out.log" "$REVIEWER/logs/reviewer.err.log" \
  "$STEWARD/logs/steward.out.log"   "$STEWARD/logs/steward.err.log"
