document.addEventListener("DOMContentLoaded", () => {
  const campos = {
    busca: document.getElementById("f-busca"),
    centro: document.getElementById("f-centro"),
    status: document.getElementById("f-status"),
    ativo: document.getElementById("f-ativo"),
    meta: document.getElementById("f-meta"),
  };
  const linhas = Array.from(document.querySelectorAll("#tabela-cursos tbody tr"));
  const contagem = document.getElementById("contagem");

  function filtrar() {
    const termo = campos.busca.value.trim().toLowerCase();
    let visiveis = 0;
    for (const linha of linhas) {
      const d = linha.dataset;
      const mostrar =
        (!termo || d.busca.includes(termo)) &&
        (!campos.centro.value || d.centro === campos.centro.value) &&
        (!campos.status.value || d.status === campos.status.value) &&
        (!campos.ativo.value || d.ativo === campos.ativo.value) &&
        (!campos.meta.value || d.meta === campos.meta.value);
      linha.hidden = !mostrar;
      if (mostrar) visiveis += 1;
    }
    contagem.textContent = visiveis;
  }

  Object.values(campos).forEach((campo) => campo.addEventListener("input", filtrar));
});
