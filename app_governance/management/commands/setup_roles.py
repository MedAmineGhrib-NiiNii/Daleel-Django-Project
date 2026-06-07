from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from cases.models import Student, Case

class Command(BaseCommand):
    help = 'Initialise les 3 rôles de sécurité obligatoires (Teacher, Counselor, Director)'

    def handle(self, *args, **kwargs):
        self.stdout.write("Création des groupes de sécurité...")

        # 1. Le rôle TEACHER (Opérateur) : Peut juste voir les élèves et importer des CSV
        teacher_group, created = Group.objects.get_or_create(name='Teacher')
        
        # 2. Le rôle COUNSELOR (Superviseur) : Gère les dossiers et les rendez-vous
        counselor_group, created = Group.objects.get_or_create(name='Counselor')
        
        # 3. Le rôle DIRECTOR (Admin) : Vue globale, accès aux audits et exports
        director_group, created = Group.objects.get_or_create(name='Director')

        # 4. Le rôle STUDENT (Élève) : accès à l'espace élève uniquement
        student_group, created = Group.objects.get_or_create(name='Student')

        # --- Attribution de permissions d'exemple ---
        # On récupère le type de contenu (la table) pour Student et Case
        student_ct = ContentType.objects.get_for_model(Student)
        case_ct = ContentType.objects.get_for_model(Case)

        # On donne au Counselor le droit de modifier les dossiers (Cases)
        change_case_perm = Permission.objects.get(content_type=case_ct, codename='change_case')
        counselor_group.permissions.add(change_case_perm)

        # Le Directeur a le droit de tout voir
        view_student_perm = Permission.objects.get(content_type=student_ct, codename='view_student')
        director_group.permissions.add(view_student_perm)

        self.stdout.write(self.style.SUCCESS('Succès ! Les rôles Teacher, Counselor et Director ont été créés.'))