import csv
import json
from functools import wraps
from django.db.models import Count
from django.http import HttpResponse
# NOUVEAU : On a ajouté "redirect" à la liste des imports ici
from django.shortcuts import render, get_object_or_404, redirect
from cases.models import Student, Case, CaseEvent
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# --- On importe notre service IA local ---
from cases.ai_service import generate_intervention_plan
from app_scoring.models import ScoringConfig
from app_scoring.services import band_for_score

# Règle de sécurité : Seuls les Counselors, Directors (et Superusers) passent
def is_authorized_for_dashboard(user):
    return user.is_superuser or user.groups.filter(name__in=['Counselor', 'Director']).exists()


# Étapes de la machine à états (pour le stepper visuel sur la fiche dossier)
STATE_FLOW = [("NEW", "step_new"), ("IN_REVIEW", "step_review"),
              ("INTERVENTION", "step_intervention"), ("FOLLOW_UP", "step_followup"), ("CLOSED", "step_closed")]

import json as _json
def _trajectory_data(case):
    snaps = list(case.snapshots.all())
    return _json.dumps({
        "labels": [sn.created_at.strftime("%d/%m") for sn in snaps],
        "scores": [float(sn.risk_score) for sn in snaps],
    })

def _trend_for(case):
    from cases.services import risk_trend
    direction, delta = risk_trend(case)
    return {"direction": direction, "delta": delta}

def build_steps(current_status, request=None):
    from amal.i18n import get_translation
    lang = request.session.get('lang', 'fr') if request else 'fr'
    t = get_translation(lang)
    codes = [c for c, _ in STATE_FLOW]
    idx = codes.index(current_status) if current_status in codes else 0
    steps = []
    for i, (code, token) in enumerate(STATE_FLOW):
        steps.append({'label': t.get(token, token), 'done': i < idx, 'current': i == idx})
    return steps


def role_required(test_func):
    """Non connecté -> login ; connecté mais non autorisé -> page 403 stylisée."""
    def decorator(view):
        @wraps(view)
        @login_required(login_url='/login/')
        def wrapped(request, *args, **kwargs):
            if not test_func(request.user):
                return render(request, '403.html', {
                    'message': "Cet espace est réservé aux Conseillers et au Directeur. "
                               "Votre rôle ne vous autorise pas à le consulter."
                }, status=403)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


# On protège la vue avec notre décorateur de rôle
@role_required(is_authorized_for_dashboard)
def dashboard_home(request):
    # KPI 1 : Total des élèves suivis
    total_students = Student.objects.count()
    
    # KPI 2 : Nombre de dossiers ouverts
    total_cases = Case.objects.exclude(status='CLOSED').count()
    
    # KPI 3 : Nombre de dossiers à haut risque
    high_risk_cases = Case.objects.filter(risk_band='HIGH', status='IN_REVIEW').count()
    
    # Liste des cas nécessitant une action (priorité au risque élevé)
    active_cases = Case.objects.exclude(status='CLOSED').order_by('-risk_score')[:10]

    # --- Données pour les graphiques (Chart.js) ---
    # 1. Répartition par bande de risque
    band_map = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0}
    for row in Case.objects.values('risk_band').annotate(n=Count('id')):
        if row['risk_band'] in band_map:
            band_map[row['risk_band']] = row['n']
    risk_distribution = [band_map['LOW'], band_map['MEDIUM'], band_map['HIGH']]

    # 2. Répartition par statut de dossier
    status_labels = dict(Case.STATUS_CHOICES)
    status_rows = Case.objects.values('status').annotate(n=Count('id')).order_by('-n')
    status_chart = {
        'labels': [status_labels.get(r['status'], r['status']) for r in status_rows],
        'data': [r['n'] for r in status_rows],
    }

    # 3. Élèves à risque (MEDIUM/HIGH) par gouvernorat
    gov_rows = (Case.objects.filter(risk_band__in=['MEDIUM', 'HIGH'])
                .values('student__governorate').annotate(n=Count('id')).order_by('-n')[:6])
    gov_chart = {
        'labels': [r['student__governorate'] or 'N/A' for r in gov_rows],
        'data': [r['n'] for r in gov_rows],
    }

    context = {
        'total_students': total_students,
        'total_cases': total_cases,
        'high_risk_cases': high_risk_cases,
        'active_cases': active_cases,
        'risk_distribution': json.dumps(risk_distribution),
        'status_chart': json.dumps(status_chart),
        'gov_chart': json.dumps(gov_chart),
    }

    return render(request, 'dashboard/index.html', context)

