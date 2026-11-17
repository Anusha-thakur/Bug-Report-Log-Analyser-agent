#!/usr/bin/env python3
"""Check QA reports against samples, expected outputs, and report conventions."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt, RGBColor

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
NOT_RUN = "NOT RUN"
NA = "–"
COLUMNS = ("Sections", "Title", "Values", "Secrets", "Evidence", "Questions", "Matches expected")
REQUIRED_SECTIONS = (
    "Defect summary",
    "Environment",
    "Test data used",
    "Steps to reproduce",
    "Expected and actual result",
    "Evidence",
    "Classification suggestions",
    "Missing information",
)
CANONICAL_SECTIONS = (
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
SECTION_ALIASES = {
    "likely cause": "likely cause (hypothesis)",
    "preconditions (if any)": "preconditions",
}
EMAIL_RE = re.compile(
    r"(?i)\b[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+\b"
)
URL_RE = re.compile(r"(?i)\bhttps?://[^\s<>;,\])}]+")
NUMBER_RE = re.compile(r"\b\d{3,}\b")
VERSION_RE = re.compile(r"(?i)\bv?\d+(?:\.\d+){1,}\b")
ID_RE = re.compile(r"\b[A-Z]{1,8}[-_][A-Z0-9_-]*\d{2,}[A-Z0-9_-]*\b", re.I)
LOG_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}")
LOG_ERROR_RE = re.compile(
    r"(?i)^\s*(?:\[[^\]]+\]\s*)?(?:(?:INFO|DEBUG|TRACE|FATAL)\s+)?"
    r"(?:ERROR\b|WARN\b|Exception\b|Uncaught\b|TypeError\b|Error:)"
)
LOG_HTTP_RE = re.compile(
    r"(?i)^\s*(?:HTTP/\d(?:\.\d)?\s+\d{3}\b|"
    r"(?:GET|POST|PUT|DELETE)\s+(?:https?://\S+|/\S+|\d{3}\b)|"
    r"status(?:code)?\s*[:=]\s*\d{3}\b)"
)
LOG_EXCEPTION_RE = re.compile(r"(?i)^\s*(?:Traceback\b|Caused by:)")
LOG_LABEL_RE = re.compile(
    r"(?i)^\s*(?:(?:console|network|log|selenium\s+log)\s*:|devtools\b\s*:?)"
)
TRIM_NOTE_RE = re.compile(r"(?i)Log trimmed from \d+ to \d+ lines by log-trimmer\.")


@dataclass
class Result:
    report: str
    kind: str
    statuses: dict[str, str] = field(default_factory=dict)
    details: list[tuple[str, str]] = field(default_factory=list)

    def set(self, column: str, status: str, reason: str | None = None) -> None:
        previous = self.statuses.get(column, NA)
        rank = {NA: -1, PASS: 0, WARN: 1, FAIL: 2}
        if rank.get(status, -1) > rank.get(previous, -1):
            self.statuses[column] = status
        elif previous == NA and status == PASS:
            self.statuses[column] = PASS
        if reason:
            self.details.append((status, reason))

    def overall(self) -> str:
        if any(level == NOT_RUN for level, _ in self.details):
            return NOT_RUN
        states = self.statuses.values()
        if FAIL in states:
            return FAIL
        if WARN in states:
            return WARN
        return PASS


def normalized_heading(value: str) -> str:
    value = value.strip().casefold()
    return SECTION_ALIASES.get(value, value)


def sections(text: str) -> tuple[list[tuple[str, int, str]], dict[str, str]]:
    found: list[tuple[str, int, str]] = []
    bodies: dict[str, str] = {}
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", text))
    for number, match in enumerate(matches):
        raw_name = match.group(1).strip()
        name = normalized_heading(raw_name)
        found.append((name, match.start(), raw_name))
        end = matches[number + 1].start() if number + 1 < len(matches) else len(text)
        bodies[name] = text[match.end():end]
    return found, bodies


def section_body(bodies: dict[str, str], name: str) -> str:
    return bodies.get(normalized_heading(name), "")


def markdown_row(text: str, field_name: str) -> str | None:
    pattern = re.compile(rf"(?im)^\s*\|\s*{re.escape(field_name)}\s*\|\s*([^|]*)\|")
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def parse_severity(text: str | None) -> str | None:
    if not text:
        return None
    value = re.sub(r"\*", "", text).strip()
    if re.match(r"(?i)^to\s+be\s+assessed\b", value):
        return "to be assessed"
    match = re.match(r"(?i)^([1-4])\s*[-–]\s*(critical|high|medium|low)\b", value)
    if match:
        return f"{match.group(1)} {match.group(2).casefold()}"
    return None


def parse_priority(text: str | None) -> str | None:
    if not text:
        return None
    value = re.sub(r"\*", "", text).strip().casefold()
    if re.match(r"to\s+be\s+set\s+by\s+the\s+team\b", value):
        return "to be set by the team"
    if re.match(r"to\s+be\s+assessed\b", value):
        return "to be assessed"
    match = re.match(r"([1-4])\b", value)
    return match.group(1) if match else None


def parse_critical(text: str | None) -> str | None:
    if not text:
        return None
    value = re.sub(r"\*", "", text).strip().casefold()
    match = re.match(r"(yes|no|to\s+be\s+assessed)\b", value)
    return re.sub(r"\s+", " ", match.group(1)) if match else None


# Placeholder values that are not secrets (e.g. "Password: Not provided").
NOT_A_SECRET = r"(?!\[MASKED\]|not\s+provided\b|unknown\b|none\b)"
DEMO_PASSWORDS = ("secret_sauce", "SuperSecretPassword!", "admin123", "Pa55word")
PASSWORD_VALUE = re.compile(r"(?i)\b(?:password|passwd|pwd|pass)\s*[:=]\s*(\"[^\"]*\"|'[^']*'|[^\s,;|]+)")
NOT_SECRET_VALUE = re.compile(r"(?i)^(?:\[MASKED\]|<MASKED>|REDACTED|\*{2,}|n/a|-+|—)$")


def exposed_password(text: str) -> bool:
    """A labelled password value is flagged only when it is one word (no spaces)
    containing a digit or symbol, or a known demo password. Descriptive text such
    as "Password: The normal password from the login page" is not flagged."""
    demo = {password.casefold() for password in DEMO_PASSWORDS}
    for match in PASSWORD_VALUE.finditer(text):
        value = match.group(1).strip("\"'").rstrip(".,;:)")
        if not value or " " in value or NOT_SECRET_VALUE.match(value):
            continue
        if value.casefold() in demo or re.search(r"[^A-Za-z]", value):
            return True
    return False


def has_unmasked_secret(text: str) -> bool:
    if exposed_password(text):
        return True
    patterns = (
        EMAIL_RE,
        re.compile(rf"(?i)\bsecret\s*[:=|]\s*{NOT_A_SECRET}(?:\"[^\"]+\"|'[^']+'|[^\s,;|]+)"),
        re.compile(rf"(?i)\bAccountKey\s*[:=|]\s*{NOT_A_SECRET}(?:\"[^\"]+\"|'[^']+'|[^\s;|]+)"),
        re.compile(rf"(?i)\bBearer\s+{NOT_A_SECRET}[A-Za-z0-9._-]{{20,}}"),
        re.compile(r"(?i)\b(?:secret_sauce|SuperSecretPassword!|admin123|Pa55word)\b"),
    )
    if any(pattern.search(text) for pattern in patterns):
        return True
    for line in text.splitlines():
        cookie = re.search(r"(?i)\b(?:Cookie|Set-Cookie)\s*(?::|=|\|)\s*(.*)$", line)
        if not cookie:
            continue
        value = cookie.group(1).strip()
        if value and "[MASKED]" not in value and re.match(rf"(?i){NOT_A_SECRET}", value):
            return True
    return False


def table_secret_segments(table) -> list[str]:
    """Each cell on its own. Cells are never joined into 'Label: value', so
    descriptive text in a value cell is not read as a labelled secret."""
    segments: list[str] = []
    for row in table.rows:
        segments.extend(cell.text.strip() for cell in row.cells)
        for cell in row.cells:
            for nested in cell.tables:
                segments.extend(table_secret_segments(nested))
    return segments


def document_has_unmasked_secret(document: Document) -> bool:
    segments = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        segments.extend(table_secret_segments(table))
    for section in document.sections:
        for part in (section.header, section.footer):
            segments.extend(paragraph.text for paragraph in part.paragraphs)
            for table in part.tables:
                segments.extend(table_secret_segments(table))
    return any(has_unmasked_secret(segment) for segment in segments if segment.strip())


def log_lines_present(sample: str) -> bool:
    awaiting_labeled_line = False
    for line in sample.splitlines():
        if not line.strip():
            continue
        if awaiting_labeled_line:
            return True
        if (
            LOG_TIMESTAMP_RE.search(line)
            or LOG_ERROR_RE.search(line)
            or LOG_HTTP_RE.search(line)
            or LOG_EXCEPTION_RE.search(line)
        ):
            return True
        label = LOG_LABEL_RE.match(line)
        if label:
            if line[label.end():].strip():
                return True
            awaiting_labeled_line = True
    return False


def table_rows_text(table) -> list[str]:
    rows = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        rows.append(" | ".join(cells))
        for cell in row.cells:
            for nested in cell.tables:
                rows.extend(table_rows_text(nested))
    return rows


def document_text(
    document: Document,
    *,
    ignore_evidence_trim_notes: bool = False,
    skip_investigation: bool = False,
) -> str:
    lines = []
    in_evidence = False
    in_investigation = False
    for paragraph in document.paragraphs:
        if paragraph.style.name == "Heading 1":
            in_evidence = normalized_heading(paragraph.text) == "evidence"
            in_investigation = normalized_heading(paragraph.text) == normalized_heading("Suggested investigation")
        elif skip_investigation and in_investigation:
            # Suggested checks are hypothetical, not observed facts.
            continue
        text = paragraph.text
        if ignore_evidence_trim_notes:
            # Drop only the trim-note phrase (its X/Y line counts), wherever it
            # appears; any other text on the same line is still scanned.
            text = TRIM_NOTE_RE.sub("", text)
            if not text.strip():
                continue
        lines.append(text)
    for table in document.tables:
        lines.extend(table_rows_text(table))
    for section in document.sections:
        lines.extend(paragraph.text for paragraph in section.header.paragraphs)
        for table in section.header.tables:
            lines.extend(table_rows_text(table))
        lines.extend(paragraph.text for paragraph in section.footer.paragraphs)
        for table in section.footer.tables:
            lines.extend(table_rows_text(table))
    return "\n".join(lines)


def document_headings(document: Document) -> list[str]:
    return [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.style.name == "Heading 1" and paragraph.text.strip()
    ]


def paragraphs_after_heading(document: Document, heading_name: str):
    found = False
    for paragraph in document.paragraphs:
        if paragraph.style.name == "Heading 1":
            if found:
                break
            found = normalized_heading(paragraph.text) == normalized_heading(heading_name)
            continue
        if found:
            yield paragraph


def classification_values(document: Document) -> dict[str, str] | None:
    for table in document.tables:
        if not table.rows:
            continue
        header = [cell.text.strip().casefold() for cell in table.rows[0].cells]
        if header != ["field", "suggestion", "reason"]:
            continue
        values = {}
        for row in table.rows[1:]:
            if len(row.cells) >= 2:
                values[row.cells[0].text.strip().casefold()] = row.cells[1].text.strip()
        return values
    return None


UC3_SEVERITY_ROWS = ("critical", "high", "medium", "low", "not stated")


def docx_severity_counts(document: Document) -> dict[str, int] | None:
    """Read counts from the Word table whose header row is 'Severity | Count | Defects'."""
    for table in document.tables:
        if not table.rows:
            continue
        header = [cell.text.strip().casefold() for cell in table.rows[0].cells]
        if header != ["severity", "count", "defects"]:
            continue
        counts: dict[str, int] = {}
        for row in table.rows[1:]:
            if len(row.cells) < 2:
                continue
            name = row.cells[0].text.strip().strip("*").casefold()
            if name not in UC3_SEVERITY_ROWS:
                continue
            match = re.match(r"\s*(\d+)\b", row.cells[1].text)
            if match:
                counts[name] = counts.get(name, 0) + int(match.group(1))
        return counts
    return None


def extract_severity_values(text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    lines = text.splitlines()
    header_index = None
    count_index = None
    for index, line in enumerate(lines):
        if not re.search(r"(?i)\|\s*Severity\s*\|", line):
            continue
        cells = [cell.strip().casefold() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] != "severity":
            continue
        header_index = index
        preferred = next(
            (i for i, cell in enumerate(cells) if "unique defect" in cell),
            None,
        )
        if preferred is None:
            preferred = next((i for i, cell in enumerate(cells) if "count" in cell), None)
        count_index = preferred
        break
    if header_index is not None:
        for line in lines[header_index + 1:]:
            cells = [cell.strip().strip("*").casefold() for cell in line.strip().strip("|").split("|")]
            if not cells or cells[0] not in UC3_SEVERITY_ROWS:
                continue
            indices = [count_index] if count_index is not None else range(1, len(cells))
            numbers = [
                int(match.group(0))
                for i in indices
                if i is not None and i < len(cells)
                for match in [re.match(r"\s*(\d+)\b", cells[i])]
                if match
            ]
            if numbers:
                values[cells[0]] = values.get(cells[0], 0) + numbers[0]
    if values:
        return values
    for line in lines:
        table = re.match(r"\s*\|\s*(Critical|High|Medium|Low)\s*\|\s*(\d+)\b", line, re.I)
        if table:
            severity = table.group(1).casefold()
            values[severity] = values.get(severity, 0) + int(table.group(2))
    if values:
        return values
    for match in re.finditer(r"(?i)\b(\d+)\s+(Critical|High|Medium|Low)\b", text):
        values.setdefault(match.group(2).casefold(), int(match.group(1)))
    return values


def duplicate_pairs(text: str) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    patterns = (
        (re.compile(r"(?i)^\s*\|\s*([A-Z0-9]+)\s*\|[^\n]{0,250}?\bduplicate of\s+(?:Report\s+)?([A-Z0-9]+)\b"), False),
        (re.compile(r"(?i)\bReport\s+([A-Z0-9]+)\b[^\n.]{0,120}?\bduplicate of\s+(?:Report\s+)?([A-Z0-9]+)\b"), False),
        (re.compile(r"(?i)\bReports?\s+([A-Z0-9]+)\s+and\s+([A-Z0-9]+)\b[^\n.]{0,100}\bduplicates?\b"), True),
        (re.compile(r"(?i)\b(?:likely\s+|potential\s+|exact\s+)?duplicates?\b[^\n.]{0,100}\bReports?\s+([A-Z0-9]+)\s+and\s+([A-Z0-9]+)\b"), True),
    )
    for line in text.splitlines():
        for pattern, pair_lists_duplicate_first in patterns:
            match = pattern.search(line)
            if match:
                first, second = match.group(1).upper(), match.group(2).upper()
                if pair_lists_duplicate_first:
                    pairs.add((second, first))
                else:
                    pairs.add((first, second))
    return pairs


def possible_inventions(report: str, sample: str) -> list[str]:
    candidates: set[str] = set()
    for pattern in (URL_RE, VERSION_RE, ID_RE, NUMBER_RE):
        for match in pattern.finditer(report):
            value = match.group(0).rstrip(".,;:)`")
            if value and value.casefold() not in sample.casefold():
                candidates.add(value)
    return sorted(candidates, key=str.casefold)


def question_count(text: str) -> int:
    cleaned = text.strip()
    if not cleaned or (re.search(r"(?i)\bnone\b", cleaned) and "?" not in cleaned):
        return 0
    items = re.findall(r"(?m)^\s*(?:[-*+]\s+|\d+[.)]\s+).+", cleaned)
    return max(len(items), cleaned.count("?"))


def check_uc1(
    result: Result,
    document: Document,
    sample_text: str | None,
    expected_text: str | None,
    scenario_attachments: bool = False,
    scenario_has_images: bool = False,
) -> None:
    headings = document_headings(document)
    names = [normalized_heading(name) for name in headings]
    required = [normalized_heading(name) for name in REQUIRED_SECTIONS]
    missing = [name for name in required if name not in names]
    canonical = [normalized_heading(name) for name in CANONICAL_SECTIONS]
    present_canonical = [name for name in names if name in canonical]
    expected_order = [name for name in canonical if name in names]
    order_ok = present_canonical == expected_order and len(names) == len(set(names))
    if missing or not order_ok:
        parts = []
        if missing:
            parts.append("missing required sections: " + ", ".join(missing))
        if not order_ok:
            parts.append("sections are out of order or duplicated")
        result.set("Sections", FAIL, "; ".join(parts))
    else:
        result.set("Sections", PASS)

    title_paragraph = next(
        (paragraph for paragraph in document.paragraphs if paragraph.style.name == "Title"),
        None,
    )
    title = title_paragraph.text.strip() if title_paragraph else ""
    if not title or re.search(r"(?i)\b(SIT|UAT|staging|production)\b", title):
        reasons = []
        if not title:
            reasons.append("report must contain a non-empty paragraph in the Title style")
        if re.search(r"(?i)\b(SIT|UAT|staging|production)\b", title):
            reasons.append("title contains an environment name")
        result.set("Title", FAIL, "; ".join(reasons))
    else:
        result.set("Title", PASS)

    classification = classification_values(document)
    severity_raw = classification.get("severity") if classification else None
    priority_raw = classification.get("priority") if classification else None
    critical_raw = classification.get("critical flag") if classification else None
    severity = parse_severity(severity_raw)
    priority = parse_priority(priority_raw)
    critical = parse_critical(critical_raw)
    value_errors = []
    if classification is None:
        value_errors.append("Classification suggestions table with Field | Suggestion | Reason header is missing")
    if severity is None:
        value_errors.append("Severity must be 1 – Critical, 2 – High, 3 – Medium, 4 – Low, or To be assessed")
    if priority is None or priority == "to be assessed":
        value_errors.append("Priority must be 1–4 or To be set by the team")
    if critical is None:
        value_errors.append("Critical flag must be Yes, No, or To be assessed")
    if critical == "yes" and not (severity and severity.startswith("1 ")):
        value_errors.append("Critical flag is Yes but severity is not 1 – Critical")
    if severity == "1 critical" and critical != "yes":
        value_errors.append("Severity is 1 – Critical but Critical flag is not Yes")
    if value_errors:
        result.set("Values", FAIL, "; ".join(value_errors))
    else:
        result.set("Values", PASS)

    for name in headings:
        normalized = normalized_heading(name)
        if normalized == "likely cause (hypothesis)" and "hypothesis" not in name.casefold():
            result.set("Sections", FAIL, "Likely cause heading must contain 'hypothesis'")

    if "missing information" not in names:
        result.set("Questions", FAIL, "Missing information section is absent")
    else:
        checklist = [
            paragraph.text.strip()
            for paragraph in paragraphs_after_heading(document, "Missing information")
            if paragraph.text.strip().startswith("☐")
        ]
        if len(checklist) > 3:
            result.set("Questions", FAIL, f"Missing information has {len(checklist)} checklist items; maximum is 3")
        else:
            result.set("Questions", PASS)

    if document_has_unmasked_secret(document):
        result.set("Secrets", FAIL, "report contains an unmasked email, credential, token, cookie, or demo password")
    else:
        result.set("Secrets", PASS)

    if sample_text is None:
        result.set("Evidence", NA)
        result.set("Values", WARN, "sample file not found; possible-invention scan not run")
    else:
        evidence_paragraphs = list(paragraphs_after_heading(document, "Evidence"))
        log_paragraphs = [
            paragraph for paragraph in document.paragraphs
            if paragraph.style.name == "Report Log"
        ]
        has_logs = log_lines_present(sample_text)
        if scenario_attachments:
            # Attachment scenarios: LOG lines may quote JSON fields, CSV rows,
            # XML, or console text transcribed from a screenshot, none of which
            # look like timestamped log lines. Accept 0–10 quoted lines.
            if len(log_paragraphs) > 10:
                result.set("Evidence", FAIL, f"Evidence has {len(log_paragraphs)} Report Log paragraphs; maximum is 10")
            else:
                result.set("Evidence", PASS)
        elif has_logs:
            if not 1 <= len(log_paragraphs) <= 10:
                result.set(
                    "Evidence",
                    FAIL,
                    f"sample contains log lines but Evidence has {len(log_paragraphs)} Report Log paragraphs; expected 1–10",
                )
            else:
                result.set("Evidence", PASS)
        elif log_paragraphs or not any(
            paragraph.text.strip().casefold() == "no logs provided."
            for paragraph in evidence_paragraphs
        ):
            result.set(
                "Evidence",
                FAIL,
                "sample has no log lines; Evidence must have no Report Log paragraphs and say 'No logs provided.'",
            )
        else:
            result.set("Evidence", PASS)

        invention_text = document_text(document, ignore_evidence_trim_notes=True, skip_investigation=True)
        inventions = possible_inventions(invention_text, sample_text)
        if scenario_has_images and expected_text:
            # Values transcribed from a screenshot are not in the scanned text;
            # accept those the answer key also records.
            expected_folded = expected_text.casefold()
            inventions = [value for value in inventions if value.casefold() not in expected_folded]
        if inventions:
            result.set("Values", WARN, "possible invented details not found in sample: " + ", ".join(inventions))

    if expected_text is None:
        result.set("Matches expected", NA)
    else:
        expected_values = sections(expected_text)[1].get("classification suggestions", "")
        expected_severity = parse_severity(markdown_row(expected_values, "Severity"))
        expected_critical = parse_critical(markdown_row(expected_values, "Critical flag"))
        expected_priority = parse_priority(markdown_row(expected_values, "Priority"))
        comparison_status = PASS
        if expected_severity and severity and expected_severity != severity:
            result.set("Matches expected", FAIL, f"Severity is {severity}, expected {expected_severity}")
            comparison_status = FAIL
        if expected_critical and critical and expected_critical != critical:
            result.set("Matches expected", FAIL, f"Critical flag is {critical}, expected {expected_critical}")
            comparison_status = FAIL
        if expected_priority and priority and expected_priority != priority:
            result.set("Matches expected", WARN, f"Priority is {priority}, expected {expected_priority}")
            if comparison_status != FAIL:
                comparison_status = WARN
        if comparison_status == PASS:
            result.set("Matches expected", PASS)


def check_uc2(result: Result, document: Document, report_text: str, expected_text: str | None) -> None:
    if re.search(r"(?i)\bduplicate\b", report_text):
        result.set("Sections", PASS)
    else:
        result.set("Sections", FAIL, "duplicate analysis does not use the word 'duplicate'")
    expected_pairs = duplicate_pairs(expected_text or "")
    report_pairs = duplicate_pairs(report_text)
    missing_pairs = sorted(expected_pairs - report_pairs)
    if missing_pairs:
        pretty = ", ".join(
            f"Report {duplicate} is not flagged as a duplicate of Report {original}"
            for duplicate, original in missing_pairs
        )
        result.set("Matches expected", FAIL, pretty)
    else:
        result.set("Matches expected", PASS)
    for column in ("Title", "Values", "Evidence", "Questions"):
        result.set(column, NA)
    if document_has_unmasked_secret(document):
        result.set("Secrets", FAIL, "report contains an unmasked email, credential, token, cookie, or demo password")
    else:
        result.set("Secrets", PASS)


def check_uc3(result: Result, document: Document, report_text: str, expected_text: str | None) -> None:
    for column in ("Sections", "Title", "Evidence", "Questions"):
        result.set(column, NA)
    if document_has_unmasked_secret(document):
        result.set("Secrets", FAIL, "report contains an unmasked email, credential, token, cookie, or demo password")
    else:
        result.set("Secrets", PASS)
    if expected_text is None:
        result.set("Matches expected", NA)
        result.set("Values", NA)
        return

    expected_counts = extract_severity_values(expected_text)
    if expected_counts:
        # An expected table without a "Not stated" row means 0 such items.
        expected_counts.setdefault("not stated", 0)
    report_counts = docx_severity_counts(document)
    differences = []
    if report_counts is None:
        differences.append("Severity | Count | Defects table not found")
        report_counts = {}
    for severity in UC3_SEVERITY_ROWS:
        if severity in expected_counts and report_counts.get(severity) != expected_counts[severity]:
            differences.append(
                f"{severity.capitalize()} count is {report_counts.get(severity, 'missing')}, expected {expected_counts[severity]}"
            )
    if differences:
        result.set("Values", WARN, "; ".join(differences))
    else:
        result.set("Values", PASS)
    if re.search(r"(?i)not\s+confirmed", expected_text) and not re.search(r"(?i)not\s+confirmed|unconfirmed", report_text):
        result.set("Matches expected", FAIL, "expected marks an item 'not confirmed' but report does not mark anything as unconfirmed")
    else:
        result.set("Matches expected", PASS)


SKILLS_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_FOLDERS = ("root", "attachments")
# Matches attachment-reader's image types; text in these cannot be scanned.
SCENARIO_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
IMAGE_FILE_SIGNATURES = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"BM")


def is_readable_image_data(data: bytes) -> bool:
    return data.startswith(IMAGE_FILE_SIGNATURES) or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")


def check_scenario_images(result: Result, document: Document, folder: Path, expected_text: str | None) -> None:
    """Every readable screenshot must be embedded byte-for-byte; ones the answer key
    marks as sensitive ("with warning") also need a sensitive-data caption."""
    embedded = {
        hashlib.sha1(rel.target_part.blob).hexdigest()
        for rel in document.part.rels.values()
        if not rel.is_external and rel.reltype.endswith("/image")
    }
    paragraphs = [paragraph.text.casefold() for paragraph in document.paragraphs]
    expected_lines = (expected_text or "").casefold().splitlines()
    for image in sorted(folder.iterdir()):
        if not image.is_file() or image.suffix.casefold() not in SCENARIO_IMAGE_SUFFIXES:
            continue
        data = image.read_bytes()
        if not is_readable_image_data(data):
            continue
        name = image.name.casefold()
        if hashlib.sha1(data).hexdigest() not in embedded:
            result.set("Evidence", FAIL, f"{image.name} is not embedded as the original, unmodified image")
            continue
        sensitive = any(name in line and "with warning" in line for line in expected_lines)
        if sensitive and not any(name in text and "contains sensitive data" in text for text in paragraphs):
            result.set("Evidence", FAIL, f"{image.name} shows sensitive data but has no sensitive-data warning caption")


def _load_skill_module(name: str, relative_path: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, SKILLS_ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scenario_folder_text(folder: Path) -> str:
    """Notes plus the masked text of every readable attachment in a scenario folder.

    Uses attachment-reader's extractor and secret-masker, so the invented-details
    scan compares the report against everything the agent could read.
    """
    import contextlib
    import io
    import tempfile

    extractor = _load_skill_module("extract_attachments", "attachment-reader/extract_attachments.py")
    masker = _load_skill_module("mask", "secret-masker/mask.py")
    parts: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        with contextlib.redirect_stdout(io.StringIO()):
            reader = extractor.Extractor(Path(tmp))
            for path in sorted(p for p in folder.iterdir() if p.is_file()):
                reader.handle(path.name, path)
        for text_file in sorted(Path(tmp).rglob("*.txt")):
            content = text_file.read_text(encoding="utf-8", errors="replace")
            parts.append(f"### {text_file.name}\n{masker.mask_text(content)}")
    return "\n".join(parts)


def supported_sample(sample_root: Path, relative_report: Path) -> Path | None:
    folder = sample_root / relative_report.parent
    scenario = folder / relative_report.name
    if scenario.is_dir():
        return scenario
    for suffix in (".txt", ".log", ".md"):
        candidate = folder / f"{relative_report.stem}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def build_result(report_path: Path, relative: Path, sample_root: Path, expected_root: Path) -> Result:
    if relative.name.startswith("uc1_"):
        kind = "UC1"
    elif relative.name.startswith("uc2_"):
        kind = "UC2"
    elif relative.name.startswith("uc3_"):
        kind = "UC3"
    else:
        kind = "UNKNOWN"
    result = Result(relative.with_suffix(".docx").as_posix(), kind, {column: NA for column in COLUMNS})
    if not report_path.is_file():
        result.details.append((NOT_RUN, "matching report is missing"))
        return result

    document = Document(report_path)
    report_text = document_text(document)
    sample_path = supported_sample(sample_root, relative)
    expected_path = expected_root / relative.parent / f"{relative.stem}.md"
    if sample_path is None:
        sample_text = None
    elif sample_path.is_dir():
        sample_text = scenario_folder_text(sample_path)
    else:
        sample_text = sample_path.read_text(encoding="utf-8-sig", errors="replace")
    expected_text = expected_path.read_text(encoding="utf-8-sig", errors="replace") if expected_path.is_file() else None

    if kind == "UC1":
        is_scenario = sample_path is not None and sample_path.is_dir()
        has_images = is_scenario and any(
            path.is_file() and path.suffix.casefold() in SCENARIO_IMAGE_SUFFIXES
            for path in sample_path.iterdir()
        )
        check_uc1(
            result, document, sample_text, expected_text,
            scenario_attachments=is_scenario, scenario_has_images=has_images,
        )
        if is_scenario:
            check_scenario_images(result, document, sample_path, expected_text)
    elif kind == "UC2":
        check_uc2(result, document, report_text, expected_text)
    elif kind == "UC3":
        check_uc3(result, document, report_text, expected_text)
    else:
        result.details.append((FAIL, "filename does not begin with uc1_, uc2_, or uc3_"))
        result.set("Sections", FAIL)
    if expected_text is None and kind in ("UC1", "UC2", "UC3"):
        result.details.append((WARN, "matching expected file is missing; expected-output comparison was limited"))
        if result.statuses.get("Matches expected") == NA:
            result.statuses["Matches expected"] = WARN
    return result


def list_sample_reports(sample_root: Path, only: tuple[str, ...] = SAMPLE_FOLDERS) -> list[Path]:
    """Sample files in samples/, plus one scenario folder per subfolder of
    samples/attachments/. `only` limits which of these are listed."""
    paths: list[Path] = []
    if "root" in only and sample_root.is_dir():
        paths.extend(sorted((path for path in sample_root.iterdir() if path.is_file()), key=lambda path: path.name.casefold()))
    attachments = sample_root / "attachments"
    if "attachments" in only and attachments.is_dir():
        paths.extend(sorted((path for path in attachments.iterdir() if path.is_dir()), key=lambda path: path.name.casefold()))
    return paths


def resolve_single_file(
    value: str,
    reports_root: Path,
    docx_root: Path,
) -> tuple[Path, Path]:
    supplied = Path(value)
    if supplied.is_file():
        report_path = supplied.resolve()
    else:
        if supplied.suffix.casefold() != ".docx":
            supplied = supplied.with_suffix(".docx")
        if supplied.is_absolute():
            report_path = supplied.resolve()
        elif supplied.parts and supplied.parts[0].casefold() == docx_root.name.casefold():
            report_path = (reports_root / supplied).resolve()
        elif supplied.parts and supplied.parts[0].casefold() == reports_root.name.casefold():
            report_path = (reports_root.parent / supplied).resolve()
        else:
            report_path = (docx_root / supplied).resolve()
    try:
        relative = report_path.relative_to(docx_root.resolve())
    except ValueError:
        relative = Path(report_path.name).with_suffix("")
    return report_path, relative


def shade_cell(cell, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:fill"), fill)


def report_document(results: list[Result], timestamp: str, reviewer_notes: str) -> tuple[Document, str]:
    counts = {PASS: 0, WARN: 0, FAIL: 0, NOT_RUN: 0}
    for result in results:
        counts[result.overall()] += 1
    summary = (
        f"Summary: {timestamp} | Total reports: {len(results)} | PASS: {counts[PASS]} | "
        f"WARN: {counts[WARN]} | FAIL: {counts[FAIL]} | NOT RUN: {counts[NOT_RUN]}"
    )
    document = Document()
    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    document.styles["Title"].font.name = "Calibri"
    document.styles["Title"].font.size = Pt(22)
    document.styles["Heading 1"].font.name = "Calibri"
    document.styles["Heading 1"].font.size = Pt(11)
    for section in document.sections:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Mm(297)
        section.page_height = Mm(210)
        section.left_margin = Inches(0.45)
        section.right_margin = Inches(0.45)
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)

    document.add_paragraph("Report check results", style="Title")
    document.add_paragraph(summary)

    headers = ("File", "Type", *COLUMNS, "Overall")
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.autofit = False
    header_row = table.rows[0]
    header_props = header_row._tr.get_or_add_trPr()
    repeat_header = OxmlElement("w:tblHeader")
    repeat_header.set(qn("w:val"), "true")
    header_props.append(repeat_header)
    for cell, header in zip(header_row.cells, headers):
        shade_cell(cell, "D9EAF7")
        cell.text = header
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.name = "Calibri"
                run.font.size = Pt(11)

    for result in results:
        cells = (
            [NA] * len(COLUMNS)
            if result.overall() == NOT_RUN
            else [result.statuses.get(column, NA) for column in COLUMNS]
        )
        row_values = (result.report, result.kind, *cells, result.overall())
        row = table.add_row()
        for cell, value in zip(row.cells, row_values):
            cell.text = value
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = "Calibri"
                    run.font.size = Pt(11)
            if value == PASS:
                shade_cell(cell, "70AD47")
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.color.rgb = RGBColor.from_string("FFFFFF")
            elif value == WARN:
                shade_cell(cell, "FFC000")
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.color.rgb = RGBColor.from_string("000000")
            elif value == FAIL:
                shade_cell(cell, "C00000")
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.color.rgb = RGBColor.from_string("FFFFFF")
            elif value == NOT_RUN:
                shade_cell(cell, "D9E1F2")

    widths = [Mm(48), Mm(14), *(Mm(25) for _ in COLUMNS), Mm(20)]
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = width

    document.add_heading("Details", level=1)
    details = [
        (result.report, level, reason)
        for result in results
        for level, reason in result.details
        if level in (FAIL, WARN, NOT_RUN)
    ]
    if details:
        for filename, level, reason in details:
            document.add_paragraph(f"{level} — {filename}: {reason}", style="List Bullet")
    else:
        document.add_paragraph("No failures or warnings.")

    document.add_heading("Reviewer notes", level=1)
    notes = reviewer_notes.strip()
    if notes:
        for line in notes.splitlines():
            document.add_paragraph(line)
    else:
        document.add_paragraph("No reviewer notes supplied.")
    return document, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", default="reports", type=Path)
    parser.add_argument("--samples", default="samples", type=Path)
    parser.add_argument("--expected", default="expected", type=Path)
    parser.add_argument(
        "--results",
        type=Path,
        help="write the results document to this path (default: <reports>/docx/test_results.docx)",
    )
    parser.add_argument("--file", help="check only this report")
    parser.add_argument(
        "--only",
        default=",".join(SAMPLE_FOLDERS),
        help="comma-separated sample folders to score: root, attachments (default: all)",
    )
    parser.add_argument(
        "--notes",
        action="store_true",
        help="read reviewer notes from standard input and include them in test_results.docx",
    )
    args = parser.parse_args()

    reports_root = args.reports.resolve()
    docx_root = reports_root / "docx"
    sample_root = args.samples.resolve()
    expected_root = args.expected.resolve()
    reviewer_notes = sys.stdin.read() if args.notes else ""
    if args.file:
        report_path, relative = resolve_single_file(args.file, reports_root, docx_root)
        results = [build_result(report_path, relative, sample_root, expected_root)]
    else:
        results = []
        only = tuple(part.strip().casefold() for part in args.only.split(",") if part.strip())
        unknown = [part for part in only if part not in SAMPLE_FOLDERS]
        if unknown:
            parser.error(f"--only accepts {', '.join(SAMPLE_FOLDERS)}; got {', '.join(unknown)}")
        for sample in list_sample_reports(sample_root, only):
            relative = sample.relative_to(sample_root)
            report_path = docx_root / relative.parent / f"{relative.stem}.docx"
            results.append(build_result(report_path, relative, sample_root, expected_root))

    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    document, summary = report_document(results, timestamp, reviewer_notes)
    output_path = (
        args.results.resolve()
        if args.results
        else docx_root / "test_results.docx"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)
    print(summary)
    return 1 if any(result.overall() == FAIL for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
