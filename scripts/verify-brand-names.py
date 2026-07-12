#!/usr/bin/env python3
"""Guard tracked first-party docs and source files against stale brand prose."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

CURRENT_DOC_FILES = (
    "README.md",
    "CHANGELOG.md",
    "AGENTS.md",
    "backend/README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
)
DOCS_ROOT = "docs"
SCANNED_PREFIXES = ("backend/", "docs/", "mobile/", "scripts/", "searxng/")
SCANNED_ROOT_FILES = (
    ".env.example",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "Makefile",
    "README.md",
    "SECURITY.md",
    "docker-compose.yml",
)
SCANNED_EXTENSIONS = {".json", ".md", ".py", ".sh", ".ts", ".tsx", ".yaml", ".yml"}
EXCLUDED_PREFIXES = ("docs/verification/",)
EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
    "__pycache__",
}
EXCLUDED_LOCKFILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "yarn.lock",
}
CHANGELOG_HISTORY_MARKER = (
    "<!-- brand-guard: historical old-brand cutover release notes below; "
    "add new current entries above this marker. -->"
)

OLD_BRAND = "fat" + "ty"
BRAND_WORD = re.compile(rf"\b{re.escape(OLD_BRAND)}(?=\b|_)", re.IGNORECASE)
OLD_REPO_REFERENCE = re.compile(
    rf"github\.com/epurn/{re.escape(OLD_BRAND)}(?:\.git)?",
    re.IGNORECASE,
)
CHECKOUT_CD = re.compile(rf"(?<![\w.-])cd\s+{re.escape(OLD_BRAND)}(?:\s|$)", re.IGNORECASE)


@dataclass(frozen=True)
class LiteralException:
    pattern: re.Pattern[str]
    reason: str


@dataclass(frozen=True)
class Finding:
    path: str
    line_number: int
    reason: str
    line: str


# These are the intentionally narrow literals that remain valid public text.
LITERAL_EXCEPTIONS = (
    LiteralException(
        re.compile(r"\bfatty acids?\b", re.IGNORECASE),
        "ordinary English nutrition term, not the product brand",
    ),
    LiteralException(
        re.compile(r"\bfatty-reviewer\b"),
        "external GitHub App slug; rename is an operator action",
    ),
)


def exception_spans(line: str, next_line: str = "") -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for exception in LITERAL_EXCEPTIONS:
        spans.extend((match.start(), match.end()) for match in exception.pattern.finditer(line))
    wrapped_acid_match = re.search(rf"\b{re.escape(OLD_BRAND)}\s*$", line, re.IGNORECASE)
    if wrapped_acid_match and re.match(r"\s*(?:#:\s*)?acids?\b", next_line, re.IGNORECASE):
        spans.append((wrapped_acid_match.start(), wrapped_acid_match.end()))
    return spans


def span_allowed(start: int, end: int, spans: Iterable[tuple[int, int]]) -> bool:
    return any(allowed_start <= start and end <= allowed_end for allowed_start, allowed_end in spans)


def git_files(root: Path) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    return [line for line in result.stdout.splitlines() if line]


def walk_files(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    )


def repository_files(root: Path) -> list[str]:
    files = git_files(root)
    if files is not None:
        return sorted(files)
    return walk_files(root)


def excluded(path: str) -> bool:
    if path.startswith(EXCLUDED_PREFIXES):
        return True
    parts = set(Path(path).parts)
    if parts & EXCLUDED_PARTS:
        return True
    name = Path(path).name
    if name in EXCLUDED_LOCKFILES or name.endswith(".lock"):
        return True
    if name.startswith(".env") and name != ".env.example":
        return True
    return False


def is_scanned_file(path: str) -> bool:
    if excluded(path):
        return False
    file_name = Path(path).name
    if file_name == "Dockerfile":
        return True
    if path in CURRENT_DOC_FILES or path in SCANNED_ROOT_FILES:
        return True
    if Path(path).suffix not in SCANNED_EXTENSIONS:
        return False
    return path.startswith(SCANNED_PREFIXES)


def scanned_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for rel in repository_files(root):
        if not is_scanned_file(rel):
            continue
        path = root / rel
        if path.is_file():
            paths.append(path)
    return paths


def scanned_lines(rel: str, text: str) -> Iterable[tuple[int, str]]:
    for line_number, line in enumerate(text.splitlines(), start=1):
        if rel == "CHANGELOG.md" and line_number > changelog_scan_cutoff(text):
            continue
        yield line_number, line


def changelog_scan_cutoff(text: str) -> int:
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line == CHANGELOG_HISTORY_MARKER:
            return line_number
    return len(text.splitlines())


def validate(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in scanned_paths(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        lines = list(scanned_lines(rel, text))
        for index, (line_number, line) in enumerate(lines):
            next_line = lines[index + 1][1] if index + 1 < len(lines) else ""
            specific_failure_spans: list[tuple[int, int]] = []
            for match in OLD_REPO_REFERENCE.finditer(line):
                specific_failure_spans.append((match.start(), match.end()))
                findings.append(
                    Finding(
                        rel,
                        line_number,
                        "old public repo reference; use github.com/epurn/slacks",
                        line,
                    )
                )
            for match in CHECKOUT_CD.finditer(line):
                specific_failure_spans.append((match.start(), match.end()))
                findings.append(
                    Finding(rel, line_number, "old checkout directory; use cd slacks", line)
                )

            allowed_spans = exception_spans(line, next_line) + specific_failure_spans
            for match in BRAND_WORD.finditer(line):
                if span_allowed(match.start(), match.end(), allowed_spans):
                    continue
                findings.append(
                    Finding(
                        rel,
                        line_number,
                        "stale product brand prose; rename to Slacks or add a justified literal exception",
                        line,
                    )
                )

    return findings


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="slacks-brand-guard-") as tmp:
        root = Path(tmp)
        old_upper = OLD_BRAND.upper()
        old_title = OLD_BRAND.title()
        reviewer_slug = f"{OLD_BRAND}-reviewer"

        write(root / "README.md", "# Slacks\n\nSlacks is ready.\n")
        write(
            root / "CHANGELOG.md",
            "# Changelog\n\n"
            f"{CHANGELOG_HISTORY_MARKER}\n\n"
            f"- Historical migration mentioned `{old_upper}_AUTH_SECRET`.\n",
        )
        write(
            root / "docs/contracts/target-calculator.md",
            "Essential fatty acids remain ordinary prose.\n",
        )
        write(root / "docs/review-policy.md", f"The `{reviewer_slug}` app approves.\n")
        write(root / "docs/verification/FTY-000/README.md", f"{old_title} evidence.\n")
        if validate(root):
            raise AssertionError("allowed literal fixture should pass")

        write(root / "README.md", f"{old_upper}_TEST=1\n")
        findings = validate(root)
        if not any("README.md:1" in f"{item.path}:{item.line_number}" for item in findings):
            raise AssertionError("old environment-prefix fixture should fail")

        write(root / "README.md", "# Slacks\n\nSlacks is ready.\n")
        write(root / "backend/app/open_food_facts.py", f'USER_AGENT = "{old_title}/1.0"\n')
        findings = validate(root)
        if not any(
            "backend/app/open_food_facts.py:1" in f"{item.path}:{item.line_number}"
            for item in findings
        ):
            raise AssertionError("old source user-agent fixture should fail")

        (root / "backend/app/open_food_facts.py").unlink()
        write(root / "mobile/App.ts", f"// brand-{old_title} comment\nexport const ok = true;\n")
        findings = validate(root)
        if not any("mobile/App.ts:1" in f"{item.path}:{item.line_number}" for item in findings):
            raise AssertionError("old source comment fixture should fail")

        (root / "mobile/App.ts").unlink()
        write(
            root / "README.md",
            f"git clone https://github.com/epurn/{OLD_BRAND}.git\ncd {OLD_BRAND}\n",
        )
        findings = validate(root)
        if not any("old public repo reference" in item.reason for item in findings):
            raise AssertionError("old repository fixture should fail")
        if not any("old checkout directory" in item.reason for item in findings):
            raise AssertionError("old checkout directory fixture should fail")

    print("brand name guard self-tests passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return

    findings = validate(args.root.resolve())
    if findings:
        print("brand name check failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding.path}:{finding.line_number}: {finding.reason}", file=sys.stderr)
        raise SystemExit(1)

    print("brand name checks passed")


if __name__ == "__main__":
    main()
