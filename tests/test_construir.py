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


def opcoes_do_menu(html):
    menu = re.search(r'<select id="filtro-centro"[^>]*>(.*?)</select>', html, re.S).group(1)
    return re.findall(r'<option value="([^"]+)"( selected)?>([^<]+)</option>', menu)


def test_menu_de_centros_marca_a_pagina_atual(site):
    html = (site / "centro" / "ccs.html").read_text(encoding="utf-8")
    opcoes = opcoes_do_menu(html)
    assert len(opcoes) == 1 + len(list((site / "centro").glob("*.html")))
    assert opcoes[0][0] == "../index.html" and opcoes[0][2] == "Todos"
    assert [o[0] for o in opcoes if o[1]] == ["../centro/ccs.html"]
    assert 'data-filtrado="1"' in html and 'data-inicio="../index.html"' in html
    assert 'autocomplete="off"' in html
    assert 'href="../estilo.css"' in html and 'src="../plotly.min.js"' in html and 'src="../filtro-centro.js"' in html


def test_pagina_geral_abre_em_todos(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    opcoes = opcoes_do_menu(html)
    assert [o[0] for o in opcoes if o[1]] == ["index.html"]
    assert 'data-filtrado="0"' in html
    assert 'href="estilo.css"' in html


def test_menu_tem_links_de_reserva_sem_javascript(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    reserva = re.search(r"<noscript>(.*?)</noscript>", html, re.S).group(1)
    assert reserva.count('<a class="chip') == 1 + len(list((site / "centro").glob("*.html")))


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


def test_todo_link_e_arquivo_referenciado_existe_em_todas_as_paginas(site):
    paginas = [site / "index.html"] + sorted((site / "centro").glob("*.html"))
    for pagina in paginas:
        html = pagina.read_text(encoding="utf-8")
        menu = re.search(r'<select id="filtro-centro"[^>]*>(.*?)</select>', html, re.S).group(1)
        alvos = re.findall(r'<option value="([^"]+)"', menu)
        alvos += re.findall(r'(?:href|src)="((?!https?:|#|mailto:)[^"]+)"', html)
        assert alvos, pagina
        for alvo in alvos:
            assert (pagina.parent / alvo).resolve().exists(), f"{pagina.name}: {alvo} não existe"


def test_todas_as_paginas_tem_menu_cabecalho_e_pelo_menos_um_grafico(site):
    for pagina in [site / "index.html"] + sorted((site / "centro").glob("*.html")):
        html = pagina.read_text(encoding="utf-8")
        assert 'id="filtro-centro"' in html and "<header" in html and "<footer" in html, pagina.name
        assert "plotly-graph-div" in html, pagina.name
