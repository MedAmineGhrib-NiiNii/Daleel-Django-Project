# Énoncé du problème — Daleel (دليل)

> Plateforme Django de détection précoce et d'accompagnement du décrochage
> scolaire chez les jeunes en Tunisie.

## 1. Énoncé en une phrase

Daleel aide les établissements scolaires tunisiens à **repérer tôt** les élèves
en risque de décrochage et à **coordonner les interventions** (enseignants,
conseillers, direction) à travers un flux de travail tracé, explicable et
respectueux de la vie privée.

## 2. Cadrage de la tâche (task clarity)

Conformément aux exigences du sujet, chaque dimension est définie explicitement.

### Population
Élèves du secondaire (collège / lycée), tranche d'âge ~12–18 ans, dans un
établissement tunisien. Les données utilisées sont **entièrement synthétiques**
(aucun élève réel).

### Problème ciblé
Le **décrochage scolaire** : un processus progressif qui se manifeste par des
signaux précoces (absentéisme, baisse des notes, incidents disciplinaires)
avant l'abandon effectif. L'objectif est d'agir **pendant** que l'élève est
encore récupérable, pas après.

### Décideur (qui utilise la sortie et pourquoi)
- **L'enseignant** signale et importe les données de sa classe.
- **Le conseiller** (orientation / soutien psychosocial) lit le niveau de
  risque, planifie les interventions et suit les rendez-vous.
- **Le directeur** configure la politique de risque, valide les comptes et
  surveille les indicateurs globaux de l'établissement.

### Workflow opérationnel (ce que font les utilisateurs, étape par étape)
1. **Admission (intake)** : import d'un fichier CSV de classe (présence, notes,
   incidents) avec validation de schéma.
2. **Évaluation (assessment)** : calcul d'un score de risque 0–100 et d'un
   niveau (faible / moyen / élevé), avec une **explication lisible**.
3. **Planification de l'intervention** : le conseiller examine le dossier,
   planifie un rendez-vous, déclenche une orientation si nécessaire.
4. **Suivi et ré-évaluation** : la trajectoire de risque est suivie dans le
   temps ; un rendez-vous manqué déclenche automatiquement une relance.

### Valeur attendue (ce qui s'améliore)
- Intervention **plus précoce** (avant l'abandon).
- **Coordination** claire entre les trois acteurs (qui fait quoi, quand).
- **Traçabilité** : chaque action est journalisée et auditable.
- Réduction des **décrochages non détectés**.

### Règle de validation (succès / échec d'un workflow)
- **Scénario 1 (alerte précoce)** réussit si : un import valide produit un
  tableau de bord priorisé **et** au moins un export filtré est généré.
- **Scénario 2 (suivi)** réussit si : un rendez-vous manqué déclenche une
  action d'orientation **journalisée** et visible dans la chronologie du
  dossier.
- Un **échec contrôlé** par scénario (mauvais schéma CSV, accès non autorisé)
  doit être géré sans plantage, avec message et trace.

## 3. Frontière données et éthique

- **Données synthétiques uniquement.** Aucune donnée personnelle, médicale ou
  confidentielle réelle.
- **Anonymisation** : les élèves sont identifiés par un code dossier
  (ex. `ST-2026-0001`), jamais par un nom réel dans les données de risque.
- **Hypothèse de consentement** : en contexte réel, l'usage supposerait le
  consentement éclairé des responsables légaux et le cadre légal de
  l'établissement.
- **Visibilité selon le rôle** : chaque acteur ne voit que ce que son rôle
  autorise (voir `roles_matrix.md`).
- **Pas de diagnostic.** Les indicateurs sont des **proxys de repérage**, pas
  des verdicts. Toute suggestion est une **aide à la décision** validée par un
  humain (voir `ethics_and_limitations.md`).

## 4. Parties prenantes et bénéfice

| Partie prenante | Bénéfice |
|---|---|
| Établissement scolaire | Vue d'ensemble priorisée des élèves à risque |
| Conseiller | Outil de coordination et de suivi des interventions |
| Enseignant | Canal simple de signalement et de soutien |
| Élève | Espace de bien-être, ressources, contact avec le soutien |
| Direction / décideurs | Indicateurs fiables et traçables pour piloter |
