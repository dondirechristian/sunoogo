from types import SimpleNamespace

import anthropic
import pytest

from app import alerts, summary
from app.flow import Session, State
from app.scoring import evaluate


def completed(answers=(5, 5, 4, 3, 2, 1), safety=False) -> Session:
    return Session(
        woman_code="F-0042",
        state=State.COMPLETED,
        consent=True,
        answers=answers,
        safety_flag=safety,
        result=evaluate(answers, safety),
    )


# --- Nurse alert --------------------------------------------------------------------------


def test_alert_text_has_code_phone_and_level_but_no_diagnosis():
    text = alerts.alert_text(completed(safety=True), "+22670000000")
    assert "F-0042" in text and "+22670000000" in text
    assert "ROUGE" in text and "Question de sécurité : OUI" in text
    assert not summary.FORBIDDEN.search(text)


def test_send_alert_records_sent_status(monkeypatch):
    sent, recorded = [], []
    monkeypatch.setenv("NURSE_WHATSAPP_TO", "whatsapp:+22675555555")
    monkeypatch.setattr(alerts.twilio_client, "send_text", lambda to, body: sent.append(to))
    monkeypatch.setattr(alerts.db, "insert_alert", recorded.append)
    alerts.send_alert("sid", "+22670000000", completed())
    assert sent == ["whatsapp:+22675555555"]
    assert recorded == [{"session_id": "sid", "sent_to": "whatsapp:+22675555555", "status": "sent"}]


def test_send_alert_records_failure_and_never_raises(monkeypatch):
    recorded = []

    def boom(to, body):
        raise RuntimeError("twilio down")

    monkeypatch.setattr(alerts.twilio_client, "send_text", boom)
    monkeypatch.setattr(alerts.db, "insert_alert", recorded.append)
    alerts.send_alert("sid", "+22670000000", completed())
    assert recorded[0]["status"] == "failed"


def test_send_alert_survives_database_failure(monkeypatch):
    sent = []

    def db_down(row):
        raise RuntimeError("supabase down")

    monkeypatch.setattr(alerts.twilio_client, "send_text", lambda to, body: sent.append(to))
    monkeypatch.setattr(alerts.db, "insert_alert", db_down)
    alerts.send_alert("sid", "+22670000000", completed())
    assert len(sent) == 1


# --- Case summary -------------------------------------------------------------------------


class FakeClient:
    def __init__(self, text="La femme dit se sentir nerveuse.", stop_reason="end_turn", error=None):
        self.calls = []
        self._response = SimpleNamespace(
            stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)]
        )
        self._error = error
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._response


def test_case_facts_are_structured_and_contain_no_name():
    facts = summary.case_facts(completed())
    assert facts["niveau"] == "red"
    assert facts["score"] == "14/24"
    assert facts["reponses"]["nerveuse"] == "tout le temps"
    assert "F-0042" not in str(facts)


def test_summarize_uses_structured_input_and_prefixes_output():
    client = FakeClient()
    assert summary.summarize(completed(), client) == "Résumé : La femme dit se sentir nerveuse."
    call = client.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default"
    assert '"niveau": "red"' in call["messages"][0]["content"]


@pytest.mark.parametrize(
    "text",
    [
        "Elle présente une dépression.",
        "Le diagnostic est clair.",
        "Cette maladie est fréquente.",
        "x" * 800,
        "",
    ],
)
def test_summarize_rejects_unsafe_or_bad_output(text):
    assert summary.summarize(completed(), FakeClient(text=text)) is None


def test_summarize_ignores_refusal():
    assert summary.summarize(completed(), FakeClient(stop_reason="refusal")) is None


def test_summarize_handles_api_errors():
    error = anthropic.APIConnectionError(request=None)
    assert summary.summarize(completed(), FakeClient(error=error)) is None


def test_summarize_without_api_key_is_skipped(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert summary.summarize(completed()) is None
