# Order can be placed with an empty cart (0 USD purchase confirmed)

## Defect summary
With an empty cart, Place Order → Purchase completes and shows "Thank you for your purchase!" with Amount 0 USD and an order ID. An empty order should not be allowed.

## Environment
Demoblaze (https://www.demoblaze.com) · Browser: Unknown

## Test data used
| Item | Value |
| --- | --- |
| Cart | Empty |
| Order ID | 7731924 |
| Amount | 0 USD |

## Preconditions
Cart is empty.

## Steps to reproduce
1. Open Cart with no items.
2. Click Place Order.
3. Fill in name and card details.
4. Click Purchase.

## Expected result
Place Order is disabled, or a message says the cart is empty.

## Actual result
The purchase is confirmed with Amount 0 USD and order ID 7731924.

## Evidence
No logs provided.
**Screenshots/files to attach:** Screenshot of the confirmation.

## Likely cause (hypothesis)
There is no validation for an empty cart before creating the order.

## Suggested investigation
- Check client and server validation on Place Order.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 3 – Medium | Invalid orders can be created; no financial loss |
| Priority | 3 | — |
| Critical flag | No | — |

## Missing information
- Which browser was used?
