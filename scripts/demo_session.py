"""Replay a full CHW screening session without a phone, and print the WhatsApp transcript.

Messages go through the real webhook (with a valid Twilio signature), the real state machine,
scoring and database; only outgoing WhatsApp messages are printed instead of sent.

Usage:
    python scripts/demo_session.py --scenario red-safety
    python scripts/demo_session.py --scenario orange --no-db   # no Supabase needed
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()
os.environ.setdefault("TWILIO_AUTH_TOKEN", "demo-token")
os.environ.setdefault("PUBLIC_BASE_URL", "https://sunoogo.example")
os.environ.setdefault("NURSE_WHATSAPP_TO", "whatsapp:+22600000001")

from fastapi.testclient import TestClient  # noqa: E402
from twilio.request_validator import RequestValidator  # noqa: E402

from app import db, main, twilio_client  # noqa: E402

CHW = "whatsapp:+22600000000"
SCENARIOS = {
    "green": ["1", "1", "2", "1", "2", "1", "1"],
    "orange": ["3", "3", "3", "2", "3", "2", "1"],
    "red": ["4", "5", "4", "4", "3", "4", "1"],
    "red-safety": ["2", "1", "2", "1", "2", "1", "2"],
}


def show(to: str, text: str) -> None:
    who = "NURSE" if to == os.environ["NURSE_WHATSAPP_TO"] else "BOT  "
    print(f"  {who} > {text}")


def main_cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="red-safety")
    parser.add_argument("--code", default="F-0042", help="woman code, e.g. F-0042")
    parser.add_argument("--no-db", action="store_true", help="do not write to Supabase")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    twilio_client.send_text = lambda to, body: show(to, body)
    twilio_client.send_audio = lambda to, url: show(to, f"[audio] {url}")
    if args.no_db:
        db.save_session = lambda row: None
        db.insert_alert = lambda row: None

    client = TestClient(main.app)
    url = os.environ["PUBLIC_BASE_URL"].rstrip("/") + "/whatsapp"
    validator = RequestValidator(os.environ["TWILIO_AUTH_TOKEN"])

    for body in [f"START {args.code}", "1", *SCENARIOS[args.scenario]]:
        print(f"  CHW   > {body}")
        params = {"From": CHW, "To": "whatsapp:+14155238886", "Body": body, "NumMedia": "0"}
        headers = {"X-Twilio-Signature": validator.compute_signature(url, params)}
        response = client.post("/whatsapp", data=params, headers=headers)
        response.raise_for_status()
    return 0


if __name__ == "__main__":
    sys.exit(main_cli())
