# Valid credentials rejected with "Your username is invalid!" on login page

## Defect summary
On The Internet's /login page, valid credentials for tomsmith are rejected with "Your username is invalid!". Started around 10:15 today; it worked yesterday. An invalid password still shows the correct "Your password is invalid!" message.

## Environment
The Internet (https://the-internet.herokuapp.com) · Firefox 132 · macOS 14

## Test data used
| Item | Value |
| --- | --- |
| Username | tomsmith |
| Password | [MASKED] (valid password) |
| Page | /login |

## Steps to reproduce
1. Open https://the-internet.herokuapp.com/login in Firefox 132.
2. Enter username tomsmith and the valid password.
3. Click Login.

## Expected result
User is redirected to /secure with the message "You logged into a secure area!".

## Actual result
User is redirected back to /login with "Your username is invalid!".

## Evidence
**Network log**
```
POST https://the-internet.herokuapp.com/authenticate  302 -> /login
Set-Cookie: rack.session=[MASKED]; path=/; HttpOnly
```
**Screenshots/files to attach:** Screenshot of the error banner; HAR file of the login request.

## Likely cause (hypothesis)
Username validation may have changed, or the stored user record no longer matches (for example, whitespace or case handling).

## Suggested investigation
- Check recent changes to the /authenticate handler.
- Test with the username typed manually vs pasted, to rule out hidden whitespace.
- Check server logs at ~10:15 for the authentication failure reason.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 2 – High | Login is a core feature and valid users cannot get in; no workaround |
| Priority | 2 | Input does not say testing cannot continue |
| Critical flag | No | No data loss or security exposure reported; raise if all users are affected in production |

## Missing information
- Does it happen in other browsers?
- Are other users affected, or only tomsmith?
