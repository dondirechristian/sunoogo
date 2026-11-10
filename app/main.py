"""FastAPI app: WhatsApp webhooks, public /dashboard and /static files (Mooré audio).

Two providers share the same conversation logic: Twilio (POST /whatsapp) and the Meta WhatsApp
Cloud API (GET/POST /whatsapp/meta). WHATSAPP_PROVIDER selects which one sends replies.

Conversation state lives in memory, keyed by the CHW's WhatsApp number, and is persisted to
Supabase only after consent (via flow effects). A server restart drops conversations that are
in progress; this is acceptable for the prototype.
"""

import hashlib
import hmac
import logging
import mimetypes
import os
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from twilio.request_validator import RequestValidator

from app import alerts, db, messages, summary, whatsapp
from app.flow import Effect, Session, State, followup_due_date, handle_message

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Twilio rejects media served with a wrong Content-Type; do not rely on the OS registry.
mimetypes.add_type("audio/ogg", ".ogg")
mimetypes.add_type("audio/mpeg", ".mp3")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'

app = FastAPI(title="SuNoogo")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@dataclass(frozen=True)
class Conversation:
    session: Session
    session_id: str


@dataclass(frozen=True)
class Outcome:
    outgoing: list[messages.Outgoing]
    alert: Conversation | None = None  # red result: nurse must be alerted
    completed: Session | None = None  # finished session: send the case summary


_conversations: dict[str, Conversation] = {}
_lock = threading.Lock()
# Meta retries deliveries: remember recent message ids to process each message once.
_seen_message_ids: deque[str] = deque(maxlen=1000)


STAT_FIELDS = (
    "sessions_started",
    "sessions_completed",
    "level_green",
    "level_orange",
    "level_red",
    "alerts_sent",
)


@app.get("/")
def health() -> dict:
    return {"status": "ok"}


@app.get("/dashboard")
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/api/stats")
def stats() -> dict:
    """Public anonymised counters, read from the aggregated public_stats view only."""
    try:
        weeks = db.fetch_public_stats()
    except Exception:
        log.exception("Failed to read public_stats")
        raise HTTPException(status_code=503, detail="Statistics temporarily unavailable")
    return {"totals": aggregate(weeks), "weeks": weeks}


def aggregate(weeks: list[dict]) -> dict:
    return {field: sum(int(week.get(field) or 0) for week in weeks) for field in STAT_FIELDS}


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request, background: BackgroundTasks) -> Response:
    form = {key: str(value) for key, value in (await request.form()).items()}
    if not _signature_is_valid(request, form):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    sender = form.get("From", "")
    outcome = await run_in_threadpool(process_message, sender, form.get("Body", ""))
    _schedule_replies(background, sender, outcome)
    return Response(EMPTY_TWIML, media_type="application/xml")


@app.get("/whatsapp/meta")
def meta_verify(request: Request) -> PlainTextResponse:
    """Webhook verification handshake from the Meta app dashboard."""
    params = request.query_params
    expected = os.environ.get("META_VERIFY_TOKEN", "")
    token = params.get("hub.verify_token", "")
    if params.get("hub.mode") != "subscribe" or not expected or not hmac.compare_digest(
        token, expected
    ):
        raise HTTPException(status_code=403, detail="Verification failed")
    return PlainTextResponse(params.get("hub.challenge", ""))


@app.post("/whatsapp/meta")
async def meta_webhook(request: Request, background: BackgroundTasks) -> Response:
    body = await request.body()
    if not meta_signature_is_valid(body, request.headers.get("X-Hub-Signature-256", "")):
        log.warning("Rejected webhook: bad Meta signature (check META_APP_SECRET)")
        raise HTTPException(status_code=403, detail="Invalid Meta signature")
    for message_id, sender, text in meta_messages(await request.json()):
        with _lock:
            if message_id in _seen_message_ids:
                continue
            _seen_message_ids.append(message_id)
        outcome = await run_in_threadpool(process_message, sender, text)
        _schedule_replies(background, sender, outcome)
    return Response(status_code=200)


