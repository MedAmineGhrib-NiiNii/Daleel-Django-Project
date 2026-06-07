# -*- coding: utf-8 -*-
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from functools import wraps

from .models import AccessRequest, Resource, SelfAssessment
from cases.models import Case, CaseEvent
from cases.ai_service import study_chat


def _in_group(user, name):
    return user.is_authenticated and user.groups.filter(name=name).exists()

def is_director(user):
    return user.is_superuser or _in_group(user, "Director")

def director_required(view):
    @wraps(view)
    @login_required(login_url="/login/")
    def wrapped(request, *a, **k):
        if not is_director(request.user):
            return render(request, "403.html", {"message": "Seul le Directeur peut gérer les demandes d'accès."}, status=403)
        return view(request, *a, **k)
    return wrapped

def student_required(view):
    @wraps(view)
    @login_required(login_url="/login/")
    def wrapped(request, *a, **k):
        if not (_in_group(request.user, "Student") or request.user.is_superuser):
            return render(request, "403.html", {"message": "Espace réservé aux élèves."}, status=403)
        return view(request, *a, **k)
    return wrapped


def register(request):
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        full_name = (request.POST.get("full_name") or "").strip()
        role = request.POST.get("role")
        bio = (request.POST.get("biography") or "").strip()
        student_code = (request.POST.get("student_code") or "").strip()
        document = request.FILES.get("document")

        if role not in dict(AccessRequest.ROLE_CHOICES):
            messages.error(request, "Rôle invalide.")
            return redirect("register")
        if not username or not password or not full_name or len(bio) < 20:
            messages.error(request, "Tous les champs sont requis (biographie d'au moins 20 caractères).")
            return redirect("register")
        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur existe déjà.")
            return redirect("register")

        # Force du mot de passe (validateurs Django : longueur, mots trop communs, etc.)
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as PwdValidationError
        try:
            validate_password(password)
        except PwdValidationError as e:
            messages.error(request, " ".join(e.messages))
            return redirect("register")

        user = User.objects.create_user(username=username, password=password, is_active=False)
        AccessRequest.objects.create(
            user=user, full_name=full_name, requested_role=role,
            student_code=student_code, biography=bio, document=document,
        )
        return render(request, "registration/pending.html", {"full_name": full_name})

    return render(request, "registration/register.html", {"roles": AccessRequest.ROLE_CHOICES})


@director_required
def access_requests(request):
    pending = AccessRequest.objects.filter(status="PENDING").order_by("created_at")
    history = AccessRequest.objects.exclude(status="PENDING").order_by("-reviewed_at")[:20]
    return render(request, "governance/access_requests.html", {"pending": pending, "history": history})


@director_required
def review_request(request, req_id, decision):
    req = get_object_or_404(AccessRequest, id=req_id)
    if req.status != "PENDING":
        messages.error(request, "Cette demande a déjà été traitée.")
        return redirect("access_requests")

    if decision == "approve":
        group, _ = Group.objects.get_or_create(name=req.requested_role)
        req.user.is_active = True
        req.user.save()
        req.user.groups.add(group)
        req.status = "APPROVED"
        messages.success(request, f"Compte de {req.full_name} approuvé ({req.get_requested_role_display()}).")
    elif decision == "reject":
        req.user.is_active = False
        req.user.save()
        req.status = "REJECTED"
        messages.success(request, f"Demande de {req.full_name} refusée.")
    else:
        messages.error(request, "Décision invalide.")
        return redirect("access_requests")

    req.reviewed_by = request.user
    req.reviewed_at = timezone.now()
    req.save()
    return redirect("access_requests")


@student_required
def student_home(request):
    last = SelfAssessment.objects.filter(student_user=request.user).order_by("-created_at").first()
    return render(request, "student/home.html", {"last_assessment": last})


WELLBEING_QUESTIONS = [
    ("q1", "Je me sens à l'aise et motivé(e) à l'école en ce moment."),
    ("q2", "J'arrive à suivre mes cours et à comprendre les leçons."),
    ("q3", "Je dors bien et j'ai de l'énergie pour étudier."),
    ("q4", "Je me sens soutenu(e) par mon entourage (famille, amis, profs)."),
    ("q5", "Je garde confiance en mes capacités à réussir."),
]

@student_required
def self_assessment(request):
    if request.method == "POST":
        answers, total = {}, 0
        for key, _label in WELLBEING_QUESTIONS:
            try:
                v = max(0, min(4, int(request.POST.get(key, 0))))
            except (TypeError, ValueError):
                v = 0
            answers[key] = v
            total += v
        score = round((total / (len(WELLBEING_QUESTIONS) * 4)) * 100)
        band = "OK" if score >= 60 else "ATTENTION" if score >= 35 else "ALERTE"

        try:
            code = request.user.access_request.student_code
        except AccessRequest.DoesNotExist:
            code = ""

        SelfAssessment.objects.create(
            student_user=request.user, student_code=code, score=score, band=band, answers=answers,
        )
        if code:
            case = Case.objects.filter(student__code=code).first()
            if case:
                CaseEvent.objects.create(
                    case=case, actor=request.user, action="SELF_ASSESSMENT_RECEIVED", result="OK",
                    reason=f"Auto-évaluation bien-être reçue : {score}/100 ({band}).",
                )
        return render(request, "student/assessment_done.html", {"score": score, "band": band})

    return render(request, "student/self_assessment.html", {"questions": WELLBEING_QUESTIONS})


@login_required(login_url="/login/")
def resources(request):
    items = {
        "BOOK": Resource.objects.filter(resource_type="BOOK"),
        "COURSE": Resource.objects.filter(resource_type="COURSE"),
        "SUMMARY": Resource.objects.filter(resource_type="SUMMARY"),
    }
    return render(request, "student/resources.html", {"items": items})


@login_required(login_url="/login/")
def teachers_list(request):
    teachers = User.objects.filter(groups__name="Teacher", is_active=True).order_by("username")
    rows = []
    for tt in teachers:
        name = tt.username
        try:
            name = tt.access_request.full_name or tt.username
        except AccessRequest.DoesNotExist:
            pass
        rows.append({"name": name, "username": tt.username})
    return render(request, "student/teachers.html", {"teachers": rows})


@student_required
def study_chat_page(request):
    return render(request, "student/chat.html")


@student_required
def study_chat_api(request):
    message = request.GET.get("message", "")
    if not message.strip():
        return JsonResponse({"success": False, "reply": "Pose-moi une question sur tes études."})
    return JsonResponse(study_chat(message))


@login_required(login_url="/login/")
def assessments_inbox(request):
    if not (is_director(request.user) or _in_group(request.user, "Counselor")):
        return render(request, "403.html", {"message": "Réservé aux conseillers et au directeur."}, status=403)
    items = SelfAssessment.objects.select_related("student_user").order_by("-created_at")[:50]
    return render(request, "governance/assessments_inbox.html", {"items": items})