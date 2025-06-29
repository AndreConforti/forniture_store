from django.urls import path
from . import views

app_name = 'showroom'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  
]