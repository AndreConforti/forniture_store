document.addEventListener("DOMContentLoaded", function () {
  // Seleciona o botão pelo ID que adicionamos
  const reportButton = document.getElementById("generateReportBtn");

  if (reportButton) {
    // Adiciona um listener para o evento de clique
    reportButton.addEventListener("click", function () {
      // Remove o foco do botão imediatamente após o clique
      // Isso impede que o estilo :focus fique ativo
      this.blur();
    });
  }
});
