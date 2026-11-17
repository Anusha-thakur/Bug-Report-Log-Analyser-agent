# Registration and login fail with "internal error" – database connection refused

## Defect summary
Registering a new user and logging in as an existing user both fail with "An internal error has occurred and has been logged." The server log shows the application cannot connect to its database (connection refused on localhost:9001).

## Environment
ParaBank (https://parabank.parasoft.com) (local Docker instance)

## Test data used
| Item | Value |
| --- | --- |
| Action 1 | Register new user |
| Action 2 | Log in as existing user john |

## Steps to reproduce
1. Open the local ParaBank instance.
2. Register a new user, or log in as john.

## Expected result
Registration succeeds; login succeeds.

## Actual result
Both show "An internal error has occurred and has been logged."

## Evidence
**Server log**
```
15:10:03 ERROR DataSource: Cannot get connection: java.net.ConnectException: Connection refused (localhost:9001)
15:10:03 ERROR RegisterController: org.springframework.jdbc.CannotGetJdbcConnectionException: Failed to obtain JDBC Connection
15:10:20 ERROR DataSource: Cannot get connection: java.net.ConnectException: Connection refused (localhost:9001)
```
**Screenshots/files to attach:** Screenshot of the error page.

## Likely cause (hypothesis)
The database service on port 9001 is not running or not reachable from the app container.

## Suggested investigation
- Check that the database container is running and listening on 9001.
- Check the Docker network between the app and the database.
- Restart the database and retest.

## Classification suggestions
| Field | Suggestion | Reason |
| --- | --- | --- |
| Severity | 1 – Critical | Application unusable: login and registration both fail |
| Priority | 1 | — |
| Critical flag | Yes | System down |

## Missing information
- Was the Docker setup changed recently?
