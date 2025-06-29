from django import forms
from apps.customers.models import Customer
from apps.suppliers.models import Supplier
from apps.addresses.models import Address


BOOLEAN_CHOICES_WITH_ALL = (
    ('', 'Todos'),
    ('True', 'Sim'),
    ('False', 'Não'),
)


class BaseReportForm(forms.Form):
    output_format = forms.ChoiceField(
        label="Formato de Saída",
        choices=[
            ('excel', 'Excel (.xlsx)'),
            ('csv', 'CSV (.csv)'),
            ('json', 'JSON (.json)'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='excel' # Definir um valor inicial pode ser útil
    )

    def get_queryset(self):
        """
        Este método DEVE ser implementado pelas subclasses.
        Ele é responsável por retornar o queryset filtrado com base
        nos campos do formulário específico.
        """
        raise NotImplementedError("Subclasses devem implementar get_queryset() para retornar os dados filtrados.")

    def get_applied_filters_display(self):
        """
        Retorna uma lista de strings descrevendo os filtros aplicados,
        para ser usada no cabeçalho do relatório (Excel, etc.).
        As subclasses podem sobrescrever para personalizar a exibição.
        """
        applied_filters = []
        if self.is_valid(): # Garante que temos cleaned_data
            for field_name, field_obj in self.fields.items():
                if field_name == 'output_format':
                    continue

                value = self.cleaned_data.get(field_name)
                display_value = None

                if value is not None and value != '': # Considerar valores vazios como "não filtro"
                    if isinstance(field_obj, forms.ChoiceField):
                        # Para ChoiceField, incluindo ModelChoiceField e TypedChoiceField (como BooleanField com widget Select)
                        choices_dict = dict(field_obj.choices)
                        display_value = choices_dict.get(value, str(value)) # Usa o label da escolha
                    elif isinstance(field_obj, forms.BooleanField) and not isinstance(field_obj.widget, forms.Select):
                        # Para BooleanFields que não são Select (checkboxes)
                        # O valor já é True/False, precisamos do label se quisermos "Sim/Não"
                        # Mas geralmente o label do campo já diz "Ativo?" e o valor é "True"
                        display_value = "Sim" if value else "Não" # Ou apenas str(value)
                    elif hasattr(value, 'strftime'): # Datas
                        display_value = value.strftime('%d/%m/%Y')
                    else: # CharField, IntegerField, etc.
                        display_value = str(value)
                
                if display_value: # Adiciona apenas se houver um valor a ser exibido
                    applied_filters.append(f"{field_obj.label or field_name.replace('_', ' ').title()}: {display_value}")
        
        return applied_filters


class CustomerReportForm(BaseReportForm): 
    full_name = forms.CharField(
        label="Nome Completo / Razão Social",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parte do nome ou razão social'})
    )
    preferred_name = forms.CharField(
        label="Apelido / Nome Fantasia",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parte do apelido ou nome fantasia'})
    )
    tax_id = forms.CharField(
        label="CPF/CNPJ",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Somente números'})
    )
    phone = forms.CharField(
        label="Telefone",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parte do telefone'})
    )
    email = forms.EmailField(
        label="E-mail",
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Parte do e-mail'})
    )
    address_city = forms.CharField(
        label="Cidade do Endereço",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parte do nome da cidade'})
    )
    address_state = forms.ChoiceField(
        label="UF do Endereço",
        choices=[('', 'Todos')] + Address.BRAZILIAN_STATES_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    customer_type = forms.ChoiceField(
        label="Tipo de Cliente",
        choices=[('', 'Todos')] + Customer.CUSTOMER_TYPE_CHOICES, # Adiciona "Todos"
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.ChoiceField(
        label="Cliente Ativo?",
        choices=BOOLEAN_CHOICES_WITH_ALL,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_vip = forms.ChoiceField(
        label="Cliente VIP?",
        choices=BOOLEAN_CHOICES_WITH_ALL,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # Adicione outros filtros conforme necessário:
    # registration_date_start = forms.DateField(label="Cadastrado de", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    # registration_date_end = forms.DateField(label="Cadastrado até", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

    def get_queryset(self):
        queryset = Customer.objects.prefetch_related('addresses').all() # Começa com todos
        
        if not self.is_valid(): # Se o formulário não for válido, não aplicar filtros
            return queryset.none() # Ou queryset dependendo do comportamento desejado

        # Filtros de texto
        full_name = self.cleaned_data.get('full_name')
        if full_name:
            queryset = queryset.filter(full_name__icontains=full_name)

        preferred_name = self.cleaned_data.get('preferred_name')
        if preferred_name:
            queryset = queryset.filter(preferred_name__icontains=preferred_name)

        tax_id = self.cleaned_data.get('tax_id')
        if tax_id:
            cleaned_tax_id = "".join(filter(str.isdigit, tax_id))
            queryset = queryset.filter(tax_id__icontains=cleaned_tax_id)
        
        phone = self.cleaned_data.get('phone')
        if phone:
            cleaned_phone = "".join(filter(str.isdigit, phone))
            queryset = queryset.filter(phone__icontains=cleaned_phone)

        email = self.cleaned_data.get('email')
        if email:
            queryset = queryset.filter(email__icontains=email)

        # Filtros de endereço (MODIFICADO/ADICIONADO)
        address_city = self.cleaned_data.get('address_city')
        if address_city:
            queryset = queryset.filter(addresses__city__icontains=address_city)

        address_state = self.cleaned_data.get('address_state')
        if address_state:
            queryset = queryset.filter(addresses__state=address_state)

        # Filtros de escolha
        customer_type = self.cleaned_data.get('customer_type')
        if customer_type: # Se não for '' (Todos)
            queryset = queryset.filter(customer_type=customer_type)

        is_active_filter = self.cleaned_data.get('is_active')
        if is_active_filter: 
            queryset = queryset.filter(is_active=(is_active_filter == 'True'))

        is_vip_filter = self.cleaned_data.get('is_vip')
        if is_vip_filter: 
            queryset = queryset.filter(is_vip=(is_vip_filter == 'True'))
        
        # Exemplo com datas (descomente os campos no form se for usar)
        # registration_date_start = self.cleaned_data.get('registration_date_start')
        # if registration_date_start:
        #     queryset = queryset.filter(registration_date__gte=registration_date_start)
        #
        # registration_date_end = self.cleaned_data.get('registration_date_end')
        # if registration_date_end:
        #     # Adiciona 1 dia para incluir o dia final completo se for apenas data
        #     from datetime import timedelta
        #     queryset = queryset.filter(registration_date__lte=registration_date_end + timedelta(days=1))
            
        return queryset.distinct().order_by('full_name')
    

class SupplierReportForm(BaseReportForm):
    full_name = forms.CharField(
        label="Nome Completo / Razão Social",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parte do nome ou razão social'})
    )
    preferred_name = forms.CharField(
        label="Apelido / Nome Fantasia",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parte do apelido ou nome fantasia'})
    )
    tax_id = forms.CharField(
        label="CPF/CNPJ",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Somente números'})
    )
    phone = forms.CharField(
        label="Telefone",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parte do telefone'})
    )
    email = forms.EmailField(
        label="E-mail",
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Parte do e-mail'})
    )
    address_city = forms.CharField(
        label="Cidade do Endereço",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parte do nome da cidade'})
    )
    address_state = forms.ChoiceField(
        label="UF do Endereço",
        choices=[('', 'Todos')] + Address.BRAZILIAN_STATES_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    supplier_type = forms.ChoiceField(
        label="Tipo de Fornecedor",
        choices=[('', 'Todos')] + Supplier.SUPPLIER_TYPE_CHOICES, # Adiciona "Todos"
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.ChoiceField(
        label="Fornecedor Ativo?",
        choices=BOOLEAN_CHOICES_WITH_ALL,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # contact_person foi REMOVIDO
    # registration_date_start = forms.DateField(label="Cadastrado de", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    # registration_date_end = forms.DateField(label="Cadastrado até", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

    def get_queryset(self):
        queryset = Supplier.objects.prefetch_related('addresses').all()

        if not self.is_valid():
            return queryset.none()

        full_name = self.cleaned_data.get('full_name')
        if full_name:
            queryset = queryset.filter(full_name__icontains=full_name)

        preferred_name = self.cleaned_data.get('preferred_name')
        if preferred_name:
            queryset = queryset.filter(preferred_name__icontains=preferred_name)

        tax_id = self.cleaned_data.get('tax_id')
        if tax_id:
            cleaned_tax_id = "".join(filter(str.isdigit, tax_id))
            queryset = queryset.filter(tax_id__icontains=cleaned_tax_id)

        phone = self.cleaned_data.get('phone')
        if phone:
            cleaned_phone = "".join(filter(str.isdigit, phone))
            queryset = queryset.filter(phone__icontains=cleaned_phone)

        email = self.cleaned_data.get('email')
        if email:
            queryset = queryset.filter(email__icontains=email)

        address_city = self.cleaned_data.get('address_city')
        if address_city:
            queryset = queryset.filter(addresses__city__icontains=address_city)

        address_state = self.cleaned_data.get('address_state')
        if address_state:
            queryset = queryset.filter(addresses__state=address_state)

        supplier_type = self.cleaned_data.get('supplier_type')
        if supplier_type:
            queryset = queryset.filter(supplier_type=supplier_type)

        is_active_filter = self.cleaned_data.get('is_active')
        if is_active_filter:
            queryset = queryset.filter(is_active=(is_active_filter == 'True'))
            
        # Filtro por contact_person foi REMOVIDO
        
        # Exemplo com datas (descomente os campos no form se for usar)
        # registration_date_start = self.cleaned_data.get('registration_date_start')
        # if registration_date_start:
        #     queryset = queryset.filter(registration_date__gte=registration_date_start)
        #
        # registration_date_end = self.cleaned_data.get('registration_date_end')
        # if registration_date_end:
        #     from datetime import timedelta
        #     queryset = queryset.filter(registration_date__lte=registration_date_end + timedelta(days=1))

        return queryset.distinct().order_by('full_name')