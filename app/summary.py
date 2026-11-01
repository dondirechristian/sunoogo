"""Short French case summary for the CHW, written by Claude.

The LLM never scores and never decides the level: it only receives the structured result already
computed by app/scoring.py (level, score, safety flag, answer per item), never free text and
never a name. Its output is checked before sending; on any problem nothing is sent, since the
CHW already has the fixed result message.
"""

import json
import logging
import os
import re

import anthropic

from app.flow import Session

log = logging.getLogger(__name__)

MODEL = "claude-opus-5-5"
MAX_CHARS = 700  # keeps the WhatsApp message short (Twilio limit is 1600)

ITEM_LABELS = (
    "nerveuse",
    "sans espoir",
    "agitée, ne tient pas en place",
    "si déprimée que rien ne peut lui remonter le moral",
    "tout est un effort",
    "sans valeur",
)
CHOICE_LABELS = {1: "jamais", 2: "rarement", 3: "parfois", 4: "la plupart du temps", 5: "tout le temps"}

# Words that would turn the summary into a diagnosis. Item wording ("déprimée") is allowed.
FORBIDDEN = re.compile(r"d[ée]pression|diagnos|maladie|trouble|psychiatri", re.IGNORECASE)

SYSTEM_PROMPT = """\
Tu aides un agent de santé communautaire au Burkina Faso qui vient de faire passer un \
questionnaire de bien-être (échelle K6) à une femme enceinte ou ayant récemment accouché.
Tu reçois le résultat déjà calculé. Écris pour l'agent un résumé en français simple, \
en 3 phrases courtes au maximum, sans liste ni mise en forme.

Règles strictes :
- Ne pose aucun diagnostic. N'emploie jamais les mots « dépression », « maladie », « trouble » \
ou « diagnostic ». Parle seulement du « résultat du questionnaire ».
- Ne change jamais le niveau ni le score, et ne recalcule rien.
- Ne propose aucun médicament.
- Cite les deux ou trois réponses les plus fréquentes pour aider l'agent à en parler avec la femme.
- Termine par la conduite à tenir correspondant au niveau :
  vert : continuer le suivi habituel ;
  orange : écouter la femme et refaire le questionnaire dans 14 jours ;
  rouge : orienter la femme vers le centre de santé dès que possible, l'infirmière référente \
est prévenue.
- Si la question de sécurité est positive, dis à l'agent de ne pas laisser la femme seule si \
elle est en danger immédiat et de joindre l'infirmière tout de suite."""


def case_facts(session: Session) -> dict:
    """Structured input for the LLM. Contains no name and no free text."""
    result = session.result
    return {
        "niveau": result.level.value,
        "score": f"{result.score}/24",
        "question_de_securite_positive": session.safety_flag,
        "reponses": {
            label: CHOICE_LABELS[choice] for label, choice in zip(ITEM_LABELS, session.answers)
        },
    }


def is_acceptable(text: str) -> bool:
    return bool(text) and len(text) <= MAX_CHARS and not FORBIDDEN.search(text)


def summarize(session: Session, client: anthropic.Anthropic | None = None) -> str | None:
    """Return the summary text, or None if it is unavailable or fails the checks."""
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            log.info("ANTHROPIC_API_KEY not set: case summary skipped")
            return None
        client = anthropic.Anthropic(timeout=30.0, max_retries=1)
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=2000,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(case_facts(session), ensure_ascii=False)}],
        )
    except anthropic.APIError:
        log.exception("Case summary request failed")
        return None
    if response.stop_reason != "end_turn":
        log.warning("Case summary not used: stop_reason=%s", response.stop_reason)
        return None
    text = " ".join(b.text for b in response.content if b.type == "text").strip()
    if not is_acceptable(text):
        log.warning("Case summary rejected by output checks")
        return None
    return f"Résumé : {text}"
