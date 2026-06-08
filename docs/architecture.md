# Architecture — Daleel

## 1. Vue en couches

Daleel suit l'architecture logique de référence du sujet, organisée en couches.

```
┌─────────────────────────────────────────────────────────────┐
│  Couche Admission (Intake)                                    │
│  Import CSV · validation de schéma · snapshot initial         │
│  → app_intake                                                 │
├─────────────────────────────────────────────────────────────┤
│  Couche Domaine (Core)                                        │
│  Dossiers, événements, rendez-vous, snapshots, rapports       │
│  → cases                                                      │
├─────────────────────────────────────────────────────────────┤
│  Couche Décision                                              │
│  Moteur de score à règles + régression logistique explicable  │
│  → app_scoring                                                │
├─────────────────────────────────────────────────────────────┤
│  Couche Opérations                                            │
│  Tableaux de bord, filtres, simulateur, rapports, métriques   │
│  → dashboard                                                  │
├─────────────────────────────────────────────────────────────┤
│  Couche Gouvernance                                           │
│  Auth, RBAC, audit, comptes, espace élève, messagerie         │
│  → app_governance                                             │
└─────────────────────────────────────────────────────────────┘
            Configuration transverse → amal (settings, i18n, urls)
```

## 2. Applications Django

| App | Responsabilité |
|---|---|
| `app_intake` | Ingestion CSV, validation, scoring à l'import, snapshot |
| `app_scoring` | `compute_risk`, `ScoringConfig`, modèle ML (`ml.py`) |
| `cases` | Modèles du domaine (Student, Case, CaseEvent, Appointment, RiskSnapshot, Report), services, IA, génération PDF |
| `dashboard` | Tableaux de bord, listes filtrables, simulateur, config, évaluation modèle, rapports, **métriques** |
| `app_governance` | Inscriptions, validation des comptes, espace élève, auto-évaluation WHO-5, assistant IA, ressources, **messagerie**, profils enseignants |
| `amal` | `settings`, `urls`, `i18n.py`, `context_processors.py` |

## 3. Couche décision (explicabilité)

- **Moteur à règles** : `score = 0,5·absences + 0,3·baisse_notes + 0,2·discipline`
  (normalisés sur 0–100). Niveau faible / moyen / élevé selon des **seuils
  configurables** par le directeur (`ScoringConfig`).
- **Validation par modèle** : une régression logistique (pur Python, sans
  dépendance) entraînée sur des données synthétiques confirme la pondération
  (poids appris ≈ 52/28/21, AUC ≈ 0,85). Le modèle ne **remplace pas** le
  moteur à règles : il le **justifie**, en gardant l'explicabilité.

## 4. Justification des choix techniques

| Choix | Raison |
|---|---|
| Moteur à règles + ML de validation | Explicabilité (anti boîte noire) tout en justifiant les poids scientifiquement |
| i18n maison (dictionnaire) FR/EN/AR | Évite la compilation `gettext` sous Windows ; RTL pour l'arabe |
| SQLite par défaut, PostgreSQL en option | Démo simple et reproductible ; bascule prod par variable d'environnement |
| LLM **local** (Ollama) | Confidentialité (données ne quittent pas la machine) + coût nul ; modèle interchangeable en une ligne |
| Audit par chaînage de hash | Auditabilité forte avec un coût minimal, sans dépendance externe |
| Couche service dans `cases/services.py` | Sépare la logique métier des vues (maintenabilité, testabilité) |

## 5. Pile technique

- **Python 3.11+ / Django** (branche stable), **djangorestframework** présent.
- **Base** : SQLite (dev) / PostgreSQL (prod, via `USE_POSTGRES`).
- **Front** : templates Django + Chart.js (CDN) ; design system maison.
- **IA** : Ollama local (`qwen2.5:3b`) avec repli déterministe.
- **PDF** : ReportLab. **Données** : pandas pour l'ingestion.
- **i18n** : FR / EN / AR avec support RTL.
