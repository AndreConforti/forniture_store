from django.urls import path
from . import views

app_name = "docs"
urlpatterns = [
    path("", views.tutorial_index_view, name="index"),
    path("authentication/", views.tutorial_authentication_view, name="authentication"),
    path(
        "password-recovery/",
        views.tutorial_password_recovery_view,
        name="password_recovery",
    ),
    path(
        "customers/overview/",
        views.tutorial_customers_overview_view,
        name="customers_overview",
    ),
    path(
        "customers/create/",
        views.tutorial_customers_create_view,
        name="customers_create",
    ),
    path(
        "customers/manage/",
        views.tutorial_customers_manage_view,
        name="customers_manage",
    ),
    path(
        "suppliers/overview/",
        views.tutorial_suppliers_overview_view,
        name="suppliers_overview",
    ),
    path(
        "suppliers/create/",
        views.tutorial_suppliers_create_view,
        name="suppliers_create",
    ),
    path(
        "suppliers/manage/",
        views.tutorial_suppliers_manage_view,
        name="suppliers_manage",
    ),
    path("reports/", views.tutorial_reports_overview_view, name="reports_overview"),
    path("reports/customers/", views.tutorial_reports_customers_view, name="reports_customers"),
    path("reports/suppliers/", views.tutorial_reports_suppliers_view, name="reports_suppliers"),
]
