---
name: report-renderer
description: Validates report content and saves it as a Word document.
---

# Report Renderer

Prepare report content using `template.txt` for uc1 or the simple markers for
uc2/uc3, then pass the content to the renderer through standard input. Use a
quoted heredoc so special characters are not changed:

```bash
python .claude/skills/report-renderer/render_report.py --type uc1 --out reports/docx/<name>.docx <<'EOF'
...content...
EOF
```

If validation fails, fix the content and rerun the renderer until it passes.
Never save report content or any other report output as a `.md`, `.json`, or
`.txt` file. The `.docx` is the only saved report output.
