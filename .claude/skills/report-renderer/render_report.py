#!/usr/bin/env python3
"""Validate QA report content and render it directly to a Word document."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.image.image import Image as DocxImage
from docx.shared import Cm, Inches, Mm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.style import WD_STYLE_TYPE


UC1_REQUIRED_SECTIONS = (
    "Defect summary",
    "Environment",
    "Test data used",
    "Steps to reproduce",
    "Expected result",
    "Actual result",
    "Evidence",
    "Classification",
    "Missing information",
)
ENVIRONMENT_WORDS = re.compile(r"(?i)\b(?:SIT|UAT|staging|production)\b")
EMAIL = re.compile(
    r"(?i)\b[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+\b"
)
MASKED_VALUE = r"(?:\[MASKED\]|\*{2,}|<MASKED>|REDACTED)"
SECRET_PATTERNS = (
    ("token", re.compile(
        rf"(?i)(?:\b(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|auth[_ -]?token|token)\s*[:=]\s*(?!(?:bearer\s+)?{MASKED_VALUE})(?:\"[^\"]+\"|'[^']+'|[^\s,;|]+)|\bbearer\s+(?!{MASKED_VALUE})[A-Za-z0-9._-]{{20,}})"
    )),
    ("cookie", re.compile(
        rf"(?i)\b(?:set-cookie|cookie)\s*[:=]\s*(?!\s*{MASKED_VALUE})[^\r\n]+"
    )),
    ("AccountKey", re.compile(
        rf"(?i)\bAccountKey\s*=\s*(?!{MASKED_VALUE})[^;\s,|]+"
    )),
)
DEMO_PASSWORDS = ("secret_sauce", "SuperSecretPassword!", "admin123", "Pa55word")
PASSWORD_VALUE = re.compile(r"(?i)\b(?:password|passwd|pwd|pass)\s*[:=]\s*(\"[^\"]*\"|'[^']*'|[^\s,;|]+)")
NOT_SECRET_VALUE = re.compile(rf"(?i)^(?:{MASKED_VALUE}|n/a|-+|—)$")


def exposed_password(segment: str) -> bool:
    """A labelled password value is flagged only when it is one word (no spaces)
    containing a digit or symbol, or a known demo password. Descriptive text such
    as "Password: The normal password from the login page" is not flagged."""
    demo = {password.casefold() for password in DEMO_PASSWORDS}
    for match in PASSWORD_VALUE.finditer(segment):
        value = match.group(1).strip("\"'").rstrip(".,;:)")
        if not value or " " in value or NOT_SECRET_VALUE.match(value):
            continue
        if value.casefold() in demo or re.search(r"[^A-Za-z]", value):
            return True
    return False


SENSITIVE_CAPTION = "⚠ Contains sensitive data ({}) – share only with authorised people."
IMAGE_SIGNATURES = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"BM")
MAX_IMAGE_WIDTH = Cm(15)


def is_readable_image(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            head = handle.read(16)
    except OSError:
        return False
    return any(head.startswith(signature) for signature in IMAGE_SIGNATURES)
SEVERITIES = ("1 – Critical", "2 – High", "3 – Medium", "4 – Low", "To be assessed")
PRIORITIES = ("1", "2", "3", "4", "To be set by the team")
CRITICAL_FLAGS = ("Yes", "No", "To be assessed")
SECTION_ORDER = (
    "Defect summary",
    "Environment",
    "Test data used",
    "Preconditions",
    "Steps to reproduce",
    "Expected and actual result",
    "Evidence",
    "Likely cause (hypothesis)",
    "Suggested investigation",
    "Classification suggestions",
    "Missing information",
)
HEADER_FILL = "D9EAF7"
SEVERITY_COLORS = {
    "1 – Critical": ("C00000", "FFFFFF"),
    "2 – High": ("ED7D31", "FFFFFF"),
    "3 – Medium": ("FFC000", "000000"),
    "4 – Low": ("A6A6A6", "000000"),
    "To be assessed": ("DDEBF7", "000000"),
}


def parse_document(text: str) -> tuple[str, dict[str, list[str]]]:
    title = ""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("TITLE:"):
            title = line.partition(":")[2].strip()
            current = None
        elif line.startswith("== "):
            current = line[3:].strip()
            sections.setdefault(current, [])
        elif current is not None and line:
            sections[current].append(line)
    return title, sections


def section_key(name: str) -> str:
    return re.sub(r"\s*\(optional(?:;[^)]*)?\)\s*$", "", name, flags=re.I).strip()


def field_values(lines: list[str]) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for line in lines:
        key, separator, value = line.partition(":")
        if separator:
            fields.setdefault(key.strip().upper(), []).append(value.strip())
    return fields


def first_field(fields: dict[str, list[str]], name: str) -> str:
    values = fields.get(name, [])
    return values[0] if values else ""


def check_secrets(text: str) -> list[str]:
    """Check each line, and each '|'-separated table cell, on its own; cells are
    never joined into 'Label: value'."""
    problems: list[str] = []

    def add(problem: str) -> None:
        if problem not in problems:
            problems.append(problem)

    for line in text.splitlines():
        for segment in (cell.strip() for cell in line.split("|")):
            if not segment:
                continue
            if EMAIL.search(segment):
                add("contains an unmasked email address")
            if exposed_password(segment):
                add("contains an unmasked password")
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(segment):
                    add(f"contains an unmasked {label}")
            lowered = segment.casefold()
            for password in DEMO_PASSWORDS:
                if password.casefold() in lowered:
                    add(f"contains the unmasked demo password {password}")
    return problems


def sensitive_label(extra: str) -> tuple[bool, str]:
    """Parse the text after '|' on an image line. Only 'SENSITIVE: <what>' counts;
    any other caption text is ignored."""
    label, separator, what = extra.partition(":")
    if separator and label.strip().upper() == "SENSITIVE":
        return True, what.strip()
    return False, ""


def validate_uc1(text: str) -> tuple[str, dict[str, list[str]], list[str]]:
    title, raw_sections = parse_document(text)
    normalized = {section_key(name): lines for name, lines in raw_sections.items()}
    problems: list[str] = []
    if not title:
        problems.append("TITLE is missing or empty")
    elif ENVIRONMENT_WORDS.search(title):
        problems.append("TITLE must not contain SIT, UAT, staging, or production")

    for name in UC1_REQUIRED_SECTIONS:
        if name not in normalized:
            problems.append(f"required section is missing: {name}")

    # LOG: lines quote evidence verbatim (XML, HTML, generics), so they are not
    # checked for template placeholders.
    non_log_text = "\n".join(
        line for line in text.splitlines() if not line.lstrip().upper().startswith("LOG:")
    )
    if re.search(r"<(?!/?[A-Za-z][\w:-]*\s+[\w:-]+\s*=)[^>\r\n]+>", non_log_text):
        problems.append("contains leftover <placeholder> text")

    fields: dict[str, list[str]] = {}
    for name in ("Defect summary", "Environment", "Evidence", "Classification"):
        fields.update(field_values(normalized.get(name, [])))
    for required in ("WHAT_IS_BROKEN", "IMPACT", "WHERE_TO_LOOK", "COMPONENT", "REPRODUCIBILITY"):
        if not first_field(fields, required):
            problems.append(f"required field is missing or empty: {required}")
    if first_field(fields, "REPRODUCIBILITY") and first_field(fields, "REPRODUCIBILITY") not in (
        "Always", "Intermittent", "Once", "Unknown"
    ):
        problems.append("REPRODUCIBILITY must be Always, Intermittent, Once, or Unknown")

    severity = first_field(fields, "SEVERITY").partition("|")[0].strip()
    priority = first_field(fields, "PRIORITY").partition("|")[0].strip()
    critical = first_field(fields, "CRITICAL_FLAG").partition("|")[0].strip()
    if severity not in SEVERITIES:
        problems.append("SEVERITY must use one of the allowed values")
    if priority not in PRIORITIES:
        problems.append("PRIORITY must use one of the allowed values")
    if severity in SEVERITIES[:4] and priority == "To be set by the team":
        problems.append("PRIORITY must be 1, 2, 3, or 4 when SEVERITY is 1–4")
    if critical not in CRITICAL_FLAGS:
        problems.append("CRITICAL_FLAG must use one of the allowed values")
    if severity in SEVERITIES and critical in CRITICAL_FLAGS:
        if (severity == "1 – Critical") != (critical == "Yes"):
            problems.append("CRITICAL_FLAG must be Yes if and only if SEVERITY is 1 – Critical")

    evidence_fields = field_values(normalized.get("Evidence", []))
    logs = evidence_fields.get("LOG", [])
    if len(logs) > 10:
        problems.append("Evidence may contain at most 10 LOG lines")
    for value in evidence_fields.get("EMBED_IMAGE", []) + evidence_fields.get("IMAGE", []):
        is_sensitive, what = sensitive_label(value.partition("|")[2])
        if is_sensitive and not what:
            problems.append(f"EMBED_IMAGE SENSITIVE: must say what is visible: {value}")
    missing_lines = normalized.get("Missing information", [])
    missing_items = [line for line in missing_lines if line.casefold() != "none"]
    if len(missing_items) > 3:
        problems.append("Missing information may contain at most 3 items")

    problems.extend(check_secrets(text))
    return title, normalized, problems


def shade_cell(cell, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:fill"), fill)


def set_cell_text(cell, text: str, *, bold: bool = False, color: str | None = None, size: int = 10) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def set_repeat_table_header(row) -> None:
    properties = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    properties.append(repeat)


def add_table(document: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    set_repeat_table_header(table.rows[0])
    for cell, header in zip(table.rows[0].cells, headers):
        shade_cell(cell, HEADER_FILL)
        set_cell_text(cell, header, bold=True)
    for row in rows:
        cells = table.add_row().cells
        for index, cell in enumerate(cells):
            set_cell_text(cell, row[index] if index < len(row) else "")


def add_text_lines(document: Document, lines: list[str], style: str | None = None) -> None:
    for line in lines:
        if line:
            document.add_paragraph(line, style=style)


def add_report_styles(document: Document) -> None:
    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    for name in ("Title", "Heading 1"):
        document.styles[name].font.name = "Calibri"
    if "Report Log" not in document.styles:
        log_style = document.styles.add_style("Report Log", WD_STYLE_TYPE.PARAGRAPH)
    else:
        log_style = document.styles["Report Log"]
    log_style.font.name = "Consolas"
    log_style.font.size = Pt(9)
    if "Report Message" not in document.styles:
        message_style = document.styles.add_style("Report Message", WD_STYLE_TYPE.PARAGRAPH)
    else:
        message_style = document.styles["Report Message"]
    message_style.font.name = "Calibri"
    message_style.font.size = Pt(11)
    message_style.font.italic = True
    message_style.paragraph_format.left_indent = Inches(0.25)


def add_shaded_paragraph(paragraph, fill: str) -> None:
    properties = paragraph._p.get_or_add_pPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    properties.append(shading)


def add_title(document: Document, title: str) -> None:
    document.add_paragraph(title, style="Title")


def add_quick_view(document: Document, fields: dict[str, list[str]]) -> None:
    table = document.add_table(rows=1, cols=1)
    cell = table.cell(0, 0)
    shade_cell(cell, "EAF2F8")
    cell.text = ""
    for index, (label, name) in enumerate((
        ("Quick view", None),
        ("What is broken", "WHAT_IS_BROKEN"),
        ("Impact", "IMPACT"),
        ("Where to look", "WHERE_TO_LOOK"),
    )):
        paragraph = cell.paragraphs[0] if index == 0 else cell.add_paragraph()
        if name is None:
            run = paragraph.add_run(label)
            run.bold = True
        else:
            run = paragraph.add_run(f"{label}: ")
            run.bold = True
            paragraph.add_run(first_field(fields, name))


def add_uc1_section(document: Document, heading: str, lines: list[str]) -> None:
    document.add_heading(heading, level=1)
    add_text_lines(document, lines)


def embed_image(document: Document, image_path: Path, sensitive: str) -> None:
    """Embed the original image bytes unchanged, at most 15 cm wide, captioned with
    its file name and, when `sensitive` names what is visible, the fixed warning."""
    width = None
    if is_readable_image(image_path):
        try:
            width = min(DocxImage.from_file(str(image_path)).width, MAX_IMAGE_WIDTH)
        except Exception:  # python-docx raises several types for corrupt image data
            width = None
    if width is None:
        document.add_paragraph(f"{image_path.name} – could not be read")
        return
    document.add_picture(str(image_path), width=width)
    caption = document.add_paragraph()
    name_run = caption.add_run(image_path.name)
    name_run.italic = True
    if sensitive:
        name_run.add_break()
        warning_run = caption.add_run(SENSITIVE_CAPTION.format(sensitive))
        warning_run.bold = True
        warning_run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)


def is_undetermined_cause(text: str) -> bool:
    value = re.sub(r"[.!?]+$", "", text).strip().casefold()
    value = re.sub(
        r"^(?:(?:the\s+)?(?:hypothesis|likely cause|cause)\s*[:—-]?\s*(?:is\s+)?)",
        "",
        value,
    )
    return bool(re.fullmatch(
        r"(?:not determined|unknown|undetermined|none|n/?a|not provided|not applicable|"
        r"no (?:likely )?cause (?:is )?(?:known|identified|determined)|"
        r"cause (?:is )?(?:unknown|not determined|undetermined|not identified)|"
        r"cannot (?:be )?determined)"
        r"(?:\s+(?:at this time|currently|from the available evidence|based on the available evidence))?",
        value,
    ))


def uc1_render(document: Document, title: str, sections: dict[str, list[str]]) -> None:
    all_fields: dict[str, list[str]] = {}
    for name in ("Defect summary", "Environment", "Evidence", "Classification"):
        all_fields.update(field_values(sections.get(name, [])))

    add_title(document, title)
    add_quick_view(document, all_fields)

    add_uc1_section(document, "Defect summary", [
        line for line in sections.get("Defect summary", [])
        if not line.upper().startswith(("WHAT_IS_BROKEN:", "IMPACT:", "WHERE_TO_LOOK:"))
    ])
    document.add_heading("Environment", level=1)
    for label, field_name in (("Component", "COMPONENT"), ("Reproducibility", "REPRODUCIBILITY")):
        paragraph = document.add_paragraph()
        paragraph.add_run(f"{label}: ").bold = True
        paragraph.add_run(first_field(all_fields, field_name))
    add_text_lines(document, [
        line for line in sections.get("Environment", [])
        if not line.upper().startswith(("COMPONENT:", "REPRODUCIBILITY:"))
    ])

    document.add_heading("Test data used", level=1)
    test_rows = []
    for line in sections.get("Test data used", []):
        if "|" in line:
            left, _, right = line.partition("|")
            test_rows.append([left.strip(), right.strip()])
        else:
            test_rows.append([line, ""])
    add_table(document, ["Item", "Value"], test_rows)

    preconditions = sections.get("Preconditions", [])
    if preconditions:
        add_uc1_section(document, "Preconditions", preconditions)

    document.add_heading("Steps to reproduce", level=1)
    for step in sections.get("Steps to reproduce", []):
        cleaned = re.sub(r"^(?:[-*]\s*|\d+[.)]\s*)", "", step)
        document.add_paragraph(cleaned, style="List Number")

    document.add_heading("Expected and actual result", level=1)
    expected = "\n".join(sections.get("Expected result", []))
    actual = "\n".join(sections.get("Actual result", []))
    result_table = document.add_table(rows=1, cols=2)
    result_table.style = "Table Grid"
    for cell, label, fill in zip(result_table.rows[0].cells, ("Expected", "Actual"), ("548235", "C00000")):
        shade_cell(cell, fill)
        set_cell_text(cell, label, bold=True, color="FFFFFF")
    row = result_table.add_row().cells
    set_cell_text(row[0], expected)
    set_cell_text(row[1], actual)

    document.add_heading("Evidence", level=1)
    evidence = field_values(sections.get("Evidence", []))
    source = first_field(evidence, "SOURCE")
    document.add_paragraph(f"Source: {source or 'None'}")
    logs = evidence.get("LOG", [])
    if logs:
        for line in logs:
            paragraph = document.add_paragraph(style="Report Log")
            paragraph.add_run(line)
            add_shaded_paragraph(paragraph, "F2F2F2")
    else:
        document.add_paragraph("No logs provided.")
    for message in evidence.get("UI_MESSAGE", []):
        if message and message.casefold() not in ("none", "n/a"):
            document.add_paragraph(message, style="Report Message")
    trim_note = first_field(evidence, "TRIM_NOTE")
    if trim_note:
        paragraph = document.add_paragraph(trim_note)
        for run in paragraph.runs:
            run.italic = True
    attachment = first_field(evidence, "ATTACH")
    document.add_paragraph(f"Screenshots/files to attach: {attachment or 'None'}")
    # EMBED_IMAGE: <path> | SENSITIVE: <what is visible>. IMAGE: is accepted as an older alias.
    for value in evidence.get("EMBED_IMAGE", []) + evidence.get("IMAGE", []):
        path_text, _, extra = value.partition("|")
        embed_image(document, Path(path_text.strip().strip('"')), sensitive_label(extra)[1])

    cause = sections.get("Likely cause (hypothesis)", [])
    cause_text = " ".join(cause).strip()
    if cause_text and not is_undetermined_cause(cause_text):
        document.add_heading("Likely cause (hypothesis)", level=1)
        paragraph = document.add_paragraph()
        label = paragraph.add_run("Hypothesis — not confirmed: ")
        label.italic = True
        label.font.color.rgb = RGBColor.from_string("666666")
        text = paragraph.add_run(cause_text)
        text.italic = True
        text.font.color.rgb = RGBColor.from_string("666666")

    investigation = sections.get("Suggested investigation", [])
    if investigation:
        document.add_heading("Suggested investigation", level=1)
        add_text_lines(document, investigation, style="List Bullet")

    document.add_heading("Classification suggestions", level=1)
    classification = field_values(sections.get("Classification", []))
    classification_rows = []
    for label, key in (("Severity", "SEVERITY"), ("Priority", "PRIORITY"), ("Critical flag", "CRITICAL_FLAG")):
        raw = first_field(classification, key)
        suggestion, separator, reason = raw.partition("|")
        classification_rows.append([label, suggestion.strip(), reason.strip() if separator else ""])
    add_table(document, ["Field", "Suggestion", "Reason"], classification_rows)
    severity = classification_rows[0][1]
    severity_cell = document.tables[-1].rows[1].cells[1]
    fill, text_color = SEVERITY_COLORS.get(severity, ("DDEBF7", "000000"))
    shade_cell(severity_cell, fill)
    for paragraph in severity_cell.paragraphs:
        for run in paragraph.runs:
            run.font.color.rgb = RGBColor.from_string(text_color)

    document.add_heading("Missing information", level=1)
    missing = sections.get("Missing information", [])
    questions = [line for line in missing if line.casefold() != "none"]
    if questions:
        for question in questions:
            document.add_paragraph(f"☐ {question}")
    else:
        document.add_paragraph("None")


UC3_SEVERITY_HEADER = ["severity", "count", "defects"]


def ensure_not_stated_row(rows: list[list[str]]) -> None:
    """uc3: the 'Severity | Count | Defects' table always has a 'Not stated' row."""
    if [cell.casefold() for cell in rows[0]] != UC3_SEVERITY_HEADER:
        return
    if not any(row and row[0].strip("*").strip().casefold() == "not stated" for row in rows[1:]):
        rows.append(["Not stated", "0", "None"])


def uc_generic_render(document: Document, title: str, text: str, kind: str = "uc2") -> None:
    add_title(document, title or "Report")
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line or line.startswith("TITLE:"):
            index += 1
            continue
        if line.startswith("== "):
            document.add_heading(line[3:].strip(), level=1)
            index += 1
            continue
        if line.startswith("- "):
            document.add_paragraph(line[2:].strip(), style="List Bullet")
            index += 1
            continue
        if "|" in line:
            rows: list[list[str]] = []
            while index < len(lines) and "|" in lines[index]:
                rows.append([part.strip() for part in lines[index].strip().strip("|").split("|")])
                index += 1
            if rows:
                if kind == "uc3":
                    ensure_not_stated_row(rows)
                add_table(document, rows[0], rows[1:])
            continue
        document.add_paragraph(line)
        index += 1


def add_footer(document: Document) -> None:
    for section in document.sections:
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        footer.add_run("Generated by bug-report-analyser · Reviewed by: ________ · Date: ________")


def create_document(out_path: Path, kind: str, text: str, title: str, sections: dict[str, list[str]]) -> None:
    document = Document()
    add_report_styles(document)
    for section in document.sections:
        section.page_width = Mm(210)
        section.page_height = Mm(297)
    if kind == "uc1":
        uc1_render(document, title, sections)
    else:
        uc_generic_render(document, title, text, kind)
    add_footer(document)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(out_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", required=True, choices=("uc1", "uc2", "uc3"))
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.out.suffix.casefold() != ".docx":
        print("Output path must end in .docx", file=sys.stderr)
        return 2
    text = sys.stdin.read()
    if args.type == "uc1":
        title, sections, problems = validate_uc1(text)
    else:
        title, sections = parse_document(text)
        problems = check_secrets(text)
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1
    try:
        create_document(args.out, args.type, text, title, sections)
    except OSError as error:
        print(f"ERROR: could not save Word document: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
