# Documentation — Daleel (دليل)

Plateforme Django de détection précoce du décrochage scolaire et de
coordination des interventions, pour les établissements tunisiens.

Ce dossier `docs/` rassemble la documentation exigée par le sujet.

## Sommaire

| Document | Contenu | Exigence du sujet |
|---|---|---|
| [problem_statement.md](problem_statement.md) | Population, problème, décideur, workflow, valeur, règle de validation, frontière éthique | Section 18 (S1), Rubrique A |
| [roles_matrix.md](roles_matrix.md) | Les 4 rôles et la matrice complète des permissions | Section 18 (S1), Rubrique E |
| [state_machine.md](state_machine.md) | États, transitions, transitions bloquées, scénarios | Section 18 (S1), Rubrique B/D |
| [risk_register.md](risk_register.md) | Risques données / décision / opérationnels + mitigations | Section 16, Rubrique E |
| [metrics.md](metrics.md) | Métriques calculées et reproductibles | Section 10, Rubrique D/F |
| [architecture.md](architecture.md) | Couches, apps, couche décision, justifications | Rubrique B/F |
| [ethics_and_limitations.md](ethics_and_limitations.md) | Gouvernance des données, consentement, limites | Submission package, Rubrique A/E |
| [data_dictionary.md](data_dictionary.md) | Contrat de données (CSV + modèles) | Section 18 (S1) |

## Démarrage rapide (reproductible)

```bash
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py setup_roles
python manage.py setup_users
python manage.py seed_demo
python manage.py seed_resources
python manage.py train_model
python manage.py runserver
```

Site : http://127.0.0.1:8000/login/

**Comptes de démonstration** (mot de passe : `amalpassword123`) :
`directeur`, `conseiller`, `prof`, `eleve`.

## Vérifications

```bash
python manage.py test          # suite de tests automatisés
python manage.py verify_audit  # intégrité de la piste d'audit
python manage.py check --deploy
```

## Assistant IA (optionnel, local)

L'assistant d'étude utilise Ollama en local. Installer le modèle puis le
« réveiller » avant la démo :
```bash
ollama pull qwen2.5:3b
ollama run qwen2.5:3b "bonjour"
```
Si Ollama est indisponible, l'application affiche un repli propre (pas de
plantage).

## Travail individuel

Projet réalisé individuellement (auteur : NiiNii). Toute partie est explicable
à l'oral lors de la soutenance.
