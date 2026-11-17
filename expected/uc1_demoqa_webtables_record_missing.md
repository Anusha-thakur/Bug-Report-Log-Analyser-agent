# New Web Tables record disappears after page refresh

## Defect summary
On DemoQA Web Tables, a newly added record shows in the table but is gone after a page refresh. The 3 default rows remain.

## Environment
DemoQA (https://demoqa.com) · Browser: Unknown

## Test data used
| Item | Value |
| --- | --- |
| First name | Asha |
| Last name | Rao |
| Age | 29 |
| Email | [MASKED] |
| Salary | 50000 |
| Department | QA |

## Steps to reproduce
1. Open DemoQA → Elements → Web Tables.
2. Click Add and enter the record above.
3. Submit and confirm the row appears.
4. Refresh the page.

## Expected result
The new record is still in the table after refresh.

## Actual result
The new record is gone; only the 3 default rows show.

## Evidence
No logs provided.
**Screenshots/files to attach:** Screenshots before and after refresh.

## Likely cause (hypothesis)
Records may be stored only in page memory and not saved; this may be by design on a demo page.

## Suggested investigation
- Confirm whether Web Tables is meant to save records.
- Check whether anything is written to local storage or a server on submit.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 4 – Low | Possibly by-design behaviour on a demo page; to be confirmed |
| Priority | 4 | — |
| Critical flag | No | — |

## Missing information
- Is the table expected to keep records after refresh?
- Which browser was used?
