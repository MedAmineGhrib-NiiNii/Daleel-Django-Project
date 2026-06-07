from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from app_governance.models import AccessRequest, SelfAssessment


class RegistrationApprovalTests(TestCase):
    def setUp(self):
        for n in ["Teacher", "Counselor", "Director", "Student"]:
            Group.objects.get_or_create(name=n)
        d = User.objects.create_user(username="dir", password="pwd12345")
        d.groups.add(Group.objects.get(name="Director"))

    def test_registration_creates_inactive_user_and_pending_request(self):
        Client().post(reverse("register"), {
            "full_name": "Jean Test", "role": "Teacher", "username": "jean",
            "password": "pwd12345678", "biography": "Enseignant de sciences au lycee pilote.",
        })
        u = User.objects.get(username="jean")
        self.assertFalse(u.is_active)
        self.assertEqual(u.access_request.status, "PENDING")

    def test_pending_user_cannot_login(self):
        Client().post(reverse("register"), {
            "full_name": "Jean Test", "role": "Teacher", "username": "jean2",
            "password": "pwd12345678", "biography": "Enseignant de sciences au lycee pilote.",
        })
        self.assertFalse(Client().login(username="jean2", password="pwd12345678"))

    def test_director_approval_activates_and_assigns_role(self):
        Client().post(reverse("register"), {
            "full_name": "Jean Test", "role": "Counselor", "username": "jean3",
            "password": "pwd12345678", "biography": "Conseiller d'orientation experimente.",
        })
        req = User.objects.get(username="jean3").access_request
        d = Client(); d.login(username="dir", password="pwd12345")
        d.get(reverse("review_request", args=[req.id, "approve"]))
        u = User.objects.get(username="jean3")
        self.assertTrue(u.is_active)
        self.assertTrue(u.groups.filter(name="Counselor").exists())
        self.assertTrue(Client().login(username="jean3", password="pwd12345678"))

    def test_non_director_cannot_review(self):
        t = User.objects.create_user(username="t", password="pwd12345")
        t.groups.add(Group.objects.get(name="Teacher"))
        Client().post(reverse("register"), {
            "full_name": "X", "role": "Teacher", "username": "jean4",
            "password": "pwd12345678", "biography": "Une presentation suffisamment longue ici.",
        })
        req = User.objects.get(username="jean4").access_request
        c = Client(); c.login(username="t", password="pwd12345")
        self.assertEqual(c.get(reverse("review_request", args=[req.id, "approve"])).status_code, 403)


class StudentSpaceTests(TestCase):
    def setUp(self):
        for n in ["Student", "Counselor"]:
            Group.objects.get_or_create(name=n)
        self.s = User.objects.create_user(username="el", password="pwd12345")
        self.s.groups.add(Group.objects.get(name="Student"))

    def test_self_assessment_saved(self):
        c = Client(); c.login(username="el", password="pwd12345")
        c.post(reverse("self_assessment"), {"q1": "4", "q2": "4", "q3": "3", "q4": "4", "q5": "4"})
        sa = SelfAssessment.objects.get(student_user=self.s)
        self.assertGreaterEqual(sa.score, 60)
        self.assertEqual(sa.band, "OK")

    def test_student_blocked_from_staff_dashboard(self):
        c = Client(); c.login(username="el", password="pwd12345")
        self.assertEqual(c.get("/dashboard/").status_code, 403)


class ResourceManagementTests(TestCase):
    """Prof et Directeur ajoutent/suppriment des ressources ; l'élève non."""
    def setUp(self):
        for n in ["Teacher", "Director", "Student"]:
            Group.objects.get_or_create(name=n)
        for u, g in [("p_res", "Teacher"), ("e_res", "Student")]:
            x = User.objects.create_user(username=u, password="pwd12345")
            x.groups.add(Group.objects.get(name=g))

    def test_teacher_can_add_resource(self):
        from app_governance.models import Resource
        c = Client(); c.login(username="p_res", password="pwd12345")
        c.post("/ressources/ajouter/", {"resource_type": "BOOK", "title": "T", "subject": "Maths"})
        self.assertTrue(Resource.objects.filter(title="T").exists())

    def test_student_cannot_add_resource(self):
        from app_governance.models import Resource
        c = Client(); c.login(username="e_res", password="pwd12345")
        r = c.post("/ressources/ajouter/", {"resource_type": "BOOK", "title": "X", "subject": "Y"})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Resource.objects.filter(title="X").exists())


class MessagingTests(TestCase):
    """L'élève initie toujours ; le prof ne peut que répondre."""
    def setUp(self):
        for n in ["Teacher", "Student"]:
            Group.objects.get_or_create(name=n)
        self.teacher = User.objects.create_user(username="t_msg", password="pwd12345")
        self.teacher.groups.add(Group.objects.get(name="Teacher"))
        from app_governance.models import TeacherProfile
        TeacherProfile.objects.create(user=self.teacher, subjects="Maths", is_visible=True)
        self.student = User.objects.create_user(username="s_msg", password="pwd12345")
        self.student.groups.add(Group.objects.get(name="Student"))

    def test_student_initiates_and_teacher_replies(self):
        from app_governance.models import Conversation, Message
        c = Client(); c.login(username="s_msg", password="pwd12345")
        c.post("/messages/prof/t_msg/", {"body": "Bonjour"})
        conv = Conversation.objects.get(student=self.student, teacher=self.teacher)
        self.assertEqual(conv.messages.count(), 1)
        t = Client(); t.login(username="t_msg", password="pwd12345")
        t.post(f"/messages/{conv.id}/", {"body": "Salut"})
        self.assertEqual(conv.messages.count(), 2)

    def test_teacher_cannot_initiate(self):
        t = Client(); t.login(username="t_msg", password="pwd12345")
        r = t.get("/messages/prof/t_msg/")
        self.assertEqual(r.status_code, 403)

    def test_invisible_teacher_absent_from_list(self):
        self.teacher.teacher_profile.is_visible = False
        self.teacher.teacher_profile.save()
        c = Client(); c.login(username="s_msg", password="pwd12345")
        html = c.get("/eleve/profs/").content.decode()
        self.assertNotIn("Maths", html)


class CounselorMessagingTests(TestCase):
    """Élève↔conseiller : les deux peuvent initier."""
    def setUp(self):
        for n in ["Counselor", "Student"]:
            Group.objects.get_or_create(name=n)
        self.counselor = User.objects.create_user(username="c_cons", password="pwd12345")
        self.counselor.groups.add(Group.objects.get(name="Counselor"))
        self.student = User.objects.create_user(username="s_cons", password="pwd12345")
        self.student.groups.add(Group.objects.get(name="Student"))

    def test_student_can_contact_counselor(self):
        from app_governance.models import Conversation
        c = Client(); c.login(username="s_cons", password="pwd12345")
        c.post("/messages/conseiller/c_cons/", {"body": "Bonjour"})
        conv = Conversation.objects.get(student=self.student, teacher=self.counselor)
        self.assertEqual(conv.kind, "COUNSELOR")
        self.assertEqual(conv.messages.count(), 1)

    def test_counselor_can_initiate_with_student(self):
        from app_governance.models import Conversation
        c = Client(); c.login(username="c_cons", password="pwd12345")
        r = c.get(f"/messages/eleve/{self.student.id}/")
        self.assertEqual(r.status_code, 302)  # redirige vers le fil (autorisé)
        self.assertTrue(Conversation.objects.filter(student=self.student, teacher=self.counselor).exists())