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

## Alerts, summary, dashboard and DHIS2

- **Nurse alert**: a red result (score ≥ 13 or positive safety question) sends a WhatsApp alert to
  `NURSE_WHATSAPP_TO` before the result reaches the CHW, and is logged in the `alerts` table.
  In the Twilio sandbox the nurse's phone must also have joined the sandbox.
- **Case summary**: after each completed questionnaire, Claude writes a 3-sentence French summary
  for the CHW from the structured result only (never free text, never a name). It is dropped if
  it names a diagnosis or is too long. Without `ANTHROPIC_API_KEY` it is simply skipped.
- **Public dashboard**: `<PUBLIC_BASE_URL>/dashboard` shows weekly anonymised totals
  (JSON at `/api/stats`), read from the `public_stats` view only.
- **DHIS2**: `python -m app.dhis2 --week 2026-W45` pushes the week's totals (sessions completed,
  green, orange, red) to DHIS2 with the `dataValueSets` API. The "SuNoogo perinatal screening"
  data set is created or updated on each run. Add `--dry-run` to validate without saving.
- **Follow-ups**: `python -m app.followups` lists orange results whose 14-day follow-up is due.

Mooré audio files go in `static/audio/mos/` (`intro`, `consent`, `choices`, `q1`…`q6`, `safety`,
`result_green`, `result_orange`, `result_red`, `thanks`, `stop`), as `.ogg` (Opus codec, shown as a
voice note) or `.mp3`. Missing files are skipped and only the text is sent.

## License

Code: MIT (see `LICENSE`). Audio files: CC-BY 4.0.
