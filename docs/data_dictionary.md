# Dictionnaire des données — Amal

Contrat de données pour l'import et les modèles principaux.

## 1. Fichier CSV d'import (admission)

Colonnes attendues d'un fichier de classe synthétique :

| Colonne | Type | Domaine | Description |
|---|---|---|---|
| `student_code` | texte | ex. `ST-2026-0001` | Identifiant anonyme de l'élève |
| `absences_percentage` | entier | 0–100 | Pourcentage d'absences |
| `grade_drop` | nombre | 0–20 | Note / baisse de note (barème tunisien /20) |
| `disciplinary_reports` | entier | 0–5 | Nombre d'incidents disciplinaires |

**Validation** : si une colonne requise manque ou si le schéma est invalide,
l'import est **rejeté proprement** (redirection + message), sans plantage.

## 2. Modèle `Student`

| Champ | Type | Description |
|---|---|---|
| `code` | texte | Code dossier anonyme |
| `absences_percentage` | entier | Indicateur de présence |
| `grade_drop` | nombre | Indicateur de notes (/20) |
| `disciplinary_reports` | entier | Indicateur de discipline (/5) |

## 3. Modèle `Case`

| Champ | Type | Description |
|---|---|---|
| `student` | FK Student | Élève concerné |
| `risk_score` | entier | Score de risque 0–100 |
| `risk_band` | texte | `LOW` / `MEDIUM` / `HIGH` |
| `status` | texte | `NEW` / `IN_REVIEW` / `INTERVENTION` / `FOLLOW_UP` / `CLOSED` |
| `risk_explanation` | texte | Explication lisible de l'alerte |
| `data_completeness` | entier | Nombre d'indicateurs renseignés (0–3) |

## 4. Modèle `CaseEvent` (piste d'audit)

| Champ | Type | Description |
|---|---|---|
| `case` | FK Case | Dossier concerné |
| `actor` | FK User | Auteur de l'action |
| `action` | texte | Type d'action |
| `result` | texte | `OK` / `DENIED` |
| `reason` | texte | Raison (si bloqué) |
| `timestamp` | datetime | Horodatage |
| `prev_hash` | texte | Empreinte de l'événement précédent |
| `entry_hash` | texte | Empreinte SHA-256 de l'événement (chaînage) |

## 5. Autres modèles

| Modèle | Champs clés |
|---|---|
| `Appointment` | `case`, `date`, `status` (Attended / Missed) |
| `RiskSnapshot` | `case`, `risk_score`, `risk_band`, `created_at` (trajectoire) |
| `Report` | `case`, `generated_by`, `title`, `narrative`, `source_directive`, `ai_generated` |
| `ScoringConfig` | seuils et poids configurables par le directeur |
| `AccessRequest` | `full_name`, `requested_role`, `student_code`, `biography`, `document`, `status` |
| `SelfAssessment` | `student_user`, `score` (0–100), `band`, `answers` (WHO-5) |
| `TeacherProfile` | `user`, `subjects` (tags), `is_visible` |
| `Conversation` / `Message` | `student`, `teacher`, `kind` (TEACHER/COUNSELOR) ; `sender`, `body` |

## 6. Auto-évaluation WHO-5

5 items positifs, échelle 0–5 (« jamais » → « tout le temps ») sur les deux
dernières semaines. Score brut 0–25, **×4** → pourcentage 0–100. Seuils :
> 50 = OK, 29–50 = à surveiller, ≤ 28 = alerte. Source : Indice de bien-être
OMS-5 (outil de repérage non clinique).
