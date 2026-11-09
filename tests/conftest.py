import pytest


@pytest.fixture(autouse=True)
def default_provider(monkeypatch):
    """Tests use Twilio unless they choose otherwise, whatever the local .env says."""
    monkeypatch.setenv("WHATSAPP_PROVIDER", "twilio")
