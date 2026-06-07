from django.urls import path
from . import views

urlpatterns = [
    # Ton URL existante :
    path('api/close/<int:case_id>/', views.close_case_api, name='api_close_case'),
    
    # NOUVELLES URLs :
    path('api/open/<int:case_id>/', views.open_case_api, name='api_open_case'),
    path('api/schedule/<int:case_id>/', views.schedule_intervention_api, name='api_schedule_intervention'),
    path('api/appointment/<int:appointment_id>/<str:new_status>/', views.update_appointment_api, name='api_update_appointment'),
    path('api/ai-decision/<int:case_id>/<str:decision>/', views.ai_plan_decision, name='api_ai_decision'),
]