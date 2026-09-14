from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any

AUTO_SUBJECT_PATTERNS = (
    r"\bout of office\b", r"\bautomatic reply\b", r"\bauto.?reply\b",
    r"\baway from (?:the )?office\b", r"\bvacation reply\b",
    r"\babwesenheitsnotiz\b", r"\bréponse automatique\b",
    r"\brisposta automatica\b", r"\brespuesta automática\b",
    r"\bαυτόματη απάντηση\b",
)
BOUNCE_FROM_PATTERNS = (r"mailer-daemon", r"postmaster", r"mail delivery subsystem")
REPLY_SEPARATORS = (
    r"^On .+ wrote:\s*$",
    r"^-----Original Message-----\s*$",
    r"^From:\s.+$",
    r"^De:\s.+$",
    r"^Von:\s.+$",
    r"^Da:\s.+$",
    r"^Από:\s.+$",
)
SIGNATURE_MARKERS = (
    "-- ", "sent from my iphone", "sent from my android", "get outlook for ios",
    "envoyé de mon iphone", "gesendet von meinem iphone", "inviato da iphone",
    "enviado desde mi iphone", "στάλθηκε από το iphone μου",
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
    def handle_data(self, data: str) -> None:
        self.parts.append(data)
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"br", "p", "div", "li", "tr"}:
            self.parts.append("\n")
    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"p", "div", "li", "tr"}:
            self.parts.append("\n")


def html_to_text(value: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(value)
        return html.unescape("".join(parser.parts))
    except Exception:
        return re.sub(r"<[^>]+>", " ", html.unescape(value))


def _header(headers: dict[str, Any], key: str) -> str:
    for k, v in (headers or {}).items():
        if str(k).casefold() == key.casefold():
            return str(v or "")
    return ""


def classify_inbound(message: dict[str, Any]) -> tuple[str, str]:
    headers = message.get("headers") or {}
    subject = str(message.get("subject") or "")
    sender = str(message.get("from") or "")

    auto_submitted = _header(headers, "Auto-Submitted").strip().casefold()
    if auto_submitted and auto_submitted != "no":
        return "IGNORE_AUTO", "auto_submitted_header"
    precedence = _header(headers, "Precedence").strip().casefold()
    if precedence in {"bulk", "junk", "list"}:
        return "IGNORE_AUTO", f"precedence_{precedence}"
    if any(re.search(p, sender, re.I) for p in BOUNCE_FROM_PATTERNS):
        return "IGNORE_BOUNCE", "bounce_sender"
    if any(re.search(p, subject, re.I) for p in AUTO_SUBJECT_PATTERNS):
        return "IGNORE_AUTO", "auto_reply_subject"
    return "PROCESS", "customer_message_candidate"


def strip_quoted_history(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        if any(re.match(p, stripped, re.I) for p in REPLY_SEPARATORS):
            break
        out.append(line)
    return "\n".join(out)


def strip_signature(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        normalized = line.strip().casefold()
        if any(normalized == marker.casefold() or normalized.startswith(marker.casefold()) for marker in SIGNATURE_MARKERS):
            break
        out.append(line)
    return "\n".join(out)


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_message(message: dict[str, Any]) -> dict[str, Any]:
    disposition, reason = classify_inbound(message)
    raw_body = str(message.get("body_text") or "")
    if not raw_body.strip() and message.get("body_html"):
        raw_body = html_to_text(str(message.get("body_html") or ""))
    clean = normalize_whitespace(strip_signature(strip_quoted_history(raw_body)))
    if disposition == "PROCESS" and not clean:
        disposition, reason = "IGNORE_EMPTY", "empty_after_normalization"
    return {
        "message_id": str(message.get("message_id") or ""),
        "thread_id": str(message.get("thread_id") or ""),
        "from": str(message.get("from") or ""),
        "to": str(message.get("to") or ""),
        "subject": str(message.get("subject") or ""),
        "received_at": str(message.get("received_at") or ""),
        "headers": message.get("headers") or {},
        "normalized_customer_message": clean,
        "disposition": disposition,
        "disposition_reason": reason,
    }
