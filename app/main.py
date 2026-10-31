"""FastAPI app: POST /whatsapp Twilio webhook and /static files (Mooré audio).

Conversation state lives in memory, keyed by the CHW's WhatsApp number, and is persisted to
Supabase only after consent (via flow effects). A server restart drops conversations that are
in progress; this is acceptable for the prototype.
"""

import logging
import mimetypes
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from twilio.request_validator import RequestValidator

from app import db, messages, twilio_client
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


_conversations: dict[str, Conversation] = {}
_lock = threading.Lock()


@app.get("/")
def health() -> dict:
    return {"status": "ok"}


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request, background: BackgroundTasks) -> Response:
    form = {key: str(value) for key, value in (await request.form()).items()}
    if not _signature_is_valid(request, form):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    sender = form.get("From", "")
    outgoing = await run_in_threadpool(process_message, sender, form.get("Body", ""))
    # Replies are sent through the REST API after the webhook has answered Twilio.
    background.add_task(twilio_client.send_all, sender, outgoing)
    return Response(EMPTY_TWIML, media_type="application/xml")


def process_message(sender: str, text: str) -> list[messages.Outgoing]:
    with _lock:
        conversation = _conversations.get(sender)
        transition = handle_message(conversation.session if conversation else None, text)
        session = transition.session
        session_id = conversation.session_id if conversation else str(uuid4())

        if session is not None and session.is_active:
            _conversations[sender] = Conversation(session, session_id)
        else:
            _conversations.pop(sender, None)
        if session is not None:
            _apply_effects(transition.effects, session_id, sender, session)

    woman_code = session.woman_code if session else ""
    return [
        messages.build(key, _public_base_url(), lang=_lang(), woman_code=woman_code)
        for key in transition.replies
    ]


def _apply_effects(effects: tuple[Effect, ...], session_id: str, sender: str, session: Session):
    now = datetime.now(timezone.utc)
    if Effect.SAVE_SESSION in effects:
        completed_at = now if session.state is State.COMPLETED else None
        followup = followup_due_date(now.date()) if Effect.SCHEDULE_FOLLOWUP in effects else None
        row = db.session_row(session_id, _phone(sender), session, completed_at, followup)
        try:
            db.save_session(row)
        except Exception:
            log.exception("Failed to save session %s", session_id)
    if Effect.SEND_ALERT in effects:
        # TODO(day 3): WhatsApp alert to the referral nurse (app/alerts.py).
        log.warning("RED result for session %s: nurse alert not implemented yet", session_id)


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
