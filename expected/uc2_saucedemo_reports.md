# Duplicate and pattern analysis – SauceDemo reports

## Summary
5 reports received: 1 exact duplicate, 1 pattern group of related defects, 1 unrelated report.

| Report | Group | Status |
| --- | --- | --- |
| A | Group 1 – problem_user defects | Keep (images) |
| C | Group 1 | **Exact duplicate of A** (same user, same dog image symptom) |
| B | Group 1 | Related – same user, different feature (checkout last name) |
| D | Group 1 | Related – same user, different feature (add to cart) |
| E | Separate | Unrelated – performance, different user |

## Group 1: Defects that occur only for problem_user (A, B, C, D)
**Why grouped:** all reports involve problem_user only, across images, cart and checkout. This suggests a shared cause linked to that user profile (hypothesis), but the symptoms are different, so keep A, B and D as separate defects linked to one parent.

**Suggested parent title:** Multiple features misbehave for problem_user (images, add to cart, checkout)

| Defect | Severity | Priority | Critical flag |
| --- | --- | --- | --- |
| A – Same dog image for all products | 4 – Low | 3 | No |
| B – Cannot enter Last Name at checkout | 2 – High (checkout blocked for this user) | 2 | No |
| D – Add to cart does nothing for Bolt T-Shirt | 3 – Medium | 2 | No |

## Report E: Slow login for performance_glitch_user
Different user and symptom. Log as a separate defect. Severity 3 – Medium · Priority 3 · Critical flag: No.

## Missing information
- Report B: which browser was used?
- Report E: what is the agreed page-load target?
