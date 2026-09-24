function ligarFiltro({ tabela, contagem, campos }) {
  const linhas = Array.from(document.querySelectorAll(`${tabela} tbody tr`));
  const elementos = Object.fromEntries(Object.entries(campos).map(([chave, id]) => [chave, document.getElementById(id)]));
  const saida = document.getElementById(contagem);

  function filtrar() {
    let visiveis = 0;
    for (const linha of linhas) {
      const mostrar = Object.entries(elementos).every(([chave, campo]) => {
        const valor = campo.value.trim().toLowerCase();
        if (!valor) return true;
        return chave === "busca" ? linha.dataset.busca.includes(valor) : linha.dataset[chave].toLowerCase() === valor;
      });
      linha.hidden = !mostrar;
      if (mostrar) visiveis += 1;
    }
    saida.textContent = visiveis;
  }

  Object.values(elementos).forEach((campo) => campo.addEventListener("input", filtrar));
}

document.addEventListener("DOMContentLoaded", () => {
  ligarFiltro({
    tabela: "#tabela-cursos",
    contagem: "contagem",
    campos: { busca: "f-busca", centro: "f-centro", status: "f-status", ativo: "f-ativo", meta: "f-meta" },
  });
  ligarFiltro({
    tabela: "#tabela-percentuais",
    contagem: "contagem-perc",
    campos: { busca: "p-busca", centro: "p-centro" },
  });
});
