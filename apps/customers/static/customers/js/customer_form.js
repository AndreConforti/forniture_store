// Comportamentos dos botões de busca em CNPJ e CEP de acordo com o tipo de cliente
$(document).ready(function () {
  function toggleSearchButtons() {
    const customerType = $(".customer-type-select").val();
    $("#search-tax-id").prop("disabled", customerType !== "CORP");
    $("#search-zip-code").prop("disabled", customerType !== "IND");
  }

  toggleSearchButtons();
  $(".customer-type-select").change(toggleSearchButtons);

  // Função para buscar CNPJ e preencher o formulário
  $("#search-tax-id").click(function () {
    const taxId = $("#id_tax_id").val().replace(/\D/g, ""); // Remove caracteres especiais

    if (!taxId) {
      alert("Informe um CNPJ válido.");
      return;
    }

    $.ajax({
      url: "/customers/search-cnpj/",
      type: "GET",
      data: { tax_id: taxId },
      dataType: "json",
      success: function (data) {
        if (data.error) {
          alert(data.error);
        } else {
          $("#id_full_name").val(data.full_name);
          $("#id_preferred_name").val(data.preferred_name);
          $("#id_zip_code").val(data.zip_code);
          $("#id_street").val(data.street);
          $("#id_number").val(data.number);
          $("#id_neighborhood").val(data.neighborhood);
          $("#id_city").val(data.city);
          $("#id_state").val(data.state);
        }
      },
      error: function () {
        alert("Erro ao buscar dados do CNPJ. Tente novamente.");
      },
    });
  });

  // Função para buscar CEP e preencher o formulário
  $("#search-zip-code").click(function () {
    const zipCode = $("#id_zip_code").val().replace(/\D/g, "");
    if (!zipCode || zipCode.length < 8) {
      alert("Informe um CEP válido.");
      return;
    }

    $.ajax({
      url: "/customers/search-zip-code/",
      type: "GET",
      data: { zip_code: zipCode },
      dataType: "json",
      success: function (data) {
        if (data.error) {
          alert(data.error);
        } else {
          $("#id_street").val(data.street);
          $("#id_neighborhood").val(data.neighborhood);
          $("#id_city").val(data.city);
          $("#id_state").val(data.state);
        }
      },
      error: function () {
        alert("Erro ao buscar dados do CEP.");
      },
    });
  });
});
