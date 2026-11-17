# Clicking Finish at checkout does not show the order confirmation

## Defect summary
In the nightly SauceDemo regression run, the test Checkout_Finish_Confirmation failed: after clicking Finish, the "Thank you for your order!" confirmation did not appear within 10 seconds and the page stayed on checkout step two. The other 48 tests passed.

## Environment
SauceDemo (https://www.saucedemo.com) · Chrome 130 headless · Selenium nightly regression

## Test data used
| Item | Value |
| --- | --- |
| Failed test | Checkout_Finish_Confirmation |
| Run result | 48 passed, 1 failed |
| Wait timeout | 10 seconds |

## Steps to reproduce
1. Log in and add an item to the cart.
2. Complete checkout step one.
3. On checkout step two, click Finish.

## Expected result
The page shows "Thank you for your order!".

## Actual result
The page stays on checkout-step-two.html; no confirmation appears.

## Evidence
**Selenium log (about 265 lines; routine INFO/DEBUG lines filtered out)**
```
2026-11-04 07:09:57 INFO  START Checkout_Finish_Confirmation
2026-11-04 07:09:57 ERROR TimeoutException: waited 10s for element h2.complete-header text 'Thank you for your order!'
2026-11-04 07:09:57 ERROR Current URL still https://www.saucedemo.com/checkout-step-two.html
2026-11-04 07:09:57 INFO  FAIL Checkout_Finish_Confirmation (10.4s)
2026-11-04 07:15:16 INFO  SUMMARY: 48 passed, 1 failed
```
**Screenshots/files to attach:** Failure screenshot from the test run, if captured.

## Likely cause (hypothesis)
The Finish button click may not trigger navigation, or the confirmation page loads slower than the 10-second wait.

## Suggested investigation
- Run the checkout manually to see whether Finish works.
- Check the test's user account and whether the failure repeats on rerun.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 2 – High | Checkout cannot be completed in the test; core purchase flow |
| Priority | 2 | — |
| Critical flag | No | — |

## Missing information
- Does the failure repeat on rerun (could it be flaky)?
- Which user account does the test use?
