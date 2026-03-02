import imaplib
import json
import os
import re
import smtplib
from dataclasses import dataclass
from email import message_from_bytes
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import AuditChain
from app.services.audit_logger import write_audit


@dataclass
class EmailCommand:
    sender: str
    message_id: str
    subject: str
    connector: str
    action: str
    payload: dict[str, Any]
    request_id: str


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_allowed_senders() -> set[str]:
    raw = os.getenv("CONTROL_EMAIL_ALLOWED_SENDERS", "")
    return {s.strip().lower() for s in raw.split(",") if s.strip()}


def _extract_text_body(msg) -> str:
    if msg.is_multipart():
        chunks: list[str] = []
        for part in msg.walk():
            content_type = (part.get_content_type() or "").lower()
            content_disposition = str(part.get("Content-Disposition") or "").lower()
            if content_type != "text/plain" or "attachment" in content_disposition:
                continue
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            chunks.append(payload.decode(charset, errors="replace"))
        return "\n".join(chunks).strip()

    payload = msg.get_payload(decode=True) or b""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace").strip()


def _parse_key_values(body: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line in body.splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*[:=]\s*(.+)$", text)
        if not m:
            continue
        key = m.group(1).strip().lower()
        value = m.group(2).strip()
        out[key] = value
    return out


def _parse_command(sender: str, subject: str, body: str, message_id: str) -> EmailCommand | None:
    parsed: dict[str, Any] = {}

    if body:
        try:
            maybe = json.loads(body)
            if isinstance(maybe, dict):
                parsed = maybe
        except json.JSONDecodeError:
            parsed = _parse_key_values(body)

    connector = str(parsed.get("connector", "")).strip()
    action = str(parsed.get("action", "")).strip()

    # Subject fallback: "connector=Stripe action=retrieve_balance"
    if not connector or not action:
        subject_fields = _parse_key_values(subject.replace(" ", "\n"))
        connector = connector or str(subject_fields.get("connector", "")).strip()
        action = action or str(subject_fields.get("action", "")).strip()

    if not connector or not action:
        return None

    payload = parsed.get("payload", {})
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {"raw": payload}
    if not isinstance(payload, dict):
        payload = {}

    request_id = str(parsed.get("request_id") or f"email:{message_id}")

    return EmailCommand(
        sender=sender,
        message_id=message_id,
        subject=subject,
        connector=connector,
        action=action,
        payload=payload,
        request_id=request_id,
    )


def _audit_exists(db: Session, request_id: str) -> bool:
    row = db.execute(select(AuditChain.id).where(AuditChain.request_id == request_id)).first()
    return row is not None


def _send_reply(to_email: str, subject: str, body: str) -> None:
    smtp_host = os.getenv("CONTROL_EMAIL_SMTP_HOST", "").strip()
    smtp_user = os.getenv("CONTROL_EMAIL_SMTP_USERNAME", "").strip()
    smtp_pass = os.getenv("CONTROL_EMAIL_SMTP_PASSWORD", "").strip()
    from_email = os.getenv("CONTROL_EMAIL_FROM", smtp_user).strip()
    if not smtp_host or not smtp_user or not smtp_pass or not from_email:
        return

    smtp_port = int(os.getenv("CONTROL_EMAIL_SMTP_PORT", "465"))
    use_ssl = _env_bool("CONTROL_EMAIL_SMTP_SSL", True)

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    if use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)


