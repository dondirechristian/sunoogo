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

## Running the WhatsApp prototype locally

1. Create the tables: paste `sql/schema.sql` into the Supabase SQL editor and run it.
2. Install dependencies: `.venv/Scripts/python -m pip install -r requirements.txt`.
3. Start the server: `.venv/Scripts/python -m uvicorn app.main:app --port 8000`.
4. Expose it: `ngrok http 8000`, then set `PUBLIC_BASE_URL` in `.env` to the ngrok HTTPS URL
   and restart the server (Twilio signatures are checked against this URL).
5. In the Twilio console (Messaging > Try it out > WhatsApp sandbox), set
   "When a message comes in" to `<PUBLIC_BASE_URL>/whatsapp`, method `POST`.
6. From the CHW phone, join the sandbox (`join <code>`), then send `START F-0042`.

Mooré audio files go in `static/audio/mos/` (`intro`, `consent`, `choices`, `q1`…`q6`, `safety`,
`result_green`, `result_orange`, `result_red`, `thanks`, `stop`), as `.ogg` (Opus codec, shown as a
voice note) or `.mp3`. Missing files are skipped and only the text is sent.

## License

Code: MIT (see `LICENSE`). Audio files: CC-BY 4.0.
