# Em Dash Remover

[![Tests](https://github.com/nightangelflowerwin-ops/em-dash-remover/actions/workflows/tests.yml/badge.svg)](https://github.com/nightangelflowerwin-ops/em-dash-remover/actions/workflows/tests.yml)

Remove em dashes from your repository through a reviewable pull request, or prevent new ones with a CI check. Python standard library only. MIT licensed. No account-wide token is needed.

## Add it to an existing repository

1. Copy [examples/cleanup.yml](examples/cleanup.yml) into your repository as `.github/workflows/em-dash-cleanup.yml`.
2. In **Settings > Actions > General**, allow GitHub Actions to create pull requests if your repository permits it. The workflow requests only repository contents and pull-request write permissions. It never approves or merges a PR.
3. Open **Actions > Remove em dashes > Run workflow**. It also runs on default-branch pushes and weekly. Review and merge the proposed changes.

For check-only CI, copy [examples/check.yml](examples/check.yml) instead. It needs only read access and fails when matching text is found.

GitHub forks create a separate repository. To own the tool, fork this repository and change the workflow's `uses:` reference to your fork. To use it inside a repository you already have, copy the small workflow above. You do not need to fork anything. For reproducibility, pin the action to a tested full commit SHA instead of the movable `v1` tag.

## Use the action directly

Checkout the target repository and set up Python 3.11 or newer first:

```yaml
- uses: nightangelflowerwin-ops/em-dash-remover@v1
  with:
    mode: fix
    encoded: 'true'
    create-pr: 'true'
    token: ${{ github.token }}
```

Inputs: `mode` (`check`, `fix`, `report`), `root`, `all-text`, `encoded`, `exclude` (newline-separated globs), `max-bytes`, `report`, `create-pr`, `token`. Outputs: `changed-files`, `replacements`, `pr-url`.

`check` changes nothing and returns exit code 1 for matches. `report` changes nothing and succeeds with matches. `fix` writes replacements and succeeds unless an error occurs. Errors return exit code 2. Reports and job summaries show scan counts, skips and errors. A cleanup run with no matches opens no PR. While a cleanup PR is open, later runs return its URL rather than creating duplicates; they do not update that PR. Merge or close it before another cleanup proposal.

PR creation starts from a clean default-branch checkout, creates a new branch, commits only the changed files and pushes without force. It does not rewrite history. If a repository disallows automated PR creation, the cleanup branch remains available for a manual PR. Check branch protection and Actions policies in your organization. Automation-created PR checks may require approval under [GitHub's token rules](https://docs.github.com/en/actions/concepts/security/github_token).

## Run locally

Copy `emdash.py` into your repository or run it from a clone of this tool. Git and Python 3.11+ are required; no package installation is needed.

```sh
python emdash.py --root /path/to/your/repo
python emdash.py --root /path/to/your/repo --mode fix
python emdash.py --root /path/to/your/repo --mode fix --encoded --report report.json
python emdash.py --root /path/to/your/repo --mode report --all-text --exclude 'vendor/*'
```

The default checks Markdown, reStructuredText, text, HTML and SVG files and changes nothing. Replacement is a plain hyphen. Add `--encoded` for escaped Unicode, HTML entities, URL encodings, supported TeX macros and a common misencoded form. `--replacement` accepts a literal replacement string.

Add `--all-text` to include source and data files; review those diffs because punctuation can be meaningful to code, test fixtures, datasets and normalization rules. The tool does not understand those semantics. Valid JSON/notebooks are checked again before writing. It does not execute repository code. Default size limit: 2 MiB; `--max-bytes` can raise it to 100 MiB.

UTF-8 and BOM-marked UTF-16 are supported; BOMs, line endings and file permissions are preserved. Binary assets, unsupported encodings, untracked files, submodules, symlinks and oversized files are skipped. It does not edit repository descriptions, issues, release text, image/PDF contents or historical commits. No credentials or network calls are used by the local scanner. The optional PR helper contacts GitHub and pushes only to the current repository.

The tool is not a grammar editor: adjacent words separated by an em dash become words separated by a hyphen. Review the result for readability. `fix` writes each file atomically, but a multi-file run is not one filesystem transaction. A file changed concurrently is rejected.

## Develop and contribute

Run `python -m unittest -v`. CI exercises the scanner, actual composite Action inputs/outputs and file fixes on Windows and Linux. PR-helper tests use real Git commits and a local bare remote with a mocked GitHub API; that test is not evidence of GitHub accepting a real automation PR in every repository. Repository permissions remain an installation requirement.

Bug reports and contributions are welcome through issues and pull requests. Include a minimal input, expected output, operating system and mode. Use generated character codes in tests instead of putting unwanted punctuation into the repository. See [LICENSE](LICENSE).