async def poll_email_and_dispatch(db: Session) -> dict[str, Any]:
    if not _env_bool("CONTROL_EMAIL_ENABLED", False):
        return {"status": "disabled", "processed": 0}

    imap_host = os.getenv("CONTROL_EMAIL_IMAP_HOST", "").strip()
    imap_user = os.getenv("CONTROL_EMAIL_IMAP_USERNAME", "").strip()
    imap_pass = os.getenv("CONTROL_EMAIL_IMAP_PASSWORD", "").strip()
    imap_port = int(os.getenv("CONTROL_EMAIL_IMAP_PORT", "993"))
    folder = os.getenv("CONTROL_EMAIL_IMAP_FOLDER", "INBOX").strip() or "INBOX"

    if not imap_host or not imap_user or not imap_pass:
        return {"status": "misconfigured", "processed": 0, "error": "missing imap credentials"}

    allowed = _parse_allowed_senders()
    execute_url = os.getenv("CONTROL_EMAIL_EXECUTE_URL", "http://127.0.0.1:8000/execute")

    processed = 0
    executed = 0
    skipped = 0
    errors: list[str] = []

    mail = imaplib.IMAP4_SSL(imap_host, imap_port)
    try:
        mail.login(imap_user, imap_pass)
        status, _ = mail.select(folder)
        if status != "OK":
            return {"status": "error", "processed": 0, "error": f"cannot select folder {folder}"}

        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            return {"status": "error", "processed": 0, "error": "search failed"}

        ids = data[0].split() if data and data[0] else []

        async with httpx.AsyncClient(timeout=10.0) as client:
            for raw_id in ids:
                processed += 1
                msg_status, msg_data = mail.fetch(raw_id, "(RFC822)")
                if msg_status != "OK" or not msg_data or not msg_data[0]:
                    errors.append(f"fetch_failed:{raw_id.decode(errors='ignore')}")
                    continue

                blob = msg_data[0][1]
                msg = message_from_bytes(blob)
                sender = parseaddr(msg.get("From", ""))[1].lower().strip()
                subject = str(msg.get("Subject", "")).strip()
                message_id = str(msg.get("Message-ID", raw_id.decode(errors="ignore"))).strip("<>")
                body = _extract_text_body(msg)

                if allowed and sender not in allowed:
                    skipped += 1
                    write_audit(
                        db,
                        connector="EmailControl",
                        request_id=f"email-reject:{message_id}",
                        validation_result="failed",
                        decision="reject_sender",
                        outcome="skipped",
                        fallback_used=False,
                        details={"sender": sender, "subject": subject},
                    )
                    continue

                cmd = _parse_command(sender=sender, subject=subject, body=body, message_id=message_id)
                if cmd is None:
                    skipped += 1
                    write_audit(
                        db,
                        connector="EmailControl",
                        request_id=f"email-invalid:{message_id}",
                        validation_result="failed",
                        decision="invalid_command",
                        outcome="skipped",
                        fallback_used=False,
                        details={"sender": sender, "subject": subject},
                    )
                    continue

                if _audit_exists(db, cmd.request_id):
                    skipped += 1
                    write_audit(
                        db,
                        connector="EmailControl",
                        request_id=f"email-replay:{message_id}",
                        validation_result="failed",
                        decision="replay_blocked",
                        outcome="skipped",
                        fallback_used=False,
                        details={"request_id": cmd.request_id, "sender": sender},
                    )
                    continue

                payload = {
                    "connector": cmd.connector,
                    "action": cmd.action,
                    "payload": cmd.payload,
                    "request_id": cmd.request_id,
                }

                try:
                    resp = await client.post(execute_url, json=payload)
                    out = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
                    executed += 1
                    write_audit(
                        db,
                        connector="EmailControl",
                        request_id=f"email-dispatch:{message_id}",
                        validation_result="passed",
                        decision="dispatch",
                        outcome="success",
                        fallback_used=False,
                        details={"sender": sender, "request_id": cmd.request_id, "result": out},
                    )

                    _send_reply(
                        to_email=sender,
                        subject=f"[BalanceHub] {cmd.connector}:{cmd.action} -> {out.get('status', out.get('execution_result', 'ok'))}",
                        body=json.dumps({"request_id": cmd.request_id, "result": out}, ensure_ascii=False, indent=2),
                    )
                except Exception as exc:
                    errors.append(str(exc))
                    write_audit(
                        db,
                        connector="EmailControl",
                        request_id=f"email-error:{message_id}",
                        validation_result="failed",
                        decision="dispatch",
                        outcome="error",
                        fallback_used=False,
                        details={"sender": sender, "request_id": cmd.request_id, "error": str(exc)},
                    )

                # Mark message seen after handling to avoid reprocessing loops.
                mail.store(raw_id, "+FLAGS", "\\Seen")

        return {
            "status": "ok",
            "processed": processed,
            "executed": executed,
            "skipped": skipped,
            "errors": errors,
        }
    finally:
        try:
            mail.logout()
        except Exception:
            pass
