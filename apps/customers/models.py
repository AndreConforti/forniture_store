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


class Customer(models.Model):
    """
    Representa um cliente, que pode ser uma Pessoa Física ou Jurídica.

    Este modelo armazena informações cadastrais básicas, de contato e fiscais.
    Utiliza uma `GenericRelation` com o modelo `Address` para permitir que um
    cliente possa ter um endereço associado. A lógica de validação de CPF/CNPJ
    é implementada no método `clean()`, e a busca de dados de empresas
    (para Pessoa Jurídica) a partir de uma API externa ocorre no método `save()`.
    O gerenciamento do endereço (criação, atualização, exclusão) também é
    centralizado no método `save()`.
    """

    CUSTOMER_TYPE_CHOICES = [("IND", "Pessoa Física"), ("CORP", "Pessoa Jurídica")]

    addresses = GenericRelation(
        Address,
        related_query_name="customer",
        content_type_field="content_type",
        object_id_field="object_id",
        verbose_name="Endereços",
    )
    customer_type = models.CharField(
        verbose_name="Tipo de Cliente",
        max_length=6,
        choices=CUSTOMER_TYPE_CHOICES,
        default="IND",
    )
    full_name = models.CharField(
        verbose_name="Nome Completo / Razão Social",
        max_length=100
    )
    preferred_name = models.CharField(
        verbose_name="Apelido / Nome Fantasia",
        max_length=50, blank=True, null=True
    )
    phone = models.CharField(
        verbose_name="Telefone",
        max_length=11,
        validators=[
            RegexValidator(r"^\d{10,11}$", "Telefone deve ter 10 ou 11 dígitos.")
        ],
        blank=True,
        null=True,
    )
    email = models.EmailField(verbose_name="E-mail", blank=True, null=True)
    tax_id = models.CharField(
        verbose_name="CPF/CNPJ",
        max_length=18,
        unique=True,
    )
    is_active = models.BooleanField(verbose_name="Ativo", default=True)
    registration_date = models.DateTimeField(
        verbose_name="Data de Cadastro", auto_now_add=True
    )
    is_vip = models.BooleanField(verbose_name="VIP", default=False)
    profession = models.CharField(
        verbose_name="Profissão", max_length=50, blank=True, null=True
    )
    interests = models.TextField(verbose_name="Interesses", blank=True, null=True)
    notes = models.TextField(verbose_name="Observações", blank=True, null=True)

    _fetched_api_data_this_save = None

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["-registration_date", "full_name"]
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["tax_id"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        """Retorna a representação textual do cliente (em inglês)."""
        return f"{self.display_name} ({self.formatted_tax_id})"

    def clean(self):
        """
        Executa validações e limpeza dos dados do cliente antes de salvar.

        Este método é chamado automaticamente pelo Django durante a validação do modelo
        (por exemplo, em `full_clean`).
        - Valida o formato e os dígitos verificadores do CPF/CNPJ, de acordo com o
          `customer_type`.
        - Limpa o campo `phone`, removendo caracteres não numéricos.
        """
        super().clean()
        self._validate_and_clean_tax_id()
        self._clean_phone()

    def _validate_and_clean_tax_id(self):
        """
        Valida o formato e os dígitos verificadores do CPF/CNPJ e armazena apenas os números.

        Levanta `ValidationError` se o documento for inválido ou não corresponder ao tipo de cliente.
        """
        if not self.tax_id:
            raise ValidationError({"tax_id": "Documento (CPF/CNPJ) obrigatório!"})

        cleaned_tax_id = "".join(filter(str.isdigit, self.tax_id))

        if not self.customer_type:
            raise ValidationError({"customer_type": "Tipo de cliente não definido."})

        validator_map = {
            "IND": {"len": 11, "validator": CPF(), "msg": "CPF inválido!"},
            "CORP": {"len": 14, "validator": CNPJ(), "msg": "CNPJ inválido!"},
        }

        config = validator_map.get(self.customer_type)
        if not config:
            raise ValidationError(
                {"customer_type": "Tipo de cliente inválido para validar documento."}
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
        Salva a instância do Cliente e gerencia seu endereço associado.

        1.  **Busca de Dados Externos (PJ):** Se Pessoa Jurídica, tenta buscar dados da empresa
            (Razão Social, Nome Fantasia, Endereço) usando o CNPJ via serviço externo.
            Campos `full_name` e `preferred_name` podem ser atualizados.
        2.  **Validação:** Executa `self.full_clean()`.
        3.  **Persistência:** Salva a instância do cliente.
        4.  **Endereço:** Gerencia o endereço com base no argumento `address_data` (opcional).
            Se `address_data` tiver dados, cria/atualiza o endereço.
            Se `address_data` for `{}`, remove o endereço existente.
            Se `address_data` for `None` e for PJ, usa dados da API para o endereço.
            Operações ocorrem em uma transação atômica.

        Args:
            *args: Argumentos posicionais para `super().save()`.
            **kwargs: Argumentos nomeados para `super().save()`. Pode incluir `address_data`.
        """
        address_data_from_form = kwargs.pop("address_data", None)
        self._fetched_api_data_this_save = False

        company_api_data = None
        if self.customer_type == "CORP":
            temp_cleaned_tax_id = "".join(filter(str.isdigit, self.tax_id or ""))
            if len(temp_cleaned_tax_id) == 14:
                company_api_data = fetch_company_data(temp_cleaned_tax_id)
                self._fetched_api_data_this_save = True

            if company_api_data:
                if company_api_data.get("full_name"):
                    self.full_name = company_api_data["full_name"]
                if company_api_data.get("preferred_name"):
                    self.preferred_name = company_api_data["preferred_name"]

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
                and any(
                    v for v in address_data_from_form.values() if v not in [None, ""]
                )
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
            elif self.customer_type == "CORP" and not form_provided_data:
                if not self._fetched_api_data_this_save and not company_api_data:
                    company_api_data = fetch_company_data(self.tax_id)

                if company_api_data:
                    api_address_payload = {
                        k: company_api_data.get(k)
                        for k in [
                            "zip_code", "street", "number", "complement",
                            "neighborhood", "city", "state",
                        ]
                    }
                    if any(
                        v for v in api_address_payload.values() if v not in [None, ""]
                    ):
                        final_address_data_to_persist = api_address_payload
                        address_source_is_api = True
            elif self.customer_type == "IND" and form_provided_data and not form_has_valid_address_fields and not form_requested_clear_address:
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
        Cria ou atualiza o endereço associado ao cliente com os dados fornecidos.

        Filtra chaves com valores `None` ou string vazia.
        Loga a ação e a origem dos dados.

        Args:
            address_data (dict): Dicionário com dados do endereço.
            from_api (bool): True se os dados vieram da API.

        Raises:
            ValidationError: Se ocorrer erro de validação ao salvar o `Address`.
        """
        cleaned_address_data = {
            k: v for k, v in address_data.items() if v not in [None, ""]
        }

        if not cleaned_address_data:
            source_info = "API" if from_api else "formulário"
            logger.info(
                f"Nenhum dado de endereço válido da {source_info} para Cliente ID {self.pk}."
            )
            if not from_api: 
                self._delete_existing_address()
            return

        content_type = ContentType.objects.get_for_model(self)
        try:
            addr_obj, created = Address.objects.update_or_create(
                content_type=content_type,
                object_id=self.pk,
                defaults=cleaned_address_data,
            )
            action = "criado" if created else "atualizado"
            source_log = "API" if from_api else "formulário"
            logger.info(
                f"Endereço {action} para Cliente ID {self.pk} via {source_log} com dados: {cleaned_address_data}"
            )
        except ValidationError as e:
            logger.error(
                f"Erro de validação ao salvar endereço para Cliente ID {self.pk}: {e.message_dict if hasattr(e, 'message_dict') else e.messages}"
            )
            raise

    def _delete_existing_address(self):
        """Deleta o primeiro endereço associado a este cliente, se existir."""
        existing_address = self.addresses.first()
        if existing_address:
            existing_address.delete()
            logger.info(f"Endereço existente deletado para Cliente ID {self.pk}.")

    @property
    def address(self) -> Address | None:
        """
        Retorna o primeiro endereço associado ao cliente, ou `None`.
        """
        return self.addresses.first()

    @cached_property
    def display_name(self) -> str:
        """
        Retorna o nome de exibição do cliente.

        Prioriza `preferred_name`, depois `full_name`, ou "Cliente [ID]" como fallback.
        """
        return self.preferred_name or self.full_name or f"Cliente {self.pk}"

    @cached_property
    def formatted_phone(self) -> str:
        """
        Retorna o telefone formatado com máscara.
        """
        if not self.phone:
            return ""
        if len(self.phone) == 10:
            return f"({self.phone[:2]}) {self.phone[2:6]}-{self.phone[6:]}"
        if len(self.phone) == 11:
            return f"({self.phone[:2]}) {self.phone[2:7]}-{self.phone[7:]}"
        return self.phone

    @cached_property
    def formatted_tax_id(self) -> str:
        """
        Retorna o CPF/CNPJ formatado com máscara.
        """
        current_tax_id = self.tax_id
        if not current_tax_id:
            return ""
        if len(current_tax_id) == 11:  # CPF
            return f"{current_tax_id[:3]}.{current_tax_id[3:6]}.{current_tax_id[6:9]}-{current_tax_id[9:]}"
        if len(current_tax_id) == 14:  # CNPJ
            return f"{current_tax_id[:2]}.{current_tax_id[2:5]}.{current_tax_id[5:8]}/{current_tax_id[8:12]}-{current_tax_id[12:]}"
        return current_tax_id