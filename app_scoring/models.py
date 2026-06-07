from django.db import models


class ScoringConfig(models.Model):
    """
    Seuils de risque configurables par le superviseur (Conseiller / Directeur).
    Singleton : une seule ligne (pk=1). Exigence Scénario 1 : seuil configurable par rôle.
    """
    medium_threshold = models.PositiveIntegerField(default=30, help_text="Score minimum pour la bande MEDIUM")
    high_threshold = models.PositiveIntegerField(default=60, help_text="Score minimum pour la bande HIGH")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuration du scoring"
        verbose_name_plural = "Configuration du scoring"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Seuils — MEDIUM >= {self.medium_threshold}, HIGH >= {self.high_threshold}"
