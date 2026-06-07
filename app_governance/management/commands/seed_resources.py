from django.core.management.base import BaseCommand
from app_governance.models import Resource

DATA = [
    ("BOOK", "Mathématiques 2e année", "Mathématiques", "Manuel de base avec exercices corrigés.", "https://fr.khanacademy.org/math"),
    ("BOOK", "Physique-Chimie", "Physique", "Notions essentielles et expériences.", "https://fr.khanacademy.org/science/physics"),
    ("COURSE", "Cours : Fonctions et dérivées", "Mathématiques", "Support de cours pas à pas.", "https://fr.khanacademy.org/math/differential-calculus"),
    ("COURSE", "Cours : Grammaire française", "Français", "Règles de grammaire et conjugaison.", ""),
    ("SUMMARY", "Résumé : La Révolution industrielle", "Histoire", "Fiche de révision synthétique.", ""),
    ("SUMMARY", "Résumé : Les équations du second degré", "Mathématiques", "Méthode + formules clés.", ""),
]

class Command(BaseCommand):
    help = "Crée des ressources pédagogiques de démonstration."
    def handle(self, *a, **k):
        Resource.objects.all().delete()
        for rt, title, subject, desc, url in DATA:
            Resource.objects.create(resource_type=rt, title=title, subject=subject, description=desc, url=url)
        self.stdout.write(self.style.SUCCESS(f"{len(DATA)} ressources créées."))
