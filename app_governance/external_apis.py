"""
Intégrations d'API externes publiques et gratuites, avec repli propre.
Chaque fonction renvoie aussi la provenance (source + date de récupération),
comme l'exige le cahier des charges (Section 12).
"""
import datetime
import random
import requests

TIMEOUT = 8


def _today():
    return datetime.date.today().isoformat()


# ---------------------------------------------------------------------------
# 1) BANQUE MONDIALE — contexte national (gratuit, sans clé)
#    Indicateurs éducation pour la Tunisie (TUN).
# ---------------------------------------------------------------------------
WORLD_BANK_INDICATORS = {
    "SE.ADT.1524.LT.ZS": "Alphabétisation des jeunes (15-24 ans), %",
    "SE.SEC.ENRR": "Taux de scolarisation secondaire (brut), %",
    "SE.PRM.CMPT.ZS": "Achèvement du primaire, %",
}


def world_bank_context(country="TUN"):
    """Renvoie quelques indicateurs réels (Banque Mondiale) pour mise en contexte.
    Repli : liste vide si l'API est injoignable."""
    results = []
    for code, label in WORLD_BANK_INDICATORS.items():
        url = (f"https://api.worldbank.org/v2/country/{country}"
               f"/indicator/{code}?format=json&per_page=60")
        try:
            r = requests.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            payload = r.json()
            rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
            latest = next((row for row in rows if row.get("value") is not None), None)
            if latest:
                results.append({
                    "label": label,
                    "value": round(float(latest["value"]), 1),
                    "year": latest.get("date"),
                    "source": "Banque Mondiale",
                    "source_url": url,
                    "fetched_at": _today(),
                })
        except (requests.exceptions.RequestException, ValueError, KeyError, IndexError):
            continue
    return results


# ---------------------------------------------------------------------------
# 2) CITATION DE MOTIVATION (espace élève)
#    Tente une API publique, repli sur une liste française locale.
# ---------------------------------------------------------------------------
LOCAL_QUOTES_FR = [
    ("Le succès, c'est tomber sept fois et se relever huit.", "Proverbe"),
    ("Chaque expert a d'abord été un débutant.", "Anonyme"),
    ("La connaissance s'acquiert par l'expérience, tout le reste n'est que de l'information.", "A. Einstein"),
    ("Il n'y a pas d'échec, seulement des leçons.", "Anonyme"),
    ("Un petit pas chaque jour mène loin.", "Proverbe"),
    ("Crois en toi et tout devient possible.", "Anonyme"),
    ("L'effort d'aujourd'hui est la réussite de demain.", "Proverbe"),
]


def motivation_quote():
    """Citation du jour. Tente une API externe, sinon repli français local."""
    try:
        r = requests.get("https://zenquotes.io/api/today", timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data and data[0].get("q"):
            return {"text": data[0]["q"].strip(), "author": data[0].get("a", ""),
                    "source": "ZenQuotes", "fetched_at": _today()}
    except (requests.exceptions.RequestException, ValueError, KeyError, IndexError):
        pass
    # Repli déterministe : une citation par jour
    idx = datetime.date.today().toordinal() % len(LOCAL_QUOTES_FR)
    text, author = LOCAL_QUOTES_FR[idx]
    return {"text": text, "author": author, "source": "Sélection locale", "fetched_at": _today()}


# ---------------------------------------------------------------------------
# 3) QUIZ DE CONNAISSANCES — Open Trivia Database (gratuit, sans clé)
# ---------------------------------------------------------------------------
OPENTDB_CATEGORIES = {
    "9": "Culture générale",
    "17": "Sciences & Nature",
    "19": "Mathématiques",
    "23": "Histoire",
    "22": "Géographie",
}


def trivia_questions(amount=5, category="9"):
    """Renvoie des questions de quiz (OpenTDB). Repli : None si injoignable."""
    import html
    url = f"https://opentdb.com/api.php?amount={amount}&category={category}&type=multiple"
    try:
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data.get("response_code") != 0:
            return None
        out = []
        for q in data["results"]:
            options = [html.unescape(a) for a in q["incorrect_answers"]] + [html.unescape(q["correct_answer"])]
            random.shuffle(options)
            out.append({
                "question": html.unescape(q["question"]),
                "options": options,
                "correct": html.unescape(q["correct_answer"]),
            })
        return {"questions": out, "source": "Open Trivia Database",
                "source_url": url, "fetched_at": _today()}
    except (requests.exceptions.RequestException, ValueError, KeyError):
        return None