from django.db import models
from django.contrib.auth.models import User


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Vincula ao User do Django
    cpf = models.CharField(max_length=14, unique=True)
    phone = models.CharField(max_length=20)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.get_full_name()
