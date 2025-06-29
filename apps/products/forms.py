from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from .models import Category, Subcategory, Product


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['abbreviation', 'name', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.instance.is_active = True  # Define como ativa por padrão

    def clean_abbreviation(self):
        abbreviation = self.cleaned_data['abbreviation'].upper()
        if len(abbreviation) != 3 or not abbreviation.isalpha():
            raise ValidationError('A abreviação deve ter exatamente 3 letras maiúsculas.')
        return abbreviation

    def clean_name(self):
        name = self.cleaned_data['name']
        if Category.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Já existe uma categoria com este nome.')
        return name


class SubcategoryForm(forms.ModelForm):
    class Meta:
        model = Subcategory
        exclude = ['is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_active=True)

    def clean_abbreviation(self):
        abbreviation = self.cleaned_data['abbreviation'].upper()
        category = self.cleaned_data.get('category')
        
        if category and Subcategory.objects.filter(
            category=category,
            abbreviation=abbreviation
        ).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Abreviação já existe nesta categoria.')
        return abbreviation

    def clean_name(self):
        name = self.cleaned_data['name']
        category = self.cleaned_data.get('category')
        
        if category and Subcategory.objects.filter(
            category=category,
            name__iexact=name
        ).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Nome já existe nesta categoria.')
        return name

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.is_active = True
        if commit:
            instance.save()
        return instance


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        
        if self.instance and self.instance.pk:
            self.fields['subcategory'].queryset = Subcategory.objects.filter(
                category=self.instance.category,
                is_active=True
            )
        else:
            self.fields['subcategory'].queryset = Subcategory.objects.none()

    def clean_gtin(self):
        gtin = self.cleaned_data.get('gtin')
        if gtin and Product.objects.filter(gtin=gtin).exclude(pk=self.instance.pk).exists():
            raise ValidationError('GTIN já cadastrado para outro produto.')
        return gtin

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        subcategory = cleaned_data.get('subcategory')
        
        if subcategory and subcategory.category != category:
            raise ValidationError({
                'subcategory': 'Subcategoria não pertence à categoria selecionada.'
            })

        # Valida combinação única
        if all([
            category,
            cleaned_data.get('description'),
            cleaned_data.get('model'),
            cleaned_data.get('brand'),
            cleaned_data.get('color')
        ]):
            filters = {
                'category': category,
                'description__iexact': cleaned_data['description'],
                'model__iexact': cleaned_data['model'],
                'brand__iexact': cleaned_data['brand'],
                'color__iexact': cleaned_data['color']
            }
            
            if self.instance.pk:
                filters['pk__ne'] = self.instance.pk
                
            if Product.objects.filter(**filters).exists():
                raise ValidationError('Já existe um produto com esta combinação.')


class BarcodeLookupForm(forms.Form):
    barcode = forms.CharField(
        label='Código de Barras',
        max_length=14,
        validators=[
            RegexValidator(
                regex=r'^\d{8,14}$',
                message='O código deve conter entre 8 e 14 dígitos.'
            )
        ]
    )

    def clean_barcode(self):
        barcode = self.cleaned_data['barcode']
        if Product.objects.filter(gtin=barcode).exists():
            raise ValidationError('Produto já cadastrado no sistema.')
        return barcode