from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from unittest.mock import patch
from apps.customers.models import Customer
from apps.addresses.models import Address

PATH_FETCH_COMPANY_DATA = "apps.customers.models.fetch_company_data"
PATH_ADDRESS_UPDATE_OR_CREATE = "apps.addresses.models.Address.objects.update_or_create"
PATH_CUSTOMER_LOGGER = "apps.customers.models.logger"

# =======================================================================
#  CPFs/CNPJs Válidos para Teste
# =======================================================================
VALID_CPF_1 = "10585278008"
VALID_CPF_2 = "43214589008"
VALID_CPF_3 = "88956381070"
VALID_CPF_4 = "77007222005"
VALID_CPF_FOR_LOGIC_TEST = "27875969832"

VALID_CNPJ_1 = "20612379000106"
VALID_CNPJ_2 = "06086255000103"
VALID_CNPJ_FOR_LOGIC_TEST = "32762065000160"

CPF_TRANS_CREATE_FAIL_VALID = "75723268031"
CPF_TRANS_UPDATE_FAIL_VALID = "44557172008"
# =======================================================================


class CustomerAddressIntegrationTests(TestCase):
    """Testa a integração do Cliente com Endereços via `save()`."""

    def setUp(self):
        """Configura dados base para os testes de integração."""
        self.customer_pf_data = {
            "customer_type": "IND",
            "full_name": "Cliente PF Teste",
            "tax_id": VALID_CPF_1,
        }
        self.customer_pf_data_cpf2 = {
            "customer_type": "IND",
            "full_name": "Cliente PF 2 Teste",
            "tax_id": VALID_CPF_2.replace(".", "").replace("-", ""),
        }
        self.customer_pf_data_cpf3 = {
            "customer_type": "IND",
            "full_name": "Cliente PF 3 Teste",
            "tax_id": VALID_CPF_3.replace(".", "").replace("-", ""),
        }
        self.customer_pf_data_cpf4 = {
            "customer_type": "IND",
            "full_name": "Cliente PF 4 Teste",
            "tax_id": VALID_CPF_4.replace(".", "").replace("-", ""),
        }
        self.customer_pj_data = {
            "customer_type": "CORP",
            "full_name": "Empresa PJ Teste",
            "tax_id": VALID_CNPJ_1,
        }
        self.customer_pj_data_cnpj2 = {
            "customer_type": "CORP",
            "full_name": "Empresa PJ 2 Teste",
            "tax_id": VALID_CNPJ_2,
        }
        self.address_form_data_valid = {
            "street": "Rua do Formulário",
            "number": "100",
            "neighborhood": "Bairro Form",
            "city": "Cidade Form",
            "state": "SP",
            "zip_code": "12345678",
        }
        self.address_api_data_valid = {
            "street": "Rua da API",
            "number": "200A",
            "neighborhood": "Bairro API",
            "city": "Cidade API",
            "state": "RJ",
            "zip_code": "87654321",
            "complement": "Sala 2",
        }
        self.patcher_fetch_company = patch(PATH_FETCH_COMPANY_DATA)
        self.mock_fetch_company = self.patcher_fetch_company.start()
        self.mock_fetch_company.return_value = None

    def tearDown(self):
        """Finaliza o patcher após cada teste."""
        self.patcher_fetch_company.stop()

    def test_save_customer_creates_address_from_form_data(self):
        """Testa criação de endereço a partir de dados de formulário."""
        customer = Customer.objects.create(**self.customer_pf_data)
        self.assertEqual(customer.addresses.count(), 0)
        customer.save(address_data=self.address_form_data_valid)
        self.assertEqual(customer.addresses.count(), 1)
        address = customer.addresses.first()
        self.assertIsNotNone(address)
        self.assertEqual(
            address.street.lower(), self.address_form_data_valid["street"].lower()
        )

    def test_save_customer_updates_existing_address_from_form_data(self):
        """Testa atualização de endereço existente via dados de formulário."""
        customer = Customer.objects.create(**self.customer_pf_data_cpf2)
        initial_address_data = {
            "street": "Rua Antiga",
            "city": "Velha Cidade",
            "zip_code": "00000000",
            "state": "BA",
        }
        customer.save(address_data=initial_address_data)
        address_original = customer.addresses.first()
        self.assertIsNotNone(address_original)
        original_address_pk = address_original.pk
        updated_address_form_data = {
            "street": "Rua Nova Atualizada",
            "city": "Nova Cidade Atualizada",
            "zip_code": "11111111",
            "state": "MG",
        }
        customer.save(address_data=updated_address_form_data)
        self.assertEqual(customer.addresses.count(), 1)
        address_updated = customer.addresses.first()
        self.assertEqual(address_updated.pk, original_address_pk)
        self.assertEqual(
            address_updated.street.lower(), updated_address_form_data["street"].lower()
        )

    def test_save_customer_deletes_address_when_form_address_data_is_empty_dict(self):
        """Testa deleção de endereço quando `address_data` é um dicionário vazio."""
        customer = Customer.objects.create(**self.customer_pf_data_cpf3)
        customer.save(address_data=self.address_form_data_valid)
        self.assertEqual(customer.addresses.count(), 1)
        customer.save(address_data={})
        self.assertEqual(customer.addresses.count(), 0)

    def test_save_pj_customer_creates_address_from_company_api_if_no_form_data(self):
        """Testa criação de endereço para PJ via API se `address_data` não for fornecido."""
        self.mock_fetch_company.return_value = self.address_api_data_valid.copy()
        customer = Customer(**self.customer_pj_data)
        customer.save()
        self.assertEqual(
            customer.addresses.count(), 1, "Endereço da API deveria ter sido criado."
        )
        address = customer.addresses.first()
        self.assertIsNotNone(address)
        self.assertEqual(
            address.street.lower(), self.address_api_data_valid["street"].lower()
        )
        self.assertEqual(address.zip_code, self.address_api_data_valid["zip_code"])
        self.mock_fetch_company.assert_called_once_with(self.customer_pj_data["tax_id"])

    def test_save_pj_customer_api_returns_no_address_data_does_not_create_address(self):
        """Testa que nenhum endereço é criado para PJ se API não retorna dados de endereço."""
        self.mock_fetch_company.return_value = {
            "full_name": "Empresa API",
            "preferred_name": "Fantasia API",
        }
        customer = Customer.objects.create(**self.customer_pj_data_cnpj2)
        self.assertEqual(customer.addresses.count(), 0)
        self.mock_fetch_company.assert_called_with(
            self.customer_pj_data_cnpj2["tax_id"]
        )

    def test_save_customer_form_data_precedence_over_api_data(self):
        """Testa que dados de endereço do formulário têm precedência sobre os da API."""
        self.mock_fetch_company.return_value = self.address_api_data_valid.copy()
        customer = Customer.objects.create(**self.customer_pj_data)
        customer.save(address_data=self.address_form_data_valid)
        self.assertEqual(customer.addresses.count(), 1)
        address = customer.addresses.first()
        self.assertEqual(
            address.street.lower(), self.address_form_data_valid["street"].lower()
        )

    def test_save_customer_no_change_if_no_form_or_api_address_data(self):
        """Testa que endereço não muda se não houver `address_data` ou dados de endereço da API."""
        customer = Customer.objects.create(**self.customer_pf_data_cpf4)
        customer.save(address_data=self.address_form_data_valid)
        self.assertIsNotNone(customer.addresses.first())
        address_original_pk = customer.addresses.first().pk
        address_original_street = customer.addresses.first().street
        self.mock_fetch_company.return_value = None
        customer.save()
        self.assertEqual(customer.addresses.count(), 1)
        address_apos_save = customer.addresses.first()
        self.assertEqual(address_apos_save.pk, address_original_pk)
        self.assertEqual(address_apos_save.street, address_original_street)

    def test_save_pj_customer_updates_address_from_company_api_if_no_form_data(self):
        """Testa atualização de endereço para PJ via API se `address_data` não for fornecido."""
        customer_data_pj_update_api = self.customer_pj_data.copy()
        customer = Customer.objects.create(**customer_data_pj_update_api)
        initial_address_data = {
            "street": "Rua Antiga da API",
            "city": "Cidade Velha API",
            "zip_code": "99999999",
            "state": "BA",
        }
        customer.save(address_data=initial_address_data)
        original_address = customer.addresses.first()
        self.assertIsNotNone(original_address)
        original_address_pk = original_address.pk
        self.mock_fetch_company.return_value = self.address_api_data_valid.copy()
        customer.save()
        self.assertEqual(
            customer.addresses.count(), 1, "Deveria haver apenas um endereço."
        )
        updated_address = customer.addresses.first()
        self.assertIsNotNone(updated_address)
        self.assertEqual(
            updated_address.pk,
            original_address_pk,
            "O PK do endereço não deveria mudar (update).",
        )
        self.assertEqual(
            updated_address.street.lower(),
            self.address_api_data_valid["street"].lower(),
        )
        self.assertEqual(
            updated_address.city.lower(), self.address_api_data_valid["city"].lower()
        )
        self.assertEqual(
            updated_address.zip_code, self.address_api_data_valid["zip_code"]
        )
        self.assertEqual(updated_address.state, self.address_api_data_valid["state"])
        self.mock_fetch_company.assert_called_with(
            customer_data_pj_update_api["tax_id"]
        )


