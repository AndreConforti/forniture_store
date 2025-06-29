from .models import Employee

# Mapeamento manual das classes de tema para cores de preview (fundo, borda).
# Estas cores são usadas para exibir uma amostra visual de cada tema na interface,
# por exemplo, em um seletor de temas. As cores devem corresponder
# de forma representativa às cores principais de cada tema CSS.
THEME_PREVIEW_COLORS = {
    'theme-blue-gray': ('#042345', '#DCDCDC'), 
    'theme-green-gray': ('#01370d', '#a3a3a3'),
    'theme-brown-sand': ('#2f1703', '#F2E8DA'), 
    'theme-purple-gray': ('#2f0a60', '#DCDCDC'), 
}

def theme_processor(request):
    """
    Processador de contexto para disponibilizar informações de tema aos templates.

    Esta função determina o tema CSS ativo para o usuário atual e prepara uma
    lista de temas disponíveis com suas respectivas cores de preview para
    serem usadas, por exemplo, em um seletor de temas na barra de navegação.

    Determinação do Tema Ativo (`active_theme_class`):
    1.  Usa o tema selecionado pelo usuário (`request.user.selected_theme`),
        se o usuário estiver autenticado, tiver o atributo `selected_theme`,
        e este tiver um valor definido.
    2.  Caso contrário, usa o valor padrão definido para o campo `selected_theme`
        no modelo `Employee`.

    Lista de Temas para Navbar (`THEME_CHOICES_FOR_NAVBAR`):
    -   Itera sobre `Employee.THEME_CHOICES`.
    -   Para cada tema, busca as cores de preview em `THEME_PREVIEW_COLORS`.
    -   Se um tema não tiver cores de preview definidas, utiliza cores de fallback
        (cinza claro `#cccccc` para fundo e cinza escuro `#999999` para borda).
    -   Cria uma lista de dicionários, cada um contendo:
        -   `value`: O valor da classe CSS do tema (e.g., 'theme-blue-gray').
        -   `name`: O nome de exibição do tema (e.g., "Azul e Cinza").
        -   `bg_color`: Cor hexadecimal para o fundo do preview.
        -   `border_color`: Cor hexadecimal para a borda do preview.

    Args:
        request: O objeto HttpRequest atual.

    Returns:
        dict: Um dicionário contendo:
            - `active_theme_class` (str): A classe CSS do tema ativo.
            - `THEME_CHOICES_FOR_NAVBAR` (list): Lista de dicionários com
              informações dos temas disponíveis para exibição.
    """
    active_theme_class = Employee._meta.get_field('selected_theme').default

    if request.user.is_authenticated and hasattr(request.user, 'selected_theme'):
        # Verifica se o usuário tem um tema selecionado e se ele não é None/vazio
        if request.user.selected_theme:
            active_theme_class = request.user.selected_theme

    theme_choices_for_navbar_list = []
    default_preview_colors = ('#cccccc', '#999999') 

    for theme_value, display_name in Employee.THEME_CHOICES:
        bg_color, border_color = THEME_PREVIEW_COLORS.get(theme_value, default_preview_colors)
        theme_choices_for_navbar_list.append({
            'value': theme_value,
            'name': display_name,
            'bg_color': bg_color,
            'border_color': border_color,
        })

    return {
        'active_theme_class': active_theme_class,
        'THEME_CHOICES_FOR_NAVBAR': theme_choices_for_navbar_list
    }