# apps/employees/tests/tests.py

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model, SESSION_KEY
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.core.cache import cache
from unittest.mock import patch
from django.conf import settings # Importar settings

from apps.addresses.models import Address
from ..forms import EmployeeLoginForm
from ..models import Employee

User = get_user_model()

# Helper functions
def create_employee(username, password="testpassword123", **extra_fields):
    """Helper function to create an employee."""
    return User.objects.create_user(username=username, password=password, **extra_fields)

def create_superuser_employee(username, password="superpassword123", **extra_fields):
    """Helper function to create a superuser employee."""
    return User.objects.create_superuser(username=username, password=password, **extra_fields)


class EmployeeModelTests(TestCase):
    """Testes para o modelo Employee."""

    def setUp(self):
        """Configuração inicial antes de cada método de teste."""
        cache.clear()
        self.user_data_dict = {
            'username': 'testemployee_model',
            'email': 'test_model@example.com',
            'first_name': 'TestModel',
            'last_name': 'EmployeeModel'
        }

    def test_create_employee(self):
        """Testa a criação de um funcionário padrão com create_user."""
        user = create_employee(username=self.user_data_dict['username'], email=self.user_data_dict['email'])
        self.assertTrue(User.objects.filter(username=self.user_data_dict['username']).exists())
        self.assertEqual(user.email, self.user_data_dict['email'])
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.selected_theme, 'theme-blue-gray')

    def test_create_superuser_employee(self):
        """Testa a criação de um superusuário funcionário com create_superuser."""
        User.objects.filter(username="superemp_model_unique").delete()
        superuser = create_superuser_employee(username="superemp_model_unique", email="super_model@example.com")
        self.assertTrue(User.objects.filter(username="superemp_model_unique").exists())
        self.assertTrue(superuser.is_active)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertEqual(superuser.selected_theme, 'theme-blue-gray')

    def test_employee_phone_validation_valid(self):
        """Testa a validação do campo de telefone com números válidos."""
        valid_phones = ["+5511987654321", "11987654321", "9876543210"]
        for phone_number in valid_phones:
            with self.subTest(phone=phone_number):
                user = User(
                    username=f'user_phone_v_{"".join(filter(str.isalnum, phone_number))}',
                    password='testpassword',
                    phone=phone_number
                )
                user.full_clean()
                self.assertEqual(user.phone, phone_number)

    def test_employee_phone_validation_invalid(self):
        """Testa a validação do campo de telefone com números inválidos."""
        invalid_phones = ["123", "+55(11)98765-4321", "abcdef", "12345678"]
        for phone_number in invalid_phones:
            with self.subTest(phone=phone_number):
                user = User(
                    username=f'user_phone_inv_{"".join(filter(str.isalnum, phone_number))}',
                    password='testpassword',
                    phone=phone_number
                )
                with self.assertRaises(ValidationError):
                    user.full_clean()

    def test_employee_selected_theme_valid(self):
        """Testa a atribuição de um tema válido."""
        user = create_employee(username="themeuser_val_model")
        valid_theme = Employee.THEME_CHOICES[1][0]
        user.selected_theme = valid_theme
        user.full_clean()
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.selected_theme, valid_theme)

    def test_employee_selected_theme_invalid(self):
        """Testa a atribuição de um tema inválido, esperando ValidationError."""
        user = create_employee(username="themeuser_inval_model")
        user.selected_theme = 'invalid-theme-value'
        with self.assertRaises(ValidationError) as context:
            user.full_clean()
        self.assertIn('selected_theme', context.exception.message_dict)
        error_messages = context.exception.message_dict['selected_theme']
        self.assertTrue(any("not a valid choice" in msg.lower() or "não é uma opção válida" in msg.lower() for msg in error_messages))

    def test_employee_address_property_no_address(self):
        """Testa a propriedade 'address' quando o funcionário não tem endereço."""
        user = create_employee(username="no_address_prop_user_model")
        self.assertIsNone(user.address)

    def test_employee_address_property_with_address(self):
        """Testa a propriedade 'address' quando o funcionário tem um endereço."""
        user = create_employee(username="with_address_prop_user_model")
        address = Address.objects.create(
            street='Rua Teste Prop', number='123', zip_code='12345001',
            city='Cidade Teste Prop', state='SP', neighborhood='Bairro Prop',
            content_object=user
        )
        self.assertEqual(user.address, address)

    @patch('apps.addresses.models.fetch_address_data')
    def test_address_model_save_when_cep_api_returns_none(self, mock_fetch_address_data):
        """Testa Address.save() quando fetch_address_data retorna None."""
        cache.clear()
        mock_fetch_address_data.return_value = None
        owner_user = create_employee(username="owner_cep_api_none_model_addr")
        
        address = Address(
            content_object=owner_user, 
            zip_code='00000000',
            street="", city="", neighborhood="", state=""
        )
        address.save()
        
        mock_fetch_address_data.assert_called_once_with('00000000')
        self.assertEqual(address.zip_code, '00000000')
        self.assertEqual(address.street, "")

    @patch('apps.addresses.models.fetch_address_data')
    def test_employee_save_triggers_completion_for_associated_incomplete_address(self, mock_fetch_address_data):
        """
        Testa se Employee.save() aciona a conclusão de um Address associado
        que está intencionalmente incompleto ANTES do Employee.save().
        """
        employee = create_employee(username="emp_triggers_comp_model_final")
        
        cache.clear()
        mock_fetch_address_data.return_value = None 
        address = Address.objects.create(
            content_object=employee,
            zip_code="11111111",
            street="", city="", neighborhood="", state=""
        )
        mock_fetch_address_data.assert_called_once_with("11111111")
        address.refresh_from_db()
        self.assertEqual(address.street, "")

        mock_fetch_address_data.reset_mock()
        cache.clear()
        
        # CORREÇÃO APLICADA AQUI: Usar um 'state' válido
        final_api_response = {'street':'Rua Final Via Employee', 'neighborhood':'Bairro Final', 'city':'Cidade Final', 'state':'SP'} 
        mock_fetch_address_data.return_value = final_api_response
        
        employee.first_name = "Nome Emp Atualizado Model Triggers Final"
        employee.save()

        address.refresh_from_db()
        
        mock_fetch_address_data.assert_called_once_with("11111111")
        self.assertEqual(address.street, "Rua Final Via Employee")
        self.assertEqual(address.state, "SP") # Verifique o estado corrigido


    @patch('apps.addresses.models.fetch_address_data')
    def test_employee_save_with_manually_filled_address_does_not_call_api(self, mock_fetch_address_data):
        """
        Testa que Employee.save() não chama API de CEP se o endereço associado
        já está completamente preenchido manualmente.
        """
        employee = create_employee(username="emp_manual_addr_filled_model_final")
        Address.objects.create(
            content_object=employee,
            street='Rua Manual Completa', number='789', neighborhood='Bairro Manual Comp',
            city='Cidade Manual Comp', state='SP',
            zip_code='77889900'
        )
        mock_fetch_address_data.assert_not_called()

        employee.last_name = "Sobrenome Emp Atualizado Filled Model Final"
        employee.save()
        
        mock_fetch_address_data.assert_not_called()


