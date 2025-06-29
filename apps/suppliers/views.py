# apps/suppliers/views.py
from django.contrib import messages
from django.db.models import Q
from django.forms import ValidationError as DjangoFormsValidationError
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin


from .models import Supplier
from .forms import SupplierForm
import logging

logger = logging.getLogger(__name__)

class SupplierListView(LoginRequiredMixin, ListView):
    """
    View para listar fornecedores ativos com busca e filtragem.
    """
    model = Supplier
    template_name = 'suppliers/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 10

    def get_queryset(self):
        """
        Retorna o queryset de fornecedores filtrado e paginado.
        """
        queryset = super().get_queryset().filter(is_active=True)

        search_term = self.request.GET.get('search', '').strip() # Variável local em inglês
        supplier_type_filter = self.request.GET.get('supplier_type', 'all') # Variável local em inglês

        if supplier_type_filter in ['IND', 'CORP']:
            queryset = queryset.filter(supplier_type=supplier_type_filter)

        if search_term:
            cleaned_search_term_for_tax_id = "".join(filter(str.isdigit, search_term)) # Variável local em inglês
            query_conditions = (
                Q(full_name__icontains=search_term) |
                Q(preferred_name__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(contact_person__icontains=search_term)
            )
            if cleaned_search_term_for_tax_id:
                query_conditions |= Q(tax_id__icontains=cleaned_search_term_for_tax_id)
            
            queryset = queryset.filter(query_conditions)
        
        return queryset.prefetch_related('addresses')

    def get_context_data(self, **kwargs):
        """Adiciona parâmetros de busca e filtro ao contexto."""
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '') # Chave de contexto em inglês
        context['selected_supplier_type'] = self.request.GET.get('supplier_type', 'all') # Chave de contexto em inglês
        return context


class SupplierCreateView(LoginRequiredMixin, CreateView):
    """
    View para criar um novo fornecedor.
    """
    model = Supplier
    form_class = SupplierForm
    template_name = 'suppliers/supplier_form.html'
    success_url = reverse_lazy('suppliers:list')

    def form_valid(self, form) -> HttpResponseRedirect:
        """
        Processa o formulário válido, salvando o fornecedor.
        """
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Fornecedor cadastrado com sucesso!")
            return response
        except DjangoFormsValidationError as e: 
            logger.error(
                f"Erro de validação ao criar fornecedor: {e.message_dict if hasattr(e, 'message_dict') else e}",
                exc_info=True
            )
            error_messages_list = []
            if hasattr(e, 'message_dict'):
                for field_name, error_list in e.message_dict.items(): # Parâmetro local em inglês
                    field_label = form.fields[field_name].label if field_name in form.fields and form.fields[field_name].label else field_name.replace("_", " ").title()
                    error_messages_list.append(f"{field_label}: {', '.join(error_list)}")
            if not error_messages_list and hasattr(e, 'messages') and e.messages: 
                 error_messages_list.extend(e.messages)

            user_message = "Erro de validação. Verifique os campos: " + "; ".join(error_messages_list) if error_messages_list else "Erro de validação. Verifique os campos."
            messages.error(self.request, user_message)
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Erro inesperado ao criar fornecedor: {str(e)}", exc_info=True)
            messages.error(self.request, "Ocorreu um erro inesperado ao cadastrar o fornecedor.")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs) -> dict:
        """Adiciona título e flags de UI ao contexto."""
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Cadastrar Novo Fornecedor" # Chave de contexto em inglês, valor em pt-BR
        context['show_cnpj_button_logic'] = True 
        context['show_cep_button_logic'] = True
        return context


class SupplierDetailView(LoginRequiredMixin, DetailView):
    """
    View para exibir detalhes de um fornecedor.
    """
    model = Supplier
    template_name = 'suppliers/supplier_detail.html'
    context_object_name = 'supplier'

    def get_context_data(self, **kwargs) -> dict:
        """Adiciona o endereço do fornecedor ao contexto."""
        context = super().get_context_data(**kwargs)
        supplier_object = self.get_object() # Variável local em inglês
        context['address'] = supplier_object.address # Chave de contexto em inglês
        return context


class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    """
    View para atualizar um fornecedor existente.
    """
    model = Supplier
    form_class = SupplierForm
    template_name = 'suppliers/supplier_form.html'
    success_url = reverse_lazy('suppliers:list')

    def form_valid(self, form) -> HttpResponseRedirect:
        """
        Processa o formulário válido, salvando as alterações.
        """
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Fornecedor atualizado com sucesso!")
            return response
        except DjangoFormsValidationError as e:
            logger.error(
                f"Erro de validação ao atualizar fornecedor: {e.message_dict if hasattr(e, 'message_dict') else e}",
                exc_info=True
            )
            error_messages_list = []
            if hasattr(e, 'message_dict'):
                for field_name, error_list in e.message_dict.items(): # Parâmetro local em inglês
                    field_label = form.fields[field_name].label if field_name in form.fields and form.fields[field_name].label else field_name.replace("_", " ").title()
                    error_messages_list.append(f"{field_label}: {', '.join(error_list)}")
            if not error_messages_list and hasattr(e, 'messages') and e.messages:
                 error_messages_list.extend(e.messages)
            
            user_message = "Erro de validação. Verifique os campos: " + "; ".join(error_messages_list) if error_messages_list else "Erro de validação. Verifique os campos."
            messages.error(self.request, user_message)
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Erro inesperado ao atualizar fornecedor: {str(e)}", exc_info=True)
            messages.error(self.request, "Ocorreu um erro inesperado ao atualizar o fornecedor.")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs) -> dict:
        """Adiciona título e flags de UI ao contexto."""
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Editar Fornecedor" # Chave de contexto em inglês, valor em pt-BR
        context['show_cnpj_button_logic'] = True 
        context['show_cep_button_logic'] = True  
        return context