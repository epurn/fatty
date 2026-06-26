package tui

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"

	"github.com/epurn/fatty-fatop/internal/state"
	"github.com/epurn/fatty-fatop/internal/ui"
)

// formatEvent renders one event as a single line that fits within width.
func formatEvent(e state.Event, width int) string {
	if width < 20 {
		width = 20
	}
	ts := "--:--:--"
	if !e.Ts.IsZero() {
		ts = e.Ts.Local().Format("15:04:05")
	}
	icon := ui.EventIcon(e.EventT, e.Field("kind"))
	st := ui.LevelStyle(e.Level)

	prefix := ui.Muted.Render(ts) + " " + icon + " " + st.Render(pad(e.EventT, 14))
	if e.RunID != "" && e.RunID != "service" {
		prefix += " " + ui.Run.Render("["+e.RunID+"]")
	}
	prefixW := lipgloss.Width(prefix)

	msg := e.Msg
	if msg == "" {
		msg = e.Field("kind")
	}
	avail := width - prefixW - 1
	if avail < 1 {
		avail = 1
	}
	msg = strings.ReplaceAll(msg, "\n", " ")
	msg = truncate(msg, avail)
	return prefix + " " + msg
}

// fitRow places left and right-justified text within width.
func fitRow(left, right string, width int) string {
	if width < 4 {
		return left
	}
	lw := lipgloss.Width(left)
	rw := lipgloss.Width(right)
	gap := width - lw - rw
	if gap < 1 {
		// Drop the right side if there is no room.
		return truncateStyled(left, width)
	}
	return left + strings.Repeat(" ", gap) + right
}

// truncateStyled is a best-effort truncation that avoids cutting mid-escape by
// only trimming when the string has no styling; otherwise it returns as-is.
func truncateStyled(s string, width int) string {
	if lipgloss.Width(s) <= width {
		return s
	}
	return s
}

func reviewWord(pr state.PR) string {
	switch pr.Review {
	case "APPROVED":
		return ui.OK.Render("ok")
	case "CHANGES_REQUESTED":
		return ui.Err.Render("changes")
	case "REVIEW_REQUIRED":
		return ui.Warn.Render("review")
	default:
		if pr.Draft {
			return ui.Muted.Render("draft")
		}
		if pr.Checks == "FAILURE" {
			return ui.Err.Render("ci✗")
		}
		return ui.Muted.Render("-")
	}
}

func levelLabel(min int) string {
	names := []string{"  ≥debug", "  ≥info", "  ≥warn", "  ≥error"}
	if min < 0 || min >= len(names) {
		return ""
	}
	return names[min]
}

func levelRank(l string) int {
	switch l {
	case "debug":
		return 0
	case "info", "":
		return 1
	case "warn":
		return 2
	case "error":
		return 3
	}
	return 1
}

func pad(s string, n int) string {
	if len(s) >= n {
		return s
	}
	return s + strings.Repeat(" ", n-len(s))
}

func truncate(s string, n int) string {
	if n <= 0 {
		return ""
	}
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	if n == 1 {
		return string(r[:1])
	}
	return string(r[:n-1]) + "…"
}

func shortDur(d time.Duration) string {
	if d <= 0 {
		return "0s"
	}
	switch {
	case d < time.Minute:
		return fmt.Sprintf("%ds", int(d.Seconds()))
	case d < time.Hour:
		return fmt.Sprintf("%dm", int(d.Minutes()))
	default:
		return fmt.Sprintf("%dh%dm", int(d.Hours()), int(d.Minutes())%60)
	}
}
