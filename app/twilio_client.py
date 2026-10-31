"""Send WhatsApp text and audio messages through the Twilio REST API.

WhatsApp drops the text body of an audio message, so each Outgoing is sent as two messages:
first the audio (if any), then the text.
"""

import logging
import os
from functools import lru_cache

from twilio.rest import Client

from app.messages import Outgoing

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client() -> Client:
    return Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])


def _sender() -> str:
    return os.environ["TWILIO_WHATSAPP_FROM"]


def send_text(to: str, body: str) -> None:
    _client().messages.create(from_=_sender(), to=to, body=body)


def send_audio(to: str, media_url: str) -> None:
    _client().messages.create(from_=_sender(), to=to, media_url=[media_url])


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
        log.exception("Twilio send failed")
