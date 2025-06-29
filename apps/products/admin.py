from django.contrib import admin
from .models import Category, Subcategory


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('is_active',)


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'category', 'is_active')
    list_filter = ('category', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name', 'abbreviation', 'category__name')
    ordering = ('category__name', 'name')
    raw_id_fields = ('category',)
    
    fieldsets = (
        (None, {
            'fields': ('category', 'abbreviation', 'name', 'is_active')
        }),
        ('Informações Adicionais', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
    )