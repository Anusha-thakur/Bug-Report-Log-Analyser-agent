# Dashboard widgets fail to load (action-summary API 500) and auth token is written to the browser console

## Defect summary
After logging in as Admin, the dashboard widgets are blank. The console screenshot shows the action-summary API returning 500 and a TypeError in renderWidgets. The application also writes the user's email and bearer token to the browser console in a debug line, which is a security issue.

## Environment
OrangeHRM demo (https://opensource-demo.orangehrmlive.com) · Edge 130

## Test data used
| Item | Value |
| --- | --- |
| User | Admin |
| API endpoint | /web/index.php/api/v2/dashboard/employees/action-summary |

## Steps to reproduce
1. Log in to the OrangeHRM demo as Admin in Edge 130.
2. Open the dashboard.
3. Open DevTools → Console.

## Expected result
Dashboard widgets load, and no credentials or tokens are written to the console.

## Actual result
Widgets are blank; the action-summary request returns 500; the console shows the user's email and bearer token.

## Evidence
**Browser console (transcribed from console.png)**
```
[debug] auth user=[MASKED] token=Bearer [MASKED]
GET https://opensource-demo.orangehrmlive.com/web/index.php/api/v2/dashboard/employees/action-summary 500 (Internal Server Error)
Uncaught (in promise) TypeError: Cannot read properties of undefined (reading 'map')
    at renderWidgets (dashboard.js:88:31)
[warn] Widget 'My Actions' failed to render
```

**Attachments reviewed:**
- console.png – read. Embedded original with warning: contains a visible email and bearer token – share only with authorised people.

## Likely cause (hypothesis)
The action-summary API returns an error, so renderWidgets receives undefined and fails. A debug log statement prints auth details to the console.

## Suggested investigation
- Check server logs for the 500 on action-summary.
- Remove the debug line that logs the user and token, and rotate the exposed token.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 1 – Critical | Auth token and email written to the console by the application (security issue) |
| Priority | 1 | Security issue |
| Critical flag | Yes | Secrets exposed in application console output |

## Missing information
- Is the debug logging also enabled in production builds?
