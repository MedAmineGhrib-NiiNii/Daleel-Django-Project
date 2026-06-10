from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from cases.models import Case
from cases.serializers import CaseSerializer


class IsStaffMember(permissions.BasePermission):
    """Accès API réservé au conseiller et au directeur."""
    message = "Accès réservé au conseiller et au directeur."

    def has_permission(self, request, view):
        u = request.user
        return bool(
            u and u.is_authenticated and (
                u.is_superuser or
                u.groups.filter(name__in=["Counselor", "Director"]).exists()
            )
        )


class CaseListAPI(generics.ListAPIView):
    """GET /api/cases/ — liste anonyme des dossiers, filtrable par niveau de risque.
    Exemple : /api/cases/?risk_band=HIGH"""
    serializer_class = CaseSerializer
    permission_classes = [IsStaffMember]

    def get_queryset(self):
        qs = Case.objects.select_related("student").order_by("-risk_score")
        band = self.request.query_params.get("risk_band")
        if band:
            if band not in {"LOW", "MEDIUM", "HIGH"}:
                raise PermissionDenied("Niveau de risque invalide (LOW, MEDIUM ou HIGH).")
            qs = qs.filter(risk_band=band)
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        gov = self.request.query_params.get("governorate")
        if gov:
            qs = qs.filter(student__governorate=gov)
        return qs


class CaseDetailAPI(generics.RetrieveAPIView):
    """GET /api/cases/<id>/ — détail anonyme d'un dossier."""
    serializer_class = CaseSerializer
    permission_classes = [IsStaffMember]
    queryset = Case.objects.select_related("student").all()