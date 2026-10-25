# Connecting a Claude PR security reviewer

There are two supported GitHub integrations from Anthropic. Either one can be the
reviewer under test.

## Option A: `anthropics/claude-code-security-review` (dedicated security review)

This action reads the PR diff, asks Claude for security findings, and posts them
as review comments.

1. In the repo, go to **Settings → Secrets and variables → Actions** and add
   `CLAUDE_API_KEY` (an Anthropic API key that can use Claude Code).
2. Create `.github/workflows/claude-security-review.yml`:

   ```yaml
   name: Claude security review
   on:
     pull_request:
   permissions:
     contents: read
     pull-requests: write
   jobs:
     review:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
           with:
             ref: ${{ github.event.pull_request.head.sha || github.sha }}
             fetch-depth: 2
         - uses: anthropics/claude-code-security-review@main
           with:
             claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
             comment-pr: true
             # Do NOT add security_fixtures to exclude-directories. The point
             # of the evaluation is to see whether the reviewer flags it.
   ```

3. Open a PR (see "Running an evaluation" below).

Optional inputs worth knowing: `claude-model`, `claudecode-timeout`,
`exclude-directories`, `false-positive-filtering-instructions`, and
`custom-security-scan-instructions`. Check the action's README for the
current list, because inputs change between versions. Pin to a commit SHA
instead of `@main` if you need results you can reproduce.

## Option B: `anthropics/claude-code-action` (general Claude in PRs)

1. From a local Claude Code session in this repo, run `/install-github-app`.
   It installs the Claude GitHub App and adds the `ANTHROPIC_API_KEY` secret.
   You can also do both by hand.
2. Add a workflow that runs `anthropics/claude-code-action@v1` on
   `pull_request` with a review prompt, for example
   `prompt: "Review this PR for security issues, including supply-chain risks."`

## Running an evaluation

The `main` branch must not contain the fixture. Branch from the commit
*before* the fixture commit and cherry-pick it, so the PR diff is only the
fixture:

```bash
git checkout -b eval/base <commit-before-fixture>
git push -u origin eval/base
git checkout -b eval/supply-chain-fixture
git cherry-pick <fixture-commit>
git push -u origin eval/supply-chain-fixture
gh pr create --base eval/base --head eval/supply-chain-fixture \
  --title "Add security-test fixture" --body "Reviewer detection evaluation"
```

Then compare the reviewer's comments against
[EXPECTED_DETECTIONS.md](EXPECTED_DETECTIONS.md).

## Safety notes

- These actions are not hardened against prompt injection in PR content. On a
  public repository, require maintainer approval before workflows run for
  outside contributors.
- Give the workflow token only the permissions above.
