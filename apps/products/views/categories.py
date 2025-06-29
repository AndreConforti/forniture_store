from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
)
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from ..models import Category
from ..forms import CategoryForm

class CategoryListView(ListView):
    """
    Lista todas as categorias ativas.
    Filtra automaticamente categorias inativas se o usuário não for staff.
    Adiciona filtro de busca por nome, abreviação ou descrição.
    """
    model = Category
    template_name = 'products/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10

    def get_queryset(self):
        # Mostra apenas categorias ativas para usuários normais
        queryset = super().get_queryset().filter(is_active=True)
        
        # Se for staff, mostra todas (ou pode remover para sempre filtrar)
        if self.request.user.is_staff:
            queryset = super().get_queryset()
        
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(abbreviation__icontains=search_query) |
                Q(description__icontains=search_query)
            )
            
        return queryset.order_by('name')

class CategoryCreateView(SuccessMessageMixin, CreateView):
    """
    Cria uma nova categoria.
    Valida a unicidade do nome e abreviação via Form.
    """
    success_message = "Categoria criada com sucesso!"
    model = Category
    form_class = CategoryForm  # Usa o Form com validações customizadas
    template_name = 'products/category_form.html'
    success_url = reverse_lazy('products:category_list')

    def form_valid(self, form):
        """Garante que a abreviação seja salva em maiúsculas."""
        form.instance.abbreviation = form.instance.abbreviation.upper()
        return super().form_valid(form)

class CategoryUpdateView(SuccessMessageMixin, UpdateView):
    """
    Edita uma categoria existente.
    Mantém as mesmas validações do CreateView.
    """
    success_message = "Categoria atualizada com sucesso!"
    model = Category
    form_class = CategoryForm
    template_name = 'products/category_form.html'
    success_url = reverse_lazy('products:category_list')

    def form_valid(self, form):
        form.instance.abbreviation = form.instance.abbreviation.upper()
        return super().form_valid(form)