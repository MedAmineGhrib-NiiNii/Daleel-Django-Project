from django.contrib import admin
from django.urls import path, include
# --- NOUVEAU : On importe le système d'authentification de Django ---
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('set-language/', core_views.set_language, name='set_language'),
    
    # --- NOUVELLES ROUTES DE CONNEXION ---
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # --- Tes applications existantes ---
    path('dashboard/', include('dashboard.urls')),
    path('intake/', include('app_intake.urls')), 
    path('cases/', include('cases.urls')),
    path('', include('app_governance.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
