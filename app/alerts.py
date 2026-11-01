"""WhatsApp alert to the referral nurse for red-level sessions.

The alert is sent first and recorded afterwards, so that a database failure can never block it.
It carries the woman's code and the CHW's number only: no name, no diagnosis.
"""

import logging
import os

from app import db, twilio_client
from app.flow import Session

log = logging.getLogger(__name__)


def alert_text(session: Session, chw_phone: str) -> str:
    result = session.result
    safety = "OUI" if session.safety_flag else "non"
    return (
        f"ALERTE SuNoogo : résultat ROUGE au questionnaire pour {session.woman_code}. "
        f"Score {result.score}/24. Question de sécurité : {safety}. "
        f"Agent de santé : {chw_phone}. Merci de contacter l'agent dès aujourd'hui."
    )


def send_alert(session_id: str, chw_phone: str, session: Session) -> None:
    """Send the alert and record it. Never raises: it runs as a background task."""
    nurse = os.environ.get("NURSE_WHATSAPP_TO", "")
    status = "sent"
    try:
        twilio_client.send_text(nurse, alert_text(session, chw_phone))
    except Exception:
        status = "failed"
        log.exception("Nurse alert FAILED for session %s", session_id)
    try:
        db.insert_alert({"session_id": session_id, "sent_to": nurse, "status": status})
    except Exception:
        log.exception("Failed to record alert for session %s", session_id)
