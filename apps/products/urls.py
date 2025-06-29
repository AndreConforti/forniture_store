from django.urls import path, include

## Categorias
from .views import (
    CategoryCreateView,
    CategoryListView,
    CategoryUpdateView
)

## Subcategorias
from .views import (
    SubcategoryCreateView,
    SubcategoryListView,
    SubcategoryUpdateView
)

app_name = 'products'

urlpatterns = [
    path('categories/', include([
        path('', CategoryListView.as_view(), name='category_list'),
        path('create/', CategoryCreateView.as_view(), name='category_create'),
        path('update/<int:pk>/', CategoryUpdateView.as_view(), name='category_update'),
    ])),
    path('subcategories/', include([
        path('', SubcategoryListView.as_view(), name='subcategory_list'),
        path('create/', SubcategoryCreateView.as_view(), name='subcategory_create'),
        path('update/<int:pk>/', SubcategoryUpdateView.as_view(), name='subcategory_update'),
    ])),

]