# reports/urls.py
from django.urls import path
from .views import CustomerReportView, SupplierReportView

app_name = 'reports'

urlpatterns = [
    path('customers/', CustomerReportView.as_view(), name='customer_report'),
    path('suppliers/', SupplierReportView.as_view(), name='supplier_report'),

]