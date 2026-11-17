#!/usr/bin/env python3
"""Mask common secrets in a text file and write the sanitized text to a new file."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MASK = "[MASKED]"

_SENSITIVE_HEADER = re.compile(
    r"(?im)^(?P<prefix>\s*(?P<name>set-cookie|cookie|authorization)\s*:\s*)"
    r"(?P<value>[^\r\n]*)"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_EMAIL = re.compile(
    r"(?i)\b[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+\b"
)

_SECRET_KEYS = (
    "password",
    "passwords",
    "passwd",
    "pwd",
    "passphrase",
    "api key",
    "apikey",
    "api_key",
    "api-key",
    "x-api-key",
    "x_api_key",
    "subscription-key",
    "subscription_key",
    "client secret",
    "clientsecret",
    "client_secret",
    "client-secret",
    "access token",
    "accesstoken",
    "access_token",
    "access-token",
    "refresh token",
    "refreshtoken",
    "refresh_token",
    "refresh-token",
    "id token",
    "idtoken",
    "id_token",
    "id-token",
    "auth token",
    "authtoken",
    "auth_token",
    "auth-token",
    "token",
    "secret",
    "accountkey",
    "account key",
    "sharedaccesskey",
    "shared access key",
    "sharedaccesssignature",
    "shared access signature",
    "cookie",
    "cookies",
)
_KEY_PATTERN = "|".join(
    re.escape(key) for key in sorted(_SECRET_KEYS, key=len, reverse=True)
)
_ASSIGNMENT = re.compile(
    rf"(?i)(?P<prefix>(?<![A-Za-z0-9_])(?P<key>{_KEY_PATTERN})(?![A-Za-z0-9_])"
    r"[\"']?\s*[:=]\s*)(?P<value>\"[^\"]*\"|'[^']*'|[^;\s,}&]+)"
)


def _record_mask(counts: dict[str, int] | None, kind: str) -> None:
    if counts is not None:
        counts[kind] = counts.get(kind, 0) + 1


def _assignment_type(key: str) -> str:
    normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
    if normalized in {"accountkey", "sharedaccesskey", "sharedaccesssignature"}:
        return "account_key"
    if normalized in {"apikey", "xapikey", "subscriptionkey"}:
        return "api_key"
    if normalized in {"password", "passwords", "passwd", "pwd", "passphrase"}:
        return "password"
    if normalized in {"cookie", "cookies"}:
        return "cookie"
    return "token"


def _mask_assignment(match: re.Match[str], counts: dict[str, int] | None = None) -> str:
    value = match.group("value")
    unquoted = value[1:-1] if value.startswith(("'", '"')) and value[-1:] == value[:1] else value
    if unquoted.strip().casefold() == MASK.casefold():
        return match.group(0)
    _record_mask(counts, _assignment_type(match.group("key")))
    if value.startswith(("'", '"')) and value[-1:] == value[:1]:
        value = f"{value[0]}{MASK}{value[-1]}"
    else:
        value = MASK
    return f"{match.group('prefix')}{value}"


# Plain-text passwords in tester notes, e.g. "pwd secret_sauce",
# "password hunter2", "user + pwd X" and "creds tomsmith / X".
# The value is the next word on the same line. Ordinary words that
# commonly follow "password"/"pwd" in prose are not masked.
_NOTE_PASSWORD_STOPWORDS = frozenset("""
a an and are as at be been but by did does doesn't error expired fails failed
field fields for gave give gives in incorrect input invalid is isn't not of on
or policy rejected required reset same still the to too valid was wasn't were
with works worked wrong change changed again also then box length
flow page link screen form email hash mismatch manager rules prompt expiry
from into onto here there this that it its when which used using shown
""".split())
_NOTE_PASSWORD = re.compile(
    r"(?im)(?P<prefix>(?<![A-Za-z0-9_-])(?:password|passwd|pwd)[ \t]+)"
    r"(?P<value>[^\s,;\"']+)"
)
_NOTE_CREDS = re.compile(
    r"(?im)(?P<prefix>(?<![A-Za-z0-9_-])(?:creds|credentials)[ \t]+[^\s/]+[ \t]*/[ \t]*)"
    r"(?P<value>[^\s,;\"']+)"
)


def _mask_note_value(match: re.Match[str], counts: dict[str, int] | None) -> str:
    value = match.group("value")
    trailing = ""
    if len(value) > 1 and value[-1] == ".":
        value, trailing = value[:-1], "."
    if value.casefold() == MASK.casefold() or value.casefold() in _NOTE_PASSWORD_STOPWORDS:
        return match.group(0)
    _record_mask(counts, "password")
    return f"{match.group('prefix')}{MASK}{trailing}"


def mask_text(text: str, counts: dict[str, int] | None = None) -> str:
    """Return text with common personal and credential values replaced."""
    def mask_header(match: re.Match[str]) -> str:
        value = match.group("value")
        if value.strip().casefold() != MASK.casefold() and value.strip():
            name = match.group("name").casefold()
            _record_mask(counts, "token" if name == "authorization" else "cookie")
        return f"{match.group('prefix')}{MASK}"

    def mask_bearer(match: re.Match[str]) -> str:
        _record_mask(counts, "token")
        return "Bearer " + MASK

    def mask_email(match: re.Match[str]) -> str:
        _record_mask(counts, "email")
        return MASK

    text = _SENSITIVE_HEADER.sub(mask_header, text)
    text = _BEARER.sub(mask_bearer, text)
    text = _ASSIGNMENT.sub(lambda match: _mask_assignment(match, counts), text)
    text = _NOTE_CREDS.sub(lambda match: _mask_note_value(match, counts), text)
    text = _NOTE_PASSWORD.sub(lambda match: _mask_note_value(match, counts), text)
    return _EMAIL.sub(mask_email, text)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mask common secrets in a text file and write a new output file."
    )
    parser.add_argument("input_file", type=Path, help="source text file")
    parser.add_argument("output_file", type=Path, help="new sanitized output path")
    args = parser.parse_args()

    try:
        source = args.input_file.resolve(strict=True)
        destination = args.output_file.resolve(strict=False)
        if source == destination:
            parser.error("output path must differ from the input path")
        if destination.exists():
            parser.error(f"output file already exists: {destination}")

        contents = source.read_text(encoding="utf-8-sig")
        mask_counts: dict[str, int] = {}
        sanitized = mask_text(contents, mask_counts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8", newline="") as output:
            output.write(sanitized)
    except (OSError, UnicodeError) as error:
        print(f"secret-masker: {error}", file=sys.stderr)
        return 1

    type_order = ("password", "token", "api_key", "cookie", "account_key", "email")
    types = ", ".join(kind for kind in type_order if mask_counts.get(kind)) or "none"
    print(f"MASKED: {sum(mask_counts.values())} ({types})")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
