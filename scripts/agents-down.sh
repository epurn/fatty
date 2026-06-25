#!/usr/bin/env bash
# Command-centre orchestration: bring the Fatty agents down.
set -euo pipefail
launchctl unload "$HOME/Library/LaunchAgents/com.epurn.fatty-reviewer-agent.plist" >/dev/null 2>&1 || true
launchctl unload "$HOME/Library/LaunchAgents/com.epurn.fatty-steward-agent.plist"  >/dev/null 2>&1 || true
pkill -f 'steward_agent/runner.py'  >/dev/null 2>&1 || true
pkill -f 'reviewer_agent/runner.py' >/dev/null 2>&1 || true
pkill -f 'author_agent/runner.py'   >/dev/null 2>&1 || true
echo "stopped Fatty reviewer, steward, and author processes"
