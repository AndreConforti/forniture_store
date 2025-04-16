from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
import requests
from django.core.cache import cache

class Address(models.Model):
    # Tipos de endereço
    TYPE_CHOICES = [
        ('COMERCIAL', 'Comercial'),
        ('RESIDENCIAL', 'Residencial'),
        ('COBRANCA', 'Cobrança'),
        ('ENTREGA', 'Entrega'),
        ('RECADO', 'Recado'),
        ('OUTRO', 'Outro'),
    ]
    
    # Campos do endereço
    street = models.CharField('Logradouro', max_length=100, blank=True)
    number = models.CharField('Número', max_length=10, blank=True)
    complement = models.CharField('Complemento', max_length=50, blank=True)
    neighborhood = models.CharField('Bairro', max_length=50, blank=True)
    city = models.CharField('Cidade', max_length=50, blank=True)
    state = models.CharField('Estado', max_length=2, blank=True)
    zip_code = models.CharField('CEP', max_length=10, blank=True)
    country = models.CharField('País', max_length=50, default='Brasil')
    
    # Tipo de endereço
    address_type = models.CharField(
        'Tipo de Endereço',
        max_length=20,
        choices=TYPE_CHOICES,
        default='COMERCIAL'
    )
    
    # Relacionamento genérico
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Metadados
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    is_primary = models.BooleanField('Endereço principal', default=False)
    is_active = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Endereço'
        verbose_name_plural = 'Endereços'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['zip_code']),
            models.Index(fields=['city']),
            models.Index(fields=['state']),
            models.Index(fields=['address_type']),
        ]
        unique_together = ['content_type', 'object_id', 'is_primary']
        ordering = ['-is_primary', 'address_type']

    def __str__(self):
        return f"{self.get_address_type_display()}: {self.street}, {self.number} - {self.city}/{self.state}"

    def clean(self):
        """Validação avançada do endereço"""
        # Validação do CEP
        if self.zip_code:
            self.zip_code = ''.join(filter(str.isdigit, self.zip_code))
            if len(self.zip_code) != 8:
                raise ValidationError({'zip_code': 'CEP deve conter 8 dígitos'})
        
        # Validação de endereço principal
        if self.is_primary:
            qs = Address.objects.filter(
                content_type=self.content_type,
                object_id=self.object_id,
                is_primary=True
            ).exclude(pk=self.pk)
            
            if qs.exists():
                raise ValidationError('Já existe um endereço principal para este objeto')

    def save(self, *args, **kwargs):
        """Garante que só há um endereço principal"""
        if self.is_primary:
            # Remove a flag de principal de outros endereços
            Address.objects.filter(
                content_type=self.content_type,
                object_id=self.object_id,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    def fill_from_cep(self):
        """Preenchimento automático via API de CEP com fallback"""
        if not self.zip_code or len(self.zip_code) != 8:
            return False

        cache_key = f'cep_{self.zip_code}'
        cep_data = cache.get(cache_key)
        
        if not cep_data:
            # Tenta ViaCEP primeiro
            cep_data = self._fetch_via_cep()
            
            # Fallback para outras APIs
            if not cep_data:
                cep_data = self._fetch_apicep()
            
            if cep_data:
                cache.set(cache_key, cep_data, 86400)  # Cache por 24h

        if cep_data:
            for field, value in cep_data.items():
                if value and not getattr(self, field):
                    setattr(self, field, value)
            return True
        
        return False

    def _fetch_via_cep(self):
        """Implementação da consulta à API ViaCEP"""
        try:
            response = requests.get(f'https://viacep.com.br/ws/{self.zip_code}/json/', timeout=2)
            if response.status_code == 200:
                data = response.json()
                if not data.get('erro'):
                    return {
                        'street': data.get('logradouro', ''),
                        'neighborhood': data.get('bairro', ''),
                        'city': data.get('localidade', ''),
                        'state': data.get('uf', ''),
                    }
        except requests.RequestException:
            pass
        return None

    def _fetch_apicep(self):
        """Implementação da consulta à API CEP"""
        try:
            formatted_cep = f"{self.zip_code[:5]}-{self.zip_code[5:]}"
            response = requests.get(f'https://cdn.apicep.com/file/apicep/{formatted_cep}.json', timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 200:
                    return {
                        'street': data.get('address', ''),
                        'neighborhood': data.get('district', ''),
                        'city': data.get('city', ''),
                        'state': data.get('state', ''),
                    }
        except requests.RequestException:
            pass
        return None

    @classmethod
    def get_for_object(cls, obj, address_type=None):
        """Retorna endereços associados a um objeto, filtrados por tipo se fornecido"""
        content_type = ContentType.objects.get_for_model(obj)
        queryset = cls.objects.filter(
            content_type=content_type,
            object_id=obj.pk,
            is_active=True
        )
        if address_type:
            queryset = queryset.filter(address_type=address_type)
        return queryset

    @classmethod
    def get_primary_for_object(cls, obj):
        """Retorna o endereço principal de um objeto"""
        content_type = ContentType.objects.get_for_model(obj)
        return cls.objects.filter(
            content_type=content_type,
            object_id=obj.pk,
            is_primary=True,
            is_active=True
        ).first()

    @classmethod
    def get_delivery_address_for_object(cls, obj):
        """Retorna o endereço de entrega de um objeto"""
        return cls.get_for_object(obj, address_type='ENTREGA').first()

    @classmethod
    def get_billing_address_for_object(cls, obj):
        """Retorna o endereço de cobrança de um objeto"""
        return cls.get_for_object(obj, address_type='COBRANCA').first()