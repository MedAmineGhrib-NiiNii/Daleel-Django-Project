from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone

from .models import School, Student, Case, Appointment, CaseEvent
from .services import update_appointment_status


class Scenario2Tests(TestCase):
    """Test métier : un RDV manqué augmente le risque et laisse une trace."""

    def setUp(self):
        self.school = School.objects.create(name="École de Test")
        self.student = Student.objects.create(code="ST-TEST", age=15, grade_level="10th", school=self.school)
        self.case = Case.objects.create(student=self.student, risk_score=50, risk_band="MEDIUM", status="IN_REVIEW")
        self.appointment = Appointment.objects.create(case=self.case, date=timezone.now(), status="SCHEDULED")

    def test_missed_appointment_triggers_alert(self):
        update_appointment_status(self.appointment.id, "MISSED", notes="Absent.")
        self.case.refresh_from_db()
        self.assertEqual(self.case.risk_score, 60)
        self.assertEqual(self.case.risk_band, "HIGH")
        self.assertTrue(CaseEvent.objects.filter(case=self.case, action="MISSED_APPOINTMENT_ALERT").exists())


class RBACSecurityTests(TestCase):
    """Tests d'intégration : les rôles contrôlent l'accès (cas d'échec contrôlé)."""

    def setUp(self):
        self.client = Client()
        for name in ["Teacher", "Counselor", "Director"]:
            Group.objects.create(name=name)
        self.school = School.objects.create(name="École RBAC")
        self.student = Student.objects.create(code="ST-RBAC", age=16, grade_level="2A", school=self.school)
        self.case = Case.objects.create(student=self.student, risk_score=40, risk_band="MEDIUM", status="IN_REVIEW")

        def make(username, group):
            u = User.objects.create_user(username=username, password="pwd12345")
            u.groups.add(Group.objects.get(name=group))
            return u

        self.teacher = make("prof", "Teacher")
        self.counselor = make("conseiller", "Counselor")
        self.director = make("directeur", "Director")

    def test_teacher_cannot_close_case(self):
        self.client.login(username="prof", password="pwd12345")
        resp = self.client.get(reverse("api_close_case", args=[self.case.id]))
        self.assertEqual(resp.status_code, 403)
        self.case.refresh_from_db()
        self.assertNotEqual(self.case.status, "CLOSED")
        # La tentative refusée doit être tracée
        self.assertTrue(CaseEvent.objects.filter(case=self.case, result="DENIED").exists())

    def test_counselor_can_close_case(self):
        self.client.login(username="conseiller", password="pwd12345")
        self.client.get(reverse("api_close_case", args=[self.case.id]))
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, "CLOSED")

    def test_only_director_can_export(self):
        self.client.login(username="conseiller", password="pwd12345")
        self.assertEqual(self.client.get(reverse("export_cases_csv")).status_code, 403)
        self.client.login(username="directeur", password="pwd12345")
        self.assertEqual(self.client.get(reverse("export_cases_csv")).status_code, 200)


class Scenario2WorkflowTests(TestCase):
    """Intégration : flux RDV manqué de bout en bout via l'URL (Scénario 2)."""

    def setUp(self):
        self.client = Client()
        for name in ["Teacher", "Counselor", "Director"]:
            Group.objects.get_or_create(name=name)
        self.school = School.objects.create(name="École S2")
        self.student = Student.objects.create(code="ST-S2", age=16, grade_level="2A", school=self.school)
        self.case = Case.objects.create(student=self.student, risk_score=40, risk_band="MEDIUM", status="INTERVENTION")
        self.appt = Appointment.objects.create(case=self.case, date=timezone.now(), status="SCHEDULED")

        u = User.objects.create_user(username="cons2", password="pwd12345")
        u.groups.add(Group.objects.get(name="Counselor"))
        t = User.objects.create_user(username="prof2", password="pwd12345")
        t.groups.add(Group.objects.get(name="Teacher"))

    def test_missed_via_url_triggers_referral_and_follow_up(self):
        self.client.login(username="cons2", password="pwd12345")
        self.client.get(reverse("api_update_appointment", args=[self.appt.id, "MISSED"]))
        self.case.refresh_from_db()
        self.appt.refresh_from_db()
        self.assertEqual(self.appt.status, "MISSED")
        self.assertEqual(self.case.status, "FOLLOW_UP")
        self.assertTrue(CaseEvent.objects.filter(case=self.case, action="MISSED_APPOINTMENT_ALERT").exists())
        self.assertTrue(CaseEvent.objects.filter(case=self.case, action="REFERRAL_TRIGGERED").exists())

    def test_teacher_cannot_update_appointment(self):
        self.client.login(username="prof2", password="pwd12345")
        resp = self.client.get(reverse("api_update_appointment", args=[self.appt.id, "MISSED"]))
        self.assertEqual(resp.status_code, 403)
        self.appt.refresh_from_db()
        self.assertEqual(self.appt.status, "SCHEDULED")


