# employees/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.contrib.contenttypes.fields import GenericRelation
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class Employee(AbstractUser):
    """
    Modelo customizado para representar um funcionário (usuário do sistema).

    Herda de `django.contrib.auth.models.AbstractUser`, adicionando
    campos específicos para funcionários, como tema preferido da interface,
    telefone, data de nascimento, data de contratação e cargo.

    Também se relaciona com o modelo `Address` através de uma `GenericRelation`,
    permitindo que um funcionário possa ter um ou mais endereços associados.

    Atributos:
        THEME_CHOICES (list): Opções de temas visuais disponíveis para o funcionário.
        selected_theme (CharField): O tema visual preferido pelo funcionário.
        phone (CharField): Número de telefone do funcionário.
        birth_date (DateField): Data de nascimento do funcionário.
        hire_date (DateField): Data de contratação do funcionário.
        position (CharField): Cargo ocupado pelo funcionário.
        addresses (GenericRelation): Relação genérica com o modelo `Address`.
    """

    THEME_CHOICES = [
        ("theme-blue-gray", "Azul (Padrão)"),
        ("theme-green-gray", "Verde"),
        ("theme-brown-sand", "Marrom"),
        ("theme-purple-gray", "Roxo"),
    ]
    selected_theme = models.CharField(
        max_length=50,
        choices=THEME_CHOICES,
        default="theme-blue-gray",
        verbose_name="Tema Preferido",
        blank=True,
    )

    phone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message="Formato: '+999999999'. Até 15 dígitos.",
            )
        ],
        verbose_name="Telefone",
        blank=True,
        null=True,
    )

    birth_date = models.DateField(
        verbose_name="Data de Nascimento", blank=True, null=True
    )

    hire_date = models.DateField(
        verbose_name="Data de Contratação", blank=True, null=True
    )

    position = models.CharField(
        max_length=50, verbose_name="Cargo", blank=True, null=True
    )

    addresses = GenericRelation(
        "addresses.Address",
        related_query_name="employee",
        content_type_field="content_type",
        object_id_field="object_id",
        verbose_name="Endereços",
    )

    class Meta:
        """
        Metadados para o modelo Employee.

        Define o nome singular e plural para exibição no admin do Django
        e a ordenação padrão dos registros.
        """

        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"
        ordering = ["last_name", "first_name"]

    @property
    def address(self):
        """
        Retorna o primeiro endereço associado ao funcionário.

        Acessa a `GenericRelation` `addresses` e retorna o primeiro objeto `Address`
        encontrado, ou `None` se o funcionário não tiver nenhum endereço cadastrado.
        """
        return self.addresses.first()

    def save(self, *args, **kwargs):
        """
        Salva a instância do funcionário e tenta completar dados do seu endereço.

        Este método sobrescreve o `save` padrão para incluir lógica adicional
        dentro de uma transação atômica:
        1. Salva a instância do funcionário.
        2. Se o funcionário tiver um endereço associado (`self.address`), chama
           `_complete_address_data()` para tentar preencher automaticamente os
           campos do endereço (e.g., a partir do CEP).
        """
        with transaction.atomic():
            super().save(*args, **kwargs)
            # A atribuição walrus `:=` verifica se `self.address` não é None
            # e atribui seu valor a `address` para uso subsequente.
            if address := self.address:
                self._complete_address_data(address)

    def _complete_address_data(self, address):
        """
        Tenta completar e salvar os dados de um objeto Address.

        Se o objeto `Address` fornecido tiver um `zip_code` (CEP) preenchido,
        mas os campos `street`, `neighborhood`, `city` e `state` não estiverem
        todos preenchidos, este método chama `address.full_clean()` e
        `address.save()`. Isso aciona a lógica de validação e preenchimento
        automático (e.g., busca por CEP) definida no modelo `Address`.

        Erros durante este processo são logados, mas não impedem o salvamento
        do funcionário em si, pois a operação principal de `save()` do funcionário
        já ocorreu.

        Args:
            address (Address): A instância do modelo `Address` a ser processada.
        """
        try:
            # Verifica se o CEP existe e se algum dos campos principais do endereço está vazio.
            if address.zip_code and not all(
                [address.street, address.neighborhood, address.city, address.state]
            ):
                # `full_clean()` no modelo Address pode buscar dados do CEP e preencher os campos.
                address.full_clean()
                address.save()  # Salva as alterações no endereço (se houver).
        except Exception as e:
            logger.error(
                f"Erro ao tentar completar dados do endereço para o funcionário ID {self.pk} "
                f"(Endereço ID {address.pk if address else 'N/A'}): {str(e)}"
            )
