from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from painel.acoes import acoes_prioritarias
from painel.dados import carregar_linhas, cursos_unicos
from painel.metricas import com_meta
from painel.relatorio import gerar

FIXTURE = Path(__file__).parent / "fixtures" / "analise_curricular_2026-09-24.csv"
AGORA = datetime(2026, 9, 24, 15, 30, tzinfo=timezone(timedelta(hours=-3)))


@pytest.fixture(scope="module")
def resultado():
    return acoes_prioritarias(com_meta(cursos_unicos(carregar_linhas(FIXTURE))))


def por_titulo(resultado, titulo):
    return next(g for g in resultado["prioridades"] if g["titulo"] == titulo)


def test_prioridades_seguem_a_ordem_de_proximidade_da_conclusao(resultado):
    titulos = [g["titulo"] for g in resultado["prioridades"]]
    assert titulos == [
        "Concluir a implantação",
        "Regularizar o percentual de extensão a integralizar",
        "Finalizar a tramitação",
        "Iniciar o processo",
    ]
    assert [g["nivel"] for g in resultado["prioridades"]] == [1, 1, 2, 3]


def test_quantidades_por_grupo_na_base_real(resultado):
    assert len(por_titulo(resultado, "Concluir a implantação")["itens"]) == 5
    assert len(por_titulo(resultado, "Finalizar a tramitação")["itens"]) == 32
    assert len(por_titulo(resultado, "Iniciar o processo")["itens"]) == 44


def test_curso_abaixo_de_10_por_cento_e_sinalizado(resultado):
    itens = por_titulo(resultado, "Regularizar o percentual de extensão a integralizar")["itens"]
    assert [(i["curso"], i["centro"]) for i in itens] == [("Engenharia de Materiais", "CT")]
    assert "9,22%" in itens[0]["detalhe"]


def test_itens_ordenados_por_centro_e_curso(resultado):
    for grupo in resultado["prioridades"]:
        chaves = [(i["centro"], i["curso"]) for i in grupo["itens"]]
        assert chaves == sorted(chaves)


def test_cursos_em_extincao_nao_geram_acoes(resultado):
    total = sum(len(g["itens"]) for g in resultado["prioridades"])
    assert total == 5 + 1 + 32 + 44


def test_alertas_da_base_real(resultado):
    alertas = {a["titulo"]: a["itens"] for a in resultado["alertas"]}
    assert len(alertas["Resolução CONSEPE pendente"]) == 4
    assert len(alertas["Status diferente entre turnos do mesmo curso"]) == 3
    assert len(alertas["Cursos sem código e-MEC"]) == 1
    assert "Oferta menor que a exigência" not in alertas


def test_resumo_por_centro_soma_todas_as_acoes(resultado):
    assert sum(l["total"] for l in resultado["por_centro"]) == 5 + 1 + 32 + 44
    totais = [l["total"] for l in resultado["por_centro"]]
    assert totais == sorted(totais, reverse=True)


def test_gerar_relatorio_html_e_assunto(tmp_path):
    caminho = gerar(csv=FIXTURE, saida=tmp_path, solicitante="creditacaodaextensaoufpb@gmail.com", agora=AGORA)
    html = caminho.read_text(encoding="utf-8")
    assert "Relatório de Ações Prioritárias" in html
    assert "24/09/2026" in html and "15:30" in html
    assert "a pedido de creditacaodaextensaoufpb@gmail.com" in html
    assert "Concluir a implantação (5)" in html and "Iniciar o processo (44)" in html
    assert "NOTAS_FASE2" not in html
    assert (tmp_path / "assunto.txt").read_text(encoding="utf-8") == "Relatório de Ações Prioritárias — Análise Curricular (24/09/2026)"


def test_relatorio_nao_e_gerado_dentro_do_site(tmp_path):
    from painel.construir import construir

    site = tmp_path / "site"
    construir(csv=FIXTURE, saida=site)
    assert not list(site.rglob("relatorio*"))
    assert "Enviar relatório" not in (site / "index.html").read_text(encoding="utf-8")
