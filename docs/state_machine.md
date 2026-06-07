# Machine à états — Cycle de vie d'un dossier

Chaque dossier élève suit une séquence d'états explicite et auditable. Toute
transition est journalisée (qui, quand, quoi, résultat).

## 1. Les états

| État | Signification |
|---|---|
| `NEW` | Dossier créé à l'import, pas encore pris en charge |
| `IN_REVIEW` | Pris en charge par un conseiller, en cours d'examen |
| `INTERVENTION` | Un plan d'intervention est lancé (rendez-vous planifié) |
| `FOLLOW_UP` | Phase de suivi / ré-évaluation |
| `CLOSED` | Dossier clôturé (résolu ou archivé) |

## 2. Diagramme des transitions

```
                  prise en charge          planification
   ┌───────┐   (Conseiller/Directeur)   ┌──────────────┐   (RDV planifié)
   │  NEW  │ ───────────────────────▶  │  IN_REVIEW   │ ───────────────┐
   └───────┘                            └──────────────┘                │
       ▲                                                                ▼
       │ import (Enseignant/Directeur)                        ┌────────────────┐
       │                                                      │  INTERVENTION  │
       │                                                      └────────────────┘
       │                                                                │
       │                       RDV manqué (AUTOMATIQUE)                 │
       │                       + relance/orientation journalisée        ▼
       │                                                      ┌────────────────┐
       │                                                      │   FOLLOW_UP    │
       │                                                      └────────────────┘
       │                                                                │
       │                                       clôture (Conseiller/Dir.)│
       │                                                                ▼
       │                                                      ┌────────────────┐
       └──────────────────────────────────────────────────── │     CLOSED     │
                                                              └────────────────┘
```

## 3. Transitions détaillées

| # | De → Vers | Déclencheur | Acteur | Effet de bord |
|---|---|---|---|---|
| T1 | (—) → `NEW` | Import CSV valide | Enseignant / Directeur | Calcul du score + snapshot de risque |
| T2 | `NEW` → `IN_REVIEW` | Prise en charge | Conseiller / Directeur | Événement journalisé |
| T3 | `IN_REVIEW` → `INTERVENTION` | Planification d'un rendez-vous | Conseiller / Directeur | Rendez-vous créé |
| T4 | `INTERVENTION` → `FOLLOW_UP` | **Rendez-vous manqué** | **Automatique** | `MISSED_APPOINTMENT_ALERT` + `REFERRAL_TRIGGERED`, nouveau snapshot |
| T5 | `*` → `CLOSED` | Clôture | Conseiller / Directeur | Événement journalisé |

## 4. Transitions bloquées (failure injection)

Le sujet exige au moins un échec contrôlé par scénario. Amal en gère plusieurs :

| Tentative | Comportement attendu |
|---|---|
| Import d'un CSV au **mauvais schéma** | Rejet propre, redirection + message d'erreur, **pas de plantage** |
| Action sur rendez-vous par un rôle **non autorisé** (ex. enseignant) | **403** + événement `DENIED` journalisé avec la raison |
| Accès d'un **élève** au tableau de bord staff | **403** + journalisé |
| Enseignant qui tente d'**initier** une conversation | **403** (seul l'élève initie) |

## 5. Lien avec les deux scénarios du sujet

- **Scénario 1 — Alerte précoce (éducation)** : T1 → T2, puis tableau de bord
  priorisé et export filtré. Échec injecté : mauvais schéma CSV.
- **Scénario 2 — Suivi (santé / bien-être)** : T3 → T4 (automatique sur RDV
  manqué) avec relance/orientation tracée et chronologie complète. Échec
  injecté : action non autorisée bloquée et journalisée.

## 6. Auditabilité

Chaque transition crée un `CaseEvent` (acteur, horodatage, action, résultat,
raison). La piste d'audit est **infalsifiable** par chaînage de hash (voir
`risk_register.md` et la commande `python manage.py verify_audit`).
