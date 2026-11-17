# Practice form Submit button covered by fixed banner at 1366×768

## Defect summary
On the DemoQA practice form, the Submit button cannot be clicked at 1366×768 because a fixed banner (div#fixedban) covers it. The automated test fails with ElementClickInterceptedException. At 1920×1080, manual submission works.

## Environment
DemoQA (https://demoqa.com) · Chrome 130 headless · 1366×768

## Test data used
| Item | Value |
| --- | --- |
| Page | /automation-practice-form |
| Fields filled | first name, last name, email, gender, mobile |
| Test | PracticeForm_Submit |

## Steps to reproduce
1. Open the practice form at a 1366×768 window size.
2. Fill in first name, last name, email, gender and mobile.
3. Click Submit.

## Expected result
The form is submitted and the confirmation dialog opens.

## Actual result
The click is intercepted by div#fixedban; the form is not submitted.

## Evidence
**Selenium log**
```
09:31:06 ERROR ElementClickInterceptedException: element click intercepted: Element <button id="submit"> is not clickable at point (683, 742). Other element would receive the click: <div id="fixedban">
09:31:06 INFO  Test PracticeForm_Submit FAILED
```
**Screenshots/files to attach:** Screenshot at 1366×768 showing the banner over the button.

## Likely cause (hypothesis)
The fixed banner overlaps the Submit button on smaller screens.

## Suggested investigation
- Check the banner's CSS position and z-index at 1366×768.
- As a test workaround, scroll the button into view or hide the banner before clicking.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 3 – Medium | Submission blocked on smaller screens; works at larger sizes |
| Priority | 3 | Workaround: works at 1920x1080 |
| Critical flag | No | — |

## Missing information
- Does this affect manual users at 1366×768, or only headless runs?
