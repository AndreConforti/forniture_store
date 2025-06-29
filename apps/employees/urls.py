from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import custom_login, custom_logout, change_employee_theme


app_name = "employees"

urlpatterns = [
    path("login/", custom_login, name="login"),
    path("logout/", custom_logout, name="logout_page"),
    path("change-theme/", change_employee_theme, name="change_theme"),
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="employees/password_reset_form.html",
            email_template_name="employees/password_reset_email.html",
            subject_template_name="employees/password_reset_subject.txt",
            success_url=reverse_lazy("employees:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="employees/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="employees/password_reset_confirm.html",
            success_url=reverse_lazy("employees:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="employees/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
