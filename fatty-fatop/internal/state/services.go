package state

import (
	"os/exec"
	"strings"
)

// Service describes one always-on agent process.
type Service struct {
	Name   string
	Up     bool
	Detail string // pid list or status hint
}

var serviceProcPatterns = map[string]string{
	"steward":  "steward_agent/runner.py",
	"reviewer": "reviewer_agent/runner.py",
	"author":   "author_agent/runner.py",
}

// LoadServices reports whether each agent process is currently running by
// matching the runner command line via pgrep. The author is one-shot, so it is
// frequently (and correctly) down.
func LoadServices() []Service {
	order := []string{"steward", "reviewer", "author"}
	out := make([]Service, 0, len(order))
	for _, name := range order {
		pattern := serviceProcPatterns[name]
		pids := pgrep(pattern)
		svc := Service{Name: name, Up: len(pids) > 0}
		if svc.Up {
			svc.Detail = "pid " + strings.Join(pids, ",")
		} else {
			svc.Detail = "not running"
		}
		out = append(out, svc)
	}
	return out
}

func pgrep(pattern string) []string {
	cmd := exec.Command("pgrep", "-f", pattern)
	data, err := cmd.Output()
	if err != nil {
		return nil
	}
	var pids []string
	for _, line := range strings.Split(strings.TrimSpace(string(data)), "\n") {
		line = strings.TrimSpace(line)
		if line != "" {
			pids = append(pids, line)
		}
	}
	return pids
}