# Vue pour afficher la chronologie d'un élève spécifique
@role_required(is_authorized_for_dashboard)
def case_detail(request, case_id):
    # On récupère le dossier ou on renvoie une erreur 404
    case = get_object_or_404(Case, id=case_id)
    
    # On récupère l'historique et les rendez-vous, triés du plus récent au plus ancien
    events = case.caseevent_set.all().order_by('-timestamp')
    appointments = case.appointments.all().order_by('-date')
    
    context = {
        'case': case,
        'events': events,
        'appointments': appointments,
        'steps': build_steps(case.status, request),
        'trajectory': _trajectory_data(case),
        'trend': _trend_for(case),
    }
    return render(request, 'dashboard/detail.html', context)

# --- Vue pour l'assistant IA (Track F) ---
@role_required(is_authorized_for_dashboard)
def generate_ai_plan(request, case_id):
    # On récupère le dossier
    case = get_object_or_404(Case, id=case_id)
    
    # Appel à notre Service IA (Le fameux Track F de l'examen)
    ai_result = generate_intervention_plan(case.student.code, case.risk_band, case.risk_score)
    
    # On recharge les données de la page de profil
    events = case.caseevent_set.all().order_by('-timestamp')
    appointments = case.appointments.all().order_by('-date')
    
    context = {
        'case': case,
        'events': events,
        'appointments': appointments,
        'ai_result': ai_result,  # On envoie la réponse de l'IA au template
        'steps': build_steps(case.status, request),
        'trajectory': _trajectory_data(case),
        'trend': _trend_for(case),
    }
    
    # On rend la même page, mais avec la suggestion de l'IA affichée
    return render(request, 'dashboard/detail.html', context)

# --- Exportation CSV pour le rôle Directeur ---
@login_required(login_url='/login/')
def export_cases_csv(request):
    # 1. SÉCURITÉ : On vérifie que c'est bien le Directeur (ou un superuser) qui clique
    if not (request.user.is_superuser or request.user.groups.filter(name='Director').exists()):
        return render(request, '403.html', {
            'message': "Seul le Directeur de l'établissement est autorisé à exporter "
                       "les données médicales et scolaires."
        }, status=403)
    
    # 2. PRÉPARATION DU FICHIER CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="rapport_amal_risques.csv"'
    
    writer = csv.writer(response)
    # Ligne d'en-tête
    writer.writerow(['Code Élève', 'Niveau', 'Gouvernorat', 'Score de Risque (/100)', 'Niveau de Risque', 'Statut du Dossier'])
    
    # 3. EXTRACTION DES DONNÉES (en respectant les filtres du tableau de bord)
    cases = _filter_cases(request).select_related('student')
    for case in cases:
        writer.writerow([
            case.student.code,
            case.student.grade_level,
            case.student.governorate,
            case.risk_score,
            case.risk_band,
            case.status
        ])
        
    return response


# --- Filtre partagé (liste + export) ---
def _filter_cases(request):
    """Applique les filtres status / risk_band / governorate passés en GET."""
    qs = Case.objects.select_related('student').all()
    status = request.GET.get('status')
    band = request.GET.get('risk_band')
    gov = request.GET.get('governorate')
    if status:
        qs = qs.filter(status=status)
    if band:
        qs = qs.filter(risk_band=band)
    if gov:
        qs = qs.filter(student__governorate=gov)
    return qs.order_by('-risk_score')


# --- Liste des dossiers avec filtres (Section 11 : case list with filters) ---
@role_required(is_authorized_for_dashboard)
def case_list(request):
    cases = _filter_cases(request)
    governorates = (Case.objects.exclude(student__governorate__isnull=True)
                    .values_list('student__governorate', flat=True).distinct().order_by('student__governorate'))
    context = {
        'cases': cases,
        'total': cases.count(),
        'governorates': governorates,
        'status_choices': Case.STATUS_CHOICES,
        'band_choices': Case.BAND_CHOICES,
        'cur_status': request.GET.get('status', ''),
        'cur_band': request.GET.get('risk_band', ''),
        'cur_gov': request.GET.get('governorate', ''),
        'querystring': request.GET.urlencode(),
    }
    return render(request, 'dashboard/case_list.html', context)


