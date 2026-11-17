# Cart total shows 1520 instead of 1610 for Nokia Lumia 1520 and Sony Vaio i5

## Defect summary
With Nokia lumia 1520 (820) and Sony vaio i5 (790) in the Demoblaze cart, the total shows 1520 instead of 1610. Deleting one item and adding it again corrects the total. Reproduced 3 out of 3 times.

## Environment
Demoblaze · Chrome 130 · Windows 11

## Test data used
| Item | Value |
| --- | --- |
| Product 1 | Nokia lumia 1520 – 820 |
| Product 2 | Sony vaio i5 – 790 |
| Expected total | 1610 |
| Shown total | 1520 |

## Steps to reproduce
1. Add Nokia lumia 1520 to the cart.
2. Add Sony vaio i5 to the cart.
3. Open Cart and check the total.

## Expected result
Total is 1610.

## Actual result
Total is 1520.

## Evidence
No logs provided.

**Attachments reviewed:**
- defect_notes.docx – read; facts and the product table taken from it.

## Likely cause (hypothesis)
The total may be calculated before the second item's price is loaded.

## Suggested investigation
- Compare the total calculation with the cart item list after both items load.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 3 – Medium | Wrong cart total, but a workaround exists (delete and re-add the item) |
| Priority | 3 | Workaround available |
| Critical flag | No | — |

## Missing information
- Does the wrong total carry through to Place Order?
