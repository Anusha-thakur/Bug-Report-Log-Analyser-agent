# New employee not found by name in PIM Employee List (found by ID)

## Defect summary
A newly created employee ("Test Kumar", ID 0451) cannot be found by name in PIM → Employee List; the search returns "No Records Found" even after 10 minutes. Searching by ID 0451 finds the record. The API returns an empty result for the name search.

## Environment
OrangeHRM demo (https://opensource-demo.orangehrmlive.com) · Chrome 130

## Test data used
| Item | Value |
| --- | --- |
| Employee name | Test Kumar |
| Employee ID | 0451 |
| Created at | 14:20 |

## Preconditions
Employee "Test Kumar" (ID 0451) created and saved.

## Steps to reproduce
1. In PIM, create employee "Test Kumar" with ID 0451 and save.
2. Go to PIM → Employee List.
3. Search by employee name "Test Kumar".

## Expected result
The employee appears in the results.

## Actual result
"No Records Found" is shown. Searching by ID 0451 returns the employee.

## Evidence
**Network log**
```
GET /web/index.php/api/v2/pim/employees?nameOrId=Test%20Kumar&includeEmployees=onlyCurrent  200  {"data":[],"meta":{"total":0}}
```
**Screenshots/files to attach:** Screenshots of the name search and the ID search.

## Likely cause (hypothesis)
Name search may match on a separate search index that is not updated for new employees, or may not handle the full name with a space.

## Suggested investigation
- Search by first name only ("Test") to check the space handling.
- Check whether a search index is updated on employee creation.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 3 – Medium | Workaround: search by ID |
| Priority | 3 | Workaround: search by ID |
| Critical flag | No | — |

## Missing information
- Does searching by first name only find the employee?
- Are older employees found by full name?
