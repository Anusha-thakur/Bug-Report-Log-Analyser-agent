# Admin login fails with "Invalid credentials" after requesting a password reset

## Defect summary
After requesting a password reset for Admin, logging in with the existing password fails with "Invalid credentials". The API log shows a password hash mismatch. The reset email never arrived, so the user cannot log in by either route.

## Environment
OrangeHRM demo (https://opensource-demo.orangehrmlive.com) · Edge 130

## Test data used
| Item | Value |
| --- | --- |
| Username | Admin |
| Password | [MASKED] (password used before the reset request) |
| Reset email | [MASKED] |

## Steps to reproduce
1. Open the OrangeHRM demo login page in Edge 130.
2. Click "Forgot your password?" and request a reset for Admin.
3. Without using a reset link, log in as Admin with the existing password.

## Expected result
Either the existing password still works until reset is completed, or the reset email arrives so a new password can be set.

## Actual result
Login fails with "Invalid credentials" and no reset email arrives.

## Evidence
**Application log**
```
11:02:10 INFO  POST /web/index.php/auth/requestResetPassword user=Admin email=[MASKED]
11:04:46 ERROR AuthService: credentials invalid for user Admin (password_hash mismatch)
11:04:46 DEBUG Request headers: Cookie: orangehrm=[MASKED]; Authorization: Bearer [MASKED]
11:04:46 INFO  Response 302 /web/index.php/auth/login?error=invalid
```
**Screenshots/files to attach:** Screenshot of the "Invalid credentials" message.

## Likely cause (hypothesis)
Requesting a reset may invalidate or change the stored password hash before the user completes the reset; the reset email may also be failing to send.

## Suggested investigation
- Check whether requestResetPassword modifies the password hash.
- Check the mail queue for the reset email.
- Stop logging cookies and auth headers in DEBUG lines.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 1 – Critical | Admin locked out with no workaround, and session cookies and tokens are written to logs (security issue) |
| Priority | 1 | Admin access blocked; credentials exposed in logs |
| Critical flag | Yes | Security issue: auth headers and cookies logged |

## Missing information
- Does this happen for non-admin users?
- Is the mail service working for other emails?
