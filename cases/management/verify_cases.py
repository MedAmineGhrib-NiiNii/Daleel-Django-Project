from django.core.management.base import BaseCommand
from cases.models import Case


class Command(BaseCommand):
    help = "Vérifie l'intégrité des dossiers (empreinte SHA-256). Détecte toute altération."

    def handle(self, *args, **opts):
        total, altered = 0, []
        for c in Case.objects.select_related("student"):
            total += 1
            expected = c.compute_integrity_hash()
            if c.integrity_hash and c.integrity_hash != expected:
                altered.append(c.id)
        if not altered:
            self.stdout.write(self.style.SUCCESS(
                f"✓ Intégrité des dossiers vérifiée : {total} dossier(s), aucune altération."))
        else:
            self.stdout.write(self.style.ERROR(
                f"✗ {len(altered)} dossier(s) altéré(s) détecté(s) : {altered}"))
