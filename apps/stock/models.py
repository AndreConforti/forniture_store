from django.db import models, transaction
from django.db.models import F
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.products.models import Product

User = get_user_model()

class Stock(models.Model):
    """
    Modelo que representa o estoque físico de um produto no sistema.
    
    Atributos:
        product (OneToOneField): Produto relacionado ao estoque
        quantity (PositiveIntegerField): Quantidade atual em estoque
        min_quantity (PositiveIntegerField): Nível mínimo de estoque para alertas
        location (CharField): Localização física no armazém
        last_updated (DateTimeField): Data/hora da última atualização
    """
    product = models.OneToOneField(
        Product,
        verbose_name='Produto',
        on_delete=models.CASCADE,
        related_name='stock',
        help_text="Produto relacionado a este registro de estoque"
    )
    quantity = models.PositiveIntegerField(
        verbose_name='Quantidade Disponível',
        default=0,
        help_text="Quantidade atual disponível em estoque"
    )
    min_quantity = models.PositiveIntegerField(
        verbose_name='Estoque Mínimo',
        default=5,
        help_text="Quantidade mínima para gerar alertas de reposição"
    )
    location = models.CharField(
        verbose_name='Localização no Armazém',
        max_length=50,
        blank=True,
        help_text="Corredor, prateleira ou código de localização"
    )
    last_updated = models.DateTimeField(
        verbose_name='Última Atualização',
        auto_now=True,
        help_text="Data e hora da última atualização do estoque"
    )

    class Meta:
        verbose_name = 'Estoque'
        verbose_name_plural = 'Estoques'
        indexes = [
            models.Index(fields=['product'], name='stock_product_idx'),
        ]
        ordering = ['-last_updated']

    def __str__(self):
        """Representação string do objeto."""
        return f"{self.product.name} | {self.quantity} unidades"



class StockMovement(models.Model):
    """
    Modelo que representa todas as movimentações de estoque no sistema.
    
    Atributos:
        product (ForeignKey): Produto relacionado à movimentação
        movement_type (CharField): Tipo de movimentação (Entrada, Saída, Devolução, etc.)
        quantity (PositiveIntegerField): Quantidade movimentada (sempre positiva)
        reference_id (CharField): Identificador externo para referência (ex: número do pedido)
        user (ForeignKey): Usuário responsável pela movimentação
        notes (TextField): Observações adicionais sobre a movimentação
        is_cancelled (BooleanField): Indica se a movimentação foi cancelada
        cancelled_reason (TextField): Motivo detalhado do cancelamento
        cancelled_by (ForeignKey): Usuário que realizou o cancelamento
        cancelled_at (DateTimeField): Data/hora do cancelamento
        created_at (DateTimeField): Data/hora de criação do registro
        updated_at (DateTimeField): Data/hora da última atualização do registro
    """
    MOVEMENT_TYPE_CHOICES = [
        ('IN', 'Entrada'),
        ('OUT', 'Saída'),
        ('RETURN', 'Devolução'),
        ('ADJUSTMENT', 'Ajuste'),
        ('CANCELLATION', 'Cancelamento')
    ]

    product = models.ForeignKey(
        Product,
        verbose_name='Produto',
        on_delete=models.PROTECT,
        related_name='movements',
        help_text="Produto que foi movimentado no estoque"
    )
    movement_type = models.CharField(
        verbose_name='Tipo de Movimentação',
        max_length=12,
        choices=MOVEMENT_TYPE_CHOICES,
        help_text="Tipo de operação realizada no estoque"
    )
    quantity = models.PositiveIntegerField(
        verbose_name='Quantidade',
        help_text="Quantidade movimentada (valor sempre positivo)"
    )
    reference_id = models.CharField(
        verbose_name='ID de Referência',
        max_length=50,
        blank=True,
        help_text="Identificador externo para rastreamento (ex: número do pedido, NF, etc.)"
    )
    user = models.ForeignKey(
        verbose_name='Responsável',
        to=User,
        on_delete=models.PROTECT,
        help_text="Usuário que registrou a movimentação"
    )
    notes = models.TextField(
        verbose_name='Observações',
        blank=True,
        help_text="Informações adicionais sobre a movimentação"
    )
    is_cancelled = models.BooleanField(
        verbose_name='Cancelado',
        default=False,
        help_text="Indica se esta movimentação foi cancelada"
    )
    cancelled_reason = models.TextField(
        verbose_name='Motivo do Cancelamento',
        blank=True,
        help_text="Descrição detalhada do motivo do cancelamento"
    )
    cancelled_by = models.ForeignKey(
        verbose_name='Cancelado por',
        to=User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cancelled_movements',
        help_text="Usuário que realizou o cancelamento"
    )
    cancelled_at = models.DateTimeField(
        verbose_name='Data de Cancelamento',
        null=True,
        blank=True,
        help_text="Data e hora em que o cancelamento foi realizado"
    )
    created_at = models.DateTimeField(
        verbose_name='Data de Criação',
        auto_now_add=True,
        help_text="Data e hora de criação do registro"
    )
    updated_at = models.DateTimeField(
        verbose_name='Última Atualização',
        auto_now=True,
        help_text="Data e hora da última atualização do registro"
    )

    class Meta:
        verbose_name = 'Movimentação de Estoque'
        verbose_name_plural = 'Movimentações de Estoque'
        app_label = 'stock'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product'], name='movement_product_idx'),
            models.Index(fields=['movement_type'], name='movement_type_idx'),
            models.Index(fields=['is_cancelled'], name='movement_cancelled_idx'),
        ]

    def __str__(self):
        """Representação string do objeto."""
        status = "(CANCELADO)" if self.is_cancelled else ""
        return f"{self.get_movement_type_display()} {status} | {self.product.name} | {self.quantity} unidades"
