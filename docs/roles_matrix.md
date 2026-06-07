# Matrice des rôles et permissions — Amal

Le contrôle d'accès est basé sur les rôles (RBAC) via les groupes Django.
Toute action est filtrée par un décorateur de rôle ; une tentative non
autorisée renvoie une page **403** et est **journalisée** (événement
`DENIED` dans la piste d'audit).

## 1. Les quatre rôles

| Rôle (groupe) | Description |
|---|---|
| **Enseignant** (`Teacher`) | Saisit / importe les données, signale, soutient |
| **Conseiller** (`Counselor`) | Valide et planifie les interventions, suit le bien-être |
| **Directeur** (`Director`) | Configure la politique, valide les comptes, supervise |
| **Élève** (`Student`) | Accède à son espace personnel (bien-être, ressources, contact) |

> Le sujet exige un minimum de 3 rôles ; Amal en implémente **4**.

## 2. Matrice des permissions

Légende : ✅ autorisé · ❌ refusé (403 + journalisé)

| Action | Enseignant | Conseiller | Directeur | Élève |
|---|:--:|:--:|:--:|:--:|
| Importer un CSV de classe | ✅ | ✅ | ✅ | ❌ |
| Voir la liste des dossiers | ✅ | ✅ | ✅ | ❌ |
| Voir le détail d'un dossier (score, explication) | ✅ | ✅ | ✅ | ❌ |
| Planifier / marquer un rendez-vous | ❌ | ✅ | ✅ | ❌ |
| Générer un rapport d'intervention | ❌ | ✅ | ✅ | ❌ |
| Voir la boîte des auto-évaluations | ❌ | ✅ | ✅ | ❌ |
| Utiliser le simulateur de risque | ❌ | ✅ | ✅ | ❌ |
| Configurer les seuils / poids (politique) | ❌ | ❌ | ✅ | ❌ |
| Valider / refuser les demandes de compte | ❌ | ❌ | ✅ | ❌ |
| Voir la page Métriques | ❌ | ✅ | ✅ | ❌ |
| Voir l'évaluation du modèle (AUC, etc.) | ❌ | ✅ | ✅ | ❌ |
| Ajouter / supprimer des ressources | ✅ | ❌ | ✅ | ❌ |
| Définir son profil de soutien (matières, visibilité) | ✅ | ❌ | ❌ | ❌ |
| Accéder à l'espace élève | ❌ | ❌ | ❌ | ✅ |
| Remplir une auto-évaluation (WHO-5) | ❌ | ❌ | ❌ | ✅ |
| Utiliser l'assistant d'étude (IA) | ❌ | ❌ | ❌ | ✅ |
| Contacter un enseignant (initier) | ❌ | ❌ | ❌ | ✅ |
| Contacter un conseiller (initier) | ❌ | ❌ | ❌ | ✅ |
| Initier un message vers un élève | ❌ | ✅ | ❌ | — |
| Répondre dans un fil existant | ✅* | ✅ | ❌ | ✅ |

\* L'enseignant peut **uniquement répondre** : il ne peut jamais initier une
conversation. Seul l'élève ouvre un fil enseignant↔élève (règle vérifiée par
test : l'enseignant reçoit un 403 s'il tente d'initier).

## 3. Cycle de vie d'un dossier — qui peut faire quoi

| Transition | Rôle autorisé |
|---|---|
| Créer / importer (→ NEW) | Enseignant, Directeur |
| Prendre en charge (NEW → IN_REVIEW) | Conseiller, Directeur |
| Planifier l'intervention (IN_REVIEW → INTERVENTION) | Conseiller, Directeur |
| Passer en suivi (→ FOLLOW_UP) | Conseiller, Directeur, **ou automatique** (RDV manqué) |
| Clôturer (→ CLOSED) | Conseiller, Directeur |

Voir le détail des états dans `state_machine.md`.

## 4. Gouvernance des comptes

- L'inscription publique crée un compte **inactif** + une demande d'accès, avec
  biographie (anti-bot) et document justificatif.
- Le **directeur** examine chaque demande (bio complète + document) et
  **approuve ou refuse**. Le compte n'est activé qu'après approbation.
- Le mot de passe est soumis aux **validateurs Django** (longueur, robustesse).
