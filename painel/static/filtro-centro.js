document.addEventListener("DOMContentLoaded", () => {
  const menu = document.getElementById("filtro-centro");
  if (!menu) return;

  menu.addEventListener("change", () => {
    window.location.href = menu.value;
  });

  const navegacao = performance.getEntriesByType("navigation")[0];
  if (menu.dataset.filtrado === "1" && navegacao && navegacao.type === "reload") {
    window.location.replace(menu.dataset.inicio);
  }
});