class CustomerSaveLogicTests(TestCase):
    """Testa lógicas do `save()` do Cliente não relacionadas diretamente a Endereço."""

    def setUp(self):
        """Configura mock para a API de empresa."""
        self.patcher_fetch_company = patch(PATH_FETCH_COMPANY_DATA)
        self.mock_fetch_company = self.patcher_fetch_company.start()
        self.mock_fetch_company.return_value = None

    def tearDown(self):
        """Finaliza o patcher após cada teste."""
        self.patcher_fetch_company.stop()

    def test_save_pj_fetches_company_data_and_updates_names(self):
        """Testa se, para PJ, dados da API atualizam nome e nome fantasia."""
        api_data = {
            "full_name": "Nome Completo da API",
            "preferred_name": "Nome Fantasia da API",
        }
        self.mock_fetch_company.return_value = api_data
        customer_data = {
            "customer_type": "CORP",
            "full_name": "Nome Antigo",
            "tax_id": VALID_CNPJ_FOR_LOGIC_TEST,
        }
        customer = Customer(**customer_data)
        customer.save()
        self.mock_fetch_company.assert_called_once_with(customer_data["tax_id"])
        self.assertEqual(customer.full_name, api_data["full_name"])
        self.assertEqual(customer.preferred_name, api_data["preferred_name"])

    def test_save_pf_does_not_fetch_company_data(self):
        """Testa se, para PF, a API de dados da empresa não é consultada."""
        customer_data = {
            "customer_type": "IND",
            "full_name": "Pessoa Fisica",
            "tax_id": VALID_CPF_FOR_LOGIC_TEST,
        }
        Customer.objects.create(**customer_data)
        self.mock_fetch_company.assert_not_called()


