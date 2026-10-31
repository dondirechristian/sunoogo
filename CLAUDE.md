# SũNoogo — contexte projet pour Claude Code

## En une phrase
Assistant vocal WhatsApp en mooré qui aide les agents de santé communautaires à dépister la dépression périnatale (échelle K6), alerte l'infirmière référente pour les cas à risque, et envoie des indicateurs anonymisés vers DHIS2.

Projet candidat à UNICEF Femtech Ventures (dépôt le 9 novembre 2026). Le prototype doit marcher de bout en bout sur un vrai téléphone le 5 novembre au soir.

## Règles non négociables
- **Le score n'est JAMAIS calculé par un LLM.** Règle fixe en Python, testée unitairement.
- **Aucun diagnostic** dans les messages : on parle de « résultat du questionnaire », jamais de « dépression ».
- **Aucun nom de femme stocké.** Chaque femme = un code (ex. `F-0042`) saisi par l'agent. Seul le numéro de l'agent est stocké.
- **Question de sécurité positive = niveau rouge**, quel que soit le score, et alerte immédiate.
- Secrets uniquement dans `.env` (jamais commité). Fournir `.env.example`.
- Code, commentaires, README et commits **en anglais** (évaluation UNICEF). Licence **MIT** pour le code, **CC-BY 4.0** pour les audios.

## Stack
- Python 3.11+, FastAPI (webhook + pages)
- Twilio WhatsApp Sandbox (prototype) — webhook entrant `POST /whatsapp`
- Supabase (Postgres) via `supabase-py`
- API Anthropic (Claude) uniquement pour le résumé de cas en français
- DHIS2 : instance de démonstration publique (play.dhis2.org), API `dataValueSets`
- Dev local : ngrok pour exposer le webhook à Twilio
- Tests : pytest

## Architecture
```
sunoogo/
├── app/
│   ├── main.py            # FastAPI : /whatsapp, /dashboard, /static
│   ├── flow.py            # machine à états de la session (pure, testable)
│   ├── scoring.py         # score K6 + niveau + règle de sécurité
│   ├── messages.py        # textes FR/EN + noms des fichiers audio
│   ├── twilio_client.py   # envoi texte + audio
│   ├── db.py              # accès Supabase
│   ├── alerts.py          # alerte WhatsApp à l'infirmière référente
│   ├── summary.py         # résumé LLM (entrée = données structurées uniquement)
│   └── dhis2.py           # agrégation hebdo + push dataValueSets
├── static/audio/mos/      # audios mooré (.mp3 ou .ogg)
├── static/dashboard.html  # compteurs publics anonymisés
├── sql/schema.sql
├── tests/
├── docs/SAFETY.md
├── .env.example
├── LICENSE
└── README.md
```

## Déroulé d'une session (machine à états)
1. L'agent envoie `START F-0042` → audio d'accueil + audio de consentement.
2. Réponse `1` = accepte, `2` = refuse (fin polie, rien n'est stocké).
3. 6 questions K6, une par une : audio mooré + texte FR court. Réponse attendue : chiffre `1` à `5`.
   - Mapping : 1 = jamais (0 pt), 2 = rarement (1), 3 = parfois (2), 4 = la plupart du temps (3), 5 = tout le temps (4).
   - Réponse invalide → réécoute de l'audio d'explication des choix, sans avancer.
4. Question de sécurité : « Ces 30 derniers jours, avez-vous pensé à vous faire du mal ? » `1` = non, `2` = oui.
5. Calcul : score 0–24. Niveaux (seuils provisoires, à valider par l'infirmière, dans `scoring.py` en constantes) :
   - VERT : score ≤ 7 et sécurité = non
   - ORANGE : 8–12 et sécurité = non
   - ROUGE : ≥ 13 ou sécurité = oui
6. Message de résultat à l'agent (audio mooré + texte FR) + résumé LLM pour l'agent.
7. ROUGE → alerte immédiate à l'infirmière référente (numéro dans `.env`).
8. ORANGE → rappel programmé à J+14 (pour le prototype : champ `followup_due` en base + script qui liste les rappels dus).
9. `STOP` à tout moment → fin de session.

Questions K6 (référence, période = 30 derniers jours) : nerveuse ; sans espoir ; agitée, ne tient pas en place ; si déprimée que rien ne peut lui remonter le moral ; tout est un effort ; sans valeur.

## Fichiers audio attendus (`static/audio/mos/`)
`intro`, `consent`, `choices` (explication des chiffres 1 à 5), `q1` … `q6`, `safety`, `result_green`, `result_orange`, `result_red`, `thanks`, `stop`.
Tant qu'ils n'existent pas : envoyer seulement le texte FR, sans planter.

## Données (sql/schema.sql)
- `sessions` : id, chw_phone, woman_code, consent, answers (jsonb), score, level, safety_flag, started_at, completed_at, followup_due
- `alerts` : id, session_id, sent_to, sent_at, status
- Vue `public_stats` : nombre de sessions, terminées, par niveau, alertes envoyées — **aucune donnée individuelle**

## DHIS2
- Script `python -m app.dhis2 --week 2026-W45` : agrège `public_stats` de la semaine et pousse vers l'instance démo.
- Créer si besoin, via l'API, un data set de démo « SuNoogo perinatal screening » avec 4 éléments : sessions_completed, level_green, level_orange, level_red.
- URL, utilisateur et mot de passe dans `.env`.

## Ordre de travail (4 jours)
1. J1 : squelette repo, `schema.sql`, `scoring.py` + tests, `flow.py` + tests (sans réseau).
2. J2 : webhook Twilio + envoi texte/audio, session complète testée sur téléphone via ngrok.
3. J3 : alertes, résumé LLM, page `dashboard.html`, script DHIS2.
4. J4 : README anglais avec captures, `docs/SAFETY.md`, démo de bout en bout, nettoyage.

## Style
- Fonctions courtes, logique métier pure (pas d'appel réseau dans `flow.py` et `scoring.py`).
- Chaque étape terminée = un commit clair en anglais.
- Avant d'écrire du code qui touche un service externe, vérifier sa doc actuelle plutôt que de supposer l'API.
