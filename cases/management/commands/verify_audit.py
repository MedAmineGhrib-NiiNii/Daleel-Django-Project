from django.core.management.base import BaseCommand
from cases.models import CaseEvent


class Command(BaseCommand):
    help = "Vérifie l'intégrité de la piste d'audit (chaînage par hash)."

    def handle(self, *args, **opts):
        events = list(CaseEvent.objects.order_by("id"))
        prev = "0" * 64
        broken = 0
        for e in events:
            expected = e.compute_hash()
            if e.prev_hash != prev or e.entry_hash != expected:
                broken += 1
                self.stdout.write(self.style.ERROR(
                    f"  ✗ Entrée #{e.id} altérée (chaîne rompue)."))
            prev = e.entry_hash
        if broken == 0:
            self.stdout.write(self.style.SUCCESS(
                f"✓ Piste d'audit intègre : {len(events)} entrées, chaîne de hash valide."))
        else:
            self.stdout.write(self.style.ERROR(
                f"✗ {broken} entrée(s) altérée(s) sur {len(events)}. Audit compromis."))