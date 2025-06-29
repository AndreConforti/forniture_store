from django.urls import path
from core.utils import fetch_company_data_view, fetch_address_data_view
from .views import (
    SupplierListView, 
    SupplierDetailView, 
    SupplierUpdateView,
    SupplierCreateView,
)

app_name = 'suppliers'

urlpatterns = [
    path('', SupplierListView.as_view(), name='list'),
    path('create/', SupplierCreateView.as_view(), name='create'),    
    path('<int:pk>/', SupplierDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', SupplierUpdateView.as_view(), name='edit'),
    path('search-cnpj/', fetch_company_data_view, name='search_cnpj'),
    path('search-zip-code/', fetch_address_data_view, name='search_zip_code'),
]