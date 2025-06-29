from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from .forms import EmployeeLoginForm
from .models import Employee


@require_http_methods(["GET", "POST"])
def custom_login(request):
    """
    View para autenticação de funcionários (login).

    Permite que os usuários façam login no sistema utilizando o `EmployeeLoginForm`.
    - Se o usuário já estiver autenticado, redireciona para o dashboard.
    - Para requisições GET, exibe um formulário de login vazio.
    - Para requisições POST:
        - Valida os dados do formulário.
        - Se válido, autentica o usuário, realiza o login e redireciona
          para o dashboard.
        - Se inválido, o formulário é renderizado novamente na página de login,
          exibindo os erros de validação (e.g., usuário ou senha incorretos).

    Args:
        request: O objeto HttpRequest.

    Returns:
        HttpResponse: Renderiza o template de login ou redireciona
                      após login bem-sucedido.
    """
    if request.user.is_authenticated:
        return redirect("showroom:dashboard")

    if request.method == "POST":
        form = EmployeeLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("showroom:dashboard")
        # Se o formulário não for válido, ele será passado para o template
        # com os erros para serem exibidos.
    else:
        form = EmployeeLoginForm()

    return render(request, "employees/custom_login.html", {"form": form})


@require_POST
@login_required
def custom_logout(request):
    """
    View para deslogar um funcionário autenticado (logout).

    Esta view requer que o usuário esteja autenticado (`@login_required`)
    e que a requisição seja do tipo POST (`@require_POST`) por questões
    de segurança, prevenindo logout acidental via GET.

    Após o logout, renderiza uma página de confirmação de logout.

    Args:
        request: O objeto HttpRequest.

    Returns:
        HttpResponse: Renderiza o template de confirmação de logout.
    """
    auth_logout(request)
    # Idealmente, adicionar uma mensagem de sucesso aqui, se desejado.
    # messages.success(request, "Você foi desconectado com sucesso.")
    return render(request, "employees/custom_logout.html")


@login_required
@require_POST
def change_employee_theme(request):
    """
    View para alterar o tema visual preferido do funcionário autenticado.

    Esta view requer que o usuário esteja autenticado (`@login_required`)
    e que a requisição seja do tipo POST (`@require_POST`).
    O valor do tema selecionado é obtido do `request.POST`.

    Processo:
    1.  Obtém o valor do tema do `request.POST`.
    2.  Valida se o tema recebido é uma das opções válidas definidas
        em `Employee.THEME_CHOICES`.
    3.  Se o tema for válido e o usuário logado (`request.user`) for uma
        instância do modelo `Employee`:
        - Atualiza o campo `selected_theme` do funcionário.
        - Salva a alteração no banco de dados, atualizando apenas o campo
          `selected_theme` para otimização.
    4.  Se o tema for inválido ou o usuário não for um `Employee`, uma
        mensagem de erro é exibida.
    5.  Redireciona o usuário para a página de origem da requisição
        (`HTTP_REFERER`) ou para o dashboard como fallback.

    Args:
        request: O objeto HttpRequest.

    Returns:
        HttpResponseRedirect: Redireciona para a página anterior ou dashboard.
    """
    theme_value = request.POST.get("selected_theme_value")
    valid_theme_values = [choice[0] for choice in Employee.THEME_CHOICES]

    if theme_value in valid_theme_values:
        employee = request.user
        # Garante que estamos tratando com uma instância do nosso modelo Employee
        if isinstance(employee, Employee):
            employee.selected_theme = theme_value
            employee.save(update_fields=["selected_theme"])
            messages.success(request, "Tema atualizado com sucesso!")
        else:
            messages.error(
                request, "Não foi possível atualizar o tema para este tipo de usuário."
            )
    else:
        messages.error(request, "Tema inválido selecionado.")

    return redirect(request.META.get("HTTP_REFERER", "showroom:dashboard"))
