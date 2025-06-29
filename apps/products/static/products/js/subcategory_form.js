// Atualiza dinamicamente as subcategorias quando a categoria é alterada
        document.getElementById('id_category').addEventListener('change', function() {
            const categoryId = this.value;
            const subcategorySelect = document.getElementById('id_subcategory');
            
            if (subcategorySelect) {
                // Limpa e desabilita temporariamente
                subcategorySelect.innerHTML = '<option value="">Carregando...</option>';
                subcategorySelect.disabled = true;
                
                // Busca as subcategorias via AJAX
                fetch(`/api/categories/${categoryId}/subcategories/`)
                    .then(response => response.json())
                    .then(data => {
                        subcategorySelect.innerHTML = '';
                        data.forEach(subcategory => {
                            const option = document.createElement('option');
                            option.value = subcategory.id;
                            option.textContent = subcategory.name;
                            subcategorySelect.appendChild(option);
                        });
                        subcategorySelect.disabled = false;
                    });
            }
        });

// Converte automaticamente para maiúsculas
document.getElementById('id_abbreviation').addEventListener('input', function() {
    this.value = this.value.toUpperCase();
});

// Atualiza dinamicamente as subcategorias quando a categoria é alterada
document.addEventListener('DOMContentLoaded', function() {
    const categorySelect = document.getElementById('id_category');
    
    if (categorySelect) {
        categorySelect.addEventListener('change', function() {
            const categoryId = this.value;
            const subcategorySelect = document.getElementById('id_subcategory');
            
            if (subcategorySelect) {
                subcategorySelect.innerHTML = '<option value="">Carregando...</option>';
                subcategorySelect.disabled = true;
                
                fetch(`/api/categories/${categoryId}/subcategories/`)
                    .then(response => response.json())
                    .then(data => {
                        subcategorySelect.innerHTML = '';
                        data.forEach(subcategory => {
                            const option = document.createElement('option');
                            option.value = subcategory.id;
                            option.textContent = subcategory.name;
                            subcategorySelect.appendChild(option);
                        });
                        subcategorySelect.disabled = false;
                    });
            }
        });
    }
});