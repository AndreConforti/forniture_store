from django.urls import path
from core.utils import fetch_company_data_view, fetch_address_data_view
from .views import (
    CustomerListView,
    CustomerDetailView,
    CustomerUpdateView,
    CustomerCreateView,
)

app_name = "customers"

urlpatterns = [
    path("", CustomerListView.as_view(), name="list"),
    path("create/", CustomerCreateView.as_view(), name="create"),
    path("<int:pk>/", CustomerDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", CustomerUpdateView.as_view(), name="edit"),
    path("search-cnpj/", fetch_company_data_view, name="search_cnpj"),
    path("search-zip-code/", fetch_address_data_view, name="search_zip_code"),
]