class CustomerAddressTransactionTests(TransactionTestCase):
    """Testa a atomicidade das transações de Cliente e Endereço."""

    @patch(PATH_ADDRESS_UPDATE_OR_CREATE)
    def test_validation_error_in_address_save_rolls_back_customer_creation(
        self, mock_address_update_or_create
    ):
        """Testa se erro ao salvar Endereço impede criação do Cliente (rollback)."""
        mock_address_update_or_create.side_effect = ValidationError(
            "Erro ao salvar endereço!"
        )
        customer_data = {
            "customer_type": "IND",
            "full_name": "Cliente Rollback Criação",
            "tax_id": CPF_TRANS_CREATE_FAIL_VALID,
        }
        address_data = {
            "street": "Rua Teste Rollback",
            "city": "Cidade Rollback",
            "state": "SP",
            "zip_code": "12121212",
        }
        customer_instance = Customer(**customer_data)
        with self.assertRaises(ValidationError):
            customer_instance.save(address_data=address_data)
        self.assertEqual(
            Customer.objects.filter(tax_id=CPF_TRANS_CREATE_FAIL_VALID).count(), 0
        )
        mock_address_update_or_create.assert_called_once()

    @patch(PATH_ADDRESS_UPDATE_OR_CREATE)
    def test_validation_error_in_address_save_rolls_back_customer_update(
        self, mock_address_update_or_create
    ):
        """Testa se erro ao atualizar Endereço reverte alterações no Cliente (rollback)."""
        mock_address_update_or_create.side_effect = ValidationError(
            "Erro ao atualizar endereço!"
        )
        customer = Customer.objects.create(
            customer_type="IND",
            full_name="Cliente Original Update",
            tax_id=CPF_TRANS_UPDATE_FAIL_VALID,
        )
        original_name = customer.full_name
        address_data_update_fail = {
            "street": "Rua Update Falha",
            "city": "Cidade Falha",
            "state": "SP",
            "zip_code": "34343434",
        }
        customer.full_name = "Nome Alterado Tentativa"
        with self.assertRaises(ValidationError):
            customer.save(address_data=address_data_update_fail)
        customer_reloaded = Customer.objects.get(pk=customer.pk)
        self.assertEqual(customer_reloaded.full_name, original_name)
        mock_address_update_or_create.assert_called_once()
