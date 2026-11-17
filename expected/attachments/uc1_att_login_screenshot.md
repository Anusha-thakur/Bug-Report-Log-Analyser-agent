# Login fails for visual_user with "Username and password do not match" error

## Defect summary
Logging in to SauceDemo as visual_user with the password shown on the login page fails. The screenshot shows "Epic sadface: Username and password do not match any user in this service" and both input fields outlined in red. standard_user logs in successfully.

## Environment
SauceDemo (https://www.saucedemo.com) · Chrome 130 · Windows 11

## Test data used
| Item | Value |
| --- | --- |
| Username | visual_user |
| Password | [MASKED] (password shown on the login page) |
| Comparison user | standard_user (logs in) |

## Steps to reproduce
1. Open https://www.saucedemo.com.
2. Enter username visual_user and the password shown on the login page.
3. Click Login.

## Expected result
User is logged in and the Products page opens.

## Actual result
The error "Epic sadface: Username and password do not match any user in this service" is shown and the user stays on the login page.

## Evidence
No logs provided.
> Epic sadface: Username and password do not match any user in this service

**Attachments reviewed:**
- login_error.png – read; shows the error banner and the visual_user username. **Embed in report** (no sensitive data visible).

## Likely cause (hypothesis)
The visual_user account may not accept this password, or the account data may differ from the other test users.

## Suggested investigation
- Confirm which password visual_user should use in this test data.
- Retry with the password typed manually, to rule out a copy-paste error.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 3 – Medium | Only one test account is affected; standard_user works |
| Priority | 3 | Workaround: use another account |
| Critical flag | No | No outage, data loss or security issue |

## Missing information
- Is visual_user expected to log in with the same password as standard_user?
