---
name: secret-masker
description: "Mask emails, passwords, API keys, bearer tokens, cookies, and secret connection-string values in log or notes files before analysis. Use before analyzing any file that may contain sensitive data."
---

# Secret Masker

Sanitize source files containing QA notes, logs, stack traces, or other diagnostic text before reading or analyzing their contents.

## Procedure

1. For each input file, choose a distinct output path in the operating-system temporary directory. Never use the source path as the output or overwrite an existing file.
2. Run the masking script:

   ```bash
   python .claude/skills/secret-masker/mask.py "<input-file>" "<new-masked-output-file>"
   ```

3. If masking fails, stop and report the error; do not read or analyze the unmasked source file.
4. Read the `MASKED: <count> (<types>)` summary printed by the script. It reports the total number of replacements and detected types, such as `password`, `token`, `api_key`, `cookie`, `account_key`, and `email`; `MASKED: 0 (none)` means no supported patterns were detected.
5. Read and analyze only the masked output. Do not copy unmasked values into reports, summaries, tool requests, or conversation responses. Use the summary and the input context to determine whether secrets appeared in application/server output or only in tester notes, test data, or a browser network capture.
6. Remove the temporary masked output when analysis is complete. Never modify or delete the original source.

For notes pasted directly into chat rather than provided as a file, apply the same masking rules to the text before analysis.

The script masks email addresses, password fields, API keys, bearer tokens, cookie headers/values, and credential values in connection strings. Treat masking as a safeguard, not a guarantee: do not reproduce any remaining value that appears sensitive.
