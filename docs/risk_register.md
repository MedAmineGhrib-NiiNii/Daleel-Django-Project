# Registre des risques et garde-fous éthiques — Amal

Conformément à la Section 16 du sujet, ce registre liste les risques par
catégorie et les mesures de mitigation mises en place dans le code.

## 1. Risques liés aux données

| Risque | Description | Mitigation (implémentée) |
|---|---|---|
| Fuite de données | Exposition de données sensibles | Données **100 % synthétiques** ; identification par code dossier, jamais par nom réel ; visibilité par rôle |
| Mauvaise qualité / valeurs manquantes | Indicateurs incomplets faussant le score | Validation de schéma à l'import ; champ `data_completeness` (N/3) affiché ; import au mauvais schéma rejeté proprement |
| Ingestion incorrecte | Fichier corrompu / mauvais format | Contrôle de schéma + message d'erreur + redirection (pas de plantage) |
| Sur-interprétation | Prendre un proxy pour une vérité | Explication lisible de chaque alerte ; mention « aide à la décision, pas un diagnostic » |

## 2. Risques liés à la décision

| Risque | Description | Mitigation |
|---|---|---|
| Faux positifs | Élève signalé à tort (stigmatisation) | Seuils **configurables** par le directeur ; simulateur « et si ? » pour calibrer ; communication non stigmatisante |
| Faux négatifs | Décrocheur non détecté | Pondération inspirée de la recherche (modèle ABC) ; validation par régression logistique (rappel ≈ 0,87) |
| Boîte noire | Décision opaque non explicable | Moteur **à règles transparent** ; explication textuelle ; poids publiés et justifiés |
| Biais | Traitement injuste | Indicateurs comportementaux objectifs uniquement ; discussion des limites dans `ethics_and_limitations.md` |

## 3. Risques opérationnels

| Risque | Description | Mitigation |
|---|---|---|
| Action non autorisée | Un rôle agit hors de ses droits | RBAC strict ; **403** + événement `DENIED` journalisé |
| Échec silencieux | Une étape échoue sans alerte | Messages utilisateur explicites ; journalisation systématique |
| Indisponibilité de l'IA | Le service LLM local est éteint | **Repli gracieux** : message « assistant indisponible », jamais de plantage |
| Altération de l'audit | Modification frauduleuse des traces | Piste d'audit **infalsifiable** (chaînage de hash) + commande de vérification |

## 4. Garde-fou clé : piste d'audit infalsifiable

Chaque `CaseEvent` contient :
- `prev_hash` : l'empreinte de l'événement précédent ;
- `entry_hash` : `SHA-256(prev_hash | dossier | acteur | action | résultat | raison | horodatage)`.

Les événements forment ainsi une **chaîne**. Toute modification ou suppression
d'une entrée rompt la chaîne et devient détectable.

**Vérification (preuve reproductible) :**
```bash
python manage.py verify_audit
```
- Chaîne intacte → `✓ Piste d'audit intègre : N entrées`.
- Entrée altérée → `✗ Entrée #X altérée — audit compromis`.

> Démonstration de soutenance : modifier une ligne directement en base, puis
> relancer `verify_audit` — le système détecte la fraude.

## 5. Garde-fous IA (Responsible AI)

- **Validation humaine obligatoire** : toute suggestion de l'IA est validée ou
  rejetée par un professionnel (boutons Valider / Rejeter, action journalisée).
- **Disclaimer dans l'interface** : « aide à la décision, pas une autorité
  clinique / légale ».
- **Encadrement par consigne système** stricte pour l'assistant d'étude
  (uniquement scolaire, pas de conseil médical/personnel, adapté aux mineurs).
- **Repli déterministe** si le modèle est indisponible ou peu fiable.
- **Traçabilité** : chaque rapport indique s'il est généré par l'IA ou par le
  modèle structuré, avec sa source / directive.

## 6. Sécurité (rappel)

- Réglages **prêts pour la production** via variables d'environnement
  (`DEBUG`, `SECRET_KEY`, cookies sécurisés et HSTS activés hors-DEBUG).
- **Validation de la robustesse** du mot de passe à l'inscription.
- **Comptes inactifs** tant que non approuvés par le directeur.
