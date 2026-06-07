from django.urls import path
# 1. NOUVEAU : On a ajouté "dashboard_router" à la toute fin de cette ligne
from .views import dashboard_home, case_detail, generate_ai_plan, export_cases_csv, dashboard_router, case_list, scoring_config, risk_simulator, simulate_api, model_evaluation, generate_report, report_history, download_report, view_report, metrics_dashboard

urlpatterns = [
    # 2. NOUVEAU : Le chemin caché de notre routeur (qui trie les rôles)
    path('routeur/', dashboard_router, name='dashboard_router'),
    
    # 3. Tes routes classiques
    path('', dashboard_home, name='dashboard_home'),
    path("cases/", case_list, name="case_list"),
    path("config/", scoring_config, name="scoring_config"),
    path("simulator/", risk_simulator, name="risk_simulator"),
    path("evaluation/", model_evaluation, name="model_evaluation"),
    path("metrics/", metrics_dashboard, name="metrics_dashboard"),
    path("reports/", report_history, name="report_history"),
    path("case/<int:case_id>/report/", generate_report, name="generate_report"),
    path("report/<int:report_id>/", view_report, name="view_report"),
    path("report/<int:report_id>/download/", download_report, name="download_report"),
    path("api/simulate/", simulate_api, name="simulate_api"),
    path('case/<int:case_id>/', case_detail, name='case_detail'),
    path('case/<int:case_id>/ai-plan/', generate_ai_plan, name='generate_ai_plan'), 
    path('export/csv/', export_cases_csv, name='export_cases_csv'),
]