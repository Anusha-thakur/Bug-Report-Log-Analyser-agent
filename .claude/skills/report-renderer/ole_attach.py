"""Embed files in a Word document as attachments (OLE "Package" objects).

This is what Word's Insert > Object > Create from file > Display as icon
produces: the file is stored inside the .docx and shown as an icon that the
reader can double-click to open or save. Pure Python: it writes the OLE
compound file that Word expects, so neither pywin32 nor Word is needed to
create the report.
"""

from __future__ import annotations

import io
import struct
import zlib
from pathlib import Path

from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml import parse_xml

OLE_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.oleObject"
PACKAGE_CLSID = struct.pack("<IHH", 0x0003000C, 0x0000, 0x0000) + bytes.fromhex("C000000000000046")

_ENDOFCHAIN = 0xFFFFFFFE
_FREESECT = 0xFFFFFFFF
_FATSECT = 0xFFFFFFFD
_NOSTREAM = 0xFFFFFFFF
_SECTOR = 512
_MINI_SECTOR = 64
_MINI_CUTOFF = 4096


# ------------------------------------------------------------ OLE compound file
def _sectors(size: int, unit: int = _SECTOR) -> int:
    return (size + unit - 1) // unit


def build_compound_file(streams: list[tuple[str, bytes]], root_clsid: bytes) -> bytes:
    """Write a version-3 compound file containing the given top-level streams."""
    streams = sorted(streams, key=lambda item: (len(item[0]), item[0].upper()))
    mini = bytearray()
    minifat: list[int] = []
    entries: list[list] = []  # [name, data, start, kind]
    for name, data in streams:
        if len(data) < _MINI_CUTOFF:
            count = _sectors(len(data), _MINI_SECTOR)
            start = len(mini) // _MINI_SECTOR if count else _ENDOFCHAIN
            for i in range(count):
                minifat.append(start + i + 1 if i < count - 1 else _ENDOFCHAIN)
            mini += data + b"\0" * ((-len(data)) % _MINI_SECTOR)
            entries.append([name, data, start, "mini"])
        else:
            entries.append([name, data, None, "big"])

    n_minifat = _sectors(len(minifat) * 4)
    n_dir = _sectors((len(entries) + 1) * 128)
    n_ministream = _sectors(len(mini))
    n_big = sum(_sectors(len(e[1])) for e in entries if e[3] == "big")
    n_fat = 1
    while n_fat * (_SECTOR // 4) < n_fat + n_minifat + n_dir + n_ministream + n_big:
        n_fat += 1
    if n_fat > 109:
        raise ValueError("attachment too large to embed")

    fat: list[int] = [_FATSECT] * n_fat

    def chain(count: int) -> int:
        start = len(fat)
        for i in range(count):
            fat.append(start + i + 1 if i < count - 1 else _ENDOFCHAIN)
        return start if count else _ENDOFCHAIN

    minifat_start = chain(n_minifat)
    dir_start = chain(n_dir)
    ministream_start = chain(n_ministream)
    for entry in entries:
        if entry[3] == "big":
            entry[2] = chain(_sectors(len(entry[1])))
    fat += [_FREESECT] * ((-len(fat)) % (_SECTOR // 4))

    def dir_entry(name: str, kind: int, start: int, size: int, child: int = _NOSTREAM,
                  right: int = _NOSTREAM, clsid: bytes = b"\0" * 16) -> bytes:
        encoded = (name + "\0").encode("utf-16-le") if name else b""
        record = encoded.ljust(64, b"\0")
        record += struct.pack("<HBB", len(encoded), kind, 1 if kind else 0)
        record += struct.pack("<III", _NOSTREAM, right, child)
        record += clsid + struct.pack("<I", 0) + b"\0" * 16
        record += struct.pack("<IQ", start, size)
        return record

    directory = dir_entry(
        "Root Entry", 5, ministream_start if mini else _ENDOFCHAIN, len(mini),
        child=1 if entries else _NOSTREAM, clsid=root_clsid,
    )
    for index, (name, data, start, _kind) in enumerate(entries, start=1):
        right = index + 1 if index < len(entries) else _NOSTREAM
        directory += dir_entry(name, 2, start, len(data), right=right)
    while len(directory) % _SECTOR:
        directory += dir_entry("", 0, 0, 0)

    header = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" + b"\0" * 16
    header += struct.pack("<HHHHH", 0x3E, 3, 0xFFFE, 9, 6) + b"\0" * 6
    header += struct.pack(
        "<IIIIIIIII", 0, n_fat, dir_start, 0, _MINI_CUTOFF,
        minifat_start if n_minifat else _ENDOFCHAIN, n_minifat, _ENDOFCHAIN, 0,
    )
    header += struct.pack("<109I", *(list(range(n_fat)) + [_FREESECT] * (109 - n_fat)))

    def pad(blob: bytes, fill: bytes = b"\0") -> bytes:
        return blob + fill * ((-len(blob)) % _SECTOR)

    body = struct.pack(f"<{len(fat)}I", *fat)
    minifat_bytes = struct.pack(f"<{len(minifat)}I", *minifat) if minifat else b""
    body += pad(minifat_bytes, b"\xFF")
    body += directory
    body += pad(bytes(mini))
    for entry in entries:
        if entry[3] == "big":
            body += pad(entry[1])
    return header + body


def _ansi(text: str) -> bytes:
    return text.encode("cp1252", errors="replace")


def package_ole_object(display_name: str, data: bytes) -> bytes:
    """oleObject.bin holding `data` as an OLE Package named `display_name`."""
    label = _ansi(display_name)
    native = struct.pack("<H", 2) + label + b"\0" + label + b"\0"
    native += struct.pack("<I", 0x00030000)
    native += struct.pack("<I", len(label) + 1) + label + b"\0"
    native += struct.pack("<I", len(data)) + data
    unicode_name = display_name.encode("utf-16-le")
    for _ in range(3):  # temp path, label, file path (Unicode copies)
        native += struct.pack("<I", len(display_name)) + unicode_name
    ole10native = struct.pack("<I", len(native)) + native

    def ansi_string(text: str) -> bytes:
        raw = text.encode("ascii") + b"\0"
        return struct.pack("<I", len(raw)) + raw

    def unicode_string(text: str) -> bytes:
        raw = (text + "\0").encode("utf-16-le")
        return struct.pack("<I", len(raw) // 2) + raw

    compobj = struct.pack("<II", 0xFFFE0001, 0x00000A03) + struct.pack("<I", 0xFFFFFFFF) + PACKAGE_CLSID
    compobj += ansi_string("OLE Package") + struct.pack("<I", 0) + ansi_string("Package")
    compobj += struct.pack("<I", 0x71B239F4)
    compobj += unicode_string("OLE Package") + struct.pack("<I", 0) + unicode_string("Package")

    return build_compound_file([("\x01Ole10Native", ole10native), ("\x01CompObj", compobj)], PACKAGE_CLSID)


# ------------------------------------------------------------------- icon PNG
_ICON_COLOURS = {
    "image": (46, 125, 50), "pdf": (198, 40, 40), "doc": (21, 101, 192),
    "zip": (239, 108, 0), "data": (106, 27, 154), "text": (84, 110, 122),
}


def _icon_kind(name: str) -> str:
    suffix = Path(name).suffix.casefold()
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
        return "image"
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".doc", ".docx", ".rtf"}:
        return "doc"
    if suffix in {".zip", ".7z", ".gz"}:
        return "zip"
    if suffix in {".json", ".har", ".csv", ".xml", ".xlsx"}:
        return "data"
    return "text"


def icon_png(name: str, width: int = 48, height: int = 60) -> bytes:
    """A plain page icon with a coloured band for the file type."""
    band = _ICON_COLOURS[_icon_kind(name)]
    white, edge, line = (255, 255, 255), (120, 120, 120), (190, 190, 190)
    fold = 12
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            inside = 4 <= x < width - 4 and 1 <= y < height - 1
            corner = x >= width - 4 - fold and y < 1 + fold
            if not inside or (corner and (x - (width - 4 - fold)) > y - 1):
                colour = white
            elif corner and (x - (width - 4 - fold)) == y - 1:
                colour = edge
            elif x in (4, width - 5) or y in (1, height - 2):
                colour = edge
            elif height - 18 <= y < height - 6:
                colour = band
            elif y > fold + 4 and y < height - 22 and y % 5 == 0 and 9 <= x < width - 9:
                colour = line
            else:
                colour = white
            row += bytes(colour)
        rows.append(b"\0" + bytes(row))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + chunk(b"IEND", b"")
    )


# ------------------------------------------------------------- docx insertion
_V = "urn:schemas-microsoft-com:vml"
_O = "urn:schemas-microsoft-com:office:office"
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_SHAPETYPE = (
    f'<v:shapetype xmlns:v="{_V}" xmlns:o="{_O}" id="_x0000_t75" coordsize="21600,21600" o:spt="75" '
    'o:preferrelative="t" path="m@4@5l@4@11@9@11@9@5xe" filled="f" stroked="f">'
    '<v:stroke joinstyle="miter"/><v:formulas>'
    '<v:f eqn="if lineDrawn pixelLineWidth 0"/><v:f eqn="sum @0 1 0"/><v:f eqn="sum 0 0 @1"/>'
    '<v:f eqn="prod @2 1 2"/><v:f eqn="prod @3 21600 pixelWidth"/><v:f eqn="prod @3 21600 pixelHeight"/>'
    '<v:f eqn="sum @0 0 1"/><v:f eqn="prod @6 1 2"/><v:f eqn="prod @7 21600 pixelWidth"/>'
    '<v:f eqn="sum @8 21600 0"/><v:f eqn="prod @7 21600 pixelHeight"/><v:f eqn="sum @10 21600 0"/>'
    '</v:formulas><v:path o:extrusionok="f" gradientshapeok="t" o:connecttype="rect"/>'
    '<o:lock v:ext="edit" aspectratio="t"/></v:shapetype>'
)


def add_attachment(document, data: bytes, display_name: str) -> None:
    """Append a paragraph holding `data` as an attachment icon named `display_name`."""
    part = document.part
    package = part.package
    counter = getattr(document, "_ole_counter", 0) + 1
    document._ole_counter = counter

    ole_part = Part(
        PackURI(package.next_partname("/word/embeddings/oleObject%d.bin")),
        OLE_CONTENT_TYPE,
        package_ole_object(display_name, data),
        package,
    )
    ole_rid = part.relate_to(ole_part, RT.OLE_OBJECT)
    image_rid, _image = part.get_or_add_image(io.BytesIO(icon_png(display_name)))

    shape_id = f"_x0000_i{1024 + counter}"
    object_id = f"_{1700000000 + counter}"
    shapetype = _SHAPETYPE if counter == 1 else ""
    xml = (
        f'<w:r xmlns:w="{_W}" xmlns:v="{_V}" xmlns:o="{_O}" xmlns:r="{_R}">'
        f'<w:object w:dxaOrig="720" w:dyaOrig="900">{shapetype}'
        f'<v:shape id="{shape_id}" type="#_x0000_t75" style="width:36pt;height:45pt" o:ole="">'
        f'<v:imagedata r:id="{image_rid}" o:title=""/></v:shape>'
        f'<o:OLEObject Type="Embed" ProgID="Package" ShapeID="{shape_id}" DrawAspect="Icon" '
        f'ObjectID="{object_id}" r:id="{ole_rid}"/>'
        "</w:object></w:r>"
    )
    paragraph = document.add_paragraph()
    paragraph._p.append(parse_xml(xml))
