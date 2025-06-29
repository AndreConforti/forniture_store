from django.apps import AppConfig


class CustomersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.docs"
    verbose_name = "Documentos"  # Nome do app que aparece no admin
