import os, sys
import django
from django.core.exceptions import ValidationError

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

from pprint import pprint
import logging
logging.basicConfig(level=logging.DEBUG)

def test_supplier_creation(cnpj, cep=None, numero=None):
    print("\n" + "="*50)
    print(f"INICIANDO TESTE PARA CNPJ: {cnpj}")
    print("="*50 + "\n")
    
    try:
        # Passo 1: Criar instância básica
        print("[1/5] Criando objeto Supplier...")
        supplier = Supplier(
            document_type='CNPJ',
            document=cnpj,
            phone='1633334444'
        )
        
        # Passo 2: Validar antes de criar relacionamento
        print("\n[2/5] Executando validação (supplier.clean())...")
        supplier.full_clean()
        
        # Passo 3: Salvar o supplier para ter um ID
        print("\n[3/5] Salvando Supplier no banco...")
        supplier.save()
        
        # Passo 4: Criar address se CEP foi fornecido
        address = None
        if cep:
            print(f"\n[4/5] Criando Address com CEP: {cep}")
            address = Address(
                content_object=supplier,
                zip_code=cep,
                number=numero or 'SN'
            )
            address.full_clean()
            address.save()
        
        # Passo 5: Mostrar resultados
        print("\n[5/5] DADOS COLETADOS:")
        print("Supplier:")
        pprint({
            'id': supplier.id,
            'document': supplier.document,
            'legal_name': supplier.legal_name,
            'trade_name': supplier.trade_name,
            'email': supplier.email,
            'phone': supplier.phone
        })
        
        if address:
            print("\nAddress:")
            pprint({
                'id': address.id,
                'zip_code': address.zip_code,
                'street': address.street,
                'number': address.number,
                'complement': address.complement,
                'neighborhood': address.neighborhood,
                'city': address.city,
                'state': address.state,
                'is_complete': address.is_complete
            })
        
        print("\n✅ TESTE CONCLUÍDO COM SUCESSO!")
        return supplier
        
    except Exception as e:
        print("\n❌ FALHA NO TESTE:")
        print(f"ERRO: {type(e).__name__}: {str(e)}")
        if hasattr(e, 'message_dict'):
            print("Detalhes:", e.message_dict)
        return None

if __name__ == '__main__':
    # Limpar dados de teste anteriores
    Supplier.objects.all().delete()
    Address.objects.all().delete()
    
    # CNPJs reais para teste (fonte: https://www.4devs.com.br/gerador_de_cnpj)
    TEST_CNPJS = [
        '33014556000196',  # Magazine Luiza
        '60701190000104',  # Bradesco
        '15185690000130'   # Vale
    ]

    # Teste 1: CNPJ válido sem CEP
    print("\n" + "="*30 + " TESTE 1 - Sem CEP " + "="*30)
    test_supplier_creation(cnpj=TEST_CNPJS[0])
    
    # Teste 2: CNPJ válido com CEP
    print("\n" + "="*30 + " TESTE 2 - Com CEP " + "="*30)
    test_supplier_creation(
        cnpj=TEST_CNPJS[1],  # CNPJ diferente!
        cep='01311000',      # CEP da Av. Paulista
        numero='100'
    )
    
    # Teste 3: CNPJ inválido
    print("\n" + "="*30 + " TESTE 3 - CNPJ Inválido " + "="*30)
    test_supplier_creation(cnpj='12345678901234')
    
    # Teste 4: CNPJ válido com CEP inválido
    print("\n" + "="*30 + " TESTE 4 - CEP Inválido " + "="*30)
    test_supplier_creation(
        cnpj=TEST_CNPJS[2],
        cep='00000000',  # CEP inexistente
        numero='200'
    )