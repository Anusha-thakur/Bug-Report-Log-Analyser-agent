# "Add to cart" does nothing for Bolt T-Shirt and Fleece Jacket for problem_user

## Defect summary
For problem_user, clicking "Add to cart" on Sauce Labs Bolt T-Shirt and Sauce Labs Fleece Jacket has no effect: the button does not change to "Remove" and the cart badge does not update. The other 4 products work, and all 6 work for standard_user. No console errors.

## Environment
SauceDemo (https://www.saucedemo.com) · Chrome 130 · Windows 11

## Test data used
| Item | Value |
| --- | --- |
| Username | problem_user |
| Affected products | Sauce Labs Bolt T-Shirt; Sauce Labs Fleece Jacket |
| Comparison user | standard_user (all 6 products work) |

## Preconditions
Logged in as problem_user.

## Steps to reproduce
1. Log in to SauceDemo as problem_user.
2. On the Products page, click "Add to cart" for Sauce Labs Bolt T-Shirt.
3. Repeat for Sauce Labs Fleece Jacket.

## Expected result
The button changes to "Remove" and the cart badge count increases by 1.

## Actual result
Nothing happens: the button stays "Add to cart" and the badge is unchanged.

## Evidence
No logs provided.
**Screenshots/files to attach:** Screen recording of the click with the cart badge visible.

## Likely cause (hypothesis)
The click handler may not be bound for these two products for this user profile.

## Suggested investigation
- Inspect the button element for these products and check its event listener.
- Compare the DOM for a working and a non-working product.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 3 – Medium | Cart feature partly broken; workaround: other accounts work |
| Priority | 3 | Workaround: standard_user |
| Critical flag | No | No data loss or security issue |

## Missing information
- Does removing and re-adding other items change anything?
