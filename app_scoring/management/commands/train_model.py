from django.core.management.base import BaseCommand
from app_scoring.ml import evaluate_and_save


class Command(BaseCommand):
    help = "Entraine une regression logistique sur donnees synthetiques et calcule les metriques (AUC, etc.)."

    def add_arguments(self, parser):
        parser.add_argument("--n", type=int, default=1200)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **opts):
        r = evaluate_and_save(n=opts["n"], seed=opts["seed"])
        self.stdout.write(self.style.SUCCESS(
            f"Modele entraine sur {r['n_train']} eleves, teste sur {r['n_test']}.\n"
            f"  AUC = {r['auc']}  | Exactitude = {r['accuracy']}  | Precision = {r['precision']}  | Rappel = {r['recall']}\n"
            f"  Matrice de confusion : {r['confusion']}\n"
            f"  Importance apprise : {r['learned_importance']}  (vs poids fixes {r['configured_weights']})"
        ))
