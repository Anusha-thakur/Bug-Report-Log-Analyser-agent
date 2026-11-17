# "Hello World!" never appears after clicking Start on Dynamic Loading example 2

## Defect summary
On /dynamic_loading/2, clicking Start shows the loading bar, but "Hello World!" never appears, even after 30 seconds. The console shows a TypeError in finishLoading. Example 1 works.

## Environment
The Internet (https://the-internet.herokuapp.com) · Chrome 130

## Test data used
| Item | Value |
| --- | --- |
| Page | /dynamic_loading/2 |
| Wait time | 30 seconds |

## Steps to reproduce
1. Open https://the-internet.herokuapp.com/dynamic_loading/2.
2. Click Start.
3. Wait for the loading bar to finish.

## Expected result
"Hello World!" is displayed after loading.

## Actual result
The loading bar disappears and no text appears.

## Evidence
**Browser console**
```
Uncaught TypeError: Cannot set properties of null (setting 'innerHTML')
    at finishLoading (dynamic_loading.js:14:22)
```
**Screenshots/files to attach:** Screenshot of the page and console after loading.

## Likely cause (hypothesis)
finishLoading tries to write into an element that does not exist on example 2 (element ID mismatch).

## Suggested investigation
- Check dynamic_loading.js line 14 and the element ID it targets.
- Compare the element IDs on example 1 and example 2.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 3 – Medium | Feature broken on one page; example 1 works |
| Priority | 3 | — |
| Critical flag | No | — |

## Missing information
- Does it fail in other browsers?
