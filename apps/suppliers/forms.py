# apps/suppliers/forms.py
from django import forms
from .models import Supplier
from apps.addresses.models import Address

class SupplierForm(forms.ModelForm):
    """
    Formulário para criar e atualizar instâncias de `Supplier`.

    Gerencia dados do fornecedor e campos de endereço. A persistência do endereço
    é delegada ao método `save()` do modelo `Supplier`.
    """
    zip_code = forms.CharField(
        label="CEP", # Mantido em pt-BR para template
        max_length=9, 
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control cep-mask",
                "placeholder": "00000-000",
                "data-action": "cep-lookup",
            }
        ),
        help_text="Formato: 00000-000" # Mantido em pt-BR para template
    )
    street = forms.CharField(
        label="Logradouro", # Mantido em pt-BR para template
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    number = forms.CharField(
        label="Número", # Mantido em pt-BR para template
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    complement = forms.CharField(
        label="Complemento", # Mantido em pt-BR para template
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    neighborhood = forms.CharField(
        label="Bairro", # Mantido em pt-BR para template
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    city = forms.CharField(
        label="Cidade", # Mantido em pt-BR para template
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    state = forms.ChoiceField(
        label="UF", # Mantido em pt-BR para template
        required=False,
        choices=[("", "----")] + Address.BRAZILIAN_STATES_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Supplier
        fields = [
            'supplier_type', 'full_name', 'preferred_name', 'tax_id',
            'state_registration', 'municipal_registration',
            'phone', 'email', 'contact_person',
            'bank_name', 'bank_agency', 'bank_account', 'pix_key',
            'notes'
        ]
        widgets = {
            'supplier_type': forms.Select(attrs={
                'class': 'form-select supplier-type-select',
                'data-action': 'supplier-type-change'
            }),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'preferred_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control tax-id-mask',
                'placeholder': 'CPF ou CNPJ', 
                'data-action': 'document-input',
            }),
            'state_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'municipal_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={
                'class': 'form-control phone-mask',
                'placeholder': '(00) 00000-0000',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'exemplo@email.com'
            }),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_agency': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account': forms.TextInput(attrs={'class': 'form-control'}),
            'pix_key': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = { # Labels em pt-BR para template
            'tax_id': 'CPF/CNPJ',
            'full_name': 'Nome Completo / Razão Social',
            'preferred_name': 'Apelido / Nome Fantasia',
            'supplier_type': 'Tipo de Fornecedor',
        }
        help_texts = { # Help texts em pt-BR para template
            'tax_id': 'Somente números.',
            'pix_key': 'CPF/CNPJ, e-mail, telefone ou chave aleatória.',
        }


    def __init__(self, *args, **kwargs):
        """
        Inicializa o formulário, pré-preenchendo campos de endereço na edição
        e configurando atributos para melhor UX.
        """
        super().__init__(*args, **kwargs)

        if (self.instance and self.instance.pk and hasattr(self.instance, "address") and self.instance.address):
            supplier_address = self.instance.address # Variável local em inglês
            self.fields["zip_code"].initial = supplier_address.zip_code
            self.fields["street"].initial = supplier_address.street
            self.fields["number"].initial = supplier_address.number
            self.fields["complement"].initial = supplier_address.complement
            self.fields["neighborhood"].initial = supplier_address.neighborhood
            self.fields["city"].initial = supplier_address.city
            self.fields["state"].initial = supplier_address.state
        
        if "tax_id" in self.fields:
            self.fields["tax_id"].widget.attrs.update(
                {"pattern": r"[\d.\-/]*", "inputmode": "text"}
            )

        address_field_names = [
            "zip_code", "street", "number", "complement",
            "neighborhood", "city", "state",
        ]
        for field_name in address_field_names:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs["autocomplete"] = "off"

    def clean_tax_id(self):
        """Limpa o campo CPF/CNPJ, removendo não-dígitos."""
        tax_id_value = self.cleaned_data.get("tax_id")
        if not tax_id_value:
             raise forms.ValidationError("O CPF/CNPJ é obrigatório.")
        
        cleaned_tax_id = "".join(filter(str.isdigit, tax_id_value))
        return cleaned_tax_id


    def clean_phone(self):
        """Limpa o campo telefone, removendo não-dígitos."""
        phone_value = self.cleaned_data.get("phone") # Variável local em inglês
        if phone_value:
            return "".join(filter(str.isdigit, phone_value))
        return phone_value

    def clean_zip_code(self):
        """Limpa o CEP e valida seu formato (8 dígitos)."""
        zip_code_value = self.cleaned_data.get("zip_code") # Variável local em inglês
        if zip_code_value:
            cleaned_zip = "".join(filter(str.isdigit, zip_code_value))
            if cleaned_zip and len(cleaned_zip) != 8:
                raise forms.ValidationError("CEP deve conter 8 números.")
            return cleaned_zip if cleaned_zip else None
        return None

    def clean(self):
        """Validações cruzadas: `supplier_type` e `preferred_name` (para PJ)."""
        cleaned_data = super().clean()
        supplier_type_value = cleaned_data.get("supplier_type") # Variável local em inglês
        tax_id_value = cleaned_data.get("tax_id") # Variável local em inglês

        if tax_id_value and not supplier_type_value:
            self.add_error(
                "supplier_type", "Selecione o tipo de fornecedor para validar o CNPJ/CPF."
            )
        
        if supplier_type_value == "CORP" and not cleaned_data.get('preferred_name'):
            self.add_error('preferred_name', "Nome Fantasia é obrigatório para Pessoa Jurídica.")
                
        return cleaned_data

    def save(self, commit=True):
        """
        Salva a instância do fornecedor e gerencia o endereço.
        """
        instance = super().save(commit=False)

        address_data = {
            "zip_code": self.cleaned_data.get("zip_code"),
            "street": self.cleaned_data.get("street", "").strip(),
            "number": self.cleaned_data.get("number", "").strip(),
            "complement": self.cleaned_data.get("complement", "").strip(),
            "neighborhood": self.cleaned_data.get("neighborhood", "").strip(),
            "city": self.cleaned_data.get("city", "").strip(),
            "state": self.cleaned_data.get("state", "").strip().upper(),
        }

        is_any_address_data_present = any(
            value for value in address_data.values() if value not in [None, ""]
        )
        
        address_data_to_pass_to_model = address_data if is_any_address_data_present else {} # Variável local em inglês

        if commit:
            instance.save(address_data=address_data_to_pass_to_model)
        
        return instance