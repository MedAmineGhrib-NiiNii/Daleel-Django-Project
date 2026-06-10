from django.utils import timezone
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class School(models.Model):
    name = models.CharField(max_length=100)
    region = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Student(models.Model):
    code = models.CharField(max_length=12, unique=True)
    age = models.PositiveSmallIntegerField()
    grade_level = models.CharField(max_length=20)
    school = models.ForeignKey(School, on_delete=models.PROTECT)

    # --- NOUVEAU : Données d'identité (Issues du CSV) ---
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    governorate = models.CharField(max_length=100, null=True, blank=True)
    
    # --- NOUVEAU : Données pour le moteur de Scoring (Scénario 1) ---
    absences_percentage = models.IntegerField(default=0)
    grade_drop = models.FloatField(default=0.0)
    disciplinary_reports = models.IntegerField(default=0)

    def __str__(self):
        # Anonymat : on n'affiche que le code dossier, jamais le nom réel.
        return self.code

class Case(models.Model):
    STATUS_CHOICES = [
        ("NEW", "New"),
        ("IN_REVIEW", "In Review"),
        ("INTERVENTION", "Intervention"),
        ("FOLLOW_UP", "Follow Up"),
        ("CLOSED", "Closed"),
        ("ESCALATED", "Escalated"),
        ("REJECTED", "Rejected"),
    ]
    
    BAND_CHOICES = [
        ("LOW", "Low Risk"),
        ("MEDIUM", "Medium Risk"),
        ("HIGH", "High Risk"),
    ]

    student = models.ForeignKey(Student, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NEW")
    risk_score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    risk_band = models.CharField(max_length=10, choices=BAND_CHOICES, null=True, blank=True)
    risk_explanation = models.TextField(blank=True)
    # Fiabilité de la donnée : nombre d'indicateurs (sur 3) effectivement renseignés à l'import
    data_completeness = models.PositiveSmallIntegerField(default=3)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Empreinte d'intégrité SHA-256 : sceau sur les champs clés du dossier.
    # Permet de détecter toute altération frauduleuse (cf. verify_cases).
    integrity_hash = models.CharField(max_length=64, blank=True)

    def compute_integrity_hash(self):
        import hashlib
        content = "|".join(str(x) for x in [
            self.student.code,
            self.student.absences_percentage,
            self.student.grade_drop,
            self.student.disciplinary_reports,
            self.risk_score,
            self.risk_band,
        ])
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        # Recalcule l'empreinte à chaque sauvegarde légitime (via l'application).
        if self.student_id:
            self.integrity_hash = self.compute_integrity_hash()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Case {self.id} - {self.student.code} ({self.status})"

class CaseEvent(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    actor = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    action = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    result = models.CharField(max_length=10, choices=[("OK", "ok"), ("DENIED", "denied")])
    reason = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    # Piste d'audit infalsifiable : chaînage par hash (chaque entrée scelle la précédente)
    prev_hash = models.CharField(max_length=64, blank=True)
    entry_hash = models.CharField(max_length=64, blank=True)

    def compute_hash(self):
        import hashlib
        content = (
            f"{self.prev_hash}|{self.case_id}|{self.actor_id}|{self.action}|"
            f"{self.result}|{self.reason}|{self.timestamp.isoformat()}"
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        # Au moment de la création, on scelle l'entrée dans la chaîne
        if not self.pk and not self.entry_hash:
            if not self.timestamp:
                self.timestamp = timezone.now()
            last = CaseEvent.objects.order_by("-id").first()
            self.prev_hash = last.entry_hash if last else "0" * 64
            self.entry_hash = self.compute_hash()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.actor} - {self.action} - {self.result}"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ("SCHEDULED", "Programmé"),
        ("ATTENDED", "Présent"),
        ("MISSED", "Manqué"),
        ("CANCELLED", "Annulé"),
    ]

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='appointments')
    date = models.DateTimeField()
    counselor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SCHEDULED")
    notes = models.TextField(blank=True, help_text="Notes de la séance ou raison de l'absence")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rendez-vous {self.case.student.code} - {self.date.strftime('%Y-%m-%d')} ({self.status})"

class RiskSnapshot(models.Model):
    """Capture du score de risque à un instant T (pour la trajectoire / alerte précoce)."""
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="snapshots")
    risk_score = models.DecimalField(max_digits=5, decimal_places=2)
    risk_band = models.CharField(max_length=10)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.case.student.code} - {self.risk_score} @ {self.created_at:%Y-%m-%d}"


class Report(models.Model):
    """Rapport d'intervention généré (narratif IA) + historique téléchargeable en PDF."""
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="reports")
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=160)
    narrative = models.TextField()
    source_directive = models.TextField(blank=True)
    ai_generated = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Rapport {self.case.student.code} - {self.created_at:%Y-%m-%d}"