import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from cases.models import School, Student, Case, RiskSnapshot
from app_scoring.services import compute_risk, band_for_score

PRENOMS = ["Mohamed", "Ahmed", "Yassine", "Aziz", "Skander", "Mariem", "Salma",
           "Ines", "Farah", "Nour", "Rania", "Khalil", "Hamza", "Aya", "Lina"]
NOMS = ["Ben Ali", "Trabelsi", "Gharbi", "Mejri", "Bouazizi", "Khelifi",
        "Jebali", "Sassi", "Hamdi", "Chaabane", "Dridi", "Ayari"]


class Command(BaseCommand):
    help = "Genere des ecoles, des eleves synthetiques et leurs dossiers de risque (donnees de demo)."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=200, help="Nombre d'eleves a generer")

    def handle(self, *args, **options):
        n = options["count"]
        RiskSnapshot.objects.all().delete()
        Case.objects.all().delete()
        Student.objects.all().delete()
        School.objects.all().delete()

        ecoles_data = [
            ("Lycee Pilote", "Ariana"), ("Lycee Carnot", "Tunis"),
            ("Lycee Hedi Chaker", "Sfax"), ("Lycee de Gabes", "Gabes"),
        ]
        ecoles = [School.objects.create(name=nom, region=region) for nom, region in ecoles_data]
        niveaux = ["1ere Annee", "2eme Annee", "3eme Annee", "Baccalaureat"]

        high = medium = low = 0
        for i in range(n):
            # Distribution realiste : la majorite va bien, une minorite est a risque
            profile = random.choices(["stable", "fragile", "critique"], weights=[60, 28, 12])[0]
            if profile == "stable":
                absences, drop, disc = random.randint(0, 12), round(random.uniform(0, 4), 1), random.randint(0, 1)
            elif profile == "fragile":
                absences, drop, disc = random.randint(15, 35), round(random.uniform(5, 9), 1), random.randint(1, 3)
            else:
                absences, drop, disc = random.randint(40, 80), round(random.uniform(10, 18), 1), random.randint(3, 6)

            ecole = random.choice(ecoles)
            student = Student.objects.create(
                code=f"ST-2026-{i + 1:04d}",
                first_name=random.choice(PRENOMS),
                last_name=random.choice(NOMS),
                age=random.randint(15, 19),
                grade_level=random.choice(niveaux),
                governorate=ecole.region,
                absences_percentage=absences,
                grade_drop=drop,
                disciplinary_reports=disc,
                school=ecole,
            )

            score, band, explanation = compute_risk(absences, drop, disc)
            case = Case.objects.create(
                student=student, risk_score=score, risk_band=band,
                risk_explanation=explanation,
                status="IN_REVIEW" if band == "HIGH" else "NEW",
            )
            # Historique synthétique : 3 captures passées qui dérivent vers le score actuel
            cur = float(score)
            start = max(0.0, min(100.0, cur + random.uniform(-25, 25)))
            now = timezone.now()
            for wk in range(3, 0, -1):
                frac = (3 - wk) / 3.0
                val = round(start + (cur - start) * frac, 2)
                b = band_for_score(val)
                RiskSnapshot.objects.create(case=case, risk_score=val, risk_band=b,
                                            created_at=now - timedelta(weeks=wk))
            RiskSnapshot.objects.create(case=case, risk_score=score, risk_band=band, created_at=now)
            high += band == "HIGH"
            medium += band == "MEDIUM"
            low += band == "LOW"

        self.stdout.write(self.style.SUCCESS(
            f"OK : {len(ecoles)} ecoles, {n} eleves et dossiers crees "
            f"(HIGH={high}, MEDIUM={medium}, LOW={low})."
        ))
