# Text Box form: clicking Submit does nothing (TC-045 step 4)

## Defect summary
Test case TC-045 fails at step 4: after entering a full name and email on the DemoQA Text Box form, clicking Submit has no effect and no error is shown. Steps and expected results are taken from the attached test case.

## Environment
DemoQA (https://demoqa.com/text-box) · Firefox 132

## Test data used
| Item | Value |
| --- | --- |
| Test case | TC-045 – Text Box form submission |
| Full name | Asha Rao |
| Email | Placeholder in the test case ('[test email]') |

## Preconditions
Browser open; no login required (from TC-045).

## Steps to reproduce
1. Open https://demoqa.com/text-box.
2. Enter Full Name 'Asha Rao'.
3. Enter the test email.
4. Click Submit.

## Expected result
The output panel shows the name and email below the form (TC-045 step 4).

## Actual result
Nothing happens when clicking Submit; no error is shown.

## Evidence
No logs provided.

**Attachments reviewed:**
- testcase_TC-045.pdf – read; steps, precondition and expected results taken from it.

## Likely cause (hypothesis)
The Submit click handler may not run in Firefox 132.

## Suggested investigation
- Check the browser console for errors when clicking Submit.
- Repeat in another browser.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 3 – Medium | Non-core demo form broken |
| Priority | 3 | Matches severity; no blocking impact stated |
| Critical flag | No | — |

## Missing information
- Does it fail in other browsers?
- Which email value was used?
