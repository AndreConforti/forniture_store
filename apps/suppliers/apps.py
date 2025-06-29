from django.apps import AppConfig


class SuppliersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.suppliers'
    verbose_name = 'Fornecedores' ## Nome do app que aparece no admin
