# SũNoogo

WhatsApp voice assistant in Mooré that helps community health workers (CHWs) screen for perinatal
psychological distress using the K6 scale, alerts the referral nurse for high-risk cases, and sends
anonymised indicators to DHIS2.

> Status: prototype under construction.

## Key principles

- The score is computed by a fixed, unit-tested Python rule (`app/scoring.py`), never by an LLM.
- Messages never state a diagnosis; they report a "questionnaire result".
- No woman's name is stored. Each woman is identified by a code (e.g. `F-0042`) entered by the CHW.
- A positive safety question always yields the red level and an immediate alert.

## Development

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # Windows
.venv/Scripts/python -m pytest
```

Copy `.env.example` to `.env` and fill in the secrets. Never commit `.env`.

## License

Code: MIT (see `LICENSE`). Audio files: CC-BY 4.0.
