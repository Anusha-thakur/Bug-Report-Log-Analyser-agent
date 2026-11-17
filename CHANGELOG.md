# Changelog

## Test run history

Counts and timestamps come from the `Summary:` line of each run's `test_results.docx`. Run 1 has no results file; its counts were recorded by hand.

| Run | Date (IST) | Reports | PASS | WARN | FAIL | Results file |
|---|---|---|---|---|---|---|
| Run 1 | Not recorded | 37 | 6 | – | 31 | None |
| Run 2 | 2026-11-05 10:45 | 38 | 38 | 0 | 0 | `reports/docx/test_results_run2.docx` |
| Run 3 | 2026-11-05 12:39 | 38 | 14 | 10 | 14 | `reports/run3/test_results.docx` |
| Run 4 | 2026-11-05 12:30 | 18 | 8 | 6 | 4 | `reports/run4/test_results.docx` |
| Run 5-check | 2026-11-06 09:05 | 2 | 2 | 0 | 0 | `reports/run5-check/test_results.docx` |
| Run 5 | 2026-11-06 09:25 | 38 | 29 | 4 | 5 | `reports/run5/test_results.docx` |
| Run 6 | 2026-11-06 09:36 | 38 | 38 | 0 | 0 | `reports/run6/test_results.docx` |
| Run 6-polish | 2026-11-06 09:43 | 5 | 5 | 0 | 0 | `reports/run6-polish/test_results.docx` |

Run 4 rescored only 18 reports. Run 3's results file has a later timestamp than Run 4's, so it was probably rescored after Run 4.

### Changes before each run

- **Run 1:** Reports were free text. Their headings did not match the template, which caused most of the failures.
- **Run 2:** Added the report template, renderer validation and Word (.docx) output. Severity and priority rules were made clearer.
- **Run 3:** Edited the rules and added the secret-masker. The failures had three causes: masking hid security evidence; Bash rules conflicted; and a "financial records missing" rule was too broad.
- **Run 4:** Made the priority rules first-match. uc3 summaries now require a `Severity | Count | Defects` table. Most WARNs came from the checker not reading that Word table.
- **Run 5-check (2 samples):**
  - Made the severity rules first-match and moved To be assessed and 4 – Low ahead of 2 – High.
  - Behaviour is treated as by design only when the input says so.
  - Priority 1 now requires the input to say testing or release cannot continue.
  - Updated the answer key for two samples, and added a by-design note to the DemoQA web-table sample.
  - The checker now reads uc3 counts from the Word table.
- **Run 5:** Same rules as Run 5-check, run across all samples. The answer key was brought in line with the rules. Review found 4 stale Priority values in the answer key, 2 agent errors and 4 checker false positives for secrets.
- **Run 6:**
  - Defined core features: a broken non-core feature is now 3 – Medium.
  - Reordered priority to 1 → 4 → 3 → 2.
  - Added rules to quote URLs exactly and to leave out Test data rows that would say "Not provided" or "Unknown".
  - Checker fixes: secrets are checked cell by cell and placeholder values are skipped; trim-note line counts are ignored everywhere.
  - Updated 5 Priority values in the answer key.
  - Ran 5 bug-report-analyser subagents in parallel.
- **Run 6-polish (5 samples):**
  - `mask.py` now masks plain-text passwords in tester notes, with 11 new tests in `test_mask.py`.
  - The renderer and checker flag "Bearer" only when it is followed by a token of 20+ characters, so the plain words "bearer token" no longer fail validation.
  - Client IDs, tenant IDs and connection-string values are always masked.
  - The uc3 answer key now includes a `Not stated` row.

## 2026-11-04

| Change to `.claude/agents/bug-report-analyser.md` | Test failure addressed | Retest |
|---|---|---|
| Created the analyzer instructions: role and use cases; report fields; severity guidance; log handling; redaction, evidence, and other guardrails. | No prior test failure was recorded for the initial version. | N/A |
| Replaced the report structure with the ordered 13-field template and defined evidence and classification requirements, including numeric severity, priority guidance, and the Critical flag criteria. | The audit identified missing required fields and unsupported priority/classification decisions in `uc1_demoqa_submit_button_blocked.md` and two samples that have since been removed. | Passed after rerunning those reports; the updated audit marks their Template, Invented, and Severity checks Pass. |
| Restricted titles to what fails and where in the application, with environment details only in Environment. | No corresponding failure was identified in `reports/test_results.md`. | N/A |
| Clarified preconditions, detailed-but-evidence-based reproduction steps, and screenshot/file handling. | No corresponding failure was identified in `reports/test_results.md`. | N/A |
| Strengthened the description to require proactive use and delegation instead of writing bug reports in the main conversation. | No corresponding failure was identified in `reports/test_results.md`. | N/A |
| Added a final completeness check requiring all 13 fields in order and reasoned Severity, Priority, and Critical flag rows, using explicit unknown values when needed. | Fixed the missing Defect summary, Test data used, Evidence, and Critical flag row in `uc1_demoqa_submit_button_blocked.md`. | Passed; the rerun report contains all required fields and classification rows. |

The audit also found severity classifications needing correction in `uc2_orangehrm_reports.md` and `uc2_saucedemo_reports.md`. No additional instruction change was needed: the existing severity guide covered these cases. Both reports were rerun using that guide, and their Severity checks passed.

All five reports that failed the previous audit were rerun. Their updated checks pass in `reports/test_results.md`.
