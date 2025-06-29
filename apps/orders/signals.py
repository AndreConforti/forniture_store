from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.core.exceptions import ValidationError
import logging
from .models import Order
from apps.stock.models import Stock, StockMovement
from apps.employees.models import Employee 

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Order)
def update_stock_on_order_confirmation(sender, instance, created, **kwargs):
    """
    Signal atualizado para funcionar melhor no admin
    """
    # Verifica se é um pedido confirmado e se o estoque ainda não foi atualizado
    if instance.status == 'confirmed' and not instance._stock_updated:
        try:
            with transaction.atomic():
                # Obtém o usuário sistema
                system_user = Employee.get_system_user()  
                if not system_user:
                    logger.error("Usuário sistema não configurado")
                    return
                
                # Processa cada item do pedido
                for item in instance.items.all():
                    try:
                        stock = Stock.objects.select_for_update().get(product=item.product)
                        
                        if stock.quantity < item.quantity:
                            logger.error(f"Estoque insuficiente para {item.product.name}")
                            raise ValidationError(
                                f"Estoque insuficiente: {item.product.name}. "
                                f"Disponível: {stock.quantity}, Necessário: {item.quantity}"
                            )
                        
                        # Atualiza o estoque
                        stock.quantity -= item.quantity
                        stock.save()
                        
                        # Registra a movimentação
                        StockMovement.objects.create(
                            product=item.product,
                            movement_type='OUT',
                            quantity=item.quantity,
                            reference_id=f"ORDER-{instance.id}",
                            user=system_user,  
                            notes=f"Baixa automática para pedido #{instance.id}"
                        )
                    
                    except Stock.DoesNotExist:
                        logger.error(f"Produto {item.product.name} sem registro de estoque")
                        raise ValidationError(f"Produto {item.product.name} não encontrado no estoque")
                
                # Marca o pedido como processado
                instance._stock_updated = True
                instance.save(update_fields=['_stock_updated'])
                
        except Exception as e:
            logger.error(f"Erro ao atualizar estoque: {str(e)}")
            raise