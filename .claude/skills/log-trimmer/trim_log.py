#!/usr/bin/env python3
"""Trim noisy logs around failures while preserving key evidence."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
FAILURE = re.compile(r"ERROR|FATAL|Exception|Traceback|failed", re.IGNORECASE)
IMPORTANT = re.compile(r"\b(?:ERROR|FATAL|WARN)\b", re.IGNORECASE)
SUMMARY = re.compile(r"\bSUMMARY\b|\bpassed\b|\bprocessed\b|\bwritten\b", re.IGNORECASE)
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def timestamp_for(line: str) -> datetime | None:
    match = TIMESTAMP.search(line)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(0), TIMESTAMP_FORMAT)
    except ValueError:
        return None


def is_continuation(line: str) -> bool:
    return (
        line.startswith((" ", "\t"))
        or line.startswith("at ")
        or line.startswith("--->")
        or line.startswith("Caused by")
    )


def top_notes(lines: list[str]) -> set[int]:
    notes: set[int] = set()
    for index, line in enumerate(lines):
        if TIMESTAMP.search(line):
            break
        notes.add(index)
    return notes


def select_lines(lines: list[str], context: int, window: float) -> tuple[set[int], int | None]:
    notes = top_notes(lines)
    failure_index = next(
        (index for index, line in enumerate(lines) if FAILURE.search(line)), None
    )

    if len(lines) <= 50:
        return set(range(len(lines))), failure_index

    if failure_index is None:
        selected = notes | {
            index for index, line in enumerate(lines)
            if re.search(r"\bWARN\b", line, re.IGNORECASE)
        }
        selected.update(range(max(0, len(lines) - 20), len(lines)))
    else:
        selected = set(notes)
        selected.update(
            index for index, line in enumerate(lines) if IMPORTANT.search(line)
        )
        selected.update(
            index for index, line in enumerate(lines) if SUMMARY.search(line)
        )
        selected.update(
            range(max(0, failure_index - context), min(len(lines), failure_index + context + 1))
        )

        failure_time = timestamp_for(lines[failure_index])
        if failure_time is not None:
            seconds = window * 60
            for index, line in enumerate(lines):
                if re.search(r"\b(?:WARN|ERROR|FATAL)\b", line, re.IGNORECASE):
                    line_time = timestamp_for(line)
                    if line_time and abs((line_time - failure_time).total_seconds()) <= seconds:
                        selected.add(index)

    # Keep indented stack frames and explicit continuation lines immediately
    # following any selected line, including chained continuation lines.
    pending = sorted(selected)
    visited: set[int] = set()
    while pending:
        index = pending.pop()
        if index in visited:
            continue
        visited.add(index)
        next_index = index + 1
        while next_index < len(lines) and is_continuation(lines[next_index]):
            if next_index not in selected:
                selected.add(next_index)
                pending.append(next_index)
            next_index += 1

    return selected, failure_index


def build_body(lines: list[str], selected: set[int], passthrough: bool) -> tuple[str, int]:
    if passthrough:
        return "".join(lines), len(lines)

    # Collapse identical selected lines globally, keeping the first occurrence
    # and annotating how many source occurrences it represents.
    counts: dict[str, int] = {}
    first_index: dict[str, int] = {}
    for index in sorted(selected):
        text = lines[index].rstrip("\r\n")
        counts[text] = counts.get(text, 0) + 1
        first_index.setdefault(text, index)

    records = sorted((index, text, counts[text]) for text, index in first_index.items())
    kept_count = len(records)
    output: list[str] = []
    previous_index = -1

    for index, text, count in records:
        removed = index - previous_index - 1
        if removed > 0:
            output.append(f"... [{removed} lines removed] ...\n")
        suffix = f" [repeated {count - 1} times]" if count > 1 else ""
        output.append(f"{text}{suffix}\n")
        previous_index = index

    trailing = len(lines) - previous_index - 1
    if trailing > 0:
        output.append(f"... [{trailing} lines removed] ...\n")
    return "".join(output), kept_count


def trim_file(input_path: Path, context: int, window: float) -> tuple[Path, int, int]:
    if context < 0 or window < 0:
        raise ValueError("--context and --window must be non-negative")

    source = input_path.resolve(strict=True)
    with source.open("r", encoding="utf-8", errors="replace", newline="") as input_file:
        lines = input_file.read().splitlines(keepends=True)
    selected, failure_index = select_lines(lines, context, window)
    body, kept_count = build_body(lines, selected, len(lines) <= 50)

    output_dir = Path.cwd() / "trimmed"
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{source.name}.trimmed.log"

    if failure_index is None:
        failure_header = "# First failure: No ERROR found"
    else:
        failure_text = lines[failure_index].rstrip("\r\n")
        failure_header = f"# First failure at line {failure_index + 1}: {failure_text}"

    header = (
        "# Trimmed by log-trimmer\n"
        f"# Source: {input_path} | Original lines: {len(lines)} | Kept lines: {kept_count}\n"
        f"{failure_header}\n"
    )
    with destination.open("w", encoding="utf-8", newline="") as output:
        output.write(header)
        output.write(body)
    return destination, len(lines), kept_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--context", type=int, default=10)
    parser.add_argument("--window", type=float, default=2)
    args = parser.parse_args()

    try:
        output_path, original_count, kept_count = trim_file(
            args.input_file, args.context, args.window
        )
    except (OSError, ValueError) as error:
        print(f"log-trimmer: {error}", file=sys.stderr)
        return 1

    print(f"Output: {output_path}")
    print(f"Original lines: {original_count}; Kept lines: {kept_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
