# Daleel — Plateforme de prévention du décrochage scolaire

Projet Django (examen Python Web Programming, SESAME University) sur le thème
*« Tunisian Hope and Future for Children and Youth »*. La plateforme détecte les
élèves en risque de décrochage, gère les dossiers et coordonne les interventions,
avec une piste d'audit complète et un assistant IA local (RAG).

## Architecture (5 couches)
- `app_intake` — ingestion des relevés CSV
- `app_scoring` — moteur de calcul du risque (`compute_risk`)
- `cases` — modèles métier (Student, Case, CaseEvent, Appointment) + actions
- `dashboard` — tableau de bord, graphiques, export, assistant IA
- `app_governance` — rôles RBAC et comptes de démonstration

## Rôles (RBAC)
- **Teacher** — importe les CSV, consulte
- **Counselor** — prend en charge, planifie, traite les dossiers, reçoit les auto-évaluations
- **Director** — vue globale, export, et validation des demandes de compte
- **Student** — espace élève : auto-évaluation bien-être, assistant d'étude, ressources, profs

Tous les comptes (sauf le Directeur) passent par une inscription validée manuellement par le Directeur (sécurité anti-bot).

## Installation
```bash
# 1) Créer et activer l'environnement virtuel
python -m venv venv
# Windows (PowerShell) :
venv\Scripts\activate
# macOS / Linux :
# source venv/bin/activate

# 2) Installer les dépendances
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_roles      # crée Teacher / Counselor / Director / Student
python manage.py setup_users      # crée prof / conseiller / directeur
python manage.py seed_demo        # 200 élèves + dossiers synthétiques
python manage.py seed_resources   # ressources pédagogiques (espace élève)
python manage.py train_model      # entraîne le modèle + calcule AUC/métriques
python manage.py runserver
```
Connexion : http://127.0.0.1:8000/login/ — comptes démo : `prof`, `conseiller`, `directeur`, `eleve` (mot de passe `amalpassword123`).
Inscription publique (validée par le Directeur) : http://127.0.0.1:8000/register/

## Tests
```bash
python manage.py test
```

## Évaluation du modèle (métriques)
`python manage.py train_model` entraîne une régression logistique sur données synthétiques et calcule AUC, matrice de confusion, précision/rappel. Résultats visibles sur la page « Évaluation modèle ». Les poids appris (~52/28/21) valident la pondération configurée (50/30/20), inspirée du modèle ABC de la recherche sur le décrochage.

## Trajectoire & rapports
Chaque dossier garde un historique de score (`RiskSnapshot`) affiché en courbe sur la fiche, avec une alerte de tendance (en hausse / baisse / stable) — logique d'alerte précoce. Le bouton « Générer un rapport » produit un rapport d'intervention (rédigé par Ollama si disponible, sinon un modèle structuré), consultable dans « Rapports » et téléchargeable en PDF (ReportLab). `pip install -r requirements.txt` installe ReportLab.

## Base de données
SQLite par défaut (prototype). Pour PostgreSQL : définir `USE_POSTGRES=1` et les variables `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` (nécessite `pip install psycopg2-binary`). Aucune logique métier ne change — seul le bloc `DATABASES` bascule.

## Données & éthique
Données 100% synthétiques (`seed_demo`) ou anonymisées (codes `ST-2026-XXXX`).
Aucune donnée personnelle ou médicale réelle. Toute action sensible est tracée
dans `CaseEvent`. L'assistant IA est une aide à la décision : la validation reste humaine.

## Limites connues
- `DEBUG=True` et `SECRET_KEY` en clair : configuration de développement uniquement.
- L'assistant IA nécessite Ollama en local. Deux modèles sont utilisés : `qwen2.5:3b` pour l'assistant d'étude de l'élève (meilleure qualité en français) et `tinyllama` pour la génération des plans et des rapports (plus léger). En l'absence d'Ollama, une erreur propre est affichée.