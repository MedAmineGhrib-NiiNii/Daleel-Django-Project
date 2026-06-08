from rest_framework import serializers
from cases.models import Case


class CaseSerializer(serializers.ModelSerializer):
    """Sérialiseur anonyme : expose le code dossier, jamais le nom de l'élève."""
    student_code = serializers.CharField(source="student.code", read_only=True)
    absences_percentage = serializers.IntegerField(source="student.absences_percentage", read_only=True)
    grade_drop = serializers.FloatField(source="student.grade_drop", read_only=True)
    disciplinary_reports = serializers.IntegerField(source="student.disciplinary_reports", read_only=True)

    class Meta:
        model = Case
        fields = [
            "id", "student_code", "risk_score", "risk_band", "status",
            "risk_explanation", "data_completeness",
            "absences_percentage", "grade_drop", "disciplinary_reports",
        ]
        read_only_fields = fields
