package state

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParseEventLine(t *testing.T) {
	line := `{"ts":"2026-06-25T18:03:11.482Z","agent":"steward","run_id":"FTY-010","level":"info","event":"assign_story","msg":"ready","fields":{"lane":"contracts","files":7}}`
	ev, ok := ParseEventLine(line)
	if !ok {
		t.Fatal("expected ok")
	}
	if ev.Agent != "steward" || ev.EventT != "assign_story" || ev.RunID != "FTY-010" {
		t.Fatalf("bad parse: %+v", ev)
	}
	if ev.Ts.IsZero() {
		t.Fatal("timestamp not parsed")
	}
	if got := ev.Field("lane"); got != "contracts" {
		t.Fatalf("lane = %q", got)
	}
	if got := ev.Field("files"); got != "7" {
		t.Fatalf("files = %q want 7", got)
	}
}

func TestParseEventLineBad(t *testing.T) {
	for _, line := range []string{"", "   ", "not json", "[1,2,3]"} {
		if _, ok := ParseEventLine(line); ok {
			t.Fatalf("expected !ok for %q", line)
		}
	}
}

func TestReadAndMergeEvents(t *testing.T) {
	dir := t.TempDir()
	a := filepath.Join(dir, "a.jsonl")
	b := filepath.Join(dir, "b.jsonl")
	os.WriteFile(a, []byte(
		`{"ts":"2026-06-25T18:00:00.000Z","agent":"steward","event":"poll_cycle","msg":"x","fields":{}}`+"\n"+
			`garbage line`+"\n"+
			`{"ts":"2026-06-25T18:00:02.000Z","agent":"steward","event":"decision","msg":"y","fields":{}}`+"\n"), 0o644)
	os.WriteFile(b, []byte(
		`{"ts":"2026-06-25T18:00:01.000Z","agent":"reviewer","event":"review_start","msg":"z","fields":{}}`+"\n"), 0o644)

	got, err := ReadEvents(a, 0)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 2 {
		t.Fatalf("ReadEvents got %d, want 2 (garbage skipped)", len(got))
	}

	merged := MergeEvents([]string{a, b}, 0)
	if len(merged) != 3 {
		t.Fatalf("MergeEvents got %d, want 3", len(merged))
	}
	// Sorted ascending by ts: poll_cycle, review_start, decision
	wantOrder := []string{"poll_cycle", "review_start", "decision"}
	for i, w := range wantOrder {
		if merged[i].EventT != w {
			t.Fatalf("order[%d] = %q want %q", i, merged[i].EventT, w)
		}
	}
}

func TestReadEventsMissingFile(t *testing.T) {
	got, err := ReadEvents(filepath.Join(t.TempDir(), "nope.jsonl"), 0)
	if err != nil {
		t.Fatalf("missing file should not error: %v", err)
	}
	if len(got) != 0 {
		t.Fatal("expected empty")
	}
}