# --- Seuils de risque configurables par le superviseur (Scénario 1) ---
@role_required(is_authorized_for_dashboard)
def scoring_config(request):
    cfg = ScoringConfig.get_solo()
    if request.method == 'POST':
        try:
            medium = int(request.POST.get('medium_threshold'))
            high = int(request.POST.get('high_threshold'))
        except (TypeError, ValueError):
            messages.error(request, "Valeurs de seuil invalides.")
            return redirect('scoring_config')

        if not (0 < medium < high <= 100):
            messages.error(request, "Contrainte : 0 < seuil MEDIUM < seuil HIGH <= 100.")
            return redirect('scoring_config')

        cfg.medium_threshold = medium
        cfg.high_threshold = high
        cfg.save()

        # Re-classification de tous les dossiers existants selon les nouveaux seuils
        reclassed = 0
        for case in Case.objects.exclude(risk_score__isnull=True):
            new_band = band_for_score(float(case.risk_score), (medium, high))
            if new_band != case.risk_band:
                case.risk_band = new_band
                case.save(update_fields=['risk_band'])
                reclassed += 1

        # Trace d'audit (sur un dossier de référence si présent)
        ref = Case.objects.first()
        if ref:
            CaseEvent.objects.create(
                case=ref, actor=request.user, action="UPDATE_SCORING_THRESHOLDS", result="OK",
                reason=f"Seuils mis à jour : MEDIUM>={medium}, HIGH>={high}. {reclassed} dossiers reclassés."
            )
        messages.success(request, f"Seuils enregistrés. {reclassed} dossier(s) reclassé(s).")
        return redirect('scoring_config')

    return render(request, 'dashboard/scoring_config.html', {'cfg': cfg})


# --- Simulateur de risque « what-if » (aide à la décision explicable) ---
@role_required(is_authorized_for_dashboard)
def risk_simulator(request):
    cfg = ScoringConfig.get_solo()
    # Échantillon de dossiers chargeables comme point de départ
    sample = []
    for case in Case.objects.select_related('student').order_by('-risk_score')[:40]:
        s = case.student
        label = s.code + (f" — {s.first_name} {s.last_name}" if s.first_name else "")
        sample.append({
            'id': case.id, 'label': label,
            'absences': s.absences_percentage, 'grade_drop': s.grade_drop,
            'disciplinary': s.disciplinary_reports,
        })
    context = {
        'medium': cfg.medium_threshold,
        'high': cfg.high_threshold,
        'cases_json': json.dumps(sample),
    }
    return render(request, 'dashboard/simulator.html', context)


# --- Endpoint de vérification : prouve que le calcul = le moteur Python ---
@role_required(is_authorized_for_dashboard)
def simulate_api(request):
    from django.http import JsonResponse
    from app_scoring.services import compute_risk, risk_contributions
    try:
        absences = float(request.GET.get('absences', 0))
        grade_drop = float(request.GET.get('grade_drop', 0))
        disciplinary = float(request.GET.get('disciplinary', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'paramètres invalides'}, status=400)

    score, band, explanation = compute_risk(absences, grade_drop, disciplinary)
    return JsonResponse({
        'score': float(score), 'band': band, 'explanation': explanation,
        'contributions': risk_contributions(absences, grade_drop, disciplinary),
    })


# --- Évaluation du modèle (métriques calculées, Section 10) ---
@role_required(is_authorized_for_dashboard)
def model_evaluation(request):
    from app_scoring.ml import load_metrics
    eval_labels = [('absences', "Absentéisme"), ('grades', "Chute des notes"), ('discipline', "Discipline")]
    return render(request, 'dashboard/model_eval.html', {'m': load_metrics(), 'eval_labels': eval_labels})


