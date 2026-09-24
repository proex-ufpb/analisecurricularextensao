from pathlib import Path

import pytest

from painel.dados import carregar_linhas, cursos_ativos, cursos_unicos
from painel.metricas import (
    classificar_meta,
    com_meta,
    COLUNAS_COMPONENTES,
    componentes_por_centro,
    cursos_com_extensao,
    formatar_horas,
    formatar_nome,
    formatar_pp,
    linhas_oferta,
    oferta_por_centro,
    resumo_oferta,
    linhas_componentes,
    resumo_componentes,
    linhas_percentuais,
    meta_por_centro,
    resumo_meta,
    resumo_status,
    status_por_centro,
)

FIXTURE = Path(__file__).parent / "fixtures" / "analise_curricular_2026-09-24.csv"


def base_real():
    cursos = cursos_unicos(carregar_linhas(FIXTURE))
    return cursos, cursos_ativos(cursos)


def test_formatar_nome_mantem_conectivos_em_minuscula():
    assert formatar_nome("TECNOLOGIA EM GESTÃO PÚBLICA") == "Tecnologia em Gestão Pública"
    assert formatar_nome("EAD") == "EAD"
    assert formatar_nome("JOÃO PESSOA") == "João Pessoa"


def test_totais_e_percentuais_usam_so_cursos_ativos():
    _, ativos = base_real()
    resumo = resumo_status(ativos)
    assert sum(item["total"] for item in resumo) == len(ativos) == 118
    assert round(sum(item["percentual"] for item in resumo), 6) == 100.0
    assert [item["status"] for item in resumo][0] == "IMPLANTADO"


def test_status_por_centro_soma_igual_ao_total_de_ativos():
    _, ativos = base_real()
    tabela = status_por_centro(ativos)
    assert tabela["TOTAL"].sum() == len(ativos)
    assert (tabela.drop(columns="TOTAL").sum(axis=1) == tabela["TOTAL"]).all()
    assert tabela["TOTAL"].is_monotonic_decreasing


@pytest.mark.parametrize("valor,esperado", [
    (float("nan"), "NAO_IMPLANTADO"),
    (0.0, "NAO_IMPLANTADO"),
    (0.0999, "ABAIXO"),
    (0.09999999999999, "DENTRO"),
    (0.10, "DENTRO"),
    (0.15, "DENTRO"),
    (0.15000000000001, "DENTRO"),
    (0.1501, "ACIMA"),
])
def test_classificar_meta_nos_limites(valor, esperado):
    assert classificar_meta(valor) == esperado


def test_meta_da_base_real():
    cursos, ativos = base_real()
    ativos = com_meta(ativos)
    itens, com_dado = resumo_meta(ativos)
    total = {i["classe"]: i["total"] for i in itens}
    assert com_dado == 42
    assert total == {"ABAIXO": 1, "DENTRO": 41, "ACIMA": 0, "NAO_IMPLANTADO": 76}
    assert sum(total.values()) == len(ativos)
    tabela = meta_por_centro(ativos)
    assert tabela["TOTAL"].sum() == len(ativos)


def test_linhas_percentuais_so_implantados_em_ordem_crescente():
    _, ativos = base_real()
    linhas = linhas_percentuais(com_meta(ativos))
    assert len(linhas) == 42
    assert all(l["percentual"] != "0,00%" for l in linhas)
    assert linhas[0]["curso"] == "Engenharia de Materiais"
    valores = [float(l["percentual"].rstrip("%").replace(",", ".")) for l in linhas]
    assert valores == sorted(valores)


def base_extensao():
    _, ativos = base_real()
    return cursos_com_extensao(com_meta(ativos))


def test_formatar_horas():
    assert formatar_horas(0) == "—"
    assert formatar_horas(float("nan")) == "—"
    assert formatar_horas(390.0) == "390"
    assert formatar_horas(358.5) == "358,5"
    assert formatar_horas(18759.0) == "18.759"


def test_componentes_somam_o_total_de_cada_curso():
    base = base_extensao()
    assert len(base) == 42
    soma = sum(base[coluna] for coluna in COLUNAS_COMPONENTES.values())
    assert (abs(soma - base["CH_TOTAL_EXT"]) < 0.01).all()


def test_resumo_componentes_fecha_100_por_cento():
    itens, destaques = resumo_componentes(base_extensao())
    assert round(sum(i["percentual"] for i in itens), 6) == 100.0
    assert destaques["total_horas"] == "18.759"
    assert destaques["so_obrigatorias"] == 8
    assert destaques["maioria_livre"] == 15


def test_componentes_por_centro_preserva_o_total():
    base = base_extensao()
    tabela = componentes_por_centro(base)
    assert tabela["TOTAL"].sum() == base["CH_TOTAL_EXT"].sum()
    assert tabela["TOTAL"].is_monotonic_decreasing


def test_linhas_componentes_uma_por_curso():
    linhas = linhas_componentes(base_extensao())
    assert len(linhas) == 42
    biotec = next(l for l in linhas if l["curso"] == "Biotecnologia")
    assert (biotec["BASICA"], biotec["COMPLEMENTAR"], biotec["OPTATIVA"], biotec["FLEXIVEL"]) == ("150", "120", "120", "—")
    assert biotec["total"] == "390" and biotec["obrigatorias"] == "69%"


def test_formatar_pp():
    assert formatar_pp(0.0) == "0,00"
    assert formatar_pp(16.25) == "+16,25"
    assert formatar_pp(-1.5) == "-1,50"


def test_oferta_nunca_e_menor_que_a_exigencia_na_base_real():
    resumo = resumo_oferta(base_extensao())
    assert resumo["menores"] == 0
    assert resumo["iguais"] + resumo["maiores"] == resumo["total"] == 42
    assert (resumo["iguais"], resumo["maiores"]) == (14, 28)


def test_resumo_oferta_horas_e_destaques():
    resumo = resumo_oferta(base_extensao())
    assert resumo["horas_exigidas"] == "14.797,5"
    assert resumo["horas_ofertadas"] == "18.759"
    assert resumo["horas_a_mais"] == "3.961,5"
    assert resumo["acima_teto"] == 9
    assert resumo["maior_curso"] == "Hotelaria" and resumo["maior_centro"] == "CCTA"
    assert resumo["maior_margem"] == "+16,25"


def test_oferta_por_centro_media_exigido_menor_ou_igual_ao_ofertado():
    tabela = oferta_por_centro(base_extensao())
    assert (tabela["OFERTADO"] >= tabela["EXIGIDO"] - 1e-9).all()
    assert tabela["CURSOS"].sum() == 42


def test_linhas_oferta_ordenadas_pela_maior_margem():
    linhas = linhas_oferta(base_extensao())
    assert len(linhas) == 42
    assert linhas[0]["curso"] == "Hotelaria"
    assert (linhas[0]["pct_exigido"], linhas[0]["pct_ofertado"]) == ("12,50%", "28,75%")
    margens = [float(l["margem"].replace("+", "").replace(",", ".")) for l in linhas]
    assert margens == sorted(margens, reverse=True)
