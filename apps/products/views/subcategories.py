from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from ..models import Subcategory
from ..forms import SubcategoryForm

class SubcategoryListView(ListView):
    """
    Lista todas as subcategorias ativas.
    Filtra por categoria pai e permite busca por nome ou abreviação.
    """
    model = Subcategory
    template_name = 'products/subcategory_list.html'
    context_object_name = 'subcategories'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('category')
        
        # Filtro por categoria (se fornecido)
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filtro por status (apenas ativas para usuários normais)
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        
        # Filtro de busca
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(abbreviation__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
            
        return queryset.order_by('category__name', 'name')

class SubcategoryCreateView(SuccessMessageMixin, CreateView):
    """
    Cria uma nova subcategoria.
    Valida a unicidade do nome e abreviação dentro da categoria.
    """
    success_message = "Subcategoria criada com sucesso!"
    model = Subcategory
    form_class = SubcategoryForm
    template_name = 'products/subcategory_form.html'
    success_url = reverse_lazy('products:subcategory_list')

    def form_valid(self, form):
        """Garante que a abreviação seja salva em maiúsculas."""
        form.instance.abbreviation = form.instance.abbreviation.upper()
        form.instance.is_active = True
        return super().form_valid(form)

class SubcategoryUpdateView(SuccessMessageMixin, UpdateView):
    """
    Edita uma subcategoria existente.
    Mantém as mesmas validações do CreateView.
    """
    success_message = "Subcategoria atualizada com sucesso!"
    model = Subcategory
    form_class = SubcategoryForm
    template_name = 'products/subcategory_form.html'
    success_url = reverse_lazy('products:subcategory_list')

    def form_valid(self, form):
        form.instance.abbreviation = form.instance.abbreviation.upper()
        return super().form_valid(form)