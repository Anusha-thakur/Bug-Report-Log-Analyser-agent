# Bug Report and Log Analyser Agent

A Claude Code agent for QA teams. It turns rough defect notes, logs and attachments into ticket-ready bug reports, flags duplicate and related bugs, and writes daily QA summaries. Reports are saved as Word (.docx) documents.

It does **not** reproduce bugs, change code or close tickets. A person reviews every report before it is filed.

| Use case | Input | Output |
|---|---|---|
| uc1 – Bug report | Tester notes, logs, stack traces, attachments (screenshots, JSON, PDF, Word, ZIP) | One structured bug report with severity, priority and a critical flag |
| uc2 – Duplicates and patterns | Several bug reports | Duplicate groups, related issues and unrelated items |
| uc3 – Daily QA summary | A day's defect notes | Counts by severity, open items and follow-ups |

## Folder structure

```
.claude/
  agents/bug-report-analyser.md   Subagent: role, report template, severity rules, guardrails
  skills/                         Seven skills (below), with their Python scripts
samples/                          Test inputs
  attachments/<scenario>/         Scenarios with screenshots, JSON, PDF and Word files
expected/                         Answer key: one ideal report per sample (same name, .md)
tests/smoke_set.txt               Quick regression set (8 samples)
CLAUDE.md                         Project instructions for Claude Code
system_prompt.md                  Original system prompt
CHANGELOG.md                      Rule changes and test-run history
```

`reports/` (generated Word reports) and `trimmed/` (intermediate logs) are created at run time and are not committed.

## Subagent

- **bug-report-analyser**: writes every bug report, log analysis, duplicate check and daily summary. Claude Code delegates these tasks to it automatically.

## Skills

- **secret-masker**: masks emails, passwords, API keys, tokens, cookies and connection-string values before analysis.
- **log-trimmer**: reduces logs longer than 50 lines to the lines that explain the failure.
- **attachment-reader**: turns attachments (JSON/HAR, CSV/XML, Word, PDF, ZIP, screenshots) into text and flags empty, corrupt or unsupported files.
- **evidence-extractor**: rules for what to quote, embed or flag from attachments as evidence.
- **qa-summaries**: rules for duplicate and pattern detection (uc2) and daily summaries (uc3).
- **report-renderer**: validates report content against the template and saves it as a .docx file.
- **report-checker**: scores the generated reports against the answer key in `expected/`.

## Requirements

- [Claude Code](https://claude.com/claude-code) (CLI or VS Code extension)
- Python 3.10+ with `python-docx` (`pip install python-docx`)

## Run a single report

Open the project in Claude Code and ask, for example:

```
Write a bug report for samples/uc1_saucedemo_locked_out_login.txt
```

The bug-report-analyser masks secrets, trims long logs, writes the report and saves it to `reports/docx/uc1_saucedemo_locked_out_login.docx`. You can also paste your own notes or logs into the chat.

## Run the regression tests

1. Ask Claude Code to process every sample in `tests/smoke_set.txt` (or all of `samples/` for a full run).
2. Score the reports from the main conversation (the analyser never grades its own work):

   ```bash
   python .claude/skills/report-checker/check_reports.py
   ```

   Options: `--file reports/docx/<name>.docx` checks one report; `--only root` or `--only attachments` checks one folder. Results go to `reports/docx/test_results.docx`, and the script exits with code 1 if any check fails.
3. Unit tests for the masking rules:

   ```bash
   python .claude/skills/secret-masker/test_mask.py
   python .claude/skills/report-checker/test_secret_rules.py
   ```

## Test results

All **29/29** sample reports pass: 22 root samples and 7 attachment scenarios. In the last full run (2026-11-07), 27 passed straight away. The other 2 (1 FAIL, 1 WARN) were fixed, re-run, and passed. See `CHANGELOG.md` for the run history and the rule changes behind each run.

## Sample data is fake

All defects, logs, IDs, emails, passwords, tokens, keys and cookies in `samples/` and `expected/` were **made up for testing**. The websites (SauceDemo, The Internet, OrangeHRM, DemoQA, ParaBank, Demoblaze, Automation Exercise) are public QA practice sites. A few behaviours are bugs those sites include on purpose; the rest are illustrative. Demo-site passwords appear in some inputs on purpose so the masking can be tested.
