# Audio scripts (Mooré recordings)

*Source scripts in French for the translator and voice talent. Each script is translated into
Mooré, checked by back-translation, then recorded. File names are fixed: the app looks for
`static/audio/mos/<name>.ogg` (or `.mp3`).*

---

# Scripts audio en mooré : guide pour la traduction et l'enregistrement

## Comment procéder

1. **Traduire** chaque script ci-dessous du français vers le mooré. Cherchez des mots simples,
   ceux qu'emploient les femmes au village, plutôt qu'une traduction mot à mot.
2. **Retraduire** : une deuxième personne, qui n'a pas vu le texte français, retraduit le mooré
   en français. On compare les deux et on corrige les écarts de sens.
   **C'est obligatoire pour les questions `q1` à `q6` et `safety`.**
3. **Faire relire** par l'infirmière référente et deux agents de santé communautaires.
4. **Tester** auprès de deux ou trois femmes : demandez-leur de redire la question avec leurs
   propres mots. Si elles ne comprennent pas pareil, reformulez.
5. **Enregistrer** (voir les consignes techniques en bas de page).

## Qui écoute quoi ?

L'agent fait écouter les audios à la femme sur son téléphone. Les audios d'accueil, de
consentement et les questions s'adressent donc **à la femme** (« vous »). Les audios de
résultat s'adressent **à l'agent**, mais la femme peut les entendre : le ton doit rester calme
et rassurant, sans mot qui fait peur.

**Règles de vocabulaire :**
- Ne jamais dire « dépression », « maladie mentale », « folie » ni aucun diagnostic.
- Parler de « questionnaire », de « comment vous vous sentez », du « résultat ».
- Garder les mêmes mots d'une question à l'autre pour « ces 30 derniers jours » et pour les
  cinq réponses possibles.

---

## 1. `intro`, l'accueil (pour la femme)

Joué juste après que l'agent a envoyé `START`. Durée visée : 15 à 20 secondes.

> Bonjour. L'agent de santé va vous poser quelques questions sur la façon dont vous vous sentez
> ces derniers temps. Pendant la grossesse et après l'accouchement, beaucoup de femmes vivent
> des moments difficiles. Ces questions nous aident à mieux vous accompagner.

## 2. `consent`, le consentement (pour la femme)

Joué juste après `intro`. Durée visée : 25 à 30 secondes.

> Il y a six questions courtes, puis une dernière question. Vous êtes libre de répondre ou non,
> et vous pouvez arrêter à tout moment. Votre nom ne sera pas enregistré. Vos réponses servent
> seulement à votre suivi par l'agent et l'infirmière.
> Est-ce que vous acceptez de répondre ? Dites « oui » ou « non » à l'agent.

*Note : l'agent tape 1 pour oui, 2 pour non. La femme n'a pas à connaître les chiffres.*

## 3. `choices`, les réponses possibles (pour la femme)

Joué une fois avant la première question, puis à nouveau si l'agent tape une réponse
incorrecte. Durée visée : 15 secondes.

> Pour chaque question, dites à l'agent ce qui vous correspond le mieux :
> jamais… rarement… parfois… la plupart du temps… ou tout le temps.

*Note : bien marquer une petite pause entre chaque réponse possible. Ces cinq expressions
doivent être exactement les mêmes dans toutes les questions.*

## 4. Les six questions (pour la femme)

Durée visée : 8 à 12 secondes chacune. Toutes commencent par la même formule.

| Fichier | Script |
|---|---|
| `q1` | Ces 30 derniers jours, combien de fois vous êtes-vous sentie **nerveuse** ? |
| `q2` | Ces 30 derniers jours, combien de fois vous êtes-vous sentie **sans espoir** ? |
| `q3` | Ces 30 derniers jours, combien de fois vous êtes-vous sentie **agitée, au point de ne pas pouvoir rester en place** ? |
| `q4` | Ces 30 derniers jours, combien de fois vous êtes-vous sentie **si triste que rien ne pouvait vous redonner le moral** ? |
| `q5` | Ces 30 derniers jours, combien de fois avez-vous eu l'impression que **tout vous demandait un effort** ? |
| `q6` | Ces 30 derniers jours, combien de fois vous êtes-vous sentie **sans valeur** ? |

*Notes pour la traduction :*
- *Ce sont les six questions de l'échelle K6, un questionnaire reconnu. Le sens doit rester
  très proche de l'original : mieux vaut une phrase un peu longue que fausse.*
- *`q2` « sans espoir » : l'idée est de ne plus voir d'avenir meilleur.*
- *`q4` : en français, le questionnaire dit « si déprimée que… ». Utilisez l'expression mooré
  de la tristesse profonde, pas un mot médical.*
