import json
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
    assert html.count("Nenhum curso implantado deste Centro tem percentual de extensão.") == 3
    assert "plotly-graph-div" in html or 'class="selos"' in html


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
        assert "plotly-graph-div" in html or 'class="selos"' in html, pagina.name


def test_menu_mostra_a_descricao_de_cada_centro_depois_de_um_traco(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    textos = {t.split(" – ")[0]: t for _, _, t in opcoes_do_menu(html) if t != "Todos"}
    assert textos["CCEN"] == "CCEN – Centro de Ciências Exatas e da Natureza"
    assert textos["CPT-ETS"] == "CPT-ETS – Centro Profissional e Tecnológico – Escola Técnica de Saúde"
    assert textos["CCHSA"] == "CCHSA – Centro de Ciências Humanas, Sociais e Agrárias"
    assert len(textos) == 17 and all(" – " in t and "(" not in t for t in textos.values())


def test_todo_centro_da_base_tem_descricao_cadastrada():
    from painel.tema import NOMES_CENTROS

    centros = set(cursos_unicos(carregar_linhas(FIXTURE))["CENTRO"])
    assert centros <= set(NOMES_CENTROS)


def test_titulo_da_pagina_do_centro_traz_a_descricao(site):
    html = (site / "centro" / "ccs.html").read_text(encoding="utf-8")
    assert "<title>CCS – Centro de Ciências da Saúde | Análise Curricular | PROEX/UFPB</title>" in html


def test_pagina_da_equipe_existe_com_botao_desativado_sem_endereco(tmp_path, monkeypatch):
    monkeypatch.setattr("painel.construir.URL_ENVIO_RELATORIO", "")
    construir(csv=FIXTURE, saida=tmp_path)
    html = (tmp_path / "equipe.html").read_text(encoding="utf-8")
    assert 'name="robots" content="noindex"' in html
    assert "Relatório" in html and "Equipe PROEX" in html
    assert "Envio em configuração" in html and "botao-principal" in html


def test_pagina_da_equipe_mostra_botao_com_link_quando_ha_endereco(tmp_path, monkeypatch):
    monkeypatch.setattr("painel.construir.URL_ENVIO_RELATORIO", "https://script.google.com/macros/s/EXEMPLO/exec")
    construir(csv=FIXTURE, saida=tmp_path)
    html = (tmp_path / "equipe.html").read_text(encoding="utf-8")
    assert 'href="https://script.google.com/macros/s/EXEMPLO/exec"' in html
    assert 'rel="noopener"' in html and "Envio em configuração" not in html


def test_link_discreto_da_equipe_fica_no_rodape_e_nao_no_topo(site):
    paginas = [site / "index.html"] + sorted((site / "centro").glob("*.html"))
    for pagina in paginas:
        html = pagina.read_text(encoding="utf-8")
        esperado = "../equipe.html" if pagina.parent.name == "centro" else "equipe.html"
        rodape = html[html.index('<footer class="rodape">'):]
        assert f'<a href="{esperado}">Área da equipe</a>' in rodape, pagina.name
        assert 'href="' + esperado + '"' not in html[: html.index('<footer class="rodape">')], pagina.name
        assert "menu-topo" not in html and "botao-equipe" not in html, pagina.name


def test_pagina_da_equipe_tem_voltar_ao_painel(site):
    html = (site / "equipe.html").read_text(encoding="utf-8")
    assert '<a href="index.html">← Voltar ao painel</a>' in html


def test_paginas_publicas_nao_expoem_o_e_mail_da_conta_autorizada(site):
    for pagina in [site / "equipe.html", site / "index.html"] + sorted((site / "centro").glob("*.html")):
        assert "creditacaodaextensaoufpb" not in pagina.read_text(encoding="utf-8"), pagina.name


def test_endereco_configurado_do_apps_script_aparece_na_pagina_da_equipe(site):
    from painel.tema import URL_ENVIO_RELATORIO

    assert URL_ENVIO_RELATORIO.startswith("https://script.google.com/macros/s/") and URL_ENVIO_RELATORIO.endswith("/exec")
    assert f'href="{URL_ENVIO_RELATORIO}"' in (site / "equipe.html").read_text(encoding="utf-8")


def test_textos_da_secao_de_implantacao_por_semestre(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "Quantitativo de cursos com a inserção da extensão no currículo implantada por semestre" in html
    eixo_x = json.dumps("Ano e Semestre de implantação do PPC")[1:-1]  # o Plotly grava os acentos do gráfico escapados
    assert eixo_x in html
    tabela = html[html.index('id="tabela-periodo"'):html.index("</table>", html.index('id="tabela-periodo"'))]
    assert '<th scope="col">Ano.Semestre</th>' in tabela and "Período do PPC novo" not in html


def linhas_da_tabela(html, tabela_id):
    if f'id="{tabela_id}"' not in html:
        return 0
    inicio = html.index(f'id="{tabela_id}"')
    return html[inicio:html.index("</table>", inicio)].count("<tr data-centro=")


def test_modificacao_curricular_das_paginas_por_centro_soma_a_da_pagina_geral(site):
    geral = linhas_da_tabela((site / "index.html").read_text(encoding="utf-8"), "tabela-ppc")
    soma = sum(linhas_da_tabela(p.read_text(encoding="utf-8"), "tabela-ppc") for p in (site / "centro").glob("*.html"))
    assert geral == soma == 35  # 36 cursos ativos com classificação, menos Engenharia Química (ainda não implantada)


def test_centro_sem_modificacao_curricular_informada_mostra_aviso(site):
    html = (site / "centro" / "ccj.html").read_text(encoding="utf-8")
    assert "Nenhum curso deste Centro tem modificação curricular informada." in html
    assert 'id="tabela-ppc"' not in html


def test_fonte_saira_e_servida_pelo_proprio_site(site):
    for pagina in [site / "index.html", site / "equipe.html"] + sorted((site / "centro").glob("*.html")):
        html = pagina.read_text(encoding="utf-8")
        assert "fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html, pagina.name
    css = (site / "estilo.css").read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in css and "@font-face" in css
    for arquivo in re.findall(r'url\("([^"]+)"\)', css):
        assert (site / arquivo).is_file(), arquivo
    assert (site / "fonts" / "LICENCA-Saira-OFL.txt").is_file()


def test_arquivos_da_fonte_sao_woff2_validos(site):
    for nome in ("saira-latin.woff2", "saira-latin-ext.woff2"):
        assert (site / "fonts" / nome).read_bytes()[:4] == b"wOF2", nome


def test_site_nao_chama_nenhum_endereco_externo(site):
    externos = set()
    for pagina in [site / "index.html", site / "equipe.html"] + sorted((site / "centro").glob("*.html")):
        externos |= set(re.findall(r'(?:href|src)="(https?://[^"]+)"', pagina.read_text(encoding="utf-8")))
    permitidos = {e for e in externos if e.startswith("https://script.google.com/macros/") or "mailto" in e}
    assert externos - permitidos == set()


def test_pagina_do_centro_tem_graficos_por_curso_e_a_geral_continua_por_centro(site):
    geral = (site / "index.html").read_text(encoding="utf-8")
    ccta = (site / "centro" / "ccta.html").read_text(encoding="utf-8")
    for titulo in ("Situação de implantação por", "Modificação curricular por", "Distribuição por", "UCE por"):
        assert f"{titulo} Centro" in geral and f"{titulo} curso" in ccta
        assert f"{titulo} Centro" not in ccta and f"{titulo} curso" not in geral
    assert "Hotelaria" in ccta and "Turismo" in ccta
    assert json.dumps("Música Brasileira Popular")[1:-1].split("<br>")[0][:6] in ccta


def test_rotulos_de_curso_sao_unicos_dentro_do_centro():
    from painel.dados import cursos_ativos
    from painel.metricas import rotular_cursos

    ativos = cursos_ativos(cursos_unicos(carregar_linhas(FIXTURE)))
    for _, grupo in ativos.groupby("CENTRO"):
        rotulos = rotular_cursos(grupo)["ROTULO"]
        assert rotulos.is_unique
    ccen = rotular_cursos(ativos[ativos["CENTRO"] == "CCEN"])["ROTULO"]
    assert "Física (Licenciatura)" in set(ccen) and "Física (Bacharelado)" in set(ccen)


def test_graficos_por_curso_somam_o_mesmo_que_por_centro():
    from painel.dados import cursos_ativos
    from painel.metricas import (com_meta, cursos_com_extensao, rotular_cursos, status_por_centro, uce_por_centro)

    ativos = rotular_cursos(cursos_ativos(cursos_unicos(carregar_linhas(FIXTURE))))
    assert status_por_centro(ativos, "ROTULO")["TOTAL"].sum() == status_por_centro(ativos)["TOTAL"].sum() == len(ativos)
    base = cursos_com_extensao(com_meta(ativos))
    assert uce_por_centro(base, "ROTULO")["UCES"].sum() == uce_por_centro(base)["UCES"].sum()


def test_a_partir_da_secao_por_semestre_so_entram_cursos_implantados(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    inicio = html.index('id="t-periodo"')
    for tabela_id in ("tabela-ppc", "tabela-oferta", "tabela-componentes", "tabela-uce"):
        if f'id="{tabela_id}"' not in html:
            continue
        i = html.index(f'id="{tabela_id}"')
        assert i > inicio
        assert "Engenharia Química" not in html[i:html.index("</table>", i)], tabela_id
        assert "Hotelaria" not in html[i:html.index("</table>", i)], tabela_id
