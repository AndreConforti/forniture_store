from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.customers.models import Customer


@login_required(login_url='/auth/login/')
def dashboard(request):
    customers = Customer.objects.all()      
    return render(request, 'showroom/dashboard.html')