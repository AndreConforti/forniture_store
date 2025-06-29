from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.customers.models import Customer
from apps.addresses.models import Address
from django.contrib.contenttypes.models import ContentType
from unittest.mock import patch

PATH_FETCH_COMPANY_DATA = "apps.customers.models.fetch_company_data"

# =======================================================================
#  CPFs/CNPJs Válidos para Teste
# =======================================================================
CPF_VALID_1 = "10585278008"
CPF_VALID_2 = "27875969832"
CPF_VALID_FOR_PROP_TEST_1 = "75723268031"
CPF_VALID_FOR_PROP_TEST_2 = "44557172008"
CPF_VALID_FOR_PROP_TEST_3 = "66654096002"
CPF_VALID_FOR_PROP_TEST_4 = "98238392047"

CNPJ_VALID_1 = "20612379000106"
# =======================================================================


class CustomerModelValidationTests(TestCase):
    """Testa validações e o método `clean()` do modelo Cliente."""

    def test_create_individual_customer_valid(self):
        """Testa a criação bem-sucedida de um cliente Pessoa Física."""
        customer = Customer(
            customer_type="IND",
            full_name="João da Silva",
            tax_id=CPF_VALID_1,
            phone="11987654321",
            email="joao.silva@example.com",
        )
        customer.full_clean()
        customer.save()
        self.assertIsNotNone(customer.pk)
        self.assertEqual(customer.tax_id, CPF_VALID_1)
        self.assertEqual(customer.addresses.count(), 0)

    def test_create_corporate_customer_valid(self):
        """Testa a criação bem-sucedida de um cliente Pessoa Jurídica."""
        with patch(PATH_FETCH_COMPANY_DATA) as mock_fetch:
            mock_fetch.return_value = None
            customer = Customer(
                customer_type="CORP",
                full_name="Empresa Alpha Ltda",
                tax_id=CNPJ_VALID_1,
                phone="2134567890",
                email="contato@empresaalpha.com",
            )
            customer.full_clean()
            customer.save()
            self.assertIsNotNone(customer.pk)
            self.assertEqual(customer.tax_id, CNPJ_VALID_1)
            self.assertEqual(customer.addresses.count(), 0)

    def test_create_customer_invalid_cpf(self):
        """Testa a falha na criação de cliente PF com CPF inválido."""
        customer = Customer(
            customer_type="IND", full_name="Inválido", tax_id="11111111111"
        )
        with self.assertRaises(ValidationError) as cm:
            customer.full_clean()
        self.assertIn("tax_id", cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict["tax_id"][0], "CPF inválido!")

    def test_create_customer_invalid_cnpj(self):
        """Testa a falha na criação de cliente PJ com CNPJ inválido."""
        with patch(PATH_FETCH_COMPANY_DATA, return_value=None):
            customer = Customer(
                customer_type="CORP", full_name="Inválida Corp", tax_id="11111111111111"
            )
            with self.assertRaises(ValidationError) as cm:
                customer.full_clean()
            self.assertIn("tax_id", cm.exception.message_dict)
            self.assertEqual(cm.exception.message_dict["tax_id"][0], "CNPJ inválido!")

    def test_create_customer_tax_id_missing(self):
        """Testa a falha na criação de cliente sem CPF/CNPJ."""
        customer = Customer(customer_type="IND", full_name="Cliente Sem Doc")
        with self.assertRaises(ValidationError) as cm:
            customer.full_clean()
        self.assertIn("tax_id", cm.exception.message_dict)
        self.assertIn(
            "Este campo não pode estar vazio.", cm.exception.message_dict["tax_id"][0]
        )

    def test_clean_tax_id_with_formatting(self):
        """Testa se o método `clean` remove a formatação do CPF/CNPJ."""
        cpf_formatted = (
            f"{CPF_VALID_1[:3]}.{CPF_VALID_1[3:6]}.{CPF_VALID_1[6:9]}-{CPF_VALID_1[9:]}"
        )
        customer_cpf = Customer(
            customer_type="IND", full_name="Teste CPF Formatado", tax_id=cpf_formatted
        )
        customer_cpf.full_clean()
        self.assertEqual(customer_cpf.tax_id, CPF_VALID_1)

        cnpj_formatted = f"{CNPJ_VALID_1[:2]}.{CNPJ_VALID_1[2:5]}.{CNPJ_VALID_1[5:8]}/{CNPJ_VALID_1[8:12]}-{CNPJ_VALID_1[12:]}"
        customer_cnpj = Customer(
            customer_type="CORP",
            full_name="Teste CNPJ Formatado",
            tax_id=cnpj_formatted,
        )
        customer_cnpj.full_clean()
        self.assertEqual(customer_cnpj.tax_id, CNPJ_VALID_1)

    def test_clean_phone_method_removes_formatting(self):
        """Testa se o método `_clean_phone` remove a formatação do telefone."""
        customer = Customer(phone="(11) 98877-6655")
        customer._clean_phone()  # Testa o método diretamente
        self.assertEqual(customer.phone, "11988776655")

    def test_full_clean_with_valid_cleaned_phone(self):
        """Testa se `full_clean` passa com um telefone já limpo e válido."""
        customer_valid_phone = Customer(
            customer_type="IND",
            full_name="Teste Phone Valido",
            tax_id=CPF_VALID_1,
            phone="11988776655",
        )
        customer_valid_phone.full_clean()
        self.assertEqual(customer_valid_phone.phone, "11988776655")

    def test_full_clean_rejects_uncleaned_long_phone(self):
        """Testa se `full_clean` rejeita telefone formatado que excede `max_length`."""
        customer = Customer(
            customer_type="IND",
            full_name="Teste Phone Longo",
            tax_id=CPF_VALID_2,
            phone="(11) 98877-6655",
        )
        with self.assertRaises(ValidationError) as cm:
            customer.full_clean()
        self.assertIn("phone", cm.exception.message_dict)
        self.assertTrue(
            any(
                "máximo 11 caracteres" in msg
                for msg in cm.exception.message_dict["phone"]
            )
            or any(
                "Telefone deve ter 10 ou 11 dígitos" in msg
                for msg in cm.exception.message_dict["phone"]
            )
        )

    def test_full_clean_with_no_phone(self):
        """Testa se `full_clean` funciona corretamente quando o telefone é `None`."""
        customer_no_phone = Customer(
            customer_type="IND",
            full_name="Teste Sem Phone",
            tax_id=CPF_VALID_1,
            phone=None,
        )
        customer_no_phone.full_clean()
        self.assertIsNone(customer_no_phone.phone)


