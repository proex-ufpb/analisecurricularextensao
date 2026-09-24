function ligarFiltro({ tabela, contagem, campos }) {
  const linhas = Array.from(document.querySelectorAll(`${tabela} tbody tr`));
  const elementos = Object.fromEntries(Object.entries(campos).map(([chave, id]) => [chave, document.getElementById(id)]));
  const saida = document.getElementById(contagem);
  if (!saida || Object.values(elementos).some((campo) => !campo)) return;

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

const colador = new Intl.Collator("pt-BR", { sensitivity: "base", numeric: true });
const PADRAO_NUMERO = /^[+-]?(\d{1,3}(\.\d{3})+|\d+)(,\d+)?%?$|^\d{4}\.\d$/;

function vazio(texto) {
  return texto === "" || texto === "—";
}

function numero(texto) {
  const limpo = texto.replace("%", "").replace(/\s/g, "");
  if (/^\d{4}\.\d$/.test(limpo)) return parseFloat(limpo);
  return parseFloat(limpo.replace(/\./g, "").replace(",", "."));
}

function ligarOrdenacao(tabela) {
  const cabecalhos = Array.from(tabela.querySelectorAll("thead th"));
  const corpo = tabela.querySelector("tbody");
  if (!corpo) return;

  cabecalhos.forEach((cabecalho, coluna) => {
    cabecalho.tabIndex = 0;
    cabecalho.classList.add("ordenavel");

    const ordenar = () => {
      const crescente = cabecalho.getAttribute("aria-sort") !== "ascending";
      cabecalhos.forEach((outro) => outro.removeAttribute("aria-sort"));
      cabecalho.setAttribute("aria-sort", crescente ? "ascending" : "descending");

      const linhas = Array.from(corpo.rows).map((linha, indice) => ({
        linha,
        indice,
        texto: (linha.cells[coluna] ? linha.cells[coluna].textContent : "").trim(),
      }));
      const preenchidas = linhas.filter((l) => !vazio(l.texto));
      const numerica = preenchidas.length > 0 && preenchidas.every((l) => PADRAO_NUMERO.test(l.texto));
      const comparar = numerica
        ? (a, b) => numero(a.texto) - numero(b.texto)
        : (a, b) => colador.compare(a.texto, b.texto);

      linhas.sort((a, b) => {
        const vaziaA = vazio(a.texto);
        const vaziaB = vazio(b.texto);
        if (vaziaA || vaziaB) return vaziaA === vaziaB ? a.indice - b.indice : vaziaA ? 1 : -1;
        const resultado = comparar(a, b);
        return resultado === 0 ? a.indice - b.indice : crescente ? resultado : -resultado;
      });
      linhas.forEach((l) => corpo.appendChild(l.linha));
    };

    cabecalho.addEventListener("click", ordenar);
    cabecalho.addEventListener("keydown", (evento) => {
      if (evento.key === "Enter" || evento.key === " ") {
        evento.preventDefault();
        ordenar();
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  ligarFiltro({
    tabela: "#tabela-cursos",
    contagem: "contagem",
    campos: { busca: "f-busca", centro: "f-centro", status: "f-status", ativo: "f-ativo" },
  });
  ligarFiltro({
    tabela: "#tabela-periodo",
    contagem: "contagem-periodo",
    campos: { busca: "i-busca", centro: "i-centro", periodo: "i-periodo" },
  });
  ligarFiltro({
    tabela: "#tabela-ppc",
    contagem: "contagem-ppc",
    campos: { busca: "m-busca", centro: "m-centro", modificacao: "m-modificacao" },
  });
  ligarFiltro({
    tabela: "#tabela-oferta",
    contagem: "contagem-oferta",
    campos: { busca: "o-busca", centro: "o-centro" },
  });
  ligarFiltro({
    tabela: "#tabela-uce",
    contagem: "contagem-uce",
    campos: { busca: "u-busca", centro: "u-centro", situacao: "u-situacao" },
  });
  ligarFiltro({
    tabela: "#tabela-componentes",
    contagem: "contagem-comp",
    campos: { busca: "c-busca", centro: "c-centro" },
  });
  document.querySelectorAll(".rolagem table").forEach(ligarOrdenacao);
});
