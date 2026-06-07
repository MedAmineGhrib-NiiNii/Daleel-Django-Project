# Tableau de métriques d'évaluation — Amal

Conformément à la Section 10 du sujet, l'évaluation est **mesurable** et
**reproductible**. Toutes ces métriques sont calculées à partir des données
réelles du système et affichées sur la page **Métriques**
(`/dashboard/metrics/`).

> Règle du sujet : « une métrique non calculée à partir de données
> reproductibles est considérée comme non étayée. » Les valeurs ci-dessous
> sont donc toutes issues du code, pas déclaratives.

## 1. Métriques opérationnelles (calculées sur la base)

| Métrique | Définition | Source |
|---|---|---|
| Taux de complétion du workflow | % de dossiers pris en charge (état ≠ `NEW`) | `Case.status` |
| Taux de dossiers clôturés | % de dossiers en état `CLOSED` | `Case.status` |
| Fiabilité des données | % de dossiers avec 3/3 indicateurs renseignés | `Case.data_completeness` |
| Tentatives non autorisées bloquées | Nombre d'événements `DENIED` | `CaseEvent` |
| Événements d'audit | Nombre total d'événements journalisés | `CaseEvent` |
| Rapports générés | Nombre de rapports d'intervention produits | `Report` |

## 2. Couverture de sécurité et fiabilité

| Métrique du sujet | Comment Amal y répond |
|---|---|
| Taux de validation des données | Schéma vérifié à l'import ; mauvais schéma rejeté proprement |
| Efficacité de récupération | Échecs injectés gérés sans plantage (CSV invalide, 403) |
| Couverture des tests de sécurité | Tests RBAC + règle « l'élève initie » + audit (suite automatisée) |
| Intégrité de l'audit | Statut de la chaîne de hash affiché + `verify_audit` |
| Reproductibilité | Commandes de setup/seed/test documentées dans le README |

## 3. Qualité du modèle de risque

Le score à règles (poids 50/30/20) est **validé** par une régression logistique
entraînée sur des données synthétiques étiquetées (commande
`python manage.py train_model`, résultats dans `model_metrics.json`).

| Métrique | Valeur (indicative) | Interprétation |
|---|---|---|
| AUC | ≈ 0,85 | Bonne capacité à distinguer élève à risque / non à risque |
| Exactitude | ≈ 0,80 | Proportion de prédictions correctes |
| Précision | ≈ 0,85 | Parmi les alertes, % de vrais cas à risque |
| Rappel | ≈ 0,87 | Parmi les vrais décrocheurs, % détectés |
| Poids appris | ≈ 52 / 28 / 21 | Confirme la pondération choisie 50 / 30 / 20 |

> Les valeurs exactes dépendent du tirage synthétique ; elles sont recalculées
> à chaque `train_model` et affichées sur la page Évaluation du modèle.

## 4. Reproductibilité (depuis le README)

```bash
python manage.py migrate
python manage.py setup_roles
python manage.py setup_users
python manage.py seed_demo
python manage.py seed_resources
python manage.py train_model
python manage.py test          # suite de tests
python manage.py verify_audit  # intégrité de l'audit
python manage.py runserver
```

## 5. Tests automatisés

La suite couvre : le scoring, les deux scénarios de bout en bout, les échecs
contrôlés (mauvais CSV, 403), le RBAC des quatre rôles, la messagerie
(règle « l'élève initie »), la gestion des ressources, et l'intégrité de la
piste d'audit. Lancement : `python manage.py test`.
