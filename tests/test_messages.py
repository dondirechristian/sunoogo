import re

import pytest

from app.flow import MESSAGE_KEYS
from app.messages import AUDIO_FILES, TEXTS, Outgoing, build

BASE = "https://example.ngrok-free.app"
EXPECTED_AUDIO = {
    "intro", "consent", "choices", "q1", "q2", "q3", "q4", "q5", "q6", "safety",
    "result_green", "result_orange", "result_red", "thanks", "stop",
}  # fmt: skip


@pytest.mark.parametrize("lang", sorted(TEXTS))
def test_every_flow_key_has_a_text(lang):
    assert set(TEXTS[lang]) == set(MESSAGE_KEYS)


@pytest.mark.parametrize("lang", sorted(TEXTS))
def test_texts_never_name_a_diagnosis(lang):
    for key, text in TEXTS[lang].items():
        assert not re.search(r"d[ée]pression|diagnos", text, re.IGNORECASE), key


def test_audio_names_match_the_expected_files():
    assert set(AUDIO_FILES.values()) == EXPECTED_AUDIO
    assert set(AUDIO_FILES) <= set(MESSAGE_KEYS)


def test_build_without_audio_file_is_text_only(tmp_path):
    out = build("q1", BASE, audio_dir=tmp_path)
    assert out == Outgoing(TEXTS["fr"]["q1"])


def test_build_with_audio_file_returns_public_url(tmp_path):
    (tmp_path / "q1.mp3").write_bytes(b"")
    out = build("q1", BASE + "/", audio_dir=tmp_path)
    assert out.audio_url == f"{BASE}/static/audio/mos/q1.mp3"


def test_build_prefers_ogg_over_mp3(tmp_path):
    (tmp_path / "q1.mp3").write_bytes(b"")
    (tmp_path / "q1.ogg").write_bytes(b"")
    assert build("q1", BASE, audio_dir=tmp_path).audio_url.endswith("/q1.ogg")


def test_text_only_keys_never_carry_audio(tmp_path):
    (tmp_path / "help.ogg").write_bytes(b"")
    assert build("help", BASE, audio_dir=tmp_path).audio_url is None


def test_intro_includes_the_woman_code(tmp_path):
    assert "F-0042" in build("intro", BASE, woman_code="F-0042", audio_dir=tmp_path).text


def test_english_texts(tmp_path):
    assert build("stop", BASE, lang="en", audio_dir=tmp_path).text.startswith("Questionnaire stopped")
