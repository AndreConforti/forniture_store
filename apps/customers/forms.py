from django import forms
from .models import Customer
from apps.addresses.models import Address


class CustomerForm(forms.ModelForm):
    """
    Formulário para criar e atualizar instâncias de `Customer`.

    Gerencia dados do cliente e campos de endereço. A persistência do endereço
    é delegada ao método `save()` do modelo `Customer`.
    Campos de endereço são explícitos para personalização.
    """

    zip_code = forms.CharField(
        label="CEP",
        max_length=9,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control cep-mask",
                "placeholder": "00000-000",
                "data-action": "cep-lookup",
            }
        ),
    )
    street = forms.CharField(
        label="Logradouro",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    number = forms.CharField(
        label="Número",
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    complement = forms.CharField(
        label="Complemento",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    neighborhood = forms.CharField(
        label="Bairro",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    city = forms.CharField(
        label="Cidade",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    state = forms.ChoiceField(
        label="UF",
        required=False,
        choices=[("", "----")] + Address.BRAZILIAN_STATES_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Customer
        fields = [
            "customer_type", "full_name", "preferred_name", "tax_id",
            "phone", "email", "is_vip", "profession", "interests", "notes",
        ]
        widgets = {
            "customer_type": forms.Select(
                attrs={"class": "form-select", "data-action": "customer-type-change"}
            ),
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "preferred_name": forms.TextInput(attrs={"class": "form-control"}),
            "tax_id": forms.TextInput(
                attrs={
                    "class": "form-control tax-id-mask",
                    "placeholder": "CPF ou CNPJ",
                    "data-action": "document-input",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control phone-mask",
                    "placeholder": "(00) 00000-0000",
                }
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "exemplo@email.com"}
            ),
            "is_vip": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "profession": forms.TextInput(attrs={"class": "form-control"}),
            "interests": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = { 
            "tax_id": "CPF/CNPJ",
            "full_name": "Nome Completo / Razão Social",
            "customer_type": "Tipo de Cliente",
            "is_vip": "Cliente VIP",
            "preferred_name": "Apelido / Nome Fantasia",
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa o formulário, pré-preenchendo campos de endereço na edição
        e configurando atributos para UX.
        """
        super().__init__(*args, **kwargs)

        if (
            self.instance
            and self.instance.pk
            and hasattr(self.instance, "address")
            and self.instance.address
        ):
            customer_address = self.instance.address
            self.fields["zip_code"].initial = customer_address.zip_code
            self.fields["street"].initial = customer_address.street
            self.fields["number"].initial = customer_address.number
            self.fields["complement"].initial = customer_address.complement
            self.fields["neighborhood"].initial = customer_address.neighborhood
            self.fields["city"].initial = customer_address.city
            self.fields["state"].initial = customer_address.state

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
        phone_value = self.cleaned_data.get("phone")
        if phone_value:
            return "".join(filter(str.isdigit, phone_value))
        return phone_value

    def clean_zip_code(self):
        """Limpa o CEP e valida seu formato (8 dígitos)."""
        zip_code_value = self.cleaned_data.get("zip_code")
        if zip_code_value:
            cleaned_zip = "".join(filter(str.isdigit, zip_code_value))
            if cleaned_zip and len(cleaned_zip) != 8:
                raise forms.ValidationError("CEP deve conter 8 números.")
            return cleaned_zip if cleaned_zip else None
        return None

    def clean(self):
        """Validações cruzadas: `customer_type` é obrigatório se `tax_id` for fornecido."""
        cleaned_data = super().clean()
        customer_type_value = cleaned_data.get("customer_type")
        tax_id_value = cleaned_data.get("tax_id")

        if tax_id_value and not customer_type_value:
            self.add_error(
                "customer_type", "Selecione o tipo de cliente para validar o CPF/CNPJ."
            )
        return cleaned_data

    def save(self, commit=True):
        """
        Salva a instância do cliente e gerencia o endereço.

        Coleta dados de endereço do formulário e passa para `instance.save()`.
        O modelo `Customer` lida com a criação/atualização/exclusão do `Address`.
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

        address_data_to_pass_to_model = address_data if is_any_address_data_present else {}

        if commit:
            instance.save(address_data=address_data_to_pass_to_model)

        return instance