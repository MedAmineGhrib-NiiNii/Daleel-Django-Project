import logging

import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from cases.models import Student, School, Case
from app_scoring.services import compute_risk

logger = logging.getLogger(__name__)

# Seul student_code est obligatoire (schema). Les 3 indicateurs sont optionnels :
# une valeur manquante est traitée comme 0 mais REDUIT la fiabilité de la donnée.
REQUIRED_COLUMNS = ["student_code"]
INDICATOR_COLUMNS = ["absences_percentage", "grade_drop", "disciplinary_reports"]


def _read_indicator(row, df, col):
    """Retourne (valeur, present). present=False si colonne absente ou cellule vide."""
    if col not in df.columns or pd.isna(row.get(col)):
        return 0, False
    return row[col], True


@login_required(login_url="/login/")
def upload_csv(request):
    if request.method != "POST":
        return render(request, "app_intake/upload.html")

    # 1. Presence du fichier
    if "csv_file" not in request.FILES:
        messages.error(request, "Veuillez selectionner un fichier.")
        return redirect("upload_csv")

    csv_file = request.FILES["csv_file"]

    # 2. Extension
    if not csv_file.name.lower().endswith(".csv"):
        messages.error(request, "Erreur : le fichier doit etre au format CSV.")
        return redirect("upload_csv")

    # 3. Lecture
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        logger.warning("Echec lecture CSV : %s", e)
        messages.error(request, f"Fichier illisible : {e}")
        return redirect("upload_csv")

    # 4. Validation stricte du schema (cas d'echec controle)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        messages.error(request, f"Fichier invalide. Colonnes manquantes : {', '.join(missing)}")
        return redirect("upload_csv")

    # 5. Ingestion + scoring (Scenario 1, bout en bout)
    school, _ = School.objects.get_or_create(name="Lycee Pilote de Tunis", region="Tunis")
    created_count = 0
    cases_count = 0
    error_rows = 0

    for index, row in df.iterrows():
        try:
            # Lecture tolérante des 3 indicateurs + comptage de fiabilité
            abs_val, abs_ok = _read_indicator(row, df, "absences_percentage")
            gd_val, gd_ok = _read_indicator(row, df, "grade_drop")
            disc_val, disc_ok = _read_indicator(row, df, "disciplinary_reports")
            completeness = sum([abs_ok, gd_ok, disc_ok])

            absences = int(float(abs_val))
            grade_drop = float(gd_val)
            disciplinary = int(float(disc_val))

            student, created = Student.objects.update_or_create(
                code=str(row["student_code"]).strip(),
                defaults={
                    # Anonymisation à l'ingestion : on ne stocke PAS les noms,
                    # même s'ils figurent dans le CSV. Seul le code dossier est conservé.
                    "first_name": None,
                    "last_name": None,
                    "age": int(row["age"]) if "age" in df.columns and pd.notna(row.get("age")) else 16,
                    "grade_level": row.get("grade_level", "N/A"),
                    "governorate": row.get("governorate") if pd.notna(row.get("governorate")) else None,
                    "absences_percentage": absences,
                    "grade_drop": grade_drop,
                    "disciplinary_reports": disciplinary,
                    "school": school,
                },
            )

            # Calcul du risque -> creation / mise a jour du dossier
            score, band, explanation = compute_risk(absences, grade_drop, disciplinary)
            case_obj, _ = Case.objects.update_or_create(
                student=student,
                defaults={
                    "risk_score": score,
                    "risk_band": band,
                    "risk_explanation": explanation,
                    "data_completeness": completeness,
                    "status": "IN_REVIEW" if band == "HIGH" else "NEW",
                },
            )
            from cases.services import record_snapshot
            record_snapshot(case_obj)
            cases_count += 1
            if created:
                created_count += 1
        except (KeyError, ValueError, TypeError) as e:
            # Ligne malformee : on l'ignore mais on garde une trace (recuperation sure)
            error_rows += 1
            logger.warning("Ligne %s ignoree : %s", index, e)

    msg = f"Importation reussie : {created_count} nouveaux eleves, {cases_count} dossiers evalues."
    if error_rows:
        msg += f" {error_rows} ligne(s) ignoree(s) (donnees invalides)."
    messages.success(request, msg)
    return redirect("upload_csv") 