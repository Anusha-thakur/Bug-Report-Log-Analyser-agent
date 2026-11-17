# GET account 13344 returns 500 (NullPointerException: account.customer is null)

## Defect summary
Calling the ParaBank REST API for account 13344 returns 500 Internal Server Error with "NullPointerException: account.customer is null". The same request for account 13455 returns 200.

## Environment
ParaBank (https://parabank.parasoft.com) REST API · called from Postman

## Test data used
| Item | Value |
| --- | --- |
| Account | 13344 (fails) |
| Comparison account | 13455 (returns 200) |
| Request ID | req-5f2a91 |
| Timestamp | 2026-11-06T10:12:44Z |

## Steps to reproduce
1. Send GET https://parabank.parasoft.com/parabank/services/bank/accounts/13344 with Accept: application/json.

## Expected result
200 with the account details.

## Actual result
500 Internal Server Error: "NullPointerException: account.customer is null".

## Evidence
**API response (from api_response.json, relevant fields only)**
```
status: 500
message: NullPointerException: account.customer is null
path: /parabank/services/bank/accounts/13344
trace: com.parasoft.parabank.service.AccountService.getAccount(AccountService.java:112)
trace: com.parasoft.parabank.web.AccountController.get(AccountController.java:45)
x-api-key: [MASKED]
```

**Attachments reviewed:**
- api_response.json – read; the x-api-key header was masked in this report. Attach a copy with the key removed.

## Likely cause (hypothesis)
Account 13344 has no linked customer record, and AccountService.getAccount does not handle a missing customer.

## Suggested investigation
- Check the customer link for account 13344 in the database.
- Check AccountService.java line 112 for null handling.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 2 – High | Retrieving an account record fails and no workaround exists for this account |
| Priority | 2 | Core record lookup affected |
| Critical flag | No | The API key appears only in the tester's own request capture, not in application logs |

## Missing information
- Does the same error appear in the UI for account 13344?
