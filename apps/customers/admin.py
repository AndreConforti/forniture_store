from django.contrib import admin
from django.utils.html import format_html
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True

    list_display = (
        "full_name",
        "formatted_tax_id",
        "customer_type_display",
        "formatted_phone",
        "email_link",
        "is_active",
        "is_vip_display",
    )

    list_filter = ("customer_type", "is_active", "is_vip", "registration_date")
    search_fields = ("full_name", "preferred_name", "tax_id", "email", "phone")
    list_per_page = 20
    list_editable = ("is_active",)

    readonly_fields = (
        "customer_type_display",
        "full_name",
        "preferred_name",
        "formatted_tax_id",
        "phone",
        "formatted_phone",
        "email",
        "email_link",
        "is_active_display",
        "is_vip_display",
        "profession",
        "interests",
        "notes",
        "registration_date",
        "address_display",
    )

    fieldsets = (
        (
            "Informações Básicas",
            {
                "fields": (
                    "customer_type_display",
                    "full_name",
                    "preferred_name",
                    "formatted_tax_id",
                    "registration_date",
                )
            },
        ),
        ("Contato", {"fields": ("phone", "formatted_phone", "email_link")}),
        ("Status", {"fields": ("is_active_display", "is_vip_display")}),
        (
            "Informações Adicionais",
            {"fields": ("profession", "interests", "notes", "address_display")},
        ),
    )

    # Métodos customizados para exibição
    def customer_type_display(self, obj):
        return dict(Customer.CUSTOMER_TYPE_CHOICES).get(
            obj.customer_type, obj.customer_type
        )

    customer_type_display.short_description = "Tipo de Cliente"

    def formatted_tax_id(self, obj):
        return obj.formatted_tax_id

    formatted_tax_id.short_description = "CPF/CNPJ"

    def formatted_phone(self, obj):
        return obj.formatted_phone

    formatted_phone.short_description = "Telefone Formatado"

    def email_link(self, obj):
        if obj.email:
            return format_html('<a href="mailto:{}">{}</a>', obj.email, obj.email)
        return "-"

    email_link.short_description = "E-mail"
    email_link.admin_order_field = "email"

    def is_active_display(self, obj):
        return "✅ Ativo" if obj.is_active else "❌ Inativo"

    is_active_display.short_description = "Status (Detalhe)"

    def is_vip_display(self, obj):
        return "⭐ VIP" if obj.is_vip else "➖ Regular"

    is_vip_display.short_description = "Tipo"

    def address_display(self, obj):
        address = obj.addresses.first()
        if address:
            return format_html(
                """
                <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    <strong>Endereço:</strong><br>
                    {street}, {number}{complement}<br>
                    {neighborhood}<br>
                    {city}/{state}<br>
                    CEP: {zip_code}
                </div>
                """,
                street=address.street or "--",
                number=address.number or "--",
                complement=", " + address.complement if address.complement else "",
                neighborhood=address.neighborhood or "--",
                city=address.city or "--",
                state=address.state or "--",
                zip_code=address.zip_code or "--",
            )
        return "Nenhum endereço cadastrado"

    address_display.short_description = "Endereço Completo"

    def changelist_view(self, request, extra_context=None):
        self.has_change_permission = lambda r, o=None: True
        response = super().changelist_view(request, extra_context=extra_context)
        self.has_change_permission = lambda r, o=None: False
        return response
