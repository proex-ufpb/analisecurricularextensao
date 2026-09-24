from pathlib import Path

import pandas as pd
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
    com_uce,
    formatar_pp,
    linhas_uce,
    resumo_uce,
    uce_por_centro,
    formatar_processo,
    formatar_resolucao,
    linhas_tabela,
    linhas_oferta,
    oferta_por_centro,
    resumo_oferta,
    linhas_componentes,
    resumo_componentes,
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
    itens, total_horas = resumo_componentes(base_extensao())
    assert round(sum(i["percentual"] for i in itens), 6) == 100.0
    assert total_horas == "18.759"


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


@pytest.mark.parametrize("valores,esperado", [
    (["Nº 09/2024 (MAR-24)"], "09/2024"),
    (["Nº 9/2024"], "09/2024"),
    (["Nº 31/2023 (altera nº 20/2021)"], "31/2023"),
    (["", "Nº 42/2025 (JUL-2025)"], "42/2025"),
    (["Nº 42/2025 (JUL-2025)", "Nº 42/2025 (JUL-2025)"], "42/2025"),
    (["PENDENTE"], "Pendente"),
    (["#N/A (Did not find value '25/012005' in VLOOKUP evaluation.)"], "—"),
    ([""], "—"),
    ([], "—"),
])
def test_formatar_resolucao(valores, esperado):
    assert formatar_resolucao(valores) == esperado


@pytest.mark.parametrize("valores,esperado", [
    (["23074.104191/2022-04"], "23074.104191/2022-04"),
    (["#N/A (Did not find value '292006' in VLOOKUP evaluation.)", "23074.124991/2023-31"], "23074.124991/2023-31"),
    (["NÃO CONSTA", "#N/A (Did not find value '652006' in VLOOKUP evaluation.)"], "Não consta"),
    (["SEM PROCESSO - EXCEÇÃO"], "Sem processo (exceção)"),
    (["#N/A (Did not find value '51998' in VLOOKUP evaluation.)"], "—"),
    ([], "—"),
])
def test_formatar_processo(valores, esperado):
    assert formatar_processo(valores) == esperado


def test_processo_e_resolucao_da_base_real():
    cursos, _ = base_real()
    linhas = {(l["emec"], l["curso"]): l for l in linhas_tabela(com_meta(cursos))}
    biotec = next(l for l in linhas.values() if l["curso"] == "Biotecnologia")
    assert biotec["processo"] == "23074.104191/2022-04" and biotec["resolucao"] == "09/2024"
    economicas = next(l for l in linhas.values() if l["curso"] == "Ciências Econômicas" and l["emec"] == "13394")
    assert economicas["processo"] == "23074.028746/2023-16" and economicas["resolucao"] == "42/2025"
    assert all(set(l) >= {"processo", "resolucao"} for l in linhas.values())


def frame_uce(*linhas):
    return pd.DataFrame([
        {"CENTRO": "CT", "CURSO": f"C{i}", "CÓDIGO E-MEC": str(i), "QTDE_UCE": q, "CH_UCE": h, "CREDITO_UCE": h / 15 if h == h else 0.0}
        for i, (q, h) in enumerate(linhas)
    ])


def test_classificacao_de_uce():
    base = com_uce(frame_uce((2, 120.0), (float("nan"), 60.0), (3, float("nan")), (0, 0.0), (float("nan"), float("nan"))))
    assert list(base["UCE_CLASSE"]) == ["COM_UCE", "COM_UCE", "COM_UCE", "SEM_UCE", "SEM_UCE"]


def test_linhas_uce_campo_vazio_conta_como_sem_uce():
    linhas = linhas_uce(frame_uce((float("nan"), float("nan")), (0, 0.0), (4, 60.0)))
    assert [l["situacao"] for l in linhas] == ["Com UCE", "Sem UCE", "Sem UCE"]
    assert (linhas[0]["qtde"], linhas[0]["horas"], linhas[0]["creditos"]) == ("4", "60", "4")
    assert all((l["qtde"], l["horas"], l["creditos"]) == ("0", "0", "0") for l in linhas[1:])


def test_base_das_analises_so_tem_cursos_com_percentual_maior_que_zero():
    ativos = pd.DataFrame({
        "CENTRO": ["A", "A", "A"],
        "CURSO": ["x", "y", "z"],
        "% CH_INTEGRALIZADA_EXTENSAO": [0.10, 0.0, float("nan")],
        "CH_BASICA_PROFISSIONAL_EXT": [100.0, 0.0, float("nan")],
        "CH_COMPL_OBRIG_EXT": [float("nan")] * 3,
        "CH_OPTATIVA_EXT": [float("nan")] * 3,
        "CH_FLEXÍVEL_EXT": [float("nan")] * 3,
        "CH_TOTAL_EXT": [100.0, 0.0, float("nan")],
    })
    base = cursos_com_extensao(com_meta(ativos))
    assert list(base["CURSO"]) == ["x"]


def test_uce_da_base_real():
    base = base_extensao()
    resumo = resumo_uce(base)
    assert (resumo["total"], resumo["com_uce"], resumo["qtde"]) == (42, 23, "70")
    classes = com_uce(base)["UCE_CLASSE"].value_counts().to_dict()
    assert classes == {"COM_UCE": 23, "SEM_UCE": 19}


def test_uce_por_centro_preserva_totais():
    base = base_extensao()
    tabela = uce_por_centro(base)
    assert tabela["UCES"].sum() == 70 and tabela["CURSOS"].sum() == 42
    assert tabela["UCES"].is_monotonic_decreasing
    assert tabela["COM_UCE"].sum() == 23
