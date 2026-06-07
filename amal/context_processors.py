# -*- coding: utf-8 -*-
from .i18n import get_translation, RTL_LANGUAGES, LANGUAGES


def i18n(request):
    lang = request.session.get("lang", "fr")
    if lang not in dict(LANGUAGES):
        lang = "fr"
    u = getattr(request, "user", None)
    def in_group(name):
        return bool(u and u.is_authenticated and u.groups.filter(name=name).exists())
    is_student = in_group("Student")
    is_director = bool(u and (u.is_superuser or in_group("Director")))
    is_counselor = in_group("Counselor")
    is_teacher = in_group("Teacher")
    return {
        "t": get_translation(lang),
        "LANG": lang,
        "RTL": lang in RTL_LANGUAGES,
        "LANGUAGES": LANGUAGES,
        "IS_STUDENT": is_student,
        "IS_DIRECTOR": is_director,
        "IS_COUNSELOR": is_counselor,
        "IS_TEACHER": is_teacher,
        "CAN_MANAGE_RESOURCES": bool(u and (getattr(u,"is_superuser",False) or is_teacher or is_director)),
        "IS_STAFF_DASH": bool(u and u.is_authenticated and not is_student),
    }