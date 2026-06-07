from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
# NOUVEAU : On importe aussi Appointment
from .models import Case, CaseEvent, Appointment

# --- 1. FERMER UN DOSSIER ---
@login_required(login_url='/login/')
def close_case_api(request, case_id):
    case = get_object_or_404(Case, id=case_id)
    
    if not request.user.groups.filter(name__in=['Counselor', 'Director']).exists():
        CaseEvent.objects.create(
            case=case,
            actor=request.user,
            action="ATTEMPT_CLOSE_CASE",
            result="DENIED",
            reason="Violation de sécurité : Un Enseignant a tenté de fermer un dossier."
        )
        return render(request, '403.html', {
            'message': "Votre rôle (Enseignant) ne vous permet pas de fermer un dossier. "
                       "Cette tentative a été enregistrée dans le journal d'audit de l'établissement."
        }, status=403)

    case.status = "CLOSED"
    case.save()
    
    CaseEvent.objects.create(
        case=case,
        actor=request.user,
        action="CLOSE_CASE",
        result="OK",
        reason="Dossier fermé par le personnel autorisé."
    )
    
    messages.success(request, f"Le dossier {case.student.code} a été fermé avec succès.")
    # MODIFIÉ : On renvoie vers le dashboard, pas vers l'admin
    return redirect('case_detail', case_id=case.id)


# --- 2. OUVRIR UN DOSSIER (Prise en charge) ---
@login_required(login_url='/login/')
def open_case_api(request, case_id):
    case = get_object_or_404(Case, id=case_id)
    
    # Sécurité : Conseiller ou Directeur
    if request.user.groups.filter(name__in=['Counselor', 'Director']).exists():
        case.status = 'IN_REVIEW' # Le dossier passe de NEW à "En cours de révision"
        case.save()
        
        # Trace d'audit
        CaseEvent.objects.create(
            case=case, actor=request.user, action="OPEN_CASE", 
            result="OK", reason="Prise en charge du dossier par le conseiller."
        )
    return redirect('case_detail', case_id=case.id)


# --- 3. PLANIFIER UNE INTERVENTION ---
@login_required(login_url='/login/')
def schedule_intervention_api(request, case_id):
    case = get_object_or_404(Case, id=case_id)
    
    if request.method == "POST" and request.user.groups.filter(name__in=['Counselor', 'Director']).exists():
        date_intervention = request.POST.get('date')
        
        # 1. On crée le rendez-vous dans la base
        Appointment.objects.create(
            case=case, counselor=request.user, 
            date=date_intervention, status='SCHEDULED'
        )

        # 2. Le dossier passe à l'étape INTERVENTION (machine à états)
        case.status = 'INTERVENTION'
        case.save()
        
        # 3. On trace l'action pour l'audit
        CaseEvent.objects.create(
            case=case, actor=request.user, action="SCHEDULE_INTERVENTION", 
            result="OK", reason=f"Intervention planifiée pour le {date_intervention}."
        )
    return redirect('case_detail', case_id=case.id)


# --- 4. METTRE À JOUR UN RDV (Scénario 2 : honoré / manqué) ---
@login_required(login_url='/login/')
def update_appointment_api(request, appointment_id, new_status):
    from .services import update_appointment_status
    appt = get_object_or_404(Appointment, id=appointment_id)
    case_id = appt.case.id

    # Sécurité : seuls Conseiller/Directeur, sinon 403 stylisée + trace d'audit
    if not request.user.groups.filter(name__in=['Counselor', 'Director']).exists():
        CaseEvent.objects.create(
            case=appt.case, actor=request.user, action="ATTEMPT_UPDATE_APPOINTMENT",
            result="DENIED", reason="Tentative non autorisée de mise à jour d'un rendez-vous."
        )
        return render(request, '403.html', {
            'message': "Seuls les Conseillers et le Directeur peuvent mettre à jour un rendez-vous."
        }, status=403)

    if new_status not in ['ATTENDED', 'MISSED', 'CANCELLED']:
        messages.error(request, "Statut de rendez-vous invalide.")
        return redirect('case_detail', case_id=case_id)

    _, msg = update_appointment_status(appointment_id, new_status, actor=request.user)
    messages.success(request, msg)
    return redirect('case_detail', case_id=case_id)


# --- 5. VALIDER / REJETER une suggestion IA (human-in-the-loop, tracé) ---
@login_required(login_url='/login/')
def ai_plan_decision(request, case_id, decision):
    case = get_object_or_404(Case, id=case_id)

    if not request.user.groups.filter(name__in=['Counselor', 'Director']).exists():
        CaseEvent.objects.create(
            case=case, actor=request.user, action="ATTEMPT_AI_DECISION",
            result="DENIED", reason="Tentative non autorisée de validation d'une suggestion IA."
        )
        return render(request, '403.html', {
            'message': "Seuls les Conseillers et le Directeur peuvent valider une suggestion IA."
        }, status=403)

    if decision == "validate":
        CaseEvent.objects.create(
            case=case, actor=request.user, action="AI_PLAN_VALIDATED", result="OK",
            reason="Plan d'action proposé par l'IA validé par un humain (human-in-the-loop)."
        )
        messages.success(request, "Suggestion IA validée et tracée.")
    elif decision == "reject":
        CaseEvent.objects.create(
            case=case, actor=request.user, action="AI_PLAN_REJECTED", result="OK",
            reason="Plan d'action proposé par l'IA rejeté par un humain (validation requise)."
        )
        messages.success(request, "Suggestion IA rejetée et tracée.")
    else:
        messages.error(request, "Décision invalide.")
    return redirect('case_detail', case_id=case.id)