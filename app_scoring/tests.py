from django.test import TestCase
from app_scoring.services import compute_risk


class ScoringEngineTests(TestCase):
    def test_low_risk_profile(self):
        score, band, _ = compute_risk(absences_percentage=5, grade_drop=0, disciplinary_reports=0)
        self.assertEqual(band, "LOW")
        self.assertLess(score, 30)

    def test_high_risk_profile(self):
        score, band, explanation = compute_risk(absences_percentage=70, grade_drop=5, disciplinary_reports=5)
        self.assertEqual(band, "HIGH")
        self.assertGreaterEqual(score, 60)
        self.assertIn("absent", explanation.lower())

    def test_handles_missing_values_safely(self):
        # Des valeurs nulles ne doivent pas faire planter le moteur
        score, band, _ = compute_risk(None, None, None)
        self.assertEqual(band, "LOW")
        self.assertEqual(float(score), 0.0)


class ModelTrainingTests(TestCase):
    """Le modèle entraîné apprend un vrai signal et donne des métriques valides."""
    def test_evaluation_metrics_are_valid(self):
        from app_scoring.ml import evaluate_and_save
        r = evaluate_and_save(n=600, seed=7)
        # AUC entre 0.5 (hasard) et 1 ; ici nettement > 0.5 car signal présent
        self.assertGreater(r["auc"], 0.7)
        self.assertLessEqual(r["auc"], 1.0)
        # la matrice de confusion couvre tout l'ensemble de test
        c = r["confusion"]
        self.assertEqual(c["TP"] + c["FP"] + c["TN"] + c["FN"], r["n_test"])
        # l'absentéisme reste le facteur le plus important (cohérent avec ABC)
        imp = r["learned_importance"]
        self.assertGreaterEqual(imp["absences"], imp["grades"])
        self.assertGreaterEqual(imp["absences"], imp["discipline"])
