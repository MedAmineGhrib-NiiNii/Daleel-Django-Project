from django.db import models
# -*- coding: utf-8 -*-
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
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
                v = max(0, min(5, int(request.POST.get(key, 0))))   # WHO-5 : 0 à 5
            except (TypeError, ValueError):
                v = 0
            answers[key] = v
            total += v
        # Score officiel WHO-5 : brut 0-25, pourcentage = brut x 4 (0-100)
        score = total * 4
        # Seuil WHO-5 : <= 50 = bien-être faible ; <= 28 = seuil strict (à orienter)
        band = "OK" if score > 50 else "ATTENTION" if score > 28 else "ALERTE"

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

    from amal.i18n import get_translation
    tr = get_translation(request.session.get("lang", "fr"))
    questions = [(key, tr.get("sa_" + key, label)) for key, label in WELLBEING_QUESTIONS]
    return render(request, "student/self_assessment.html", {"questions": questions})


def _can_manage_resources(user):
    return user.is_superuser or user.groups.filter(name__in=["Teacher", "Director"]).exists()


@login_required(login_url="/login/")
def resources(request):
    items = {
        "BOOK": Resource.objects.filter(resource_type="BOOK"),
        "COURSE": Resource.objects.filter(resource_type="COURSE"),
        "SUMMARY": Resource.objects.filter(resource_type="SUMMARY"),
    }
    return render(request, "student/resources.html", {
        "items": items,
        "can_manage": _can_manage_resources(request.user),
        "type_choices": Resource.TYPE_CHOICES,
    })


@login_required(login_url="/login/")
def add_resource(request):
    if not _can_manage_resources(request.user):
        return render(request, "403.html", {"message": "Seuls les enseignants et le directeur peuvent ajouter des ressources."}, status=403)
    if request.method == "POST":
        rtype = request.POST.get("resource_type")
        title = (request.POST.get("title") or "").strip()
        subject = (request.POST.get("subject") or "").strip()
        if rtype in dict(Resource.TYPE_CHOICES) and title and subject:
            Resource.objects.create(
                resource_type=rtype, title=title, subject=subject,
                description=(request.POST.get("description") or "").strip(),
                url=(request.POST.get("url") or "").strip(),
            )
            messages.success(request, "Ressource ajoutée.")
        else:
            messages.error(request, "Type, titre et matière sont requis.")
    return redirect("resources")


@login_required(login_url="/login/")
def delete_resource(request, resource_id):
    if not _can_manage_resources(request.user):
        return render(request, "403.html", {"message": "Action non autorisée."}, status=403)
    Resource.objects.filter(id=resource_id).delete()
    messages.success(request, "Ressource supprimée.")
    return redirect("resources")


def teacher_required(view):
    @wraps(view)
    @login_required(login_url="/login/")
    def wrapped(request, *a, **k):
        if not (_in_group(request.user, "Teacher") or request.user.is_superuser):
            return render(request, "403.html", {"message": "Espace réservé aux enseignants."}, status=403)
        return view(request, *a, **k)
    return wrapped


@teacher_required
def teacher_profile_edit(request):
    from .models import TeacherProfile
    profile, _ = TeacherProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile.subjects = (request.POST.get("subjects") or "").strip()
        profile.is_visible = request.POST.get("is_visible") == "on"
        profile.save()
        messages.success(request, "Profil mis à jour.")
        return redirect("teacher_profile_edit")
    return render(request, "teacher/profile.html", {"profile": profile})


@login_required(login_url="/login/")
def teachers_list(request):
    from .models import TeacherProfile
    teachers = User.objects.filter(groups__name="Teacher", is_active=True,
                                   teacher_profile__is_visible=True).order_by("username")
    rows = []
    for tt in teachers:
        rows.append({
            "name": _display_name(tt), "username": tt.username,
            "subjects": tt.teacher_profile.subject_list(),
        })
    return render(request, "student/teachers.html", {"teachers": rows})


# ---------- Messagerie élève ↔ enseignant (l'élève initie toujours) ----------
def _display_name(user):
    try:
        return user.access_request.full_name or user.username
    except AccessRequest.DoesNotExist:
        return user.username


@student_required
def contact_teacher(request, teacher_username):
    """L'élève ouvre (et crée si besoin) un fil avec un enseignant. Réservé aux élèves."""
    from .models import Conversation, Message
    teacher = User.objects.filter(username=teacher_username, groups__name="Teacher", is_active=True).first()
    if not teacher:
        messages.error(request, "Enseignant introuvable.")
        return redirect("teachers_list")
    conv = Conversation.objects.filter(student=request.user, teacher=teacher).first()
    if request.method == "POST":
        body = (request.POST.get("body") or "").strip()
        if body:
            if not conv:
                conv = Conversation.objects.create(student=request.user, teacher=teacher, kind="TEACHER")
            Message.objects.create(conversation=conv, sender=request.user, body=body)
            conv.updated_at = timezone.now(); conv.save(update_fields=["updated_at"])
            return redirect("conversation_thread", conv_id=conv.id)
        messages.error(request, "Le message est vide.")
    msgs = conv.messages.all() if conv else []
    return render(request, "messaging/thread.html", {
        "counterpart": _display_name(teacher), "messages_list": msgs,
        "post_url": reverse("contact_teacher", args=[teacher_username]), "can_send": True,
    })


