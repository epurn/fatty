// Command fatop is a live monitor for the Fatty agent system. It reads the
// structured event logs and run-state written by the steward, reviewer, and
// author agents and renders them as a TUI dashboard (or scriptable CLI output).
//
// fatop is private command-centre tooling. It only reads local automation
// state; nothing it touches belongs in the public fatty repo.
package main

import (
	"os"

	"github.com/epurn/fatty-fatop/internal/cli"
)

func main() {
	os.Exit(cli.Execute())
}
