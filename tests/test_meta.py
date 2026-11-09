"""Meta WhatsApp Cloud API: webhook verification, signatures, payload parsing, sending. No network."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app import main, meta_client, whatsapp
from app.messages import Outgoing

SECRET = "test-app-secret"
VERIFY = "test-verify-token"
BASE = "https://sunoogo.example.ngrok-free.app"
CHW_DIGITS = "22670000000"
CHW = f"whatsapp:+{CHW_DIGITS}"
NURSE = "whatsapp:+22675555555"


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PROVIDER", "meta")
    monkeypatch.setenv("META_APP_SECRET", SECRET)
    monkeypatch.setenv("META_VERIFY_TOKEN", VERIFY)
    monkeypatch.setenv("PUBLIC_BASE_URL", BASE)
    monkeypatch.setenv("SUNOOGO_LANG", "fr")
    monkeypatch.setenv("NURSE_WHATSAPP_TO", NURSE)
    monkeypatch.setattr(main, "_conversations", {})
    monkeypatch.setattr(main, "_seen_message_ids", main.deque(maxlen=1000))
    saved, sent = [], []
    monkeypatch.setattr(main.db, "save_session", saved.append)
    monkeypatch.setattr(main.db, "insert_alert", lambda row: None)
    monkeypatch.setattr(main.summary, "summarize", lambda session: None)
    monkeypatch.setattr(meta_client, "send_all", lambda to, out: sent.append((to, out)))
    monkeypatch.setattr(
        meta_client, "send_text", lambda to, body: sent.append((to, [Outgoing(body)]))
    )
    return saved, sent


@pytest.fixture
def client(env):
    return TestClient(main.app)


def payload(body, message_id="wamid.1", sender=CHW_DIGITS, kind="text"):
    message = {"from": sender, "id": message_id, "timestamp": "1762700000", "type": kind}
    if kind == "text":
        message["text"] = {"body": body}
    value = {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "15550783881", "phone_number_id": "1065403522"},
        "messages": [message],
    }
    change = {"field": "messages", "value": value}
    return {"object": "whatsapp_business_account", "entry": [{"id": "1", "changes": [change]}]}


def signed_post(client, data, secret=SECRET):
    raw = json.dumps(data).encode()
    signature = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return client.post(
        "/whatsapp/meta",
        content=raw,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature},
    )


def texts(sent, to=None):
    return [m.text for dest, out in sent if to is None or dest == to for m in out]


# --- Provider selection ---------------------------------------------------------------------


def test_provider_defaults_to_twilio(monkeypatch):
    monkeypatch.delenv("WHATSAPP_PROVIDER")
    assert whatsapp.provider() is whatsapp.twilio_client


def test_provider_meta(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PROVIDER", "Meta")
    assert whatsapp.provider() is meta_client


# --- Verification handshake -----------------------------------------------------------------


def test_verify_returns_challenge(client):
    params = {"hub.mode": "subscribe", "hub.verify_token": VERIFY, "hub.challenge": "1158201444"}
    response = client.get("/whatsapp/meta", params=params)
    assert response.status_code == 200
    assert response.text == "1158201444"


def test_verify_rejects_wrong_token(client):
    params = {"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "1"}
    assert client.get("/whatsapp/meta", params=params).status_code == 403


def test_verify_rejects_when_no_token_configured(client, monkeypatch):
    monkeypatch.setenv("META_VERIFY_TOKEN", "")
    params = {"hub.mode": "subscribe", "hub.verify_token": "", "hub.challenge": "1"}
    assert client.get("/whatsapp/meta", params=params).status_code == 403


# --- Signed events --------------------------------------------------------------------------


def test_rejects_bad_signature(client, env):
    saved, sent = env
    assert signed_post(client, payload("START F-0042"), secret="forged").status_code == 403
    assert saved == [] and sent == []


def test_rejects_missing_signature(client, env):
    response = client.post("/whatsapp/meta", json=payload("START F-0042"))
    assert response.status_code == 403


def test_full_session_red_by_safety_alerts_nurse_first(client, env):
    saved, sent = env
    bodies = ["START F-0042", "1", "1", "1", "1", "1", "1", "1", "2"]
    for n, body in enumerate(bodies):
        assert signed_post(client, payload(body, message_id=f"wamid.{n}")).status_code == 200

    chw_texts = texts(sent, CHW)
    assert chw_texts[0].endswith("F-0042.")
    assert chw_texts[-2].startswith("Résultat du questionnaire : ROUGE")
    nurse_index = next(i for i, (to, _) in enumerate(sent) if to == NURSE)
    result_index = next(i for i, (_, out) in enumerate(sent) if out[0].text.startswith("Résultat"))
    assert nurse_index < result_index
    # The CHW number is stored as with Twilio: E.164, without the "whatsapp:" prefix.
    assert saved[-1]["chw_phone"] == f"+{CHW_DIGITS}"
    assert saved[-1]["level"] == "red"


def test_retried_delivery_is_processed_once(client, env):
    _, sent = env
    signed_post(client, payload("START F-0042", message_id="wamid.same"))
    signed_post(client, payload("START F-0042", message_id="wamid.same"))
    assert len(sent) == 1


def test_status_updates_are_ignored(client, env):
    saved, sent = env
    value = {"statuses": [{"id": "wamid.x", "status": "read"}]}
    status = {"entry": [{"changes": [{"value": value}]}]}
    assert signed_post(client, status).status_code == 200
    assert saved == [] and sent == []


def test_non_text_message_gets_help(client, env):
    _, sent = env
    signed_post(client, payload("", kind="audio"))
    assert texts(sent)[0].startswith("Pour commencer")


def test_meta_messages_parsing():
    found = main.meta_messages(payload("START F-0042", message_id="wamid.9"))
    assert found == [("wamid.9", CHW, "START F-0042")]


# --- Sending --------------------------------------------------------------------------------


def test_recipient_is_digits_only():
    assert meta_client.recipient("whatsapp:+22670000000") == "22670000000"
    assert meta_client.recipient("+22670000000") == "22670000000"


def test_text_payload():
    assert meta_client.text_payload(CHW, "Bonjour") == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": CHW_DIGITS,
        "type": "text",
        "text": {"body": "Bonjour"},
    }


AUDIO = f"{BASE}/static/audio/mos"


@pytest.mark.parametrize("url, voice", [(f"{AUDIO}/q1.ogg", True), (f"{AUDIO}/q1.mp3", False)])
def test_audio_payload_voice_note_for_ogg(url, voice):
    data = meta_client.audio_payload(CHW, url)
    assert data["type"] == "audio"
    assert data["audio"] == {"link": url, "voice": voice}


def test_send_all_sends_audio_then_text_and_survives_errors(monkeypatch):
    posted = []

    def fake_post(data):
        posted.append(data["type"])
        if data["type"] == "audio":
            raise RuntimeError("Meta API 400")

    monkeypatch.setattr(meta_client, "_post", fake_post)
    meta_client.send_all(CHW, [Outgoing("Question 1/6", f"{AUDIO}/q1.ogg"), Outgoing("Merci")])
    assert posted == ["audio", "text", "text"]
