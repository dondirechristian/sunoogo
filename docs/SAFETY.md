# Safety protocol

SuNoogo is a **screening aid** for community health workers (CHWs). It helps them run the K6
questionnaire with pregnant and postpartum women and decide when to refer. It does not make
diagnoses, give treatment advice, or replace a health worker's judgement, and it is **not an
emergency service**.

This document describes the safety rules enforced by the code, the escalation path, known
failure modes, and what must be validated before any field use.

## Rules enforced in code

| Rule | Where | How it is checked |
|---|---|---|
| The score is computed by a fixed rule, never by an LLM | `app/scoring.py` | Unit tests on every score 0–24 and every threshold |
| A positive safety question is always **red**, whatever the score | `app/scoring.py` (`risk_level`) | Tested for all 25 possible scores |
| Red triggers an immediate alert to the referral nurse, sent **before** the result reaches the CHW | `app/main.py`, `app/alerts.py` | Webhook test checks the order |
| The alert is sent even if the database is down, and recorded as `sent` or `failed` | `app/alerts.py` | Tests with the WhatsApp provider or Supabase failing |
| Messages never name a diagnosis; they speak of a "questionnaire result" | `app/messages.py` | Test scans every text in every language |
| Nothing is stored before consent; a refusal stores nothing | `app/flow.py`, `sql/schema.sql` | Flow tests + database `CHECK (consent)` |
| No woman's name is stored: only a code `F-0000` typed by the CHW | `app/flow.py`, `sql/schema.sql` | Strict format rejects free text (`START Awa`); database `CHECK` on the format |
| Invalid answers never advance the questionnaire | `app/flow.py` | Tested at every step |
| Public data is aggregated only | `sql/schema.sql` (`public_stats`) | Tables closed by row-level security; only the weekly view is readable |

### Levels

Thresholds are **provisional** and must be validated by the referral nurse. They are constants
in `app/scoring.py` (`GREEN_MAX`, `ORANGE_MAX`).

| Level | Condition | What happens |
|---|---|---|
| Green | score ≤ 7 and safety question negative | Result to the CHW: continue routine follow-up |
| Orange | score 8–12 and safety question negative | Result to the CHW; follow-up questionnaire due 14 days later (`python -m app.followups`) |
| Red | score ≥ 13 **or** safety question positive | Immediate nurse alert, then result to the CHW: refer to the health centre |

## Escalation path for a red result

1. The CHW answers the last question. The server computes the level with the fixed rule.
2. A WhatsApp alert goes to the referral nurse (`NURSE_WHATSAPP_TO`). It contains the woman's
   code, the score, whether the safety question was positive, and the CHW's number. It contains
   no name and no diagnosis.
3. The CHW then receives the red result: "the referral nurse is being alerted, refer the woman
   to the health centre as soon as possible".
4. The nurse contacts the CHW the same day and organises the referral.
5. If the safety question was positive, the case summary tells the CHW not to leave the woman
   alone if she is in immediate danger and to call the nurse right away.

The alert is logged in the `alerts` table with its delivery status, so a failed alert is
visible.

## Use of an LLM

Claude (Anthropic API) is used for one thing only: a three-sentence French summary for the CHW,
sent after the fixed result message.

- **Input:** the level, score, safety flag and the frequency chosen for each of the six items.
  No woman's code, no phone number, no free text.
- **It cannot change the outcome:** the level and the alert are decided before the LLM is
  called, and the LLM output is sent after them.
- **Output checks:** the summary is dropped if it contains diagnostic words (depression,
  diagnosis, illness, disorder, psychiatric), is longer than 700 characters, or if the model
  refuses. The CHW then simply has the fixed result message.
- Without an API key, the summary is skipped and everything else works.

## Failure modes

| Failure | Effect | Mitigation |
|---|---|---|
| Supabase unavailable | Session not saved | Conversation and alert continue; error logged |
| WhatsApp provider cannot deliver the nurse alert | Nurse not informed | Alert recorded as `failed`; the CHW still gets the referral instruction |
| LLM unavailable or output rejected | No summary | The fixed result message is already sent |
| Server restart during a session | The session in progress is lost | The CHW starts again with `START <code>` |
| CHW sends a wrong answer | — | The choices are explained again; the question is repeated |

## Known limitations: to resolve before field use

This is a prototype. Before any use with real women:

1. **Clinical validation of thresholds** with the referral nurse and the district team, and of
   the K6 in this population.
2. **Mooré audio:** translation, back-translation and cognitive testing of every recording with
   CHWs and women. The short French texts must be aligned with a validated French K6 version.
3. **Restrict access to registered CHWs.** Today any WhatsApp number that joins the sandbox can
   start a session. Production needs a whitelist of CHW numbers.
4. **Nurse acknowledgement and second-level escalation.** The nurse does not yet confirm
   receipt; an unacknowledged red alert should escalate to a second contact after a set delay.
5. **WhatsApp Business sender and templates.** The prototype runs on a Meta Cloud API test
   number (or the Twilio sandbox), which only delivers to a few registered numbers, and free-form
   messages only within 24 hours of the recipient's last message. A production alert to the
   nurse needs an approved message template on a registered WhatsApp Business sender.
6. **Local emergency guidance:** add the local emergency contacts and a clear "immediate danger"
   protocol agreed with the health district.
7. **Data protection:** data retention period, access control to the Supabase project, and a
   data protection review under applicable Burkina Faso law. Weekly counts for very small areas
   could re-identify women; publish per-area data only above a minimum count.
8. **Persistent session state:** conversations in progress live in memory and are lost on
   restart.
