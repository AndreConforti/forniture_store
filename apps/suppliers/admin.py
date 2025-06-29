# apps/suppliers/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Supplier

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'formatted_tax_id',
        'supplier_type_display',
        'contact_person',
        'formatted_phone',
        'email_link',
        'is_active', # Editável na lista
        'address_short_display'
    )
    
    list_filter = ('supplier_type', 'is_active', 'registration_date')
    search_fields = ('full_name', 'preferred_name', 'tax_id', 'email', 'phone', 'contact_person')
    list_per_page = 20
    list_editable = ('is_active',)

    readonly_fields = (
        'supplier_type_display',
        'full_name',
        'preferred_name',
        'formatted_tax_id',
        # 'state_registration', # Permitir edição se necessário
        # 'municipal_registration', # Permitir edição se necessário
        'formatted_phone',
        'email_link',
        # 'contact_person', # Permitir edição
        'bank_info_display', # Usar display para dados bancários no form
        'pix_key_display',   # Usar display para pix no form
        'registration_date',
        'updated_at',
        'notes_display', # Usar display para notas no form
        'address_display'
    )

    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'supplier_type_display', 
                'full_name',
                'preferred_name',
                'formatted_tax_id',
                'registration_date',
                'updated_at'
            )
        }),
        ('Dados Fiscais (PJ)', {
            'fields': (
                'state_registration', # Campo editável
                'municipal_registration', # Campo editável
            ),
            'classes': ('collapse',),
            'description': 'Visível e aplicável apenas para Pessoa Jurídica.'
        }),
        ('Contato', {
            'fields': (
                'contact_person', # Campo editável
                'phone', 
                'formatted_phone',
                'email', 
                'email_link'
            )
        }),
        ('Dados Bancários', {
            'fields': (
                'bank_name', 'bank_agency', 'bank_account', 'pix_key', # Campos editáveis
            ),
            'classes': ('collapse',)
        }),
        ('Outras Informações', {
            'fields': (
                'notes', # Campo editável
                'address_display'
            )
        }),
    )

    def supplier_type_display(self, obj):
        return obj.get_supplier_type_display()
    supplier_type_display.short_description = 'Tipo de Fornecedor'

    def email_link(self, obj):
        if obj.email:
            return format_html('<a href="mailto:{}">{}</a>', obj.email, obj.email)
        return "-"
    email_link.short_description = 'E-mail (Link)'
    email_link.admin_order_field = 'email'

    def bank_info_display(self, obj):
        if obj.bank_name or obj.bank_agency or obj.bank_account:
            return format_html(
                "Banco: {}<br>Agência: {}<br>Conta: {}",
                obj.bank_name or '--', obj.bank_agency or '--', obj.bank_account or '--'
            )
        return "Nenhuma informação bancária."
    bank_info_display.short_description = "Info Bancária (Resumo)"

    def pix_key_display(self, obj):
        return obj.pix_key or "Nenhuma chave PIX."
    pix_key_display.short_description = "Chave PIX (Resumo)"

    def notes_display(self, obj):
        return format_html("<div style='white-space: pre-wrap;'>{}</div>", obj.notes) if obj.notes else "Nenhuma observação."
    notes_display.short_description = "Observações (Resumo)"

    def address_display(self, obj):
        address = obj.address
        if address:
            return format_html(
                """
                <div style="margin: 5px 0; padding: 8px; background: #f8f9fa; border-radius: 4px; font-size: 0.9em;">
                    <strong>Endereço:</strong><br>
                    {street}{number_comp}<br>
                    {neighborhood}<br>
                    {city} / {state}<br>
                    CEP: {zip_code}
                </div>
                """,
                street=address.street or "--",
                number_comp=f", {address.number}" if address.number else " S/N" + (f" - {address.complement}" if address.complement else ""),
                neighborhood=address.neighborhood or "--",
                city=address.city or "--",
                state=address.state or "--",
                zip_code=address.formatted_zip_code or "--",
            )
        return "Nenhum endereço cadastrado"
    address_display.short_description = "Endereço Completo"

    def address_short_display(self, obj):
        address = obj.address
        if address:
            parts = []
            if address.street: parts.append(address.street)
            if address.city: parts.append(address.city)
            if address.state: parts.append(address.state)
            return ", ".join(filter(None, parts)) or "-"
        return "-"
    address_short_display.short_description = "Localização"
    
    def has_add_permission(self, request):
        return False # Mantém desabilitada a criação

    def has_change_permission(self, request, obj=None):
        # Permite alteração na changelist e no formulário individual (controlado por readonly_fields)
        return True 

    def has_delete_permission(self, request, obj=None):
        return True # Habilita a exclusão

    def get_readonly_fields(self, request, obj=None):
        if obj: # Formulário de alteração
            # Define quais campos devem permanecer readonly mesmo no formulário de edição
            # Os demais (não listados aqui) serão editáveis
            ro_fields = [
                'supplier_type_display', 'formatted_tax_id', 'formatted_phone',
                'email_link', 'registration_date', 'updated_at',
                'bank_info_display', 'pix_key_display', 'notes_display',
                'address_display'
            ]
            # Adiciona os campos que não estão no fieldsets mas queremos readonly (como full_name)
            # Se um campo está no fieldsets e não está aqui, será editável.
            # Se um campo está em self.readonly_fields da classe, ele já será readonly.
            # Este método permite refinar isso.

            # Campos que queremos que sejam editáveis no form:
            editable_fields_in_form = [
                'full_name', 'preferred_name', 'state_registration',
                'municipal_registration', 'phone', 'email', 'contact_person',
                'bank_name', 'bank_agency', 'bank_account', 'pix_key', 'notes'
            ]
            
            # Começa com todos os campos do modelo
            all_model_fields = [f.name for f in self.model._meta.fields + self.model._meta.many_to_many]
            # Remove os que devem ser editáveis
            current_readonly = [f for f in all_model_fields if f not in editable_fields_in_form]
            
            # Adiciona os campos de display formatado que são sempre readonly
            current_readonly.extend([
                'supplier_type_display', 'formatted_tax_id', 'formatted_phone',
                'email_link', 'bank_info_display', 'pix_key_display',
                'notes_display', 'address_display'
            ])
            # Garante que campos de data de sistema sejam readonly
            current_readonly.extend(['registration_date', 'updated_at'])
            # Remove duplicatas
            current_readonly = list(set(current_readonly))
            
            # Remove 'is_active' pois é controlado pelo list_editable
            if 'is_active' in current_readonly:
                current_readonly.remove('is_active')

            return current_readonly
        return super().get_readonly_fields(request, obj)