"""
Moteur de scoring du risque de decrochage (Scenario 1).
Source unique de verite. Les seuils sont configurables par le superviseur (ScoringConfig).
"""
from decimal import Decimal


def get_thresholds():
    """Retourne (medium, high) depuis la configuration editable par le superviseur."""
    from .models import ScoringConfig
    cfg = ScoringConfig.get_solo()
    return float(cfg.medium_threshold), float(cfg.high_threshold)


def band_for_score(score, thresholds=None):
    medium, high = thresholds if thresholds is not None else get_thresholds()
    if score >= high:
        return "HIGH"
    if score >= medium:
        return "MEDIUM"
    return "LOW"


def compute_risk(absences_percentage, grade_drop, disciplinary_reports, thresholds=None):
    """
    Calcule un score /100 et la bande de risque.
    Ponderation : absences 50%, chute des notes 30%, discipline 20%.
    Retourne (score: Decimal, band: str, explanation: str).
    """
    absences_percentage = float(absences_percentage or 0)
    grade_drop = float(grade_drop or 0)
    disciplinary_reports = float(disciplinary_reports or 0)

    norm_absences = min(absences_percentage, 100)
    norm_grade = min((grade_drop / 20) * 100, 100) if grade_drop > 0 else 0
    norm_behaviour = min((disciplinary_reports / 5) * 100, 100)

    score = (norm_absences * 0.5) + (norm_grade * 0.3) + (norm_behaviour * 0.2)
    band = band_for_score(score, thresholds)

    explanation = generate_explanation(score, band, absences_percentage, grade_drop, disciplinary_reports)
    return Decimal(score).quantize(Decimal("0.01")), band, explanation


def risk_contributions(absences_percentage, grade_drop, disciplinary_reports):
    """Contribution ponderee de chaque facteur au score (somme = score)."""
    a = float(absences_percentage or 0)
    g = float(grade_drop or 0)
    d = float(disciplinary_reports or 0)
    na = min(a, 100)
    ng = min((g / 20) * 100, 100) if g > 0 else 0
    nb = min((d / 5) * 100, 100)
    return {
        "absences": round(na * 0.5, 2),
        "grades": round(ng * 0.3, 2),
        "behaviour": round(nb * 0.2, 2),
    }


def generate_explanation(score, band, absences, grade_drop, disciplinary_reports):
    reasons = []
    if absences > 15:
        reasons.append(f"absenteisme eleve ({absences:.0f}%)")
    if grade_drop >= 4:
        reasons.append(f"chute des notes de {grade_drop:.0f} points")
    if disciplinary_reports >= 2:
        reasons.append(f"{disciplinary_reports:.0f} signalements disciplinaires")

    if not reasons:
        return "Profil stable : aucun indicateur critique detecte."
    return f"Classe en risque {band} (score {score:.0f}/100) en raison de : " + ", ".join(reasons) + "."
