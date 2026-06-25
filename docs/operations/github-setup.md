# GitHub Setup

This document records repository settings required for CI and reviewer
enforcement.

## Required Workflows

The first commit must include:

- `.github/workflows/governance.yml`
- `.github/workflows/reviewer-gate.yml`

Required status checks on `main`:

- `governance`
- `separate-reviewer`

## Branch Protection

Configure `main` with:

- require a pull request before merging,
- require conversation resolution,
- require status checks before merging,
- require branches to be up to date before merging,
- require the `governance` status check,
- require the `separate-reviewer` status check,
- keep native required approving review count at zero for the app-reviewer flow,
- block force pushes,
- block deletions,
- include administrators when practical.

Fatty enforces non-author review with the required `separate-reviewer`
workflow. The workflow checks for an approval from an eligible reviewer on the
current PR head SHA. The custom status check is the merge gate because GitHub's
native required-review rule may not count approvals submitted by the
`fatty-reviewer` app as eligible native approvals.

## GitHub CLI Setup

After the initial commit is pushed, this can be configured with the GitHub API:

```sh
gh api \
  --method PUT \
  repos/OWNER/REPO/branches/main/protection \
  --input docs/operations/main-branch-protection.json
```

GitHub may reject required status checks until each workflow has run at least once. If that happens, open a tiny PR, let both checks run, then apply the protection again.

## Manual Setup Path

When branch protection is available:

1. Open GitHub repository settings.
2. Go to Branches.
3. Add a branch protection rule for `main`.
4. Enable "Require a pull request before merging".
5. Set required native approving reviews to zero.
6. Leave stale approval dismissal disabled.
7. Leave latest-push native approval disabled.
8. Enable conversation resolution.
9. Enable required status checks.
10. Require branches to be up to date before merging.
11. Require `governance`.
12. Require `separate-reviewer`.
13. Block force pushes and deletions.
14. Apply to administrators if the plan allows it.
