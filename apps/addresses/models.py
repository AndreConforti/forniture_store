from functools import cached_property
from django.db import models
from django.core.validators import RegexValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from core.services import fetch_address_data
import logging

logger = logging.getLogger(__name__)


class Address(models.Model):
    """
    Representa um endereço físico associado a outras entidades do sistema.

    Este modelo armazena detalhes como logradouro, número, CEP, cidade e estado.
    Utiliza um `GenericForeignKey` para permitir a associação com qualquer outro
    modelo que necessite de um endereço (e.g., Cliente, Fornecedor, Ponto de Entrega).

    Inclui funcionalidades para:
    - Validar e limpar o formato do CEP.
    - Preencher automaticamente dados de endereço a partir do CEP, consultando
      uma API externa (`core.services.fetch_address_data`).
    - Cachear os resultados da consulta de CEP para otimizar o desempenho.
    - Normalizar campos de texto (e.g., para Title Case).
    - Fornecer representações formatadas do endereço e do CEP.
    """

    BRAZILIAN_STATES_CHOICES = [
        ("AC", "Acre"),
        ("AL", "Alagoas"),
        ("AP", "Amapá"),
        ("AM", "Amazonas"),
        ("BA", "Bahia"),
        ("CE", "Ceará"),
        ("DF", "Distrito Federal"),
        ("ES", "Espírito Santo"),
        ("GO", "Goiás"),
        ("MA", "Maranhão"),
        ("MT", "Mato Grosso"),
        ("MS", "Mato Grosso do Sul"),
        ("MG", "Minas Gerais"),
        ("PA", "Pará"),
        ("PB", "Paraíba"),
        ("PR", "Paraná"),
        ("PE", "Pernambuco"),
        ("PI", "Piauí"),
        ("RJ", "Rio de Janeiro"),
        ("RN", "Rio Grande do Norte"),
        ("RS", "Rio Grande do Sul"),
        ("RO", "Rondônia"),
        ("RR", "Roraima"),
        ("SC", "Santa Catarina"),
        ("SP", "São Paulo"),
        ("SE", "Sergipe"),
        ("TO", "Tocantins"),
    ]
    CEP_CACHE_TIMEOUT = 86400  # 24 horas em segundos

    street = models.CharField(max_length=100, blank=True, verbose_name="Logradouro")
    number = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="Número"
    )
    complement = models.CharField(max_length=50, blank=True, verbose_name="Complemento")
    neighborhood = models.CharField(max_length=50, blank=True, verbose_name="Bairro")
    city = models.CharField(max_length=50, blank=True, verbose_name="Cidade")
    state = models.CharField(
        max_length=2,
        blank=True,
        verbose_name="UF",
        choices=BRAZILIAN_STATES_CHOICES,
        validators=[
            RegexValidator(
                regex="^[A-Z]{2}$", message="UF deve ter 2 letras maiúsculas."
            )
        ],
    )
    zip_code = models.CharField(
        max_length=8,
        verbose_name="CEP",
        validators=[
            MinLengthValidator(8),
            RegexValidator(r"^\d{8}$", "CEP deve ter 8 dígitos numéricos."),
        ],
        blank=True,
        null=True,
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"
        indexes = [
            models.Index(fields=["state"]),
            models.Index(fields=["city"]),
            models.Index(fields=["zip_code"]),
            models.Index(fields=["content_type", "object_id"]),
        ]
        ordering = ["state", "city", "street"]

    def __str__(self):
        """Retorna a representação textual do endereço, utilizando o endereço formatado."""
        return self.formatted_address()

    def clean(self):
        """
        Executa validações e limpeza de dados antes de salvar o endereço.

        Este método é chamado automaticamente pelo Django durante a validação do modelo
        (e.g., em `full_clean`).

        - Normaliza o formato do CEP.
        - Se o CEP for fornecido e os campos de endereço não estiverem preenchidos
          manualmente, tenta preenchê-los automaticamente usando dados de uma API.
        - Normaliza campos de texto como logradouro, bairro e cidade para Title Case.
        """
        super().clean()

        if self.zip_code:
            self.zip_code = self._clean_zip_code_format(self.zip_code)
            if not self._is_address_manually_filled():
                self._fill_address_from_cep_data()

        self._normalize_text_fields()

    def save(self, *args, **kwargs):
        """
        Sobrescreve o método save para garantir que `full_clean()` seja chamado.

        Isso assegura que todas as validações e lógicas de limpeza definidas no
        método `clean()` sejam executadas antes de persistir o objeto no banco de dados.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def _clean_zip_code_format(self, zip_code_value: str | None) -> str | None:
        """
        Limpa e valida o formato do CEP.

        Remove caracteres não numéricos e verifica se o resultado tem 8 dígitos.

        Args:
            zip_code_value: O valor do CEP a ser limpo.

        Returns:
            O CEP limpo (apenas dígitos) se válido, ou None se a entrada for None/vazia.

        Raises:
            ValidationError: Se o CEP, após a limpeza, não tiver 8 dígitos.
        """
        if not zip_code_value:
            return None
        cleaned = "".join(filter(str.isdigit, str(zip_code_value)))
        if len(cleaned) == 8:
            return cleaned
        raise ValidationError(
            {"zip_code": "CEP inválido. Deve conter 8 dígitos numéricos."}
        )

    def _is_address_manually_filled(self) -> bool:
        """
        Verifica se os principais campos de endereço foram preenchidos manualmente.

        Considera-se preenchido manualmente se logradouro, bairro, cidade e UF
        possuem valores.

        Returns:
            True se os campos estiverem preenchidos, False caso contrário.
        """
        return all([self.street, self.neighborhood, self.city, self.state])

    def _fill_address_from_cep_data(self):
        """
        Preenche os campos de endereço com dados obtidos de uma API de CEP.

        Este método é chamado se o CEP for fornecido e os campos de endereço
        não estiverem preenchidos manualmente. Utiliza `get_cep_data()` para
        buscar as informações e `_update_address_fields()` para aplicá-las.
        Se os dados do CEP não forem encontrados, loga um aviso mas permite
        o salvamento do CEP fornecido.
        """
        cep_data = self.get_cep_data()
        if cep_data:
            self._update_address_fields(cep_data)
        elif self.zip_code and not self._is_address_manually_filled():
            # Loga um aviso se os dados do CEP não puderam ser obtidos mas o CEP foi fornecido
            # e o usuário não preencheu o endereço manualmente.
            logger.warning(
                f"Dados do CEP {self.zip_code} não encontrados ou API falhou. "
                f"O endereço não será preenchido automaticamente, mas o CEP será salvo."
            )

    def get_cep_data(self) -> dict | None:
        """
        Busca dados de endereço para o CEP atual, utilizando cache.

        Se o CEP não estiver definido, retorna None.
        Primeiro tenta obter os dados do cache. Se não encontrar, chama o serviço
        `fetch_address_data` para buscar externamente e armazena o resultado
        no cache para futuras consultas.

        Returns:
            Um dicionário com os dados do endereço (street, neighborhood, city, state)
            ou None se o CEP não for fornecido ou se os dados não forem encontrados.
        """
        if not self.zip_code:
            return None

        cache_key = f"cep_data_{self.zip_code}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        data = fetch_address_data(self.zip_code)

        if data:
            cache.set(cache_key, data, timeout=self.CEP_CACHE_TIMEOUT)
        return data

    def _update_address_fields(self, api_data: dict):
        """
        Atualiza os campos do modelo com os dados da API de CEP.

        Aplica os valores recebidos da API (logradouro, bairro, cidade, UF)
        nos campos correspondentes do modelo, mas apenas se o campo no modelo
        estiver vazio. Isso preserva dados inseridos manualmente pelo usuário.

        Args:
            api_data: Dicionário contendo os dados de endereço retornados pela API.
                      Esperam-se chaves como 'street', 'neighborhood', 'city', 'state'.
        """
        field_map = {
            "street": api_data.get("street"),
            "neighborhood": api_data.get("neighborhood"),
            "city": api_data.get("city"),
            "state": api_data.get("state"),
        }
        for field_name, value in field_map.items():
            # Atualiza o campo apenas se um valor foi retornado pela API
            # e o campo correspondente no modelo estiver vazio.
            if value and not getattr(self, field_name):
                setattr(self, field_name, value.strip())

    def _normalize_text_fields(self):
        """
        Normaliza campos de texto para um formato padrão.

        Converte os campos logradouro, complemento, bairro e cidade para "Title Case"
        (primeira letra de cada palavra em maiúscula) e remove espaços extras no início,
        fim e múltiplos espaços entre palavras.
        O campo UF (estado) é convertido para letras maiúsculas.
        """
        for field_name in ["street", "complement", "neighborhood", "city"]:
            value = getattr(self, field_name)
            if value:
                # Remove espaços extras e aplica Title Case
                normalized_value = " ".join(value.strip().title().split())
                setattr(self, field_name, normalized_value)
        if self.state:
            self.state = self.state.upper()

    @property
    def formatted_zip_code(self) -> str:
        """
        Retorna o CEP formatado como 'NNNNN-NNN'.

        Se o CEP não estiver definido ou não tiver 8 dígitos, retorna o valor
        original do CEP (ou uma string vazia se for None).

        Returns:
            O CEP formatado ou o valor original.
        """
        if self.zip_code and len(self.zip_code) == 8:
            return f"{self.zip_code[:5]}-{self.zip_code[5:]}"
        return self.zip_code or ""

    def formatted_address(self) -> str:
        """
        Constrói e retorna uma string com o endereço completo e formatado.

        Combina os campos de endereço (logradouro, número, complemento, bairro,
        cidade, UF e CEP formatado) em uma única string legível.
        Partes vazias ou nulas são omitidas. Se nenhum campo estiver preenchido,
        retorna "Endereço não fornecido".

        Returns:
            A string do endereço formatado.
        """
        parts = []
        if self.street:
            parts.append(f"{self.street}, {self.number or 'S/N'}")
        if self.complement:
            parts.append(f"Compl: {self.complement}")
        if self.neighborhood:
            parts.append(self.neighborhood)

        city_state_parts = []
        if self.city:
            city_state_parts.append(self.city)
        if self.state:
            city_state_parts.append(self.state)
        if city_state_parts:
            parts.append("-".join(city_state_parts))

        if self.zip_code:
            parts.append(f"CEP: {self.formatted_zip_code}")

        return ", ".join(filter(None, parts)) or "Endereço não fornecido"

    @cached_property
    def is_complete(self) -> bool:
        """
        Indica se os campos essenciais do endereço estão preenchidos.

        Considera um endereço completo se CEP, logradouro, número, bairro,
        cidade e UF estiverem todos preenchidos.
        Utiliza `cached_property` para que o resultado seja calculado apenas uma vez
        por instância e armazenado em cache.

        Returns:
            True se o endereço for considerado completo, False caso contrário.
        """
        return all(
            [
                self.zip_code,
                self.street,
                self.number,
                self.neighborhood,
                self.city,
                self.state,
            ]
        )


class DummyOwnerModel(models.Model): # A DEFINIÇÃO DE DUMMYOWNERMODEL ESTÁ AQUI
    name = models.CharField(max_length=50)

    class Meta:
        pass # Não precisa de app_label aqui

    def __str__(self):
        return self.name