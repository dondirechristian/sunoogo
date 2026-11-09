"""Send WhatsApp text and audio messages through the Meta WhatsApp Cloud API (free test number).

Same interface as app/twilio_client.py. Recipients may be given as "whatsapp:+226...",
"+226..." or "226..."; the Cloud API wants digits only.
Docs: developers.facebook.com/documentation/business-messaging/whatsapp/messages/audio-messages
"""

import logging
import os

import httpx

from app.messages import Outgoing

log = logging.getLogger(__name__)

DEFAULT_GRAPH_VERSION = "v23.0"
TIMEOUT_SECONDS = 15


def recipient(to: str) -> str:
    return to.removeprefix("whatsapp:").removeprefix("+")


def text_payload(to: str, body: str) -> dict:
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient(to),
        "type": "text",
        "text": {"body": body},
    }


def audio_payload(to: str, media_url: str) -> dict:
    # OGG/Opus is shown as a voice note (play button, one-tap playback).
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient(to),
        "type": "audio",
        "audio": {"link": media_url, "voice": media_url.endswith(".ogg")},
    }


def _post(payload: dict) -> None:
    version = os.environ.get("META_GRAPH_VERSION", DEFAULT_GRAPH_VERSION)
    url = f"https://graph.facebook.com/{version}/{os.environ['META_PHONE_NUMBER_ID']}/messages"
    headers = {"Authorization": f"Bearer {os.environ['META_ACCESS_TOKEN']}"}
    response = httpx.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
    if response.is_error:
        # The error body says why (expired token, recipient not in the test list, ...).
        raise RuntimeError(f"Meta API {response.status_code}: {response.text}")


def send_text(to: str, body: str) -> None:
    _post(text_payload(to, body))


def send_audio(to: str, media_url: str) -> None:
    _post(audio_payload(to, media_url))


def send_all(to: str, outgoing: list[Outgoing]) -> None:
    """Send messages in order. A failed message is logged and does not stop the next ones."""
    for message in outgoing:
        if message.audio_url:
            _try_send(send_audio, to, message.audio_url)
        _try_send(send_text, to, message.text)


def _try_send(send, to: str, content: str) -> None:
    try:
        send(to, content)
    except Exception:
        log.exception("Meta send failed")
