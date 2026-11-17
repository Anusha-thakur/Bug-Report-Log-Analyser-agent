# Login takes about 5 seconds to load the Products page in SauceDemo

## Defect summary
Logging in as `performance_glitch_user` takes about 5 seconds across five runs (4.9–5.3 seconds), compared with under 1 second for `standard_user`. DevTools shows the delay while `inventory.html` loads; the login POST completes without the reported delay.

## Environment
SauceDemo (https://www.saucedemo.com) · Chrome 130 · Operating system: Not provided

## Test data used
| Item | Value |
| --- | --- |
| Username | `performance_glitch_user` |
| Timings (5 runs) | 5.1 s, 4.9 s, 5.3 s, 5.0 s, 5.2 s |
| Comparison user | `standard_user` |
| Comparison timing | Under 1 s |

## Preconditions (if any)
Access to the SauceDemo login page and the test account credentials. The password value was not provided.

## Steps to reproduce
1. Navigate to https://www.saucedemo.com.
2. On the login page, enter `performance_glitch_user` in the username field.
3. Enter the test account password in the password field. The password value was not provided.
4. Click **Login**.
5. Measure the time until the Products page (`inventory.html`) finishes loading.
6. Repeat the measurement for five runs and record each duration.
7. For comparison, repeat with `standard_user` and compare the Products page load time.

## Expected result
Not provided. The sample reports `standard_user` loads in under 1 second, but does not state an agreed performance target for `performance_glitch_user`.

## Actual result
The Products page takes about 5 seconds to load for `performance_glitch_user` (five measurements: 5.1 s, 4.9 s, 5.3 s, 5.0 s, and 5.2 s). The login POST completes without the reported delay; DevTools shows `inventory.html` waiting about 5000 ms.

## Evidence
DevTools network observation from the input:
```text
POST login: completes without reported delay
inventory.html load: waiting ~5000 ms
```
No screenshot or file attachment was mentioned or provided.

## Likely cause (hypothesis)
A delay may be applied while loading the inventory page for this user profile.

## Suggested investigation
- Profile the `inventory.html` load for `performance_glitch_user`.
- Compare the network requests and page-loading timings with `standard_user`.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 3 – Medium | The page is delayed but does load; no user-facing impact beyond the reported wait is stated. |
| Priority | 3 | The page is delayed but remains usable; no urgent outage is reported. |
| Critical flag | No | No system outage, data loss, or security issue is reported. |

## Missing information
- What is the agreed performance target for the Products page load?
