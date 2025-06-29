$(document).ready(function () {
    const supplierTypeSelect = $('.supplier-type-select');
    const taxIdInput = $('#id_tax_id');
    const zipCodeInput = $('#id_zip_code');

    const searchTaxIdButton = $('#search-tax-id');
    const searchZipCodeButton = $('#search-zip-code');

    const stateRegFieldDiv = $('#state-registration-field-div');
    const municipalRegFieldDiv = $('#municipal-registration-field-div');

    function toggleFormControls() {
        const selectedType = supplierTypeSelect.val();

        // Botão de busca CNPJ: habilitado para CORP, desabilitado para IND
        searchTaxIdButton.prop('disabled', selectedType !== 'CORP');

        // Botão de busca CEP: habilitado para IND, desabilitado para CORP (dados de endereço vêm da API CNPJ)
        searchZipCodeButton.prop('disabled', selectedType !== 'IND');

        // Campos fiscais IE/IM: visíveis para CORP, ocultos para IND
        if (selectedType === 'CORP') {
            stateRegFieldDiv.slideDown();
            municipalRegFieldDiv.slideDown();
        } else { 
            stateRegFieldDiv.slideUp();
            municipalRegFieldDiv.slideUp();
        }
    }

    if (supplierTypeSelect.length) {
        toggleFormControls(); // Chama na carga da página
        supplierTypeSelect.on('change', toggleFormControls);
    }

    // Função para buscar CNPJ e preencher o formulário
    if (searchTaxIdButton.length && taxIdInput.length) {
        searchTaxIdButton.click(function () {
            const taxIdValue = taxIdInput.val().replace(/\D/g, '');
            const searchUrl = $(this).data('url'); // Pega a URL do data-attribute

            if (taxIdValue.length !== 14) {
                alert('Informe um CNPJ válido com 14 dígitos.');
                return;
            }
            if (!searchUrl) {
                alert('URL de busca de CNPJ não configurada.');
                return;
            }

            $.ajax({
                url: searchUrl, // Usa a URL do data-attribute
                type: 'GET',
                data: { tax_id: taxIdValue },
                dataType: 'json',
                beforeSend: function() {
                    searchTaxIdButton.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Buscando...');
                },
                success: function (data) {
                    if (data.error) {
                        alert('Erro: ' + data.error);
                    } else {
                        $('#id_full_name').val(data.full_name || '').trigger('change');
                        $('#id_preferred_name').val(data.preferred_name || '').trigger('change');
                        $('#id_state_registration').val(data.state_registration || '').trigger('change');
                        
                        // Preenche endereço apenas se vier da API e o tipo for CORP
                        if (supplierTypeSelect.val() === 'CORP') {
                            if(data.zip_code) $('#id_zip_code').val(data.zip_code.replace(/\D/g, '')).trigger('input'); // Aplica máscara
                            if(data.street) $('#id_street').val(data.street).trigger('change');
                            if(data.number) $('#id_number').val(data.number).trigger('change');
                            if(data.complement) $('#id_complement').val(data.complement).trigger('change');
                            if(data.neighborhood) $('#id_neighborhood').val(data.neighborhood).trigger('change');
                            if(data.city) $('#id_city').val(data.city).trigger('change');
                            if(data.state) $('#id_state').val(data.state).trigger('change'); // Para Select
                        }
                        
                        // Focar em um campo relevante
                        $('#id_contact_person').focus();
                    }
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.error("Erro AJAX CNPJ:", textStatus, errorThrown, jqXHR.responseText);
                    alert('Erro ao buscar dados do CNPJ. Verifique o console.');
                },
                complete: function() {
                     searchTaxIdButton.prop('disabled', supplierTypeSelect.val() !== 'CORP').html('<i class="bi bi-search"></i>');
                }
            });
        });
    }

    // Função para buscar CEP e preencher o formulário (habilitado para Pessoa Física)
    if (searchZipCodeButton.length && zipCodeInput.length) {
        searchZipCodeButton.click(function () {
            const zipCodeValue = zipCodeInput.val().replace(/\D/g, '');
            const searchUrl = $(this).data('url'); // Pega a URL do data-attribute

            if (zipCodeValue.length !== 8) {
                alert('Informe um CEP válido com 8 dígitos.');
                return;
            }
            if (!searchUrl) {
                alert('URL de busca de CEP não configurada.');
                return;
            }

            $.ajax({
                url: searchUrl, // Usa a URL do data-attribute
                type: 'GET',
                data: { zip_code: zipCodeValue },
                dataType: 'json',
                 beforeSend: function() {
                    searchZipCodeButton.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Buscando...');
                },
                success: function (data) {
                    if (data.error) {
                        alert('Erro: ' + data.error);
                    } else {
                        // Preenche endereço se for Pessoa Física (IND)
                        if (supplierTypeSelect.val() === 'IND') {
                            if(data.street) $('#id_street').val(data.street).trigger('change');
                            if(data.neighborhood) $('#id_neighborhood').val(data.neighborhood).trigger('change');
                            if(data.city) $('#id_city').val(data.city).trigger('change');
                            if(data.state) $('#id_state').val(data.state).trigger('change');
                             $('#id_number').focus();
                        }
                    }
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.error("Erro AJAX CEP:", textStatus, errorThrown, jqXHR.responseText);
                    alert('Erro ao buscar dados do CEP. Verifique o console.');
                },
                complete: function() {
                    searchZipCodeButton.prop('disabled', supplierTypeSelect.val() !== 'IND').html('<i class="bi bi-search"></i>');
                }
            });
        });
    }

    // Aplicar máscaras (usando jQuery Mask Plugin como exemplo)
    if (typeof $.fn.mask === 'function') {
        $('#id_zip_code').mask('00000-000');
        $('#id_phone').mask('(00) 00000-0000');

        function applyTaxIdMask() {
            const currentType = supplierTypeSelect.val();
            taxIdInput.unmask(); 
            if (currentType === 'CORP') {
                taxIdInput.mask('00.000.000/0000-00', {reverse: false});
            } else if (currentType === 'IND') {
                taxIdInput.mask('000.000.000-00', {reverse: false});
            }
        }

        if (supplierTypeSelect.length) {
             taxIdInput.on('input', function() { // Limpa se não for número ao digitar
                var value = $(this).val();
                var 숫자만 = value.replace(/[^0-9]/g, "");
                if (supplierTypeSelect.val() === 'CORP' && 숫자만.length > 14) {
                    숫자만 = 숫자만.substring(0, 14);
                } else if (supplierTypeSelect.val() === 'IND' && 숫자만.length > 11) {
                     숫자만 = 숫자만.substring(0, 11);
                }
            });

            supplierTypeSelect.on('change', function() {
                applyTaxIdMask();
            }).trigger('change'); 
        }
    } else {
        console.warn('jQuery Mask Plugin não encontrado. As máscaras não serão aplicadas.');
    }
});