def _is_counselor(user):
    return user.is_superuser or _in_group(user, "Counselor")


@student_required
def counselors_list(request):
    """Liste des conseillers que l'élève peut contacter."""
    counselors = User.objects.filter(groups__name="Counselor", is_active=True).order_by("username")
    rows = [{"name": _display_name(c), "username": c.username} for c in counselors]
    return render(request, "student/counselors.html", {"counselors": rows})


@student_required
def contact_counselor(request, counselor_username):
    """L'élève ouvre un fil avec un conseiller (l'élève peut initier)."""
    from .models import Conversation, Message
    counselor = User.objects.filter(username=counselor_username, groups__name="Counselor", is_active=True).first()
    if not counselor:
        messages.error(request, "Conseiller introuvable.")
        return redirect("counselors_list")
    conv = Conversation.objects.filter(student=request.user, teacher=counselor).first()
    if request.method == "POST":
        body = (request.POST.get("body") or "").strip()
        if body:
            if not conv:
                conv = Conversation.objects.create(student=request.user, teacher=counselor, kind="COUNSELOR")
            Message.objects.create(conversation=conv, sender=request.user, body=body)
            conv.updated_at = timezone.now(); conv.save(update_fields=["updated_at"])
            return redirect("conversation_thread", conv_id=conv.id)
        messages.error(request, "Le message est vide.")
    msgs = conv.messages.all() if conv else []
    return render(request, "messaging/thread.html", {
        "counterpart": _display_name(counselor), "messages_list": msgs,
        "post_url": reverse("contact_counselor", args=[counselor_username]), "can_send": True,
        "me_id": request.user.id,
    })


@login_required(login_url="/login/")
def counselor_contact_student(request, student_id):
    """Le conseiller initie un fil avec un élève (ex. après une auto-évaluation préoccupante)."""
    if not _is_counselor(request.user):
        return render(request, "403.html", {"message": "Réservé aux conseillers."}, status=403)
    from .models import Conversation
    student = User.objects.filter(id=student_id, groups__name="Student").first()
    if not student:
        messages.error(request, "Élève introuvable.")
        return redirect("assessments_inbox")
    conv, _ = Conversation.objects.get_or_create(
        student=student, teacher=request.user, defaults={"kind": "COUNSELOR"})
    return redirect("conversation_thread", conv_id=conv.id)


@login_required(login_url="/login/")
def my_messages(request):
    """Boîte de messages. Élève : ses fils. Staff (prof/conseiller) : les fils où il est le participant staff."""
    from .models import Conversation
    u = request.user
    if _in_group(u, "Student"):
        convs = Conversation.objects.filter(student=u)
    else:
        convs = Conversation.objects.filter(teacher=u)
    rows = []
    for c in convs.prefetch_related("messages"):
        last = c.messages.last()
        other = c.teacher if c.student_id == u.id else c.student
        rows.append({"id": c.id, "name": _display_name(other), "kind": c.kind,
                     "preview": (last.body[:60] if last else ""), "updated": c.updated_at})
    is_staff = not _in_group(u, "Student")
    return render(request, "messaging/inbox.html", {"rows": rows, "is_teacher": is_staff})


@login_required(login_url="/login/")
def conversation_thread(request, conv_id):
    """Fil d'une conversation. Les deux participants peuvent écrire (mais l'élève l'a forcément initiée)."""
    from .models import Conversation, Message
    conv = Conversation.objects.filter(id=conv_id).first()
    if not conv:
        messages.error(request, "Conversation introuvable.")
        return redirect("my_messages")
    if request.user.id not in (conv.student_id, conv.teacher_id) and not request.user.is_superuser:
        return render(request, "403.html", {"message": "Vous ne participez pas à cette conversation."}, status=403)
    if request.method == "POST":
        body = (request.POST.get("body") or "").strip()
        if body:
            Message.objects.create(conversation=conv, sender=request.user, body=body)
            conv.updated_at = timezone.now(); conv.save(update_fields=["updated_at"])
            return redirect("conversation_thread", conv_id=conv.id)
    other = conv.teacher if conv.student_id == request.user.id else conv.student
    return render(request, "messaging/thread.html", {
        "counterpart": _display_name(other), "messages_list": conv.messages.all(),
        "post_url": reverse("conversation_thread", args=[conv.id]), "can_send": True,
        "me_id": request.user.id,
    })


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