# test_model_address.py

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from unittest.mock import patch, call

from apps.addresses.models import Address, DummyOwnerModel

PATH_TO_FETCH_ADDRESS = "apps.addresses.models.fetch_address_data"
PATH_TO_LOGGER_WARNING = "apps.addresses.models.logger.warning"


class AddressModelTests(TestCase):
    """Conjunto de testes completo para o modelo Address."""

    @classmethod
    def setUpTestData(cls):
        """Configura objetos não modificados usados por todos os métodos de teste."""
        cls.owner = DummyOwnerModel.objects.create(name="Test Owner GFK")
        cls.owner_content_type = ContentType.objects.get_for_model(DummyOwnerModel)
        cls.mock_api_data_full = {
            "street": "Rua Mockada API",
            "neighborhood": "Bairro Mockado API",
            "city": "Cidade Mockada API",
            "state": "SP",
        }
        cls.mock_api_data_partial = {
            "street": "Rua Mockada Parcial",
            "city": "Cidade Mockada Parcial",
        }

    def test_create_address_minimal_valid(self):
        """Testa a criação de um endereço válido com dados mínimos de GFK."""
        address = Address(content_type=self.owner_content_type, object_id=self.owner.pk)
        address.full_clean()
        address.save()
        self.assertIsNotNone(address.pk, "O endereço deveria ter sido salvo e ter um PK.")
        self.assertEqual(address.content_object, self.owner, "O content_object não corresponde ao owner esperado.")

    def test_generic_foreign_key_relation(self):
        """Testa explicitamente a funcionalidade da relação GenericForeignKey."""
        address = Address.objects.create(
            street="Rua Teste GFK",
            content_object=self.owner
        )
        retrieved_address = Address.objects.get(pk=address.pk)
        self.assertEqual(retrieved_address.content_object, self.owner,
                         "O content_object do endereço recuperado não corresponde.")

        # Verifica se conseguimos encontrar o endereço filtrando pelo owner
        addresses_for_owner = Address.objects.filter(
            content_type=self.owner_content_type,
            object_id=self.owner.pk
        )
        self.assertIn(address, addresses_for_owner,
                      "O endereço criado não foi encontrado ao filtrar endereços para o owner.")
        self.assertEqual(addresses_for_owner.count(), 1, "Deveria haver apenas um endereço para este owner.")


    @patch(PATH_TO_FETCH_ADDRESS, return_value=None)
    def test_clean_zip_code_format(self, mock_fetch_ignored):
        """Testa a limpeza e validação do CEP para vários formatos."""
        address = Address(zip_code="12345-678", content_object=self.owner)
        address.clean()
        self.assertEqual(address.zip_code, "12345678", "CEP com hífen não foi limpo corretamente.")

        address = Address(zip_code="87654321", content_object=self.owner)
        address.clean()
        self.assertEqual(address.zip_code, "87654321", "CEP já limpo foi alterado indevidamente.")

        with self.assertRaises(ValidationError) as cm_short:
            Address(zip_code="12345", content_object=self.owner).full_clean()
        self.assertIn("zip_code", cm_short.exception.message_dict)
        error_msg = cm_short.exception.message_dict["zip_code"][0]
        self.assertIn("no mínimo 8 caracteres", error_msg, "Mensagem de erro para CEP curto incorreta.")

        with self.assertRaises(ValidationError) as cm_chars:
            Address(zip_code="12345abc", content_object=self.owner).full_clean()
        self.assertIn("zip_code", cm_chars.exception.message_dict)
        self.assertEqual(
            cm_chars.exception.message_dict["zip_code"][0],
            "CEP deve ter 8 dígitos numéricos.",
            "Mensagem de erro para CEP com caracteres inválidos incorreta."
        )

        with self.assertRaises(ValidationError) as cm_long:
            Address(zip_code="123456789", content_object=self.owner).full_clean()
        self.assertIn("zip_code", cm_long.exception.message_dict)
        # A mensagem pode ser de max_length ou do RegexValidator
        self.assertTrue(
            any("máximo 8 caracteres" in msg for msg in cm_long.exception.message_dict["zip_code"]) or
            "CEP deve ter 8 dígitos numéricos." in cm_long.exception.message_dict["zip_code"][0],
            "Mensagem de erro para CEP longo incorreta."
        )


    @patch(PATH_TO_FETCH_ADDRESS)
    def test_fill_address_from_cep_data_success(self, mock_fetch_address_data):
        """Testa o preenchimento automático do endereço via API de CEP em caso de sucesso."""
        mock_fetch_address_data.return_value = self.mock_api_data_full
        address = Address(zip_code="87654321", content_object=self.owner)
        address.full_clean()
        address.save()

        self.assertEqual(address.street, self.mock_api_data_full["street"].title())
        self.assertEqual(address.neighborhood, self.mock_api_data_full["neighborhood"].title())
        self.assertEqual(address.city, self.mock_api_data_full["city"].title())
        self.assertEqual(address.state, self.mock_api_data_full["state"].upper())
        mock_fetch_address_data.assert_called_once_with("87654321")

    @patch(PATH_TO_FETCH_ADDRESS)
    def test_update_address_fields_with_partial_api_data(self, mock_fetch_address_data):
        """Testa _update_address_fields com dados parciais da API e campos pré-existentes."""
        mock_fetch_address_data.return_value = self.mock_api_data_partial
        address = Address(
            zip_code="12345678",
            street="Rua Manual Original",
            neighborhood="Bairro Manual Original",
            state="RJ",
            content_object=self.owner
        )
        address.full_clean()

        self.assertEqual(address.street, "Rua Manual Original", "Rua manual foi sobrescrita indevidamente.")
        self.assertEqual(address.city, self.mock_api_data_partial["city"].title(), "Cidade não foi preenchida pela API.")
        self.assertEqual(address.neighborhood, "Bairro Manual Original", "Bairro manual foi alterado indevidamente.")
        self.assertEqual(address.state, "RJ", "Estado manual foi alterado indevidamente.")
        mock_fetch_address_data.assert_called_once_with("12345678")


    @patch(PATH_TO_FETCH_ADDRESS)
    @patch(PATH_TO_LOGGER_WARNING)
    def test_fill_address_from_cep_data_api_returns_none(self, mock_log_warning, mock_fetch_address_data):
        """Testa o comportamento quando a API de CEP não retorna dados; espera um aviso."""
        mock_fetch_address_data.return_value = None
        address = Address(zip_code="00000000", content_object=self.owner)
        address.full_clean()

        self.assertEqual(address.street, "", "Rua deveria estar vazia.")
        self.assertEqual(address.city, "", "Cidade deveria estar vazia.")
        mock_fetch_address_data.assert_called_once_with("00000000")
        mock_log_warning.assert_called_once()

    @patch(PATH_TO_FETCH_ADDRESS)
    def test_fill_address_does_not_overwrite_manual_data(self, mock_fetch_address_data):
        """Testa se o preenchimento via API de CEP não sobrescreve dados manuais já preenchidos."""
        mock_fetch_address_data.return_value = self.mock_api_data_full
        address = Address(
            zip_code="11111111", street="Manual Street", neighborhood="Manual Neighborhood",
            city="Manual City", state="SP", content_object=self.owner,
        )
        address.full_clean()
        address.save()

        self.assertEqual(address.street, "Manual Street")
        self.assertEqual(address.city, "Manual City")
        self.assertEqual(address.state, "SP")
        mock_fetch_address_data.assert_not_called() # CORRIGIDO

    @patch(PATH_TO_FETCH_ADDRESS, return_value=None)
    def test_normalize_text_fields(self, mock_fetch_ignored):
        """Testa a normalização de campos de texto (ex: Title Case, UF maiúscula)."""
        address = Address(
            street="  rua das   acácias  ", complement="APTO 101 bloco b",
            neighborhood=" jardim das flores ", city="são josé dos campos",
            state="SP", content_object=self.owner,
        )
        address.full_clean()
        self.assertEqual(address.street, "Rua Das Acácias")
        self.assertEqual(address.complement, "Apto 101 Bloco B")
        self.assertEqual(address.neighborhood, "Jardim Das Flores")
        self.assertEqual(address.city, "São José Dos Campos")
        self.assertEqual(address.state, "SP")

    def test_formatted_zip_code_property(self):
        """Testa a saída da propriedade `formatted_zip_code`."""
        self.assertEqual(Address(zip_code="12345678").formatted_zip_code, "12345-678")
        self.assertEqual(Address(zip_code="12345").formatted_zip_code, "12345", "CEP curto não formatado não deve quebrar.")
        self.assertEqual(Address(zip_code=None).formatted_zip_code, "", "CEP nulo deve retornar string vazia.")
        self.assertEqual(Address(zip_code="").formatted_zip_code, "", "CEP vazio deve retornar string vazia.")

    @patch(PATH_TO_FETCH_ADDRESS, return_value=None)
    def test_formatted_address_method(self, mock_fetch_ignored):
        """Testa a saída do método `formatted_address` para vários casos."""
        address_full = Address(
            street="Rua Principal", number="123", complement="Apto 4B",
            neighborhood="Centro", city="Metropolis", state="SP",
            zip_code="12345678", content_object=self.owner,
        )
        address_full.full_clean()
        expected = "Rua Principal, 123, Compl: Apto 4B, Centro, Metropolis-SP, CEP: 12345-678"
        self.assertEqual(address_full.formatted_address(), expected)

        address_no_number = Address(street="Rua Sem Numero", city="Smallville", state="GO", content_object=self.owner)
        address_no_number.full_clean()
        self.assertEqual(address_no_number.formatted_address(), "Rua Sem Numero, S/N, Smallville-GO")

        address_only_city_state_zip = Address(
            city="Rio de Janeiro", state="RJ", zip_code="20000000", content_object=self.owner
        )
        address_only_city_state_zip.full_clean() # Normaliza para "Rio De Janeiro"

        self.assertEqual(address_only_city_state_zip.formatted_address(), "Rio De Janeiro-RJ, CEP: 20000-000")

        address_empty = Address(content_object=self.owner)
        address_empty.full_clean()
        self.assertEqual(address_empty.formatted_address(), "Endereço não fornecido")

    @patch(PATH_TO_FETCH_ADDRESS, return_value=None)
    def test_is_complete_property(self, mock_fetch_ignored):
        """Testa a propriedade `is_complete` para endereços completos e incompletos."""
        complete_data = {
            "street":"Rua Completa", "number":"S/N", "neighborhood":"Bairro Legal",
            "city":"Cidade Feliz", "state":"SC", "zip_code":"11223344", "content_object":self.owner
        }
        self.assertTrue(Address(**complete_data).is_complete)

        for field_to_remove in complete_data:
            if field_to_remove == "content_object": continue
            incomplete_data = complete_data.copy()
            incomplete_data[field_to_remove] = ""
            address_incomplete = Address(**incomplete_data)
            self.assertFalse(address_incomplete.is_complete, f"Endereço deveria ser incompleto sem '{field_to_remove}'.")

    def test_save_with_valid_data(self):
        """Testa se salvar um endereço com todos os dados válidos funciona."""
        valid_data = {
            "street": "Avenida Teste", "number": "100", "complement": "Sala 1",
            "neighborhood": "Teste Bairro", "city": "Teste Cidade", "state": "PR",
            "zip_code": "80000100", "content_object": self.owner
        }
        address = Address(**valid_data)
        address.save()
        self.assertIsNotNone(address.pk, "Endereço válido não foi salvo.")
        # Verifica se os dados foram salvos (considerando normalização)
        saved_address = Address.objects.get(pk=address.pk)
        self.assertEqual(saved_address.street, "Avenida Teste") # Normalizado
        self.assertEqual(saved_address.state, "PR")


    @patch(PATH_TO_FETCH_ADDRESS, return_value=None)
    def test_save_calls_full_clean(self, mock_fetch_ignored):
        """Testa se `save()` chama implicitamente `full_clean()` e normaliza os dados."""
        address = Address(
            street="  rua suja ", state="RJ",
            zip_code="98765432", content_object=self.owner,
        )
        address.save()
        self.assertEqual(address.street, "Rua Suja")
        self.assertEqual(address.state, "RJ")
        self.assertEqual(address.zip_code, "98765432")

    def test_save_with_invalid_zip_code_raises_error(self):
        """Testa se salvar com CEP inválido (curto) levanta ValidationError."""
        address = Address(zip_code="123", content_object=self.owner)
        with self.assertRaises(ValidationError) as cm:
            address.save()
        self.assertIn("zip_code", cm.exception.message_dict)
        self.assertIn("no mínimo 8 caracteres", cm.exception.message_dict["zip_code"][0])

    def test_save_with_invalid_state_format_raises_error(self):
        """Testa se salvar com formato de UF inválido levanta ValidationError."""
        invalid_formats = ["R", "RJX", "r", "12"]
        for invalid_state in invalid_formats:
            with self.subTest(state=invalid_state):
                address = Address(state=invalid_state, content_object=self.owner)
                with self.assertRaises(ValidationError) as cm:
                    address.save()
                self.assertIn("state", cm.exception.message_dict)
                error_msg = cm.exception.message_dict["state"][0]
                self.assertTrue(
                    "não é uma opção válida" in error_msg or
                    "UF deve ter 2 letras maiúsculas" in error_msg,
                    f"Mensagem de erro inesperada para UF '{invalid_state}': {error_msg}"
                )

    def test_save_with_invalid_state_choice_raises_error(self):
        """Testa se salvar com UF que não está nas `choices` levanta ValidationError."""
        address = Address(state="XX", content_object=self.owner)
        with self.assertRaises(ValidationError) as cm:
            address.save()
        self.assertIn("state", cm.exception.message_dict)
        error_msg = cm.exception.message_dict["state"][0]
        self.assertTrue(
            "Valor 'XX' não é uma opção válida." in error_msg or
            "Value 'XX' is not a valid choice." in error_msg
        )