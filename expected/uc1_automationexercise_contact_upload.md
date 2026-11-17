# Contact Us form does not submit when a file is attached

## Defect summary
On Automation Exercise's Contact Us page, clicking Submit with a file attached does nothing. Without an attachment, the form submits and shows the success message. The console shows a TypeError reading 'files'.

## Environment
Automation Exercise (https://automationexercise.com) · Chrome 130

## Test data used
| Item | Value |
| --- | --- |
| Page | Contact Us |
| Attachment | test_upload.pdf (120 KB) |

## Steps to reproduce
1. Open the Contact Us page.
2. Fill in the required fields.
3. Attach test_upload.pdf.
4. Click Submit.

## Expected result
The form submits and the success message is shown.

## Actual result
Nothing happens; the form is not submitted.

## Evidence
**Browser console**
```
Uncaught TypeError: Cannot read properties of null (reading 'files') at contact_us.js:27
```
**Screenshots/files to attach:** Screenshot of the console; the test file.

## Likely cause (hypothesis)
contact_us.js reads the file input by a selector that does not match the page, so it gets null.

## Suggested investigation
- Check the file input selector at contact_us.js:27.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 3 – Medium | Workaround: submit without an attachment |
| Priority | 3 | — |
| Critical flag | No | — |

## Missing information
- Does it fail with other file types or sizes?