class ThresholdConfigTests(TestCase):
    """Le superviseur peut configurer les seuils, ce qui reclasse les dossiers."""

    def setUp(self):
        self.client = Client()
        Group.objects.get_or_create(name="Director")
        self.school = School.objects.create(name="École T")
        self.student = Student.objects.create(code="ST-T", age=16, grade_level="2A", school=self.school)
        # Score 45 -> MEDIUM avec seuils par défaut (30/60)
        self.case = Case.objects.create(student=self.student, risk_score=45, risk_band="MEDIUM", status="NEW")
        d = User.objects.create_user(username="dir2", password="pwd12345")
        d.groups.add(Group.objects.get(name="Director"))

    def test_lowering_high_threshold_reclasses_case(self):
        self.client.login(username="dir2", password="pwd12345")
        # On abaisse le seuil HIGH à 40 -> le dossier (45) doit passer HIGH
        self.client.post(reverse("scoring_config"), {"medium_threshold": 20, "high_threshold": 40})
        self.case.refresh_from_db()
        self.assertEqual(self.case.risk_band, "HIGH")


class HumanInTheLoopTests(TestCase):
    """L'avis IA doit être validé/rejeté par un humain, et tracé."""
    def setUp(self):
        self.client = Client()
        for n in ["Teacher", "Counselor"]:
            Group.objects.get_or_create(name=n)
        sc = School.objects.create(name="École HITL")
        st = Student.objects.create(code="ST-HITL", age=16, grade_level="2A", school=sc)
        self.case = Case.objects.create(student=st, risk_score=70, risk_band="HIGH", status="IN_REVIEW")
        for u, g in [("c_hitl", "Counselor"), ("t_hitl", "Teacher")]:
            x = User.objects.create_user(username=u, password="pwd12345")
            x.groups.add(Group.objects.get(name=g))

    def test_counselor_can_validate_ai(self):
        self.client.login(username="c_hitl", password="pwd12345")
        self.client.get(reverse("api_ai_decision", args=[self.case.id, "validate"]))
        self.assertTrue(CaseEvent.objects.filter(case=self.case, action="AI_PLAN_VALIDATED").exists())

    def test_teacher_cannot_validate_ai(self):
        self.client.login(username="t_hitl", password="pwd12345")
        r = self.client.get(reverse("api_ai_decision", args=[self.case.id, "validate"]))
        self.assertEqual(r.status_code, 403)
        self.assertFalse(CaseEvent.objects.filter(case=self.case, action="AI_PLAN_VALIDATED").exists())


class DataCompletenessTests(TestCase):
    """Une colonne d'indicateur manquante réduit la fiabilité de la donnée."""
    def setUp(self):
        self.client = Client()
        Group.objects.get_or_create(name="Teacher")
        u = User.objects.create_user(username="t_dc", password="pwd12345")
        u.groups.add(Group.objects.get(name="Teacher"))

    def test_missing_indicator_column_lowers_completeness(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        # CSV sans la colonne disciplinary_reports -> 2/3 indicateurs
        csv = b"student_code,absences_percentage,grade_drop\nST-DC-1,30,2\n"
        self.client.login(username="t_dc", password="pwd12345")
        self.client.post(reverse("upload_csv"),
                         {"csv_file": SimpleUploadedFile("c.csv", csv, content_type="text/csv")})
        case = Case.objects.get(student__code="ST-DC-1")
        self.assertEqual(case.data_completeness, 2)


class ReportAndTrajectoryTests(TestCase):
    def setUp(self):
        self.client = Client()
        for n in ["Counselor", "Director"]:
            Group.objects.get_or_create(name=n)
        sc = School.objects.create(name="École R")
        st = Student.objects.create(code="ST-R1", age=16, grade_level="2A", school=sc,
                                    absences_percentage=40, grade_drop=10, disciplinary_reports=2)
        self.case = Case.objects.create(student=st, risk_score=43, risk_band="MEDIUM", status="NEW")
        d = User.objects.create_user(username="dir_r", password="pwd12345")
        d.groups.add(Group.objects.get(name="Director"))

    def test_snapshot_and_trend(self):
        from cases.services import record_snapshot, risk_trend
        from cases.models import RiskSnapshot
        self.case.risk_score = 30; self.case.save(); record_snapshot(self.case)
        self.case.risk_score = 55; self.case.save(); record_snapshot(self.case)
        self.assertEqual(RiskSnapshot.objects.filter(case=self.case).count(), 2)
        direction, delta = risk_trend(self.case)
        self.assertEqual(direction, "up")

    def test_generate_and_download_report(self):
        from cases.models import Report
        c = Client(); c.login(username="dir_r", password="pwd12345")
        c.get(reverse("generate_report", args=[self.case.id]))  # Ollama down -> fallback
        rep = Report.objects.filter(case=self.case).first()
        self.assertIsNotNone(rep)
        self.assertIn("RECOMMANDATIONS", rep.narrative)
        resp = c.get(reverse("download_report", args=[rep.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF"))


class AuditChainTests(TestCase):
    """La piste d'audit est infalsifiable (chaînage par hash)."""
    def setUp(self):
        sc = School.objects.create(name="École Audit")
        st = Student.objects.create(code="ST-AUD", age=16, grade_level="2A", school=sc)
        self.case = Case.objects.create(student=st, risk_score=20, risk_band="LOW", status="NEW")

    def test_chain_links_and_detects_tampering(self):
        e1 = CaseEvent.objects.create(case=self.case, action="A", result="OK", reason="un")
        e2 = CaseEvent.objects.create(case=self.case, action="B", result="OK", reason="deux")
        # chaînage : e2.prev_hash == e1.entry_hash
        self.assertEqual(e2.prev_hash, e1.entry_hash)
        self.assertTrue(e1.entry_hash and e2.entry_hash)
        # falsification : on modifie le contenu -> le hash recalculé ne correspond plus
        e1.reason = "FALSIFIE"
        self.assertNotEqual(e1.compute_hash(), e1.entry_hash)