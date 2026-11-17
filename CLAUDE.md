# Bug Report and Log Analyser Agent

## Goal

A QA assistant for QA teams. It turns defect notes and logs into ticket-ready bug reports (uc1), flags duplicates and patterns (uc2), and writes daily QA summaries (uc3). It does not reproduce bugs, change code or close tickets; people review its output.

Always delegate bug reports, log analysis, duplicate detection and daily QA summaries to the bug-report-analyser subagent. Never write these yourself in the main conversation.

## Layout

- `.claude/agents/bug-report-analyser.md`: role, severity rules, guardrails
- `.claude/skills/`: secret-masker, log-trimmer, attachment-reader, evidence-extractor, qa-summaries, report-renderer (template and validator), report-checker
- `samples/`: inputs, including `attachments/<scenario>/`
- `expected/`: answer key for each sample
- `reports/docx/`: rendered Word reports (the only output)
- `tests/smoke_set.txt`: quick regression set

## Testing

Run the agent on the samples in `tests/smoke_set.txt`, then score the reports from the main conversation with the report-checker skill.
