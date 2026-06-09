from django.urls import path
from . import views

urlpatterns = [
    # Inscription publique
    path('register/', views.register, name='register'),

    # Gouvernance (Directeur)
    path('access-requests/', views.access_requests, name='access_requests'),
    path('access-requests/<int:req_id>/<str:decision>/', views.review_request, name='review_request'),
    path('assessments/', views.assessments_inbox, name='assessments_inbox'),

    # Espace élève
    path('eleve/', views.student_home, name='student_home'),
    path('eleve/auto-evaluation/', views.self_assessment, name='self_assessment'),
    path('eleve/ressources/', views.resources, name='resources'),
    path('ressources/ajouter/', views.add_resource, name='add_resource'),
    path('ressources/<int:resource_id>/supprimer/', views.delete_resource, name='delete_resource'),
    path('eleve/profs/', views.teachers_list, name='teachers_list'),
    path('eleve/quiz/', views.quiz, name='quiz'),
    path('prof/profil/', views.teacher_profile_edit, name='teacher_profile_edit'),
    path('eleve/conseillers/', views.counselors_list, name='counselors_list'),
    path('messages/conseiller/<str:counselor_username>/', views.contact_counselor, name='contact_counselor'),
    path('messages/eleve/<int:student_id>/', views.counselor_contact_student, name='counselor_contact_student'),
    path('messages/', views.my_messages, name='my_messages'),
    path('messages/prof/<str:teacher_username>/', views.contact_teacher, name='contact_teacher'),
    path('messages/<int:conv_id>/', views.conversation_thread, name='conversation_thread'),
    path('eleve/assistant/', views.study_chat_page, name='study_chat'),
    path('eleve/assistant/api/', views.study_chat_api, name='study_chat_api'),
]