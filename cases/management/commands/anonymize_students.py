from django.core.management.base import BaseCommand
from cases.models import Student


class Command(BaseCommand):
    help = "Anonymise les dossiers existants : efface prénoms et noms (ne garde que le code)."

    def handle(self, *args, **opts):
        qs = Student.objects.exclude(first_name__isnull=True, last_name__isnull=True)
        n = qs.update(first_name=None, last_name=None)
        self.stdout.write(self.style.SUCCESS(
            f"✓ {n} dossier(s) anonymisé(s). Seul le code est conservé."))