from django.contrib import messages
from django.db.models import Q
from django.forms import ValidationError as DjangoFormsValidationError
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Customer
from .forms import CustomerForm
import logging

logger = logging.getLogger(__name__)


class CustomerListView(LoginRequiredMixin, ListView):
    """
    View para listar clientes ativos com funcionalidades de busca e filtragem.

    Exibe uma lista paginada de clientes `is_active=True`.
    Permite busca por nome, e-mail, CPF/CNPJ e filtro por tipo de cliente.
    """

    model = Customer
    template_name = "customers/list.html"
    context_object_name = "customers"
    paginate_by = 10

    def get_queryset(self):
        """
        Constrói e retorna o queryset de clientes para a lista.

        Filtra por `is_active=True`. Aplica filtros adicionais baseados
        nos parâmetros GET `customer_type` e `search`.
        Otimiza com `prefetch_related('addresses')`.
        """
        queryset = super().get_queryset().filter(is_active=True)

        search_term = self.request.GET.get("search", "").strip()
        customer_type_filter = self.request.GET.get("customer_type", "all")

        if customer_type_filter in ["IND", "CORP"]:
            queryset = queryset.filter(customer_type=customer_type_filter)

        if search_term:
            cleaned_search_term_for_tax_id = "".join(filter(str.isdigit, search_term))

            query_conditions = (
                Q(full_name__icontains=search_term)
                | Q(email__icontains=search_term)
                | Q(preferred_name__icontains=search_term)
            )
            if cleaned_search_term_for_tax_id:
                query_conditions |= Q(tax_id__icontains=cleaned_search_term_for_tax_id)

            queryset = queryset.filter(query_conditions)

        return queryset.prefetch_related("addresses")

    def get_context_data(self, **kwargs):
        """
        Adiciona parâmetros de filtro e busca atuais ao contexto do template.
        """
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        context["selected_customer_type"] = self.request.GET.get("customer_type", "all")
        return context


class CustomerCreateView(LoginRequiredMixin, CreateView):
    """
    View para a criação de um novo cliente.

    Usa `CustomerForm`. A lógica de salvamento (cliente, endereço, API)
    é encapsulada no formulário e modelo.
    """

    model = Customer
    form_class = CustomerForm
    template_name = "customers/customer_form.html"
    success_url = reverse_lazy("customers:list")

    def form_valid(self, form) -> HttpResponseRedirect:
        """
        Processa o formulário válido.

        Chama `super().form_valid(form)` (que chama `form.save()`).
        Exibe mensagem de sucesso e redireciona. Trata erros de validação.
        """
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Cliente cadastrado com sucesso!")
            return response
        except DjangoFormsValidationError as e:
            logger.error(
                f"Erro de validação ao criar cliente: {e.message_dict if hasattr(e, 'message_dict') else e}",
                exc_info=True,
            )
            error_messages_list = []
            if hasattr(e, "message_dict"):
                for field_name, error_list in e.message_dict.items():
                    field_label = (
                        form.fields[field_name].label
                        if field_name in form.fields and form.fields[field_name].label
                        else field_name.replace("_", " ").title()
                    )
                    error_messages_list.append(
                        f"{field_label}: {', '.join(error_list)}"
                    )
            if not error_messages_list and hasattr(e, "messages") and e.messages:
                error_messages_list.extend(e.messages)

            user_message = (
                "Erro de validação. Verifique os campos: "
                + "; ".join(error_messages_list)
                if error_messages_list
                else "Erro de validação. Verifique os campos."
            )
            messages.error(self.request, user_message)
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Erro inesperado ao criar cliente: {str(e)}", exc_info=True)
            messages.error(
                self.request, "Ocorreu um erro inesperado ao cadastrar o cliente."
            )
            return self.form_invalid(form)

    def get_context_data(self, **kwargs) -> dict:
        """
        Adiciona dados de contexto para o template do formulário de criação.
        """
        context = super().get_context_data(**kwargs)
        context["form_title"] = "Cadastrar Novo Cliente"
        context["show_cnpj_button_logic"] = True
        context["show_cep_button_logic"] = True
        return context


class CustomerDetailView(LoginRequiredMixin, DetailView):
    """
    View para exibir os detalhes de um cliente específico.
    """

    model = Customer
    template_name = "customers/customer_detail.html"
    context_object_name = "customer"

    def get_context_data(self, **kwargs) -> dict:
        """Adiciona o endereço do cliente ao contexto."""
        context = super().get_context_data(**kwargs)
        customer_object = self.get_object()
        context["address"] = customer_object.address
        return context


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    """
    View para atualizar os dados de um cliente existente.
    """

    model = Customer
    form_class = CustomerForm
    template_name = "customers/customer_form.html"
    success_url = reverse_lazy("customers:list")

    def form_valid(self, form) -> HttpResponseRedirect:
        """
        Processa o formulário válido para atualização.
        """
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Cliente atualizado com sucesso!")
            return response
        except DjangoFormsValidationError as e:
            logger.error(
                f"Erro de validação ao atualizar cliente: {e.message_dict if hasattr(e, 'message_dict') else e}",
                exc_info=True,
            )
            error_messages_list = []
            if hasattr(e, "message_dict"):
                for field_name, error_list in e.message_dict.items():
                    field_label = (
                        form.fields[field_name].label
                        if field_name in form.fields and form.fields[field_name].label
                        else field_name.replace("_", " ").title()
                    )
                    error_messages_list.append(
                        f"{field_label}: {', '.join(error_list)}"
                    )
            if not error_messages_list and hasattr(e, "messages") and e.messages:
                error_messages_list.extend(e.messages)

            user_message = (
                "Erro de validação. Verifique os campos: "
                + "; ".join(error_messages_list)
                if error_messages_list
                else "Erro de validação. Verifique os campos."
            )
            messages.error(self.request, user_message)
            return self.form_invalid(form)
        except Exception as e:
            logger.error(
                f"Erro inesperado ao atualizar cliente: {str(e)}", exc_info=True
            )
            messages.error(
                self.request, "Ocorreu um erro inesperado ao atualizar o cliente."
            )
            return self.form_invalid(form)

    def get_context_data(self, **kwargs) -> dict:
        """
        Adiciona dados de contexto para o template do formulário de edição.
        """
        context = super().get_context_data(**kwargs)
        context["form_title"] = "Editar Cliente"
        context["show_cnpj_button_logic"] = True
        context["show_cep_button_logic"] = True
        return context
