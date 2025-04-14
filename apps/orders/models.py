from django.db import models
from apps.customers.models import Customer
from apps.products.models import Product


class Order(models.Model):
    STATUS_CHOICES = [
        ('P', 'Pendente'),
        ('A', 'Aprovado'),
        ('C', 'Cancelado'),
        ('F', 'Finalizado'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)


class Payment(models.Model):
    PAYMENT_METHODS = [
        ('CASH', 'Dinheiro'),
        ('CARDC', 'Cartão Crédito'),
        ('CARDD', 'Cartão Débito'),
        ('PIX', 'PIX'),
        ('OTHER', 'Outro'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    paid_at = models.DateTimeField(auto_now_add=True)
    transaction_code = models.CharField(max_length=100, blank=True)  # Para comprovantes

    def __str__(self):
        return f"Pagamento #{self.id} - {self.get_method_display()}"