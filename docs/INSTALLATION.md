# Guide d'installation et d'utilisation — Daleel (دليل)

Ce guide permet de lancer Daleel sur une machine neuve, étape par étape.
Suivre les sections dans l'ordre. En cas de problème, voir la section
**Dépannage** à la fin.

---

## 1. Prérequis

- **Python 3.11 ou plus**. Vérifier :
  ```powershell
  python --version
  ```
  Si la commande n'existe pas, installer Python depuis https://www.python.org
  (cocher « Add Python to PATH » à l'installation).
- Le dossier du projet (décompressé depuis le ZIP), contenant `manage.py`.

---

## 2. Préparer l'environnement (Windows / PowerShell)

Ouvrir PowerShell **dans le dossier du projet** (celui qui contient
`manage.py`). Adapter le chemin si besoin :

```powershell
cd C:\chemin\vers\amal_project
```

Créer et activer un environnement virtuel, puis installer les dépendances
(une commande par ligne, sans `&&`) :

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

> Une fois activé, l'invite affiche `(venv)` au début de la ligne.

**macOS / Linux** (équivalent) :
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Initialiser la base et les données de démonstration

Lancer ces commandes **dans l'ordre** :

```powershell
python manage.py migrate
python manage.py setup_roles
python manage.py setup_users
python manage.py seed_demo
python manage.py seed_resources
python manage.py train_model
```

Ce que fait chaque commande :

| Commande | Rôle |
|---|---|
| `migrate` | Crée la base de données (tables) |
| `setup_roles` | Crée les 4 rôles (Enseignant, Conseiller, Directeur, Élève) |
| `setup_users` | Crée les comptes de démonstration |
| `seed_demo` | Génère des élèves et dossiers synthétiques |
| `seed_resources` | Ajoute des ressources pédagogiques de départ |
| `train_model` | Entraîne le modèle de validation (AUC, métriques) |

---

## 4. Lancer le serveur

```powershell
python manage.py runserver
```

Ouvrir un navigateur sur : **http://127.0.0.1:8000/login/**

Pour arrêter le serveur : `Ctrl + C` dans le terminal.

---

## 5. Comptes de démonstration

Mot de passe commun : **`amalpassword123`**

| Identifiant | Rôle | Ce qu'il peut voir |
|---|---|---|
| `directeur` | Directeur | Tout : config, validation des comptes, métriques, supervision |
| `conseiller` | Conseiller | Dossiers, interventions, auto-évaluations, messages, rapports |
| `prof` | Enseignant | Import CSV, dossiers, ressources, profil de soutien, messages |
| `eleve` | Élève | Espace élève : bien-être, assistant, ressources, contact |

> Pour accéder à l'**administration Django** (`/admin/`), créer un super-compte :
> ```powershell
> python manage.py createsuperuser
> ```

---

## 6. Parcours de démonstration suggéré

1. **Scénario 1 (alerte précoce)** — connecté en `prof` ou `directeur` :
   importer un CSV de classe, observer le tableau de bord priorisé, exporter
   une liste filtrée.
2. **Scénario 2 (suivi)** — connecté en `conseiller` : ouvrir un dossier,
   planifier un rendez-vous, le marquer « manqué » → l'orientation se déclenche
   automatiquement et apparaît dans la chronologie.
3. **Espace élève** — connecté en `eleve` : remplir l'auto-évaluation WHO-5,
   utiliser l'assistant d'étude, contacter un enseignant ou un conseiller.
4. **Sécurité** — montrer un accès refusé (403 journalisé) et l'intégrité de
   l'audit (voir §8).

---

## 7. Assistant IA (optionnel — local)

L'assistant d'étude et la génération de rapports utilisent un modèle d'IA
**local** via Ollama. C'est **optionnel** : sans lui, l'application affiche un
repli propre (pas de plantage).

Pour l'activer :
1. Installer Ollama : https://ollama.com
2. Télécharger le modèle :
   ```powershell
   ollama pull qwen2.5:3b
   ```
3. **Important** — « réveiller » le modèle juste avant la démo (le premier
   appel peut être lent) :
   ```powershell
   ollama run qwen2.5:3b "bonjour"
   ```
   Laisser répondre, puis utiliser le chat dans le site.

---

## 8. Vérifications utiles

```powershell
python manage.py test
```
Lance toute la suite de tests automatisés (doit afficher `OK`).

```powershell
python manage.py verify_audit
```
Vérifie l'intégrité de la piste d'audit (chaînage de hash). Doit afficher
`✓ Piste d'audit intègre`.

```powershell
python manage.py check --deploy
```
Liste les recommandations de sécurité pour la production.

---

## 9. Dépannage (problèmes fréquents)

### « `python` n'est pas reconnu »
Python n'est pas dans le PATH. Réinstaller Python en cochant « Add to PATH »,
ou utiliser `py` à la place de `python`.

### L'activation du venv est bloquée (PowerShell)
Si `venv\Scripts\activate` renvoie une erreur de politique d'exécution :
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
puis réessayer.

### `verify_audit` affiche « audit compromis »
Cela arrive si la base contient d'anciens événements créés avant le système de
hash, ou après un re-seed partiel. Repartir d'une base propre :
```powershell
del db.sqlite3
python manage.py migrate
python manage.py setup_roles
python manage.py setup_users
python manage.py seed_demo
python manage.py seed_resources
python manage.py train_model
```
Puis refaire quelques actions dans l'app et relancer `verify_audit`.

### Le chat affiche « Assistant indisponible pour le moment »
Le serveur n'a pas pu joindre Ollama. Vérifier :
1. Ollama est lancé (s'il dit « port already in use », c'est qu'il tourne déjà).
2. Le modèle est installé : `ollama list` doit montrer `qwen2.5:3b`.
3. Le premier appel peut dépasser le délai : « réveiller » le modèle d'abord
   avec `ollama run qwen2.5:3b "bonjour"`, puis réessayer.

### `Error: listen tcp 127.0.0.1:11434 ... bind`
Ce n'est pas une erreur bloquante : Ollama **tourne déjà**. Inutile de relancer
`ollama serve`.

### VS Code affiche des « erreurs » dans les fichiers HTML
Les balises de gabarit Django (`{% ... %}`) sont signalées à tort par
l'éditeur. Ce ne sont pas de vraies erreurs : seules comptent les erreurs
affichées dans le **navigateur** ou le **terminal**.

### Le bouton de déconnexion est inaccessible
Vider le cache du navigateur (`Ctrl + F5`). La barre latérale défile désormais
et le bouton reste fixé en bas.

### Le port 8000 est déjà utilisé
Lancer le serveur sur un autre port :
```powershell
python manage.py runserver 8001
```

---

## 10. Réinitialisation complète

Pour repartir totalement de zéro :
```powershell
del db.sqlite3
python manage.py migrate
python manage.py setup_roles
python manage.py setup_users
python manage.py seed_demo
python manage.py seed_resources
python manage.py train_model
python manage.py runserver
```