- *`q6` « sans valeur » : l'idée est de se sentir bonne à rien, inutile.*

## 5. `safety`, la question de sécurité (pour la femme)

La question la plus délicate. Voix douce et posée, sans dramatiser. Durée visée : 15 à
20 secondes.

> Une dernière question. Nous la posons à toutes les femmes.
> Ces 30 derniers jours, avez-vous pensé à vous faire du mal ?
> Vous pouvez répondre en toute confiance. Dites « oui » ou « non » à l'agent.

*Note : la retraduction doit confirmer que la question porte bien sur l'envie de se blesser
ou de mettre fin à sa vie, et non sur un mal physique ou une maladie. L'infirmière doit
valider cette formulation.*

## 6. Les résultats (pour l'agent, la femme peut entendre)

Durée visée : 10 à 15 secondes chacun.

| Fichier | Script |
|---|---|
| `result_green` | Merci. Les réponses ne montrent pas de signe d'alerte aujourd'hui. Continuez le suivi habituel. |
| `result_orange` | Merci. Certaines réponses demandent qu'on reste attentif. Prenez le temps d'écouter la femme. Un nouveau questionnaire est prévu dans deux semaines. |
| `result_red` | Merci. Les réponses demandent une attention rapide. L'infirmière est prévenue. Accompagnez la femme au centre de santé dès que possible. |

*Note : ne pas employer de mots qui inquiètent (« grave », « danger », « malade »). Le niveau
(vert, orange, rouge) s'affiche déjà par écrit pour l'agent : pas besoin de le dire dans
l'audio.*

## 7. Fin de questionnaire

| Fichier | Quand | Script |
|---|---|---|
| `thanks` | Après le résultat | Merci beaucoup pour votre confiance et pour le temps que vous avez donné. |
| `stop` | Si la femme refuse, ou si l'agent arrête le questionnaire | D'accord, nous nous arrêtons ici. Merci pour votre temps. |

*Note : `stop` sert dans les deux cas (refus au début, ou arrêt en cours). Il doit donc rester
neutre et ne pas supposer que des questions ont été posées.*

---

## Consignes techniques d'enregistrement

- **Voix :** une seule personne pour tous les fichiers, de langue maternelle mooré, voix calme et
  chaleureuse. Une voix de femme est conseillée.
- **Lieu :** une pièce calme, sans écho (des tissus et des rideaux aident), sans bruit de
  ventilateur ni de rue. Le téléphone à 20 cm de la bouche suffit.
- **Débit :** lent et clair, avec de petites pauses. Écoutez chaque fichier avant de passer au
  suivant.
- **Format :**
  - de préférence **`.ogg` (codec Opus), mono**, environ 32 à 64 kb/s. WhatsApp l'affiche
    alors comme une note vocale avec bouton de lecture ;
  - sinon `.mp3` mono, 64 kb/s ;
  - moins de 1 Mo par fichier.
- **Noms de fichiers exacts** (en minuscules, sans espace), à déposer dans `static/audio/mos/` :
  `intro`, `consent`, `choices`, `q1`, `q2`, `q3`, `q4`, `q5`, `q6`, `safety`, `result_green`,
  `result_orange`, `result_red`, `thanks`, `stop`.
- **Droits :** les audios sont publiés sous licence **CC-BY 4.0**. Faites signer à la personne
  qui enregistre une autorisation simple : elle accepte cette diffusion et indique comment elle
  souhaite être créditée.

## Fiche de suivi

| Fichier | Traduit | Retraduit | Validé infirmière | Testé femmes | Enregistré |
|---|---|---|---|---|---|
| intro | ☐ | ☐ | ☐ | ☐ | ☑ |
| consent | ☐ | ☐ | ☐ | ☐ | ☑ |
| choices | ☐ | ☐ | ☐ | ☐ | ☑ |
| q1 | ☐ | ☐ | ☐ | ☐ | ☑ |
| q2 | ☐ | ☐ | ☐ | ☐ | ☑ |
| q3 | ☐ | ☐ | ☐ | ☐ | ☑ |
| q4 | ☐ | ☐ | ☐ | ☐ | ☑ |
| q5 | ☐ | ☐ | ☐ | ☐ | ☑ |
| q6 | ☐ | ☐ | ☐ | ☐ | ☑ |
| safety | ☐ | ☐ | ☐ | ☐ | ☑ |
| result_green | ☐ | ☐ | ☐ | — | ☑ |
| result_orange | ☐ | ☐ | ☐ | — | ☑ |
| result_red | ☐ | ☐ | ☐ | — | ☑ |
| thanks | ☐ | ☐ | ☐ | — | ☑ |
| stop | ☐ | ☐ | ☐ | — | ☑ |
