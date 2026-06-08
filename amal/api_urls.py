from django.urls import path
from cases.api import CaseListAPI, CaseDetailAPI

# API REST (DRF) — lecture seule, anonyme, réservée au personnel autorisé.
urlpatterns = [
    path('cases/', CaseListAPI.as_view(), name='api_cases'),
    path('cases/<int:pk>/', CaseDetailAPI.as_view(), name='api_case_detail'),
]
