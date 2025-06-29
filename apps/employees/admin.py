from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.contenttypes.admin import GenericStackedInline
from django import forms
from .models import Employee
from apps.addresses.models import Address

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = '__all__'
        help_texts = {
            'zip_code': 'Digite 8 dígitos para autocompletar',
            'number': 'Obrigatório para cadastro completo'
        }

class AddressInline(GenericStackedInline):
    model = Address
    form = AddressForm
    extra = 0 
    max_num = 1 
    can_delete = False
    verbose_name = 'Endereço'
    
    fields = (
        'zip_code', 'number', 'street', 
        'complement', 'neighborhood', 
        'city', 'state'
    )

    def get_extra(self, request, obj=None, **kwargs):
        """Mostra 1 form se não existir endereço, 0 caso contrário"""
        return 0 if obj and obj.addresses.exists() else 1

class EmployeeAdmin(UserAdmin):
    inlines = [AddressInline]
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informações Pessoais', {'fields': ('first_name', 'last_name', 'email', 'phone', 'birth_date')}),
        ('Informações Profissionais', {'fields': ('position', 'hire_date')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    def save_model(self, request, obj, form, change):
        """Garante que o address seja validado junto com o employee"""
        super().save_model(request, obj, form, change)
        if obj.addresses.exists():
            obj.addresses.first().full_clean()

admin.site.register(Employee, EmployeeAdmin)