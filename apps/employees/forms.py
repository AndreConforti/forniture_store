from django.contrib.auth.forms import AuthenticationForm
from django.forms import ValidationError

class EmployeeLoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_active:
            raise ValidationError("Este funcionário está inativo.")