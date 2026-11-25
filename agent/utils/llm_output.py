"""Cleaning of raw LLM outputs before they are stored as reviewable drafts."""

import json
import re

_FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")
_BODY_FIELD = re.compile(r'"corps[^"]*"\s*:\s*"((?:[^"\\]|\\.)*)"', re.DOTALL)
_SUBJECT_LINE = re.compile(r"^\s*\**\s*(objet|subject)\s*:", re.IGNORECASE)


def _unwrap(text):
    cleaned = _FENCE.sub("", text.strip()).strip()
    try:
        data = json.loads(cleaned, strict=False)  # LLMs often emit raw newlines in strings
    except ValueError:
        match = _BODY_FIELD.search(cleaned)  # truncated or slightly invalid JSON
        return json.loads(f'"{match.group(1)}"', strict=False) if match else cleaned
    if isinstance(data, dict):
        body = next((v for k, v in data.items() if "corps" in k and isinstance(v, str)), None)
        values = [v for v in data.values() if isinstance(v, str)]
        return body or (values[0] if values else cleaned)
    if isinstance(data, list) and data and isinstance(data[0], str):
        return data[0]
    return cleaned


def extract_mail_body(text):
    """
    The prompts ask for JSON ({"corps_du_mail_en_français": ...}); return the mail body
    itself so the stored message is readable by the reviewer. Plain text is kept as is.
    A leading "Objet : ..." line is dropped: the subject is generated separately.
    """
    if not isinstance(text, str):
        return text
    lines = _unwrap(text).strip().splitlines()
    if lines and _SUBJECT_LINE.match(lines[0]):
        lines = lines[1:]
    return "\n".join(lines).strip()


def clean_subject(text):
    """One line, without an "Objet :" prefix or surrounding quotes."""
    line = next((part for part in str(text).strip().splitlines() if part.strip()), "")
    line = re.sub(r"^\s*\**\s*(objet|subject)\s*:\s*", "", line, flags=re.IGNORECASE)
    return line.strip().strip('"«»*').strip()
