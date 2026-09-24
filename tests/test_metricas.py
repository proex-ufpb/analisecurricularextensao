from pathlib import Path

import pytest

from painel.dados import carregar_linhas, cursos_ativos, cursos_unicos
from painel.metricas import (
    classificar_meta,
    com_meta,
    formatar_nome,
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
