#!/usr/bin/env python3
"""Turn a defect's attachments into plain-text files that secret-masker can sanitize.

Usage:
    python .claude/skills/attachment-reader/extract_attachments.py <scenario-folder-or-file> <new-output-folder>

For every attachment it prints one manifest line:
    ATTACHMENT: <name> | <kind> | <status> | <text file to mask, or ->

Statuses:
    text          plain text copied (notes, logs, CSV, XML, Markdown, YAML, HTML)
    json-ok       JSON/HAR that parses correctly, copied as text
    json-invalid  JSON/HAR that does not parse; copied as text, report it as malformed
    extracted     text pulled out of a Word (.docx) or PDF file
    no-text       PDF with no extractable text; read the PDF directly
    unzipped      archive unpacked; each member gets its own manifest line
    image         readable image; view it directly (it cannot be text-masked)
    unreadable    empty, corrupt or unsafe file; report that it could not be read
    unsupported   file type not handled; report it as not reviewed

The source files are never modified. Nothing from an attachment is executed.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import zipfile
import zlib
from pathlib import Path

TEXT_SUFFIXES = {".txt", ".log", ".md", ".csv", ".tsv", ".xml", ".yaml", ".yml", ".ini", ".html", ".htm"}
JSON_SUFFIXES = {".json", ".har"}
IMAGE_SIGNATURES = {
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".bmp": (b"BM",),
    ".webp": (b"RIFF",),
}
MAX_ZIP_MEMBERS = 200
MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_ZIP_DEPTH = 2


def read_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


# ---------------------------------------------------------------- Word (.docx)
def docx_text(path: Path) -> str:
    from docx import Document  # python-docx, already used by the renderer

    document = Document(path)
    lines = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    for number, table in enumerate(document.tables, start=1):
        lines.append(f"[table {number}]")
        for row in table.rows:
            lines.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(lines)


# ---------------------------------------------------------------------- PDF
_PDF_TOKEN = re.compile(rb"\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]*>|\[|\]|[A-Za-z'\"*]+|-?\d*\.?\d+|/[^\s/\[\]()<>]+", re.S)
_PDF_ESCAPES = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f", b"(": b"(", b")": b")", b"\\": b"\\"}


def _pdf_string(token: bytes) -> str:
    if token.startswith(b"<"):
        hex_digits = re.sub(rb"\s", b"", token[1:-1])
        if len(hex_digits) % 2:
            hex_digits += b"0"
        return bytes.fromhex(hex_digits.decode()).decode("latin-1")
    body, out, i = token[1:-1], bytearray(), 0
    while i < len(body):
        char = body[i:i + 1]
        if char == b"\\" and i + 1 < len(body):
            nxt = body[i + 1:i + 2]
            if nxt in _PDF_ESCAPES:
                out += _PDF_ESCAPES[nxt]; i += 2; continue
            octal = re.match(rb"[0-7]{1,3}", body[i + 1:i + 4])
            if octal:
                out.append(int(octal.group(0), 8) & 0xFF); i += 1 + len(octal.group(0)); continue
            i += 2; continue
        out += char; i += 1
    return out.decode("latin-1")


def _pdf_stream_text(content: bytes) -> list[str]:
    lines, current, pending = [], [], []
    for token in _PDF_TOKEN.findall(content):
        if token.startswith((b"(", b"<")) and not token.startswith(b"<<"):
            pending.append(_pdf_string(token))
        elif token in (b"Tj", b"TJ", b"'", b'"'):
            current.append("".join(pending)); pending = []
            if token in (b"'", b'"'):
                lines.append("".join(current)); current = []
        elif token in (b"Td", b"TD", b"T*", b"Tm", b"ET"):
            if current:
                lines.append("".join(current)); current = []
            pending = []
        elif token not in (b"[", b"]") and not re.fullmatch(rb"-?\d*\.?\d+", token):
            pending = [] if token.isalpha() else pending
    if current:
        lines.append("".join(current))
    return [line for line in lines if line.strip()]


def pdf_text(path: Path) -> str:
    try:  # use pypdf when it is installed
        import pypdf  # type: ignore

        return "\n".join((page.extract_text() or "") for page in pypdf.PdfReader(str(path)).pages).strip()
    except ImportError:
        pass
    data, lines = path.read_bytes(), []
    for match in re.finditer(rb"(?<![A-Za-z])stream\r?\n(.*?)\s*endstream", data, re.S):
        raw = match.group(1)
        header = data[data.rfind(b"<<", 0, match.start()):match.start()]
        try:
            if b"/ASCII85Decode" in header:
                raw = raw.strip()
                raw = base64.a85decode(raw[:-2] if raw.endswith(b"~>") else raw)
            if b"/FlateDecode" in header:
                raw = zlib.decompress(raw)
        except (ValueError, zlib.error):
            continue
        if b"BT" in raw:
            lines.extend(_pdf_stream_text(raw))
    return "\n".join(lines).strip()


# --------------------------------------------------------------------- main
class Extractor:
    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir
        self.zip_bytes = 0

    def emit(self, name: str, kind: str, status: str, output: Path | None, note: str = "") -> None:
        target = output.as_posix() if output else "-"
        suffix = f" | {note}" if note else ""
        print(f"ATTACHMENT: {name} | {kind} | {status} | {target}{suffix}")

    def write(self, name: str, text: str) -> Path:
        target = self.out_dir / (name.replace("/", "__") + ".txt")
        target.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        return target

    def handle(self, name: str, path: Path, depth: int = 0) -> None:
        suffix = path.suffix.casefold()
        size = path.stat().st_size
        if size == 0:
            self.emit(name, suffix.lstrip(".") or "file", "unreadable", None, "empty file (0 bytes)")
            return
        try:
            if suffix in TEXT_SUFFIXES:
                self.emit(name, suffix.lstrip("."), "text", self.write(name, read_text(path.read_bytes())))
            elif suffix in JSON_SUFFIXES:
                text = read_text(path.read_bytes())
                try:
                    json.loads(text)
                    status, note = "json-ok", ""
                except json.JSONDecodeError as error:
                    status, note = "json-invalid", f"not valid JSON: {error.msg} at line {error.lineno}"
                self.emit(name, suffix.lstrip("."), status, self.write(name, text), note)
            elif suffix == ".docx":
                self.emit(name, "docx", "extracted", self.write(name, docx_text(path)))
            elif suffix == ".pdf":
                text = pdf_text(path)
                if text:
                    self.emit(name, "pdf", "extracted", self.write(name, text))
                else:
                    self.emit(name, "pdf", "no-text", None, "no extractable text; read the PDF directly")
            elif suffix == ".zip":
                self.unzip(name, path, depth)
            elif suffix in IMAGE_SIGNATURES:
                head = path.read_bytes()[:16]
                if any(head.startswith(sig) for sig in IMAGE_SIGNATURES[suffix]):
                    self.emit(name, "image", "image", None, f"{size} bytes; view directly (cannot be text-masked)")
                else:
                    self.emit(name, "image", "unreadable", None, "not a valid image file")
            else:
                self.emit(name, suffix.lstrip(".") or "file", "unsupported", None, "file type not handled")
        except Exception as error:  # report, never crash on one bad attachment
            self.emit(name, suffix.lstrip(".") or "file", "unreadable", None, f"{type(error).__name__}: {error}")

    def unzip(self, name: str, path: Path, depth: int) -> None:
        if depth >= MAX_ZIP_DEPTH:
            self.emit(name, "zip", "unsupported", None, "nested archive too deep")
            return
        try:
            archive = zipfile.ZipFile(path)
        except zipfile.BadZipFile:
            self.emit(name, "zip", "unreadable", None, "not a valid ZIP archive")
            return
        dest = self.out_dir / (name.replace("/", "__") + "_unzipped")
        dest.mkdir(parents=True, exist_ok=False)
        with archive:
            members = [info for info in archive.infolist() if not info.is_dir()]
            self.emit(name, "zip", "unzipped", dest, f"{len(members)} file(s)")
            for count, info in enumerate(members, start=1):
                member = Path(info.filename)
                member_name = f"{name}/{info.filename}"
                if member.is_absolute() or ".." in member.parts or ":" in info.filename:
                    self.emit(member_name, "zip member", "unreadable", None, "unsafe path; skipped")
                    continue
                if count > MAX_ZIP_MEMBERS or self.zip_bytes + info.file_size > MAX_ZIP_BYTES:
                    self.emit(member_name, "zip member", "unsupported", None, "archive size limit reached; skipped")
                    continue
                self.zip_bytes += info.file_size
                target = dest / member
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(info))
                self.handle(member_name, target, depth + 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract attachment text for masking and analysis.")
    parser.add_argument("source", type=Path, help="scenario folder, or a single attachment file")
    parser.add_argument("out_dir", type=Path, help="new, empty output folder")
    args = parser.parse_args()

    source = args.source
    if not source.exists():
        print(f"attachment-reader: not found: {source}", file=sys.stderr)
        return 1
    if args.out_dir.exists() and any(args.out_dir.iterdir()):
        print(f"attachment-reader: output folder is not empty: {args.out_dir}", file=sys.stderr)
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)

    extractor = Extractor(args.out_dir)
    files = sorted(p for p in source.iterdir() if p.is_file()) if source.is_dir() else [source]
    for path in files:
        extractor.handle(path.name, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
