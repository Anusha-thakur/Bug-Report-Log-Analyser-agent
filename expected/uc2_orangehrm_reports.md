# Duplicate and pattern analysis – OrangeHRM reports

## Summary
4 reports: 1 exact duplicate, 1 related report that adds a clue, 1 unrelated report.

| Report | Group | Status |
| --- | --- | --- |
| 1 | Group 1 – PIM full-name search | Keep (primary) |
| 4 | Group 1 | **Exact duplicate of 1** (same employee, same symptom) |
| 2 | Group 1 | Related – different employee, same symptom |
| 3 | Separate | Unrelated – Leave module |

## Group 1: Full-name search in PIM returns no records (1, 2, 4)
**Why grouped:** all three fail when searching by full name for employees created today. Report 2 adds a clue: searching by first name only works.

### Consolidated defect
**Title:** PIM Employee List search by full name returns no records for newly created employees

**Test data used:** Test Kumar (ID 0451); Ravi Shah

**Expected result:** employees are found by full name.

**Actual result:** "No Records Found"; search by ID or first name only works.

**Likely cause (hypothesis):** full names containing a space are not matched by the search.

**Classification suggestions:** Severity 3 – Medium (workaround: search by ID or first name) · Priority 2 · Critical flag: No

## Report 3: Leave apply never completes
Separate defect. Severity 2 – High (leave cannot be applied, no workaround reported) · Priority 2 · Critical flag: No.

## Missing information
- Report 3: any console or network errors when clicking Apply?