class CustomerModelPropertyTests(TestCase):
    """Testa as propriedades computadas do modelo Cliente."""

    @classmethod
    def setUpTestData(cls):
        """Configura clientes para teste das propriedades."""
        cls.customer_no_pref = Customer.objects.create(
            customer_type="IND",
            full_name="Fulano de Tal Completo",
            tax_id=CPF_VALID_FOR_PROP_TEST_1,
        )
        cls.customer_with_pref = Customer.objects.create(
            customer_type="IND",
            full_name="Ciclano de Algo Completo",
            preferred_name="Cicla",
            tax_id=CPF_VALID_FOR_PROP_TEST_2,
        )
        cls.customer_with_address = Customer.objects.create(
            customer_type="IND",
            full_name="Beltrano Com Endereço",
            tax_id=CPF_VALID_FOR_PROP_TEST_3,
        )
        Address.objects.create(
            street="Rua Principal Prop",
            city="Cidade Prop",
            state="SP",
            zip_code="12345000",
            content_object=cls.customer_with_address,
        )
        Address.objects.create(
            street="Rua Secundaria Prop",
            city="Cidade Prop",
            state="SP",
            zip_code="12345001",
            content_object=cls.customer_with_address,
        )

    def test_display_name_property(self):
        """Testa a lógica de exibição do nome do cliente."""
        self.assertEqual(self.customer_no_pref.display_name, "Fulano de Tal Completo")
        self.assertEqual(self.customer_with_pref.display_name, "Cicla")

    def test_formatted_phone_property(self):
        """Testa a formatação do telefone para diferentes entradas."""
        c1 = Customer(phone="11987654321")
        self.assertEqual(c1.formatted_phone, "(11) 98765-4321")
        c2 = Customer(phone="2134567890")
        self.assertEqual(c2.formatted_phone, "(21) 3456-7890")
        c3 = Customer(phone="12345")
        self.assertEqual(c3.formatted_phone, "12345")
        c4 = Customer(phone=None)
        self.assertEqual(c4.formatted_phone, "")
        c5 = Customer(phone="")
        self.assertEqual(c5.formatted_phone, "")

    def test_formatted_tax_id_property(self):
        """Testa a formatação do CPF/CNPJ."""
        cpf_customer = Customer(tax_id="12345678901")
        self.assertEqual(cpf_customer.formatted_tax_id, "123.456.789-01")
        cnpj_customer = Customer(tax_id="12345678000199")
        self.assertEqual(cnpj_customer.formatted_tax_id, "12.345.678/0001-99")
        invalid_customer = Customer(tax_id="12345")
        self.assertEqual(invalid_customer.formatted_tax_id, "12345")
        none_tax_id_customer = Customer()
        none_tax_id_customer.tax_id = None
        self.assertEqual(none_tax_id_customer.formatted_tax_id, "")

    def test_address_property(self):
        """Testa o acesso ao primeiro endereço associado ou `None`."""
        self.assertIsNotNone(self.customer_with_address.address)
        self.assertEqual(
            self.customer_with_address.address.street, "Rua Principal Prop"
        )

        customer_no_address = Customer.objects.create(
            customer_type="IND",
            full_name="Sem Endereço",
            tax_id=CPF_VALID_FOR_PROP_TEST_4,
        )
        self.assertIsNone(customer_no_address.address)
