# 2 of 3 images broken on Broken Images page (404)

## Defect summary
On /broken_images, 2 of the 3 images fail to load and show the broken image icon. The network log shows 404 responses for both.

## Environment
The Internet (https://the-internet.herokuapp.com) · Browser: Unknown

## Test data used
| Item | Value |
| --- | --- |
| Page | /broken_images |
| Broken | asdf.jpg, hjkl.jpg |
| Working | img/avatar-blank.jpg |

## Steps to reproduce
1. Open https://the-internet.herokuapp.com/broken_images.

## Expected result
All 3 images load.

## Actual result
asdf.jpg and hjkl.jpg return 404 and show as broken.

## Evidence
**Network log**
```
GET https://the-internet.herokuapp.com/asdf.jpg 404
GET https://the-internet.herokuapp.com/hjkl.jpg 404
GET https://the-internet.herokuapp.com/img/avatar-blank.jpg 200
```
**Screenshots/files to attach:** Screenshot of the page.

## Likely cause (hypothesis)
The two image paths point to files that do not exist (wrong path or missing files).

## Suggested investigation
- Check whether the files exist under /img/.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 4 – Low | Cosmetic |
| Priority | 4 | — |
| Critical flag | No | — |

## Missing information
None
