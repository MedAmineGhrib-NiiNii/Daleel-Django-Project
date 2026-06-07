from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

class Command(BaseCommand):
    help = 'Crée 3 utilisateurs de test pour la soutenance (prof, conseiller, directeur)'

    def handle(self, *args, **kwargs):
        # Définition de tes 3 utilisateurs de démonstration
        users_data = [
            {'username': 'prof', 'password': 'amalpassword123', 'group': 'Teacher'},
            {'username': 'conseiller', 'password': 'amalpassword123', 'group': 'Counselor'},
            {'username': 'directeur', 'password': 'amalpassword123', 'group': 'Director'},
            {'username': 'eleve', 'password': 'amalpassword123', 'group': 'Student'},
        ]

        for data in users_data:
            # Création de l'utilisateur
            user, created = User.objects.get_or_create(username=data['username'])
            if created:
                user.set_password(data['password'])
                # On donne un accès au panel admin juste pour la démo
                user.is_staff = True 
                user.save()
            
            # Ajout au groupe de sécurité
            try:
                group = Group.objects.get(name=data['group'])
                user.groups.add(group)
                self.stdout.write(f"✅ Utilisateur '{data['username']}' lié au rôle {data['group']}.")
            except Group.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Erreur : Le rôle {data['group']} n'existe pas."))

            # L'élève de démo est relié à un dossier existant (pour la démo conseiller)
            if data['username'] == 'eleve':
                from app_governance.models import AccessRequest
                AccessRequest.objects.get_or_create(
                    user=user,
                    defaults={'full_name': 'Élève Démo', 'requested_role': 'Student',
                              'student_code': 'ST-2026-0001', 'biography': 'Compte de démonstration élève.',
                              'status': 'APPROVED'},
                )

        self.stdout.write(self.style.SUCCESS("Tous les comptes de test sont prêts pour la soutenance ! (Mot de passe: amalpassword123)"))