---
name: qa-summaries
description: "Rules for duplicate and pattern detection (uc2) and daily QA defect summaries (uc3). Use when the bug-report-analyser compares several bug reports or summarises a day's defect notes."
---

# QA Summaries

The renderer checks only secrets for uc2 and uc3, so check these rules yourself before rendering.

## uc2: duplicate and pattern detection

- Compare supported symptoms, timestamps, affected components/pages, and evidence.
- Group likely related reports, and distinguish likely duplicates from shared patterns.
- Provide a consolidated report that preserves the supplied original report IDs/links. Do not invent IDs, links, or a shared cause.
- For every exact duplicate, in every sample folder, write exactly: `Report X is an exact duplicate of Report Y.`, replacing X and Y with the supplied report identifiers.

## uc3: daily QA defect summary

- Write a concise team update with counts of open defects by severity and area.
- List resolved and retested defects separately, and mark pending or unconfirmed details as "not confirmed".
- Count each duplicate once.
- Include a severity table with the exact header `Severity | Count | Defects` and rows named exactly `Critical`, `High`, `Medium`, `Low`, and `Not stated` (the renderer adds `Not stated` with count 0 if you leave it out).
- Pending or open items without a stated severity go in the Not stated row.
- Count only open defects in this table; never count resolved and retested defects as open. Never infer severity.

## Format

Use the simple markers `TITLE:`, `== ` headings, `- ` bullets, and pipe-separated table rows, then render with `--type uc2` or `--type uc3`.
