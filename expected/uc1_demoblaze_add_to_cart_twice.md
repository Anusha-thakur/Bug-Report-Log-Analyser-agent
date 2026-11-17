# Single "Add to cart" click adds Samsung Galaxy S6 to cart twice

## Defect summary
Clicking "Add to cart" once for Samsung Galaxy S6 adds it to the cart twice, so the total shows 720 instead of 360. The network log shows two addtocart requests for one click. Happens every time.

## Environment
Demoblaze (https://www.demoblaze.com) · Chrome 130

## Test data used
| Item | Value |
| --- | --- |
| Product | Samsung galaxy s6 (prod_id 1) |
| Expected total | 360 |
| Shown total | 720 |

## Steps to reproduce
1. Open Demoblaze and select Samsung galaxy s6.
2. Click "Add to cart" once and accept the alert.
3. Open Cart.

## Expected result
The product appears once; total is 360.

## Actual result
The product appears twice; total is 720.

## Evidence
**Network log**
```
POST https://api.demoblaze.com/addtocart 200 {"id":"fake-1","prod_id":1}
POST https://api.demoblaze.com/addtocart 200 {"id":"fake-2","prod_id":1}
```
**Screenshots/files to attach:** Screenshot of the cart; HAR file.

## Likely cause (hypothesis)
The click handler is bound twice, so one click sends two requests.

## Suggested investigation
- Check how many listeners are attached to the Add to cart button.
- Check whether the alert confirmation triggers a second request.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 2 – High | Wrong order total; user may be overcharged |
| Priority | 2 | — |
| Critical flag | No | Wrong data but no data loss; raise if real payments are taken |

## Missing information
- Does it happen for other products?
