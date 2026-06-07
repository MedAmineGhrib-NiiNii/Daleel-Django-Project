from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class AccessRequest(models.Model):
    """Demande de création de compte, soumise à la validation du Directeur."""
    ROLE_CHOICES = [
        ("Student", "Élève"),
        ("Teacher", "Enseignant"),
        ("Counselor", "Conseiller"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "En attente"),
        ("APPROVED", "Approuvée"),
        ("REJECTED", "Refusée"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="access_request")
    full_name = models.CharField(max_length=120)
    requested_role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    student_code = models.CharField(max_length=40, blank=True, help_text="Pour les élèves : leur code dossier")
    biography = models.TextField(help_text="Présentez-vous (vérification anti-bot)")
    document = models.FileField(upload_to="access_docs/", blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_requests")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.full_name} ({self.requested_role}) - {self.status}"


class Resource(models.Model):
    """Ressource pédagogique (livre, support de cours, résumé) pour l'espace élève."""
    TYPE_CHOICES = [("BOOK", "Livre"), ("COURSE", "Support de cours"), ("SUMMARY", "Résumé")]
    title = models.CharField(max_length=160)
    subject = models.CharField(max_length=80)
    resource_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)

    def __str__(self):
        return f"[{self.resource_type}] {self.title}"


class SelfAssessment(models.Model):
    """Auto-évaluation de bien-être / engagement remplie par l'élève, envoyée au conseiller."""
    student_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="self_assessments")
    student_code = models.CharField(max_length=40, blank=True)
    score = models.PositiveSmallIntegerField(default=0, help_text="0-100, plus haut = meilleur bien-être")
    band = models.CharField(max_length=10, default="OK")
    answers = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Auto-éval {self.student_user} ({self.score}/100)"


class Conversation(models.Model):
    """Fil élève↔staff. kind=TEACHER : seul l'élève initie. kind=COUNSELOR : les deux peuvent initier."""
    KIND_CHOICES = [("TEACHER", "Enseignant"), ("COUNSELOR", "Conseiller")]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conv_as_student")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conv_as_teacher")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default="TEACHER")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("student", "teacher")
        ordering = ["-updated_at"]

    @property
    def staff(self):
        """Participant côté staff (enseignant ou conseiller)."""
        return self.teacher

    def __str__(self):
        return f"{self.student} ↔ {self.teacher} ({self.kind})"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]


class TeacherProfile(models.Model):
    """Profil de soutien d'un enseignant : matières (tags) + visibilité publique.
    Rempli par l'enseignant lui-même après activation de son compte."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    subjects = models.CharField(max_length=300, blank=True,
                                help_text="Matières séparées par des virgules")
    is_visible = models.BooleanField(default=False,
                                     help_text="Apparaître dans la page « Profs de soutien »")

    def subject_list(self):
        return [s.strip() for s in self.subjects.split(",") if s.strip()]

    def __str__(self):
        return f"Profil {self.user.username} (visible={self.is_visible})"