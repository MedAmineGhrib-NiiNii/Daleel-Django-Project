# -*- coding: utf-8 -*-
from django.shortcuts import redirect
from .i18n import LANGUAGES


def set_language(request):
    """Change la langue de l'interface (stockee en session) et revient a la page courante."""
    lang = request.GET.get("lang", "fr")
    if lang in dict(LANGUAGES):
        request.session["lang"] = lang
    return redirect(request.META.get("HTTP_REFERER") or "/")
