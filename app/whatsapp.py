"""Choose the WhatsApp provider from WHATSAPP_PROVIDER: "twilio" (default) or "meta"."""

import os
from types import ModuleType

from app import meta_client, twilio_client


def provider() -> ModuleType:
    """Module exposing send_text(to, body), send_audio(to, url) and send_all(to, outgoing)."""
    if os.environ.get("WHATSAPP_PROVIDER", "twilio").lower() == "meta":
        return meta_client
    return twilio_client