# --- Rapports : génération (Ollama), historique, téléchargement PDF ---
@role_required(is_authorized_for_dashboard)
def generate_report(request, case_id):
    from cases.models import Case, Report
    from cases.ai_service import generate_case_report
    case = get_object_or_404(Case, id=case_id)
    result = generate_case_report(case)
    report = Report.objects.create(
        case=case, generated_by=request.user,
        title=f"Rapport d'intervention — {case.student.code}",
        narrative=result["narrative"], source_directive=result["directive"],
        ai_generated=result["ai_generated"],
    )
    CaseEvent.objects.create(case=case, actor=request.user, action="REPORT_GENERATED", result="OK",
                             reason="Rapport d'intervention généré.")
    messages.success(request, "Rapport généré.")
    return redirect('view_report', report_id=report.id)


@role_required(is_authorized_for_dashboard)
def report_history(request):
    from cases.models import Report
    reports = Report.objects.select_related('case__student', 'generated_by').all()
    return render(request, 'dashboard/report_history.html', {'reports': reports})


@role_required(is_authorized_for_dashboard)
def view_report(request, report_id):
    from cases.models import Report
    try:
        report = Report.objects.select_related('case__student', 'generated_by').get(id=report_id)
    except Report.DoesNotExist:
        messages.error(request, "Ce rapport n'existe plus (la base a peut-être été réinitialisée). Régénérez-le depuis le dossier.")
        return redirect('report_history')
    return render(request, 'dashboard/report_view.html', {'report': report})


@role_required(is_authorized_for_dashboard)
def download_report(request, report_id):
    from cases.models import Report
    from cases.pdf_report import render_report_pdf
    try:
        report = Report.objects.select_related('case__student', 'generated_by').get(id=report_id)
    except Report.DoesNotExist:
        messages.error(request, "Ce rapport n'existe plus (la base a peut-être été réinitialisée). Régénérez-le depuis le dossier.")
        return redirect('report_history')
    pdf = render_report_pdf(report)
    resp = HttpResponse(pdf, content_type='application/pdf')
    fname = f"rapport_{report.case.student.code}_{report.created_at:%Y%m%d}.pdf"
    resp['Content-Disposition'] = f'attachment; filename="{fname}"'
    return resp


# --- Tableau de métriques calculées (Section 10) ---
@role_required(is_authorized_for_dashboard)
def metrics_dashboard(request):
    from cases.models import Case, CaseEvent, Report
    from app_scoring.ml import load_metrics

    total = Case.objects.count()
    taken = Case.objects.exclude(status='NEW').count()
    closed = Case.objects.filter(status='CLOSED').count()
    full_data = Case.objects.filter(data_completeness=3).count()

    events = CaseEvent.objects.count()
    denied = CaseEvent.objects.filter(result='DENIED').count()

    # Intégrité de la piste d'audit (chaînage par hash)
    chain_ok, broken = True, 0
    prev = "0" * 64
    for e in CaseEvent.objects.order_by('id'):
        if e.prev_hash != prev or e.entry_hash != e.compute_hash():
            chain_ok = False; broken += 1
        prev = e.entry_hash

    def pct(a, b):
        return round(a / b * 100, 1) if b else 0.0

    model = load_metrics()
    ctx = {
        'total': total,
        'workflow_completion': pct(taken, total),
        'closed_rate': pct(closed, total),
        'data_reliability': pct(full_data, total),
        'events': events,
        'denied': denied,
        'security_blocked': denied,
        'reports': Report.objects.count(),
        'chain_ok': chain_ok, 'broken': broken,
        'model': model,
    }
    return render(request, 'dashboard/metrics.html', ctx)


# --- NOUVEAU : Le Routeur de connexion ---
@login_required(login_url='/login/')
def dashboard_router(request):
    """
    Routeur intelligent : Redirige l'utilisateur vers la bonne interface
    en fonction de son rôle de sécurité (Groupe).
    """
    user = request.user

    # Élève -> espace élève
    if user.groups.filter(name='Student').exists() and not user.is_superuser:
        return redirect('student_home')

    # 1. Si c'est le Directeur ou le Conseiller (ou l'Admin) -> Direction le grand tableau de bord
    if user.is_superuser or user.groups.filter(name__in=['Director', 'Counselor']).exists():
        return redirect('dashboard_home')
        
    # 2. Si c'est l'Enseignant -> Direction l'outil d'importation CSV
    elif user.groups.filter(name='Teacher').exists():
        return redirect('upload_csv')
        
    # 3. Par sécurité, si l'utilisateur n'a pas de rôle défini -> Retour à l'accueil
    else:
        return redirect('dashboard_home')