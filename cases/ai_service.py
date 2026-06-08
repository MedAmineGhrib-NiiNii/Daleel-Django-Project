import requests
import json

# ==========================================
# LA BASE DE CONNAISSANCES (Le "R" de RAG)
# ==========================================
KNOWLEDGE_BASE = {
    "HIGH": "L'élève présente un risque élevé. Action obligatoire : Alerter la direction, planifier une rencontre parents sous 48h, proposer un suivi psychologique.",
    "MEDIUM": "L'élève présente une fragilité. Action recommandée : Organiser un entretien avec le conseiller, proposer un tutorat ou un soutien scolaire.",
    "LOW": "L'élève est stable. Action : Maintenir le suivi trimestriel classique."
}

def generate_intervention_plan(student_code, risk_band, risk_score):
    """
    Service sécurisé qui interroge Ollama en local.
    """
    # 1. RETRIEVAL : On récupère la bonne directive
    directive_officielle = KNOWLEDGE_BASE.get(risk_band, KNOWLEDGE_BASE["LOW"])

    # 2. AUGMENTATION : Un prompt très simple et direct
    prompt = f"""
    Applique cette règle : "{directive_officielle}"
    Pour l'élève {student_code} (Score: {risk_score}/100).
    Rédige un court plan d'action.
    """

    # 3. GENERATION : Appel à l'API locale avec un SYSTEM PROMPT strict
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "tinyllama",
        "system": "Tu es un conseiller d'éducation francophone. Tu dois IMPÉRATIVEMENT et EXCLUSIVEMENT répondre en langue FRANÇAISE. Il est strictement interdit d'utiliser l'espagnol ou l'anglais.",
        "prompt": prompt,
        "stream": False 
    }

    try:
        response = requests.post(url, json=payload, timeout=20) # J'ai monté le timeout à 20s au cas où
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "suggestion": data.get("response", "Réponse vide de l'IA.").strip(),
            "source": directive_officielle
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "suggestion": f"Impossible de contacter l'IA locale.",
            "error_detail": str(e)
        }

# ==========================================
# CHATBOT D'AIDE AUX ETUDES (espace eleve)
# ==========================================
STUDY_SYSTEM_PROMPT = (
    "Tu es Daleel, un assistant d'etude bienveillant pour des eleves tunisiens. "
    "Tu reponds UNIQUEMENT en francais, de maniere simple, encourageante et adaptee a un mineur. "
    "Tu aides a comprendre les lecons, a organiser les revisions et a expliquer des notions. "
    "Tu NE donnes JAMAIS de conseil medical, psychologique ou personnel : pour ces sujets, "
    "tu invites gentiment l'eleve a en parler a un adulte de confiance (parent, enseignant, conseiller). "
    "Reste bref et clair."
)


def study_chat(message):
    """Chatbot d'aide aux etudes via le LLM local. Renvoie un dict {success, reply}."""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "qwen2.5:3b",
        "system": STUDY_SYSTEM_PROMPT,
        "prompt": str(message)[:1000],
        "stream": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        return {"success": True, "reply": data.get("response", "").strip() or "Je n'ai pas de reponse."}
    except requests.exceptions.RequestException as e:
        return {"success": False, "reply": "Assistant indisponible pour le moment. Reessaie plus tard.", "error": str(e)}


# ==========================================
# GENERATION DE RAPPORT D'INTERVENTION (Ollama + repli)
# ==========================================
def generate_case_report(case):
    """Rédige un rapport narratif pour un dossier. Utilise Ollama si dispo, sinon un repli structuré."""
    s = case.student
    band = case.risk_band or "LOW"
    directive = KNOWLEDGE_BASE.get(band, KNOWLEDGE_BASE["LOW"])
    facts = (
        f"Eleve {s.code} ({s.grade_level}, {s.governorate or 'N/A'}). "
        f"Score de risque {case.risk_score}/100, niveau {band}. "
        f"Absenteisme {s.absences_percentage}%, chute des notes {s.grade_drop}/20, "
        f"{s.disciplinary_reports} signalement(s)."
    )
    prompt = (
        "Redige un rapport d'intervention professionnel et bienveillant (en francais) pour un conseiller "
        "d'education, a partir de ces faits :\n" + facts +
        "\nDirective officielle a appliquer : " + directive +
        "\nStructure : 1) Situation, 2) Analyse du risque, 3) Recommandations concretes. "
        "Reste factuel, non stigmatisant, et rappelle que la validation humaine est requise."
    )
    url = "http://localhost:11434/api/generate"
    payload = {"model": "tinyllama",
               "system": "Tu es un conseiller d'education francophone. Reponds uniquement en francais, de maniere professionnelle.",
               "prompt": prompt, "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        narrative = r.json().get("response", "").strip()
        if narrative:
            return {"narrative": narrative, "directive": directive, "ai_generated": True}
    except requests.exceptions.RequestException:
        pass

    # Repli structuré (si Ollama indisponible) - reste un livrable propre
    narrative = (
        f"1) SITUATION\n{facts}\n\n"
        f"2) ANALYSE DU RISQUE\nLe dossier presente un niveau de risque {band} "
        f"(score {case.risk_score}/100). {case.risk_explanation}\n\n"
        f"3) RECOMMANDATIONS\n{directive}\n\n"
        f"Ce rapport est une aide a la decision : la validation par un professionnel est requise."
    )
    return {"narrative": narrative, "directive": directive, "ai_generated": False}