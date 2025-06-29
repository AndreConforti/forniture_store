import os
import sys
import django
import unittest
from django.test import TestCase
from django.db import transaction

# Configuração do caminho
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Configuração do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forniture_store.settings')
django.setup()

# Importações dos modelos
from apps.addresses.models import Address
from apps.customers.models import Customer
from apps.employees.models import Employee
from apps.orders.models import Order, OrderItem
from apps.products.models import Product, Category, Subcategory
from apps.stock.models import Stock, StockMovement
from apps.suppliers.models import Supplier


class OrderStockIntegrationTest(TestCase):
    def setUp(self):
        """Configuração inicial usando dados existentes"""
        self.product = Product.objects.filter(is_active=True).first()
        if not self.product:
            raise unittest.SkipTest("Nenhum produto ativo encontrado no banco de dados")
        
        self.customer = Customer.objects.first()
        if not self.customer:
            raise unittest.SkipTest("Nenhum cliente encontrado no banco de dados")
        
        self.stock, created = Stock.objects.get_or_create(
            product=self.product,
            defaults={'quantity': 15, 'min_quantity': 3}
        )
        
        # Garante que temos um usuário sistema para as movimentações
        self.system_user = User.objects.filter(is_superuser=True).first()
        if not self.system_user:
            self.system_user = User.objects.create_superuser(
                username='system',
                email='system@example.com',
                password='systempass'
            )

    def test_order_confirmation_updates_stock(self):
        """Testa se a confirmação de pedido atualiza o estoque corretamente"""
        print("\n=== Teste de integração de estoque ===")
        print(f"Produto: {self.product.name} (ID: {self.product.id})")
        print(f"Estoque inicial: {self.stock.quantity}")
        print(f"Cliente: {self.customer.full_name}")

        test_quantity = 1
        initial_stock = self.stock.quantity
        
        # Cria e confirma o pedido em uma transação
        with transaction.atomic():
            order = Order.objects.create(
                customer=self.customer,
                status='draft'  # Criamos como rascunho primeiro
            )
            
            OrderItem.objects.create(
                order=order,
                product=self.product,
                quantity=test_quantity,
                unit_price=self.product.sale_price,
                historical_price=self.product.sale_price
            )
            
            # Mudamos explicitamente o status para confirmed
            order.status = 'confirmed'
            order.save()
            print(f"Pedido {order.id} criado e confirmado")

        # Verificações
        self.stock.refresh_from_db()
        order.refresh_from_db()
        
        print("\n=== Resultados ===")
        print(f"Estoque esperado: {initial_stock - test_quantity}")
        print(f"Estoque atual: {self.stock.quantity}")
        print(f"Movimentações criadas: {StockMovement.objects.filter(product=self.product).count()}")
        print(f"Pedido marcado como processado? {order._stock_updated}")

        # Assertions
        self.assertEqual(self.stock.quantity, initial_stock - test_quantity,
                       f"O estoque deveria ter diminuído em {test_quantity} unidade(s)")
        
        self.assertTrue(StockMovement.objects.filter(product=self.product).exists(),
                      "Deveria existir uma movimentação de estoque")
        
        self.assertTrue(order._stock_updated,
                      "O pedido deveria estar marcado como processado no estoque")

if __name__ == '__main__':
    unittest.main()