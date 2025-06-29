# apps/suppliers/models.py
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.functional import cached_property
from apps.addresses.models import Address
from core.services import fetch_company_data
from validate_docbr import CPF, CNPJ
import logging

logger = logging.getLogger(__name__)

class Supplier(models.Model):
    """
    Representa um fornecedor, que pode ser uma Pessoa Física ou Jurídica.

    Armazena informações cadastrais, de contato, fiscais e bancárias.
    Utiliza uma `GenericRelation` com o modelo `Address` para associação de endereço.
    Validações de CNPJ/CPF são feitas no `clean()`. A busca de dados de empresas
    via API e o gerenciamento de endereço ocorrem no `save()`.
    """
    SUPPLIER_TYPE_CHOICES = [
        ('IND', 'Pessoa Física'),
        ('CORP', 'Pessoa Jurídica'),
    ]

    addresses = GenericRelation(
        Address,
        related_query_name='supplier',
        content_type_field='content_type',
        object_id_field='object_id',
        verbose_name="Endereços", # Mantido em pt-BR para Admin
    )
    supplier_type = models.CharField(
        verbose_name='Tipo de Fornecedor', # Mantido em pt-BR para Admin
        max_length=6,
        choices=SUPPLIER_TYPE_CHOICES,
        default='CORP'
    )
    full_name = models.CharField(
        verbose_name='Nome Completo / Razão Social',  # Mantido em pt-BR para Admin
        max_length=100,
        help_text="Nome completo (PF) ou Razão Social (PJ)." # Mantido em pt-BR para Admin
    )
    preferred_name = models.CharField(
        verbose_name='Apelido / Nome Fantasia', # Mantido em pt-BR para Admin
        max_length=50,
        blank=True,
        null=True
    )
    tax_id = models.CharField(
        verbose_name='CNPJ/CPF', # Mantido em pt-BR para Admin
        max_length=18,
        unique=True
    )
    state_registration = models.CharField(
        verbose_name='Inscrição Estadual', # Mantido em pt-BR para Admin
        max_length=20,
        blank=True,
        null=True
    )
    municipal_registration = models.CharField(
        verbose_name='Inscrição Municipal', # Mantido em pt-BR para Admin
        max_length=20,
        blank=True,
        null=True
    )
    phone = models.CharField(
        verbose_name='Telefone', # Mantido em pt-BR para Admin
        max_length=11,
        validators=[RegexValidator(r'^\d{10,11}$', "Telefone deve ter 10 ou 11 dígitos.")],
        blank=True,
        null=True
    )
    email = models.EmailField(
        verbose_name='E-mail', # Mantido em pt-BR para Admin
        blank=True,
        null=True
    )
    contact_person = models.CharField(
        verbose_name='Pessoa de Contato', # Mantido em pt-BR para Admin
        max_length=100,
        blank=True,
        null=True
    )
    bank_name = models.CharField(
        verbose_name='Banco', # Mantido em pt-BR para Admin
        max_length=50,
        blank=True,
        null=True
    )
    bank_agency = models.CharField(
        verbose_name='Agência', # Mantido em pt-BR para Admin
        max_length=10,
        blank=True,
        null=True
    )
    bank_account = models.CharField(
        verbose_name='Conta', # Mantido em pt-BR para Admin
        max_length=20,
        blank=True,
        null=True
    )
    pix_key = models.CharField(
        verbose_name='Chave PIX', # Mantido em pt-BR para Admin
        max_length=100,
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        verbose_name='Ativo', # Mantido em pt-BR para Admin
        default=True
    )
    registration_date = models.DateTimeField(
        verbose_name='Data de Cadastro', # Mantido em pt-BR para Admin
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        verbose_name='Última Atualização', # Mantido em pt-BR para Admin
        auto_now=True
    )
    notes = models.TextField(
        verbose_name='Observações', # Mantido em pt-BR para Admin
        blank=True,
        null=True
    )

    _fetched_api_data_this_save = None

    class Meta:
        verbose_name = 'Fornecedor' # Mantido em pt-BR para Admin
        verbose_name_plural = 'Fornecedores' # Mantido em pt-BR para Admin
        ordering = ['-registration_date', 'full_name']
        indexes = [
            models.Index(fields=['full_name']),
            models.Index(fields=['tax_id']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self) -> str:
        """Retorna a representação textual do fornecedor (em inglês)."""
        return f"{self.display_name} ({self.formatted_tax_id})"

    def clean(self):
        """
        Executa validações e limpeza dos dados do fornecedor antes de salvar.
        """
        super().clean()
        self._validate_and_clean_tax_id()
        self._clean_phone()

    def _validate_and_clean_tax_id(self):
        """
        Valida o formato e os dígitos verificadores do CNPJ/CPF e armazena apenas os números.
        """
        if not self.tax_id:
            raise ValidationError({"tax_id": "Documento (CNPJ/CPF) obrigatório!"})

        cleaned_tax_id = "".join(filter(str.isdigit, self.tax_id))

        if not self.supplier_type:
            raise ValidationError({"supplier_type": "Tipo de fornecedor não definido."})

        validator_map = {
            "IND": {"len": 11, "validator": CPF(), "msg": "CPF inválido!"},
            "CORP": {"len": 14, "validator": CNPJ(), "msg": "CNPJ inválido!"},
        }

        config = validator_map.get(self.supplier_type)
        if not config:
            raise ValidationError(
                {"supplier_type": "Tipo de fornecedor inválido para validar documento."}
            )

        if len(cleaned_tax_id) != config["len"]:
            raise ValidationError(
                {"tax_id": f"{config['msg']} Deve conter {config['len']} números."}
            )
        if not config["validator"].validate(cleaned_tax_id):
            raise ValidationError({"tax_id": config["msg"]})

        self.tax_id = cleaned_tax_id

    def _clean_phone(self):
        """Remove caracteres não numéricos do campo telefone."""
        if self.phone:
            self.phone = "".join(filter(str.isdigit, self.phone))

    def save(self, *args, **kwargs):
        """
        Salva a instância do Fornecedor e gerencia seu endereço associado.

        Inclui busca de dados da empresa via API para PJ e tratamento de dados de endereço.
        """
        address_data_from_form = kwargs.pop("address_data", None)
        self._fetched_api_data_this_save = False

        company_api_data = None
        if self.supplier_type == "CORP":
            temp_cleaned_tax_id = "".join(filter(str.isdigit, self.tax_id or ""))
            if len(temp_cleaned_tax_id) == 14:
                company_api_data = fetch_company_data(temp_cleaned_tax_id)
                self._fetched_api_data_this_save = True

            if company_api_data:
                if company_api_data.get("full_name"):
                    self.full_name = company_api_data["full_name"]
                if company_api_data.get("preferred_name"):
                    self.preferred_name = company_api_data["preferred_name"]
                if company_api_data.get("state_registration"):
                    self.state_registration = company_api_data["state_registration"]
        
        self.full_clean()

        with transaction.atomic():
            super().save(*args, **kwargs) 

            final_address_data_to_persist = None
            address_source_is_api = False
            perform_delete_address = False

            form_provided_data = address_data_from_form is not None
            form_has_valid_address_fields = (
                form_provided_data
                and isinstance(address_data_from_form, dict)
                and address_data_from_form 
                and any(v for v in address_data_from_form.values() if v not in [None, ""])
            )
            form_requested_clear_address = (
                form_provided_data
                and isinstance(address_data_from_form, dict)
                and not address_data_from_form 
            )
            
            if form_has_valid_address_fields:
                final_address_data_to_persist = address_data_from_form
            elif form_requested_clear_address:
                perform_delete_address = True
            elif self.supplier_type == "CORP" and not form_provided_data:
                if not self._fetched_api_data_this_save and not company_api_data:
                    company_api_data = fetch_company_data(self.tax_id) 

                if company_api_data:
                    api_address_payload = {
                        k: company_api_data.get(k)
                        for k in ["zip_code", "street", "number", "complement", "neighborhood", "city", "state"]
                    }
                    if any(v for v in api_address_payload.values() if v not in [None, ""]):
                        final_address_data_to_persist = api_address_payload
                        address_source_is_api = True
            elif self.supplier_type == "IND" and form_provided_data and not form_has_valid_address_fields and not form_requested_clear_address:
                perform_delete_address = True

            if final_address_data_to_persist:
                self._update_or_create_address_from_data(
                    final_address_data_to_persist, from_api=address_source_is_api
                )
            elif perform_delete_address:
                self._delete_existing_address()

        if hasattr(self, "_fetched_api_data_this_save"):
            delattr(self, "_fetched_api_data_this_save")

    def _update_or_create_address_from_data(
        self, address_data: dict, from_api: bool = False
    ):
        """
        Cria ou atualiza o endereço associado ao fornecedor.
        """
        cleaned_address_data = {
            k: v for k, v in address_data.items() if v not in [None, ""]
        }

        if not cleaned_address_data:
            source_info = "API" if from_api else "formulário" # Variável local em inglês
            logger.info(
                f"Nenhum dado de endereço válido da {source_info} para Fornecedor ID {self.pk}."
            )
            if not from_api:
                 self._delete_existing_address()
            return

        content_type = ContentType.objects.get_for_model(self)
        try:
            address_object, created = Address.objects.update_or_create( # Variável local em inglês
                content_type=content_type,
                object_id=self.pk,
                defaults=cleaned_address_data,
            )
            action = "criado" if created else "atualizado"
            source_log = "API" if from_api else "formulário"
            logger.info(
                f"Endereço {action} para Fornecedor ID {self.pk} via {source_log} com dados: {cleaned_address_data}"
            )
        except ValidationError as e:
            logger.error(
                f"Erro de validação ao salvar endereço para Fornecedor ID {self.pk}: {e.message_dict if hasattr(e, 'message_dict') else e.messages}"
            )
            raise

    def _delete_existing_address(self):
        """Deleta o primeiro endereço associado a este fornecedor, se existir."""
        existing_address = self.addresses.first()
        if existing_address:
            existing_address.delete()
            logger.info(f"Endereço existente deletado para Fornecedor ID {self.pk}.")

    @property
    def address(self) -> Address | None:
        """Retorna o primeiro endereço associado ao fornecedor."""
        return self.addresses.first()

    @cached_property
    def display_name(self) -> str:
        """Retorna o nome de exibição do fornecedor."""
        return self.preferred_name or self.full_name or f"Fornecedor {self.pk}"

    @cached_property
    def formatted_phone(self) -> str:
        """Retorna o telefone formatado."""
        if not self.phone:
            return ""
        if len(self.phone) == 10:
            return f"({self.phone[:2]}) {self.phone[2:6]}-{self.phone[6:]}"
        if len(self.phone) == 11:
            return f"({self.phone[:2]}) {self.phone[2:7]}-{self.phone[7:]}"
        return self.phone

    @cached_property
    def formatted_tax_id(self) -> str:
        """Retorna o CNPJ/CPF formatado."""
        current_tax_id = self.tax_id 
        if not current_tax_id:
            return ""
        if len(current_tax_id) == 11:  # CPF
            return f"{current_tax_id[:3]}.{current_tax_id[3:6]}.{current_tax_id[6:9]}-{current_tax_id[9:]}"
        if len(current_tax_id) == 14:  # CNPJ
            return f"{current_tax_id[:2]}.{current_tax_id[2:5]}.{current_tax_id[5:8]}/{current_tax_id[8:12]}-{current_tax_id[12:]}"
        return current_tax_id