# Login fails for locked_out_user with "user has been locked out" error

## Defect summary
Logging in to SauceDemo as locked_out_user shows "Epic sadface: Sorry, this user has been locked out." and the user stays on the login page. The same password works for standard_user. Reproduced 3 times.

## Environment
SauceDemo (https://www.saucedemo.com) · Chrome 130 · Windows 11

## Test data used
| Item | Value |
| --- | --- |
| Username | locked_out_user |
| Password | [MASKED] |
| Comparison user | standard_user (logs in fine) |
| Attempts | 3 |

## Steps to reproduce
1. Open https://www.saucedemo.com in Chrome 130.
2. Enter username locked_out_user and the valid password.
3. Click Login.

## Expected result
User is logged in and the Products page opens.

## Actual result
Error "Epic sadface: Sorry, this user has been locked out." is shown; the user is not logged in.

## Evidence
**UI error message**
```
Epic sadface: Sorry, this user has been locked out.
```
**Screenshots/files to attach:** Screenshot of the login page showing the error.

## Likely cause (hypothesis)
The account is flagged as locked in the test data; it may be locked by design or by earlier failed attempts.

## Suggested investigation
- Confirm whether locked_out_user is meant to be locked in this test data set.
- If not, unlock or reset the account and retest.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 3 – Medium | Only this account is affected; other accounts can log in |
| Priority | 3 | Blocks the checkout regression only if this account is required |
| Critical flag | No | No outage, data loss or security issue |

## Missing information
- Is this account expected to be locked in the test data?
- Is there another account that can be used for the checkout regression?
