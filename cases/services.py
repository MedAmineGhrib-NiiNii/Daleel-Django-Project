from decimal import Decimal

from .models import Appointment, CaseEvent
from app_scoring.services import band_for_score


def update_appointment_status(appointment_id, new_status, actor=None, notes=""):
    """
    Met a jour le statut d'un RDV et fait avancer le dossier (Scenario 2).
    - MISSED : penalite de risque + alerte + action de relance/orientation (referral) tracees.
    - ATTENDED : seance honoree, dossier en suivi.
    Retourne (appointment, message).
    """
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return None, "Rendez-vous introuvable."

    appointment.status = new_status
    if notes:
        appointment.notes = notes
    appointment.save()

    case = appointment.case

    if new_status == "MISSED":
        # 1. Alerte tracee (qui, quand, quoi)
        CaseEvent.objects.create(
            case=case, actor=actor, action="MISSED_APPOINTMENT_ALERT",
            payload={"appointment_date": str(appointment.date), "notes": notes},
            result="OK",
            reason="Alerte automatique : l'eleve ne s'est pas presente au suivi.",
        )

        # 2. Penalite de risque (+10) et reclassement selon les seuils configures
        if case.risk_score is not None:
            case.risk_score = case.risk_score + Decimal("10")
            case.risk_band = band_for_score(float(case.risk_score))

        # 3. Action de relance / orientation declenchee (exigence 8.2)
        case.status = "FOLLOW_UP"
        case.save()
        record_snapshot(case)
        CaseEvent.objects.create(
            case=case, actor=actor, action="REFERRAL_TRIGGERED", result="OK",
            reason="Relance envoyee a la famille et orientation vers le conseiller principal.",
        )
        return appointment, "RDV manque : alerte et relance/orientation enregistrees."

    if new_status == "ATTENDED":
        case.status = "FOLLOW_UP"
        case.save()
        CaseEvent.objects.create(
            case=case, actor=actor, action="APPOINTMENT_ATTENDED", result="OK",
            reason="Seance de suivi honoree. Dossier place en suivi.",
        )
        return appointment, "RDV marque comme honore."

    return appointment, "Statut mis a jour."


def record_snapshot(case):
    """Enregistre une capture du risque courant (trajectoire / alerte précoce)."""
    from .models import RiskSnapshot
    if case.risk_score is None:
        return None
    return RiskSnapshot.objects.create(
        case=case, risk_score=case.risk_score, risk_band=case.risk_band or "LOW",
    )


def risk_trend(case):
    """Compare les 2 dernières captures : 'up' / 'down' / 'stable'."""
    snaps = list(case.snapshots.all())
    if len(snaps) < 2:
        return "stable", 0
    delta = float(snaps[-1].risk_score) - float(snaps[-2].risk_score)
    if delta >= 5:
        return "up", round(delta, 1)
    if delta <= -5:
        return "down", round(delta, 1)
    return "stable", round(delta, 1)
