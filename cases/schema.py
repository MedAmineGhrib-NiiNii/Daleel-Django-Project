import graphene
from graphene_django import DjangoObjectType
from cases.models import Case


def _is_staff(user):
    return bool(user and user.is_authenticated and (
        user.is_superuser or
        user.groups.filter(name__in=["Counselor", "Director"]).exists()))


class CaseType(DjangoObjectType):
    """Type GraphQL anonyme : expose le code dossier, jamais le nom de l'élève."""
    student_code = graphene.String()
    absences_percentage = graphene.Int()
    grade_drop = graphene.Float()
    disciplinary_reports = graphene.Int()

    class Meta:
        model = Case
        fields = ("id", "risk_score", "risk_band", "status",
                  "risk_explanation", "data_completeness")

    def resolve_student_code(self, info):
        return self.student.code

    def resolve_absences_percentage(self, info):
        return self.student.absences_percentage

    def resolve_grade_drop(self, info):
        return self.student.grade_drop

    def resolve_disciplinary_reports(self, info):
        return self.student.disciplinary_reports


class Query(graphene.ObjectType):
    cases = graphene.List(CaseType, risk_band=graphene.String(),
                          description="Liste anonyme des dossiers (staff uniquement).")

    def resolve_cases(self, info, risk_band=None):
        if not _is_staff(info.context.user):
            return Case.objects.none()
        qs = Case.objects.select_related("student").order_by("-risk_score")
        if risk_band:
            qs = qs.filter(risk_band=risk_band)
        return qs


schema = graphene.Schema(query=Query)