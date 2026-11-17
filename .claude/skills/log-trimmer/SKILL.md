---
name: log-trimmer
description: "Use this before analysing any log file longer than 50 lines, to reduce it to the lines that explain the failure."
---

# Log Trimmer

## When to use

Use this skill before analysing any log file longer than 50 lines. If the file may contain secrets, sanitize it with the secret-masker skill first and trim the sanitized copy.

## Command

Run this exact command from the project root, replacing `<input_file>` with the log path:

```bash
python .claude/skills/log-trimmer/trim_log.py <input_file>
```

Optional arguments can widen the surrounding context and time window:

```bash
python .claude/skills/log-trimmer/trim_log.py <input_file> --context 20 --window 5
```

The script writes to the project-root path `trimmed/<original name>.trimmed.log`, creates the `trimmed/` directory if needed, and never modifies the input. It reports the output path and original/kept line counts. The kept count is the number of log lines emitted in the trimmed body after identical selected lines are collapsed; headers and gap markers are excluded.

## After trimming

- Analyse the trimmed file, not the full log.
- When quoting log lines, preserve their original timestamps.
- Under **Evidence**, add: `Log trimmed from X to Y lines by log-trimmer.` Use the original and kept counts printed by the script.
- If the trimmed file appears to miss necessary context, rerun with a larger `--context` or `--window`, or read the masked copy around the first failure line.
