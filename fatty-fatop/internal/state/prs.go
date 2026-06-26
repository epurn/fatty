package state

import (
	"encoding/json"
	"os/exec"
	"strings"
	"time"
)

// PR is the open pull-request state fatop cares about.
type PR struct {
	Number    int
	Title     string
	HeadRef   string
	Draft     bool
	Review    string // APPROVED | CHANGES_REQUESTED | REVIEW_REQUIRED | ""
	Checks    string // SUCCESS | FAILURE | PENDING | ""
	Reviewer  string // the reviewer-approved commit status, if found
}

type ghPR struct {
	Number         int    `json:"number"`
	Title          string `json:"title"`
	HeadRefName    string `json:"headRefName"`
	IsDraft        bool   `json:"isDraft"`
	ReviewDecision string `json:"reviewDecision"`
	StatusCheckRollup []struct {
		State      string `json:"state"`      // commit status contexts
		Conclusion string `json:"conclusion"` // check runs
		Context    string `json:"context"`
		Name       string `json:"name"`
	} `json:"statusCheckRollup"`
}

// LoadPRs shells out to gh for open PRs. It returns (nil, err) when gh is
// missing or unauthenticated so callers can show a hint rather than crash.
func LoadPRs(repo string) ([]PR, error) {
	cmd := exec.Command("gh", "pr", "list",
		"--repo", repo,
		"--state", "open",
		"--json", "number,title,headRefName,isDraft,reviewDecision,statusCheckRollup",
	)
	// gh can hang on a stuck network; cap it.
	done := make(chan struct{})
	var data []byte
	var err error
	go func() {
		data, err = cmd.Output()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(8 * time.Second):
		_ = cmd.Process.Kill()
		<-done
	}
	if err != nil {
		return nil, err
	}

	var raw []ghPR
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, err
	}
	out := make([]PR, 0, len(raw))
	for _, r := range raw {
		pr := PR{
			Number:  r.Number,
			Title:   r.Title,
			HeadRef: r.HeadRefName,
			Draft:   r.IsDraft,
			Review:  r.ReviewDecision,
			Checks:  rollup(r),
		}
		for _, c := range r.StatusCheckRollup {
			if c.Context == "reviewer-approved" {
				pr.Reviewer = strings.ToUpper(c.State)
			}
		}
		out = append(out, pr)
	}
	return out, nil
}

// rollup collapses the per-check states into one word.
func rollup(r ghPR) string {
	if len(r.StatusCheckRollup) == 0 {
		return ""
	}
	anyPending, anyFail := false, false
	for _, c := range r.StatusCheckRollup {
		s := strings.ToUpper(c.State)
		concl := strings.ToUpper(c.Conclusion)
		switch {
		case s == "FAILURE" || s == "ERROR" || concl == "FAILURE" || concl == "TIMED_OUT" || concl == "CANCELLED":
			anyFail = true
		case s == "PENDING" || s == "" && concl == "":
			anyPending = true
		case concl == "" && s == "":
			anyPending = true
		}
	}
	switch {
	case anyFail:
		return "FAILURE"
	case anyPending:
		return "PENDING"
	default:
		return "SUCCESS"
	}
}
