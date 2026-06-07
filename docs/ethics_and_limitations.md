# Éthique, gouvernance des données et limites — Amal

Le projet touche des **mineurs** dans un contexte sensible. Cette section
documente les hypothèses éthiques, la gouvernance des données et les limites,
comme l'exige le sujet.

## 1. Gouvernance des données

- **Données synthétiques uniquement.** Aucune donnée réelle personnelle,
  médicale ou confidentielle n'est utilisée.
- **Anonymisation.** Les élèves sont désignés par un code dossier
  (`ST-2026-0001`), jamais par un nom réel dans la logique de risque.
- **Minimisation.** Seuls trois indicateurs comportementaux objectifs sont
  collectés (absences, évolution des notes, incidents), nécessaires au
  repérage.
- **Contrôle d'accès.** Visibilité strictement limitée par rôle (voir
  `roles_matrix.md`).
- **Traçabilité.** Toute action est journalisée de façon infalsifiable.

## 2. Hypothèses de consentement (contexte réel)

En déploiement réel — hors de ce prototype — l'usage supposerait :
- le **consentement éclairé** des responsables légaux ;
- l'inscription dans le **cadre légal** de l'établissement et la réglementation
  applicable sur les données des mineurs ;
- une politique de **conservation et de suppression** des données.

## 3. Principes de décision responsable

- **Aide à la décision, pas un diagnostic.** Les indicateurs sont des **proxys
  de repérage**. Ils ne constituent ni un avis médical, ni un verdict.
- **Humain dans la boucle.** Toute suggestion (plan d'action, rapport IA) est
  **validée par un professionnel** avant tout effet.
- **Explicabilité.** Chaque alerte est accompagnée d'une explication lisible ;
  aucune décision « boîte noire ».
- **Communication non stigmatisante.** Les libellés évitent les étiquettes
  blessantes ; on parle de « niveau de risque » et de « soutien », pas de
  jugement sur l'élève.

## 4. Limites (à assumer en soutenance)

| Limite | Précision |
|---|---|
| Données synthétiques | L'AUC ≈ 0,85 prouve que **la méthode** fonctionne, pas que le modèle est validé sur de vrais élèves tunisiens. |
| Indicateurs réducteurs | Le décrochage a des causes multiples (familiales, sociales, économiques) non capturées par 3 indicateurs. |
| Risque de faux positifs/négatifs | Inévitable ; d'où les seuils configurables et la validation humaine. |
| Dépendance à la qualité des données | Un import incomplet abaisse la fiabilité (suivie via `data_completeness`). |
| LLM local | Qualité dépendante du modèle installé ; repli si indisponible. |

## 5. Prochaines étapes en conditions réelles

- **Recalibrer** les poids et seuils sur des données anonymisées
  d'établissements, avec accord éthique.
- Ajouter des **indicateurs contextuels** (sous supervision de professionnels).
- Étude d'**impact et de biais** avant tout usage opérationnel.

## 6. Auditabilité comme garantie éthique

La piste d'audit infalsifiable (chaînage de hash, `verify_audit`) garantit que
toute action sur un dossier d'élève est **traçable et non modifiable a
posteriori** — une exigence forte quand il s'agit de mineurs.
