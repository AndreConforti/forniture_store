from django.apps import AppConfig


class AddressesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.addresses"
    verbose_name = "Endereços"  ## Nome do app que aparece no admin
