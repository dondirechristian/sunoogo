"""Outgoing message texts (French / English) and Mooré audio file names, keyed by message key.

Message keys are emitted by app/flow.py (see flow.MESSAGE_KEYS). Each key maps to a short text
and, optionally, to a Mooré audio file in static/audio/mos/. Missing audio files are skipped
so that the prototype keeps working with text only.

Wording rule: never name a diagnosis. We only speak of a "questionnaire result".
"""

from dataclasses import dataclass
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent.parent / "static" / "audio" / "mos"
AUDIO_URL_PATH = "/static/audio/mos"
# Preferred first: OGG/Opus is shown as a WhatsApp voice note.
AUDIO_EXTENSIONS = (".ogg", ".mp3")

DEFAULT_LANG = "fr"

_CHOICES_FR = "1 = jamais, 2 = rarement, 3 = parfois, 4 = la plupart du temps, 5 = tout le temps"
_CHOICES_EN = "1 = never, 2 = rarely, 3 = sometimes, 4 = most of the time, 5 = all of the time"
_PERIOD_FR = "Ces 30 derniers jours, à quelle fréquence vous êtes-vous sentie"
_PERIOD_EN = "In the last 30 days, how often did you feel"

TEXTS = {
    "fr": {
        "help": "Pour commencer un questionnaire, envoyez START suivi du code de la femme, "
        "par exemple : START F-0042. Envoyez STOP à tout moment pour arrêter.",
        "invalid_code": "Code invalide. Le code a la forme F-0042 (F, tiret, 4 chiffres). "
        "N'écrivez jamais le nom de la femme. Exemple : START F-0042",
        "session_in_progress": "Un questionnaire est déjà en cours. Répondez à la question, "
        "ou envoyez STOP pour l'arrêter.",
        "intro": "Questionnaire de bien-être pour {woman_code}.",
        "consent": "Demandez à la femme si elle accepte de répondre à quelques questions sur "
        "comment elle se sent. Son nom n'est pas enregistré. "
        "Répondez 1 si elle accepte, 2 si elle refuse.",
        "consent_refused": "D'accord, rien n'a été enregistré. Merci.",
        "choices": f"Répondez à chaque question par un chiffre : {_CHOICES_FR}.",
        "q1": f"Question 1/6. {_PERIOD_FR} nerveuse ? (1 à 5)",
        "q2": f"Question 2/6. {_PERIOD_FR} sans espoir ? (1 à 5)",
        "q3": f"Question 3/6. {_PERIOD_FR} agitée, incapable de tenir en place ? (1 à 5)",
        "q4": f"Question 4/6. {_PERIOD_FR} si déprimée que rien ne pouvait vous remonter "
        "le moral ? (1 à 5)",
        "q5": f"Question 5/6. {_PERIOD_FR} que tout était un effort ? (1 à 5)",
        "q6": f"Question 6/6. {_PERIOD_FR} sans valeur ? (1 à 5)",
        "safety": "Dernière question. Ces 30 derniers jours, avez-vous pensé à vous faire "
        "du mal ? Répondez 1 = non, 2 = oui.",
        "result_green": "Résultat du questionnaire : VERT. Pas de signe d'alerte aujourd'hui. "
        "Continuez le suivi habituel.",
        "result_orange": "Résultat du questionnaire : ORANGE. Un nouveau questionnaire est "
        "prévu dans 14 jours. Encouragez la femme à parler de ce qu'elle ressent.",
        "result_red": "Résultat du questionnaire : ROUGE. L'infirmière référente est prévenue. "
        "Orientez la femme vers le centre de santé dès que possible.",
        "thanks": "Merci. Envoyez START suivi d'un code pour un nouveau questionnaire.",
        "stop": "Questionnaire arrêté. Merci.",
    },
    "en": {
        "help": "To start a questionnaire, send START followed by the woman's code, "
        "for example: START F-0042. Send STOP at any time to end it.",
        "invalid_code": "Invalid code. The code looks like F-0042 (F, dash, 4 digits). "
        "Never type the woman's name. Example: START F-0042",
        "session_in_progress": "A questionnaire is already in progress. Answer the question, "
        "or send STOP to end it.",
        "intro": "Well-being questionnaire for {woman_code}.",
        "consent": "Ask the woman whether she agrees to answer a few questions about how she "
        "feels. Her name is not recorded. Reply 1 if she agrees, 2 if she refuses.",
        "consent_refused": "Understood, nothing has been recorded. Thank you.",
        "choices": f"Answer each question with a digit: {_CHOICES_EN}.",
        "q1": f"Question 1/6. {_PERIOD_EN} nervous? (1 to 5)",
        "q2": f"Question 2/6. {_PERIOD_EN} hopeless? (1 to 5)",
        "q3": f"Question 3/6. {_PERIOD_EN} restless or fidgety? (1 to 5)",
        "q4": f"Question 4/6. {_PERIOD_EN} so depressed that nothing could cheer you up? "
        "(1 to 5)",
        "q5": f"Question 5/6. {_PERIOD_EN} that everything was an effort? (1 to 5)",
        "q6": f"Question 6/6. {_PERIOD_EN} worthless? (1 to 5)",
        "safety": "Last question. In the last 30 days, have you thought about harming "
        "yourself? Reply 1 = no, 2 = yes.",
        "result_green": "Questionnaire result: GREEN. No warning sign today. "
        "Continue the usual follow-up.",
        "result_orange": "Questionnaire result: ORANGE. A new questionnaire is planned in "
        "14 days. Encourage the woman to talk about how she feels.",
        "result_red": "Questionnaire result: RED. The referral nurse is being alerted. "
        "Refer the woman to the health centre as soon as possible.",
        "thanks": "Thank you. Send START followed by a code for a new questionnaire.",
        "stop": "Questionnaire stopped. Thank you.",
    },
}

# Message key -> Mooré audio base name. Keys absent here are text only (CHW instructions).
AUDIO_FILES = {
    "intro": "intro",
    "consent": "consent",
    "consent_refused": "stop",
    "choices": "choices",
    **{f"q{n}": f"q{n}" for n in range(1, 7)},
    "safety": "safety",
    "result_green": "result_green",
    "result_orange": "result_orange",
    "result_red": "result_red",
    "thanks": "thanks",
    "stop": "stop",
}


@dataclass(frozen=True)
class Outgoing:
    text: str
    audio_url: str | None = None


def find_audio_file(name: str, audio_dir: Path = AUDIO_DIR) -> Path | None:
    for ext in AUDIO_EXTENSIONS:
        path = audio_dir / f"{name}{ext}"
        if path.is_file():
            return path
    return None


def build(
    key: str,
    base_url: str,
    lang: str = DEFAULT_LANG,
    woman_code: str = "",
    audio_dir: Path = AUDIO_DIR,
) -> Outgoing:
    """Text and (if the file exists) public audio URL for one message key."""
    text = TEXTS[lang][key].format(woman_code=woman_code)
    audio_name = AUDIO_FILES.get(key)
    audio_path = find_audio_file(audio_name, audio_dir) if audio_name else None
    if audio_path is None:
        return Outgoing(text)
    return Outgoing(text, f"{base_url.rstrip('/')}{AUDIO_URL_PATH}/{audio_path.name}")