def meta_signature_is_valid(body: bytes, header: str) -> bool:
    secret = os.environ.get("META_APP_SECRET", "")
    if not secret or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def meta_messages(payload: dict) -> list[tuple[str, str, str]]:
    """(message id, sender, text) for each incoming message. Status updates are skipped.

    The sender is normalised to "whatsapp:+<digits>", as with Twilio, so that conversations
    and stored CHW numbers look the same whichever provider is used. A non-text message
    (voice note, image) is handled as an empty text, which gets the help reply.
    """
    found = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            # Field and keys only: never log message content.
            log.info("Meta webhook: field=%s keys=%s", change.get("field"), sorted(value))
            for message in value.get("messages", []):
                if not message.get("from"):
                    continue
                is_text = message.get("type") == "text"
                text = message.get("text", {}).get("body", "") if is_text else ""
                found.append((message.get("id", ""), f"whatsapp:+{message['from']}", text))
    return found


def _schedule_replies(background: BackgroundTasks, sender: str, outcome: "Outcome") -> None:
    # Sent through the provider API after the webhook has answered, in this order.
    # Each task catches its own errors, so one failure never cancels the next ones.
    if outcome.alert:
        background.add_task(
            alerts.send_alert, outcome.alert.session_id, _phone(sender), outcome.alert.session
        )
    background.add_task(whatsapp.provider().send_all, sender, outcome.outgoing)
    if outcome.completed:
        background.add_task(send_summary, sender, outcome.completed)


def send_summary(sender: str, session: Session) -> None:
    try:
        text = summary.summarize(session)
    except Exception:
        log.exception("Case summary failed")
        return
    if text:
        whatsapp.provider().send_all(sender, [messages.Outgoing(text)])


def process_message(sender: str, text: str) -> Outcome:
    with _lock:
        conversation = _conversations.get(sender)
        transition = handle_message(conversation.session if conversation else None, text)
        session = transition.session
        session_id = conversation.session_id if conversation else str(uuid4())

        if session is not None and session.is_active:
            _conversations[sender] = Conversation(session, session_id)
        else:
            _conversations.pop(sender, None)
        if session is not None and Effect.SAVE_SESSION in transition.effects:
            _save(transition.effects, session_id, sender, session)

    woman_code = session.woman_code if session else ""
    outgoing = [
        messages.build(key, _public_base_url(), lang=_lang(), woman_code=woman_code)
        for key in transition.replies
    ]
    completed = session if session is not None and session.state is State.COMPLETED else None
    alert = Conversation(session, session_id) if Effect.SEND_ALERT in transition.effects else None
    return Outcome(outgoing, alert=alert, completed=completed)


def _save(effects: tuple[Effect, ...], session_id: str, sender: str, session: Session) -> None:
    now = datetime.now(timezone.utc)
    completed_at = now if session.state is State.COMPLETED else None
    followup = followup_due_date(now.date()) if Effect.SCHEDULE_FOLLOWUP in effects else None
    row = db.session_row(session_id, _phone(sender), session, completed_at, followup)
    try:
        db.save_session(row)
    except Exception:
        log.exception("Failed to save session %s", session_id)


def _signature_is_valid(request: Request, form: dict) -> bool:
    # Behind ngrok, Twilio signs the public URL, not the local one.
    url = _public_base_url().rstrip("/") + request.url.path
    if request.url.query:
        url += "?" + request.url.query
    signature = request.headers.get("X-Twilio-Signature", "")
    valid = RequestValidator(os.environ["TWILIO_AUTH_TOKEN"]).validate(url, form, signature)
    if not valid:
        log.warning("Rejected webhook: bad Twilio signature for %s (check PUBLIC_BASE_URL)", url)
    return valid


def _public_base_url() -> str:
    return os.environ["PUBLIC_BASE_URL"]


def _lang() -> str:
    return os.environ.get("SUNOOGO_LANG", messages.DEFAULT_LANG)


def _phone(sender: str) -> str:
    return sender.removeprefix("whatsapp:")