class EmployeeLoginFormTests(TestCase):
    """Testes para o EmployeeLoginForm."""

    def setUp(self):
        self.active_user_creds = {'username': 'active_login_form_user', 'password': 'testpassword123'}
        self.active_user = create_employee(email='active_login_form@example.com', is_active=True, **self.active_user_creds)
        
        self.inactive_user_creds = {'username': 'inactive_login_form_user', 'password': 'testpassword123'}
        create_employee(
            username=self.inactive_user_creds['username'],
            password=self.inactive_user_creds['password'],
            email='inactive_login_form@example.com',
            is_active=False
        )
        self.factory = RequestFactory()
        session_engine = __import__(settings.SESSION_ENGINE, fromlist=['SessionStore'])
        self.session = session_engine.SessionStore()

    def test_login_form_valid_active_user(self):
        """Testa o login com um usuário ativo e credenciais válidas."""
        request = self.factory.get(reverse('employees:login'))
        request.session = self.session
        form = EmployeeLoginForm(request=request, data=self.active_user_creds)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors.as_text()}")
        self.assertEqual(form.get_user(), self.active_user)

    def test_login_form_inactive_user_gets_default_auth_error(self):
        """
        Testa que tentar logar com um usuário inativo resulta no erro padrão de autenticação.
        """
        request = self.factory.get(reverse('employees:login'))
        request.session = self.session
        form = EmployeeLoginForm(request=request, data=self.inactive_user_creds)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertTrue(len(form.errors['__all__']) > 0, "Formulário deveria ter non-field errors para usuário inativo.")

    def test_login_form_invalid_credentials(self):
        """Testa o login com credenciais inválidas."""
        form_data = {'username': self.active_user_creds['username'], 'password': 'WrongPassword!'}
        request = self.factory.get(reverse('employees:login'))
        request.session = self.session
        form = EmployeeLoginForm(request=request, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertTrue(len(form.errors['__all__']) > 0, "Formulário deveria ter non-field errors para credenciais inválidas.")


class EmployeeViewsTests(TestCase):
    """Testes para as views do app employees."""

    @classmethod
    def setUpTestData(cls):
        cls.user_creds = {'username': 'viewtest_user_views_final', 'password': 'Password123!'}
        cls.user = create_employee(email='view_test_views_final@example.com', **cls.user_creds)
        
        cls.login_url = reverse('employees:login')
        cls.logout_url = reverse('employees:logout_page')
        cls.change_theme_url = reverse('employees:change_theme')
        
        try:
            cls.dashboard_url = reverse('showroom:dashboard')
            cls.dashboard_target_status_code = 200
        except Exception:
            print("AVISO DE TESTE (EmployeeViewsTests setUpTestData): URL 'showroom:dashboard' não pôde ser revertida. Usando '/' como fallback.")
            cls.dashboard_url = "/"
            cls.dashboard_target_status_code = 200

    def test_custom_login_view_get(self):
        """Testa a view de login com GET."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'employees/custom_login.html')
        self.assertIsInstance(response.context['form'], EmployeeLoginForm)

    def test_custom_login_view_post_success(self):
        """Testa o login bem-sucedido via POST."""
        response = self.client.post(self.login_url, self.user_creds, follow=True)
        self.assertRedirects(response, self.dashboard_url, 
                             status_code=302, 
                             target_status_code=self.dashboard_target_status_code)
        self.assertEqual(str(response.context['user'].pk), str(self.user.pk))
        self.assertTrue(response.context['user'].is_authenticated)

    def test_custom_login_view_post_fail(self):
        """Testa o login malsucedido via POST."""
        wrong_data = {'username': self.user_creds['username'], 'password': 'WrongPassword'}
        response = self.client.post(self.login_url, wrong_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'employees/custom_login.html')
        self.assertFalse(response.context['user'].is_authenticated)
        self.assertTrue(response.context['form'].errors)

    def test_custom_login_view_already_authenticated(self):
        """Testa se um usuário já autenticado é redirecionado da página de login."""
        self.client.login(username=self.user_creds['username'], password=self.user_creds['password'])
        response = self.client.get(self.login_url, follow=True)
        self.assertRedirects(response, self.dashboard_url, 
                             status_code=302, 
                             target_status_code=self.dashboard_target_status_code)

    def test_custom_logout_view_post_for_authenticated_user(self):
        """Testa a view de logout via POST para um usuário autenticado."""
        self.client.login(username=self.user_creds['username'], password=self.user_creds['password'])
        self.assertIn(SESSION_KEY, self.client.session)

        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'employees/custom_logout.html')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_change_employee_theme_post_success(self):
        """Testa a mudança de tema bem-sucedida via POST."""
        self.client.login(username=self.user_creds['username'], password=self.user_creds['password'])
        employee_instance = User.objects.get(username=self.user_creds['username'])
        
        new_theme = Employee.THEME_CHOICES[1][0] 
        self.assertNotEqual(employee_instance.selected_theme, new_theme)

        http_referer = self.dashboard_url 
        response = self.client.post(
            self.change_theme_url, 
            {'selected_theme_value': new_theme},
            HTTP_REFERER=http_referer
        )
        
        self.assertRedirects(response, http_referer)
        employee_instance.refresh_from_db()
        self.assertEqual(employee_instance.selected_theme, new_theme)
        
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(messages_list)
        self.assertEqual(str(messages_list[0]), "Tema atualizado com sucesso!")

    def test_change_employee_theme_post_invalid_theme(self):
        """Testa a tentativa de mudança para um tema inválido via POST."""
        self.client.login(username=self.user_creds['username'], password=self.user_creds['password'])
        employee_instance = User.objects.get(username=self.user_creds['username'])
        original_theme = employee_instance.selected_theme
        invalid_theme = 'nonexistent-theme'
        
        http_referer = self.dashboard_url
        response = self.client.post(
            self.change_theme_url,
            {'selected_theme_value': invalid_theme},
            HTTP_REFERER=http_referer
        )
        
        self.assertRedirects(response, http_referer)
        employee_instance.refresh_from_db()
        self.assertEqual(employee_instance.selected_theme, original_theme)

        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(messages_list)
        self.assertEqual(str(messages_list[0]), "Tema inválido selecionado.")

    def test_change_theme_post_unauthenticated(self):
        """Testa se POST para change_theme por não autenticado redireciona para login."""
        response = self.client.post(self.change_theme_url, {'selected_theme_value': 'theme-green-gray'})
        expected_redirect_url = f"{self.login_url}?next={self.change_theme_url}"
        self.assertRedirects(response, expected_redirect_url)

    def test_logout_view_get_not_allowed(self):
        """Testa se a view de logout não aceita GET."""
        self.client.login(username=self.user_creds['username'], password=self.user_creds['password'])
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 405)

    def test_change_theme_view_get_not_allowed(self):
        """Testa se a view de change_theme não aceita GET."""
        self.client.login(username=self.user_creds['username'], password=self.user_creds['password'])
        response = self.client.get(self.change_theme_url)
        self.assertEqual(response.status_code, 405)