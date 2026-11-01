"""End-to-end webhook tests. Twilio and Supabase are replaced by in-memory fakes: no network."""

import pytest
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from app import main
from app.messages import Outgoing

TOKEN = "test-auth-token"
BASE = "https://sunoogo.example.ngrok-free.app"
CHW = "whatsapp:+22670000000"


NURSE = "whatsapp:+22675555555"


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("PUBLIC_BASE_URL", BASE)
    monkeypatch.setenv("SUNOOGO_LANG", "fr")
    monkeypatch.setenv("NURSE_WHATSAPP_TO", NURSE)
    monkeypatch.setattr(main, "_conversations", {})
    saved, sent = [], []
    monkeypatch.setattr(main.db, "save_session", saved.append)
    monkeypatch.setattr(main.db, "insert_alert", lambda row: None)
    monkeypatch.setattr(main.summary, "summarize", lambda session: None)
    monkeypatch.setattr(
        main.twilio_client, "send_all", lambda to, outgoing: sent.append((to, outgoing))
    )
    monkeypatch.setattr(
        main.twilio_client, "send_text", lambda to, body: sent.append((to, [Outgoing(body)]))
    )
    return saved, sent


@pytest.fixture
def client(env):
    return TestClient(main.app)


def post(client, body, sender=CHW, signature=None):
    params = {"From": sender, "To": "whatsapp:+14155238886", "Body": body, "NumMedia": "0"}
    if signature is None:
        signature = RequestValidator(TOKEN).compute_signature(f"{BASE}/whatsapp", params)
    return client.post("/whatsapp", data=params, headers={"X-Twilio-Signature": signature})


def texts(sent):
    return [message.text for _, outgoing in sent for message in outgoing]


def test_rejects_bad_signature(client, env):
    saved, sent = env
    response = post(client, "START F-0042", signature="forged")
    assert response.status_code == 403
    assert saved == [] and sent == []


def test_returns_empty_twiml(client):
    response = post(client, "bonjour")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<Response></Response>" in response.text


def test_full_session_red_by_safety(client, env):
    saved, sent = env
    for body in ["START F-0042", "1", "1", "1", "1", "1", "1", "1", "2"]:
        assert post(client, body).status_code == 200

    chw_texts = [m.text for to, out in sent if to == CHW for m in out]
    assert chw_texts[0].endswith("F-0042.")
    assert chw_texts[-2].startswith("Résultat du questionnaire : ROUGE")

    # The nurse alert goes out before the result message to the CHW.
    nurse_index = next(i for i, (to, _) in enumerate(sent) if to == NURSE)
    result_index = next(
        i for i, (_, out) in enumerate(sent) if out[0].text.startswith("Résultat")
    )
    assert nurse_index < result_index
    alert = sent[nurse_index][1][0].text
    assert "F-0042" in alert and "+22670000000" in alert and "ROUGE" in alert

    # Saved from consent onwards: consent + 6 answers + completion, always the same row id.
    assert len(saved) == 8
    assert len({row["id"] for row in saved}) == 1
    final = saved[-1]
    assert final["chw_phone"] == "+22670000000"
    assert final["woman_code"] == "F-0042"
    assert final["level"] == "red" and final["safety_flag"] is True and final["score"] == 0
    assert "completed_at" in final
    assert "followup_due" not in final
    assert main._conversations == {}


def test_orange_session_sets_followup_and_sends_no_alert(client, env):
    saved, sent = env
    for body in ["START F-0007", "1", "3", "3", "3", "3", "3", "1", "1"]:
        post(client, body)
    assert saved[-1]["level"] == "orange"
    assert "followup_due" in saved[-1]
    assert all(to == CHW for to, _ in sent)


def test_summary_is_sent_last_after_completion(client, env, monkeypatch):
    _, sent = env
    monkeypatch.setattr(main.summary, "summarize", lambda session: "Résumé : test.")
    for body in ["START F-0042", "1", "1", "1", "1", "1", "1", "1", "1"]:
        post(client, body)
    assert texts(sent)[-1] == "Résumé : test."
    assert texts(sent)[-2].startswith("Merci")


def test_alert_failure_does_not_block_the_result(client, env, monkeypatch):
    _, sent = env

    def broken_send_text(to, body):
        raise RuntimeError("twilio down")

    monkeypatch.setattr(main.twilio_client, "send_text", broken_send_text)
    for body in ["START F-0042", "1", "5", "5", "5", "5", "5", "5", "1"]:
        post(client, body)
    assert texts(sent)[-2].startswith("Résultat du questionnaire : ROUGE")


def test_refusal_saves_nothing(client, env):
    saved, sent = env
    post(client, "START F-0042")
    post(client, "2")
    assert saved == []
    assert texts(sent)[-1] == "D'accord, rien n'a été enregistré. Merci."
    assert main._conversations == {}


def test_conversations_are_kept_per_chw(client, env):
    saved, _ = env
    other = "whatsapp:+22671111111"
    post(client, "START F-0001")
    post(client, "START F-0002", sender=other)
    post(client, "1")
    post(client, "1", sender=other)
    assert {row["woman_code"] for row in saved} == {"F-0001", "F-0002"}
    assert len({row["id"] for row in saved}) == 2


def test_new_session_gets_a_new_id(client, env):
    saved, _ = env
    for body in ["START F-0042", "1", "STOP", "START F-0042", "1"]:
        post(client, body)
    assert len({row["id"] for row in saved}) == 2


def test_database_failure_does_not_block_the_conversation(client, env, monkeypatch):
    _, sent = env

    def broken_save(row):
        raise RuntimeError("supabase down")

    monkeypatch.setattr(main.db, "save_session", broken_save)
    post(client, "START F-0042")
    assert post(client, "1").status_code == 200
    assert texts(sent)[-1].startswith("Question 1/6")


def test_audio_files_are_served_with_audio_content_type(client):
    audio_dir = main.STATIC_DIR / "audio" / "mos"
    probe = audio_dir / "_test_probe.ogg"
    probe.write_bytes(b"OggS")
    try:
        response = client.get("/static/audio/mos/_test_probe.ogg")
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/ogg"
    finally:
        probe.unlink()
