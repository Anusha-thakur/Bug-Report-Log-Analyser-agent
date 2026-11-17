---
name: report-checker
description: "Use after the bug-report-analyser has processed samples or after its instructions change, to score the Word reports."
---

# Report Checker

Use this skill from the main conversation after the bug-report-analyser has
processed samples or after its instructions change. The bug-report-analyser
must never grade its own work.

## Run

From the project root, run:

```bash
python .claude/skills/report-checker/check_reports.py
```

Reports are read from `reports/docx/`, including `reports/docx/attachments/`. Each subfolder of `samples/attachments/` is one
scenario: its report is `docx/attachments/<folder>.docx`, its answer key is
`expected/attachments/<folder>.md`, and the invented-details scan compares the
report with the notes plus the masked text of every readable attachment
(extracted with attachment-reader). Use `--only root,attachments` (either or
both) to score only some sample folders; for example, `--only attachments`
scores just the attachment scenarios. A missing Word report is marked
**NOT RUN**. To check a single report:

```bash
python .claude/skills/report-checker/check_reports.py --file reports/docx/<name>.docx
```

Use `--reports <directory>` to select the reports root (the script reads its
`docx/` subfolder; the default is `reports`). Use `--results <path>` to select
the results document path. By default the script saves to
`reports/docx/test_results.docx`. It prints a summary line and exits with code
1 if any check fails.

## Review warnings

Review every WARN item in the **Details** section of `test_results.docx`.
Pay particular attention to possible invented details and compare each flagged
value with its matching sample.

Add a **Reviewer notes** section to the results document by rerunning the
script with `--notes` and passing the notes through standard input. Use a
quoted heredoc to preserve special characters:

```bash
python .claude/skills/report-checker/check_reports.py --notes <<'EOF'
Reviewed each warning against its sample.
...additional notes...
EOF
```

Add the same `--reports` and `--results` options when rerunning for a
non-default report set or results location. The rerun recreates the results
document with the supplied notes under its **Reviewer notes** heading. Do not
save reviewer notes or checker results as Markdown or any other non-Word report
file.
