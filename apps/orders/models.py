from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.db.models import F
from apps.customers.models import Customer
from apps.products.models import Product
from apps.stock.models import StockMovement, Stock
from decimal import Decimal, InvalidOperation

User = get_user_model()

class Order(models.Model):
    """
    Modelo de pedido com gestão robusta de estoque e transições de status
    """
    
    STATUS_CHOICES = [
        ('draft', 'Rascunho'),
        ('confirmed', 'Confirmado'),
        ('processing', 'Processando'),
        ('shipped', 'Enviado'),
        ('delivered', 'Entregue'),
        ('cancelled', 'Cancelado'),
        ('returned', 'Devolvido'),
    ]

    # Relacionamentos
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Cliente'
    )

    # Status e datas
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Status'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criação')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última Atualização')

    # Valores financeiros
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Subtotal'
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Desconto Global'
    )
    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Taxas'
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Total'
    )
    _stock_updated = models.BooleanField(
        default=False,
        editable=False,
        verbose_name='Estoque atualizado',
        help_text="Indica se o estoque foi atualizado para este pedido"
    )

    # Motivos de alteração de status
    cancellation_reason = models.TextField(blank=True, verbose_name='Motivo do Cancelamento')
    return_reason = models.TextField(blank=True, verbose_name='Motivo da Devolução')

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status'], name='order_status_idx'),
            models.Index(fields=['created_at'], name='order_created_idx'),
        ]

    def __str__(self):
        return f"Pedido #{self.id} - {self.get_status_display()}"


class OrderItem(models.Model):
    """
    Itens do pedido com histórico de preços
    """
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Pedido'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name='Produto'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='Quantidade'
    )
    
    # Preços
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Preço Unitário'
    )
    historical_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Preço Congelado',
        editable=False
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Desconto'
    )


    class Meta:
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'
        constraints = [
            models.CheckConstraint(
                check=models.Q(discount__lte=models.F('historical_price') * models.F('quantity')),
                name='discount_lte_total'
            )
        ]

    def __str__(self):
        return f"{self.quantity}x {self.product.name} (Pedido #{self.order.id})"

    def save(self, *args, **kwargs):
        if not self.historical_price:  # Se não tiver preço histórico
            self.historical_price = self.unit_price or self.product.sale_price
        super().save(*args, **kwargs)