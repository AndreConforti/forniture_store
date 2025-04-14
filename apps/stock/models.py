from django.db import models
from apps.products.models import Product

class StockManagement(models.Model):
    MOVEMENT_TYPES = [
        ('E', 'Entrada'),
        ('S', 'Saída'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=1, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)