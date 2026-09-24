import re
from pathlib import Path

import pytest

from painel.construir import construir, slug_centro
from painel.dados import carregar_linhas, cursos_unicos

FIXTURE = Path(__file__).parent / "fixtures" / "analise_curricular_2026-09-24.csv"


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    saida = tmp_path_factory.mktemp("site")
    construir(csv=FIXTURE, saida=saida)
    return saida


def linhas_da_tabela_de_cursos(html):
    inicio = html.index('id="tabela-cursos"')
    tabela = html[inicio:html.index("</table>", inicio)]
    return tabela.count('<tr data-centro="')


def test_gera_pagina_geral_e_uma_por_centro(site):
    centros = sorted(cursos_unicos(carregar_linhas(FIXTURE))["CENTRO"].unique())
    assert (site / "index.html").exists()
    for centro in centros:
        assert (site / "centro" / f"{slug_centro(centro)}.html").exists()
    assert len(list((site / "centro").glob("*.html"))) == len(centros)


def test_paginas_por_centro_dividem_os_131_cursos(site):
    geral = linhas_da_tabela_de_cursos((site / "index.html").read_text(encoding="utf-8"))
    soma = sum(linhas_da_tabela_de_cursos(p.read_text(encoding="utf-8")) for p in (site / "centro").glob("*.html"))
    assert geral == soma == 131


def test_barra_de_centros_marca_a_pagina_atual(site):
    html = (site / "centro" / "ccs.html").read_text(encoding="utf-8")
    ativos = re.findall(r'<a class="chip ativo" href="([^"]+)"', html)
    assert ativos == ["../centro/ccs.html"]
    assert html.count('class="chip') == 1 + len(list((site / "centro").glob("*.html")))
    assert 'href="../estilo.css"' in html and 'src="../plotly.min.js"' in html


def test_pagina_geral_marca_todos_e_usa_caminhos_da_raiz(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    assert re.findall(r'<a class="chip ativo" href="([^"]+)"', html) == ["index.html"]
    assert 'href="estilo.css"' in html


def test_centro_sem_curso_com_percentual_mostra_aviso_em_vez_de_grafico(site):
    html = (site / "centro" / "ccj.html").read_text(encoding="utf-8")
    assert html.count("Nenhum curso deste Centro tem percentual de extensão.") == 3
    assert "plotly-graph-div" in html


def test_selects_das_tabelas_ficam_so_com_o_centro_da_pagina(site):
    html = (site / "centro" / "ccs.html").read_text(encoding="utf-8")
    opcoes = re.search(r'<select id="f-centro">(.*?)</select>', html, re.S).group(1)
    assert re.findall(r"<option[^>]*>([^<]+)</option>", opcoes) == ["Todos", "CCS"]


def test_cartoes_da_pagina_do_centro_usam_so_os_cursos_dele(site):
    html = (site / "centro" / "ccs.html").read_text(encoding="utf-8")
    ativos = int(re.search(r'<span class="numero">(\d+)</span>\s*<span class="rotulo">cursos ativos', html).group(1))
    cursos = cursos_unicos(carregar_linhas(FIXTURE))
    ccs = cursos[(cursos["CENTRO"] == "CCS") & (cursos["SITUAÇÃO"] == "EM ATIVIDADE")]
    assert ativos == len(ccs)
