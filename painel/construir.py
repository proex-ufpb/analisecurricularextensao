import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader, select_autoescape
from plotly.offline import get_plotlyjs

from painel.dados import CSV_PADRAO, PRIORIDADE_STATUS, carregar_linhas, cursos_ativos, cursos_unicos
from painel.metricas import (
    CLASSES_META,
    COMPONENTES,
    LIMITE_MAXIMO,
    LIMITE_MINIMO,
    ROTULOS_COMPONENTES,
    ROTULOS_META,
    ROTULOS_STATUS,
    com_meta,
    componentes_por_centro,
    cursos_com_extensao,
    linhas_componentes,
    linhas_oferta,
    linhas_percentuais,
    linhas_tabela,
    meta_por_centro,
    oferta_por_centro,
    resumo_componentes,
    resumo_meta,
    resumo_oferta,
    resumo_status,
    status_por_centro,
)
from painel.tema import (
    AZUL_PROEX,
    CONTATO,
    COR_TEXTO_COMPONENTES,
    COR_TEXTO_META,
    COR_TEXTO_NA_BARRA,
    CORES_COMPONENTES,
    CORES_META,
    CORES_OFERTA,
    CORES_STATUS,
    EQUIPE,
)

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "site"
FUSO_BRASILIA = timezone(timedelta(hours=-3))
FONTE = "Saira, sans-serif"
CONFIG_GRAFICO = {"displayModeBar": False, "responsive": True}


def _html(fig):
    return fig.to_html(full_html=False, include_plotlyjs=False, config=CONFIG_GRAFICO)


def _barras_por_centro(tabela, categorias, rotulos, cores, cores_texto, titulo_x):
    centros = list(tabela.index)
    fig = go.Figure()
    for categoria in categorias:
        valores = tabela[categoria]
        fig.add_bar(
            y=centros,
            x=valores,
            orientation="h",
            name=rotulos[categoria],
            marker=dict(color=cores[categoria], line=dict(color="#FFFFFF", width=2)),
            text=[str(v) if v else "" for v in valores],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color=cores_texto[categoria], size=13),
            customdata=(valores / tabela["TOTAL"] * 100).round(0),
            hovertemplate=(
                "<b>%{y}</b><br>" + rotulos[categoria]
                + ": %{x} curso(s) (%{customdata:.0f}% do centro)<extra></extra>"
            ),
        )
    fig.update_layout(
        barmode="stack",
        height=max(320, 34 * len(centros) + 110),
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONTE, size=13, color="#15163A"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text="", traceorder="normal"),
        xaxis=dict(title=titulo_x, gridcolor="#E6E8F2", zeroline=False, rangemode="tozero"),
        yaxis=dict(autorange="reversed", automargin=True, title=""),
        hoverlabel=dict(font=dict(family=FONTE)),
    )
    return _html(fig)


def grafico_status_por_centro(tabela):
    return _barras_por_centro(
        tabela, PRIORIDADE_STATUS, ROTULOS_STATUS, CORES_STATUS, COR_TEXTO_NA_BARRA, "Cursos ativos"
    )


def grafico_meta_por_centro(tabela):
    return _barras_por_centro(
        tabela, CLASSES_META, ROTULOS_META, CORES_META, COR_TEXTO_META, "Cursos ativos"
    )


def grafico_componentes_por_centro(tabela):
    centros = list(tabela.index)
    fig = go.Figure()
    for chave in COMPONENTES:
        horas = tabela[chave]
        participacao = (horas / tabela["TOTAL"] * 100).fillna(0)
        fig.add_bar(
            y=centros,
            x=participacao,
            orientation="h",
            name=ROTULOS_COMPONENTES[chave],
            marker=dict(color=CORES_COMPONENTES[chave], line=dict(color="#FFFFFF", width=2)),
            text=[f"{v:.0f}%" if v >= 7 else "" for v in participacao],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color=COR_TEXTO_COMPONENTES[chave], size=12),
            customdata=horas,
            hovertemplate=(
                "<b>%{y}</b><br>" + ROTULOS_COMPONENTES[chave]
                + ": %{customdata:.0f} h (%{x:.0f}% da carga horária de extensão do centro)<extra></extra>"
            ),
        )
    fig.update_layout(
        barmode="stack",
        height=max(320, 34 * len(centros) + 110),
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONTE, size=13, color="#15163A"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text="", traceorder="normal"),
        xaxis=dict(title="Participação na carga horária de extensão do centro", ticksuffix="%", range=[0, 100],
                   gridcolor="#E6E8F2", zeroline=False),
        yaxis=dict(autorange="reversed", automargin=True, title=""),
        hoverlabel=dict(font=dict(family=FONTE)),
    )
    return _html(fig)


def grafico_exigencia_oferta(tabela):
    """Média por centro do % que o aluno integraliza e do % que o curso oferta, com a faixa de 10% a 15%."""
    centros = list(tabela.index)
    fig = go.Figure()
    fig.add_vrect(x0=LIMITE_MINIMO * 100, x1=LIMITE_MAXIMO * 100, fillcolor="#2E9E4F", opacity=0.12,
                  line_width=0, layer="below")
    series = (
        ("EXIGIDO", "A integralizar (exigido do aluno)"),
        ("OFERTADO", "Ofertado (disponível no curso)"),
    )
    for chave, nome in series:
        fig.add_bar(
            y=centros,
            x=tabela[chave],
            orientation="h",
            name=nome,
            marker=dict(color=CORES_OFERTA[chave], line=dict(color="#FFFFFF", width=1)),
            text=[f"{v:.1f}%".replace(".", ",") for v in tabela[chave]],
            textposition="outside",
            cliponaxis=False,
            textfont=dict(size=11, color="#15163A"),
            customdata=tabela["CURSOS"],
            hovertemplate="<b>%{y}</b><br>" + nome + ": %{x:.2f}% (média de %{customdata} curso(s))<extra></extra>",
        )
    fig.add_annotation(x=(LIMITE_MINIMO + LIMITE_MAXIMO) / 2 * 100, y=1.0, yref="paper", xanchor="center",
                       yanchor="bottom", showarrow=False, text="Faixa UFPB para o que o aluno integraliza: 10% a 15%",
                       font=dict(color="#1E6B36", size=12), yshift=4)
    fig.update_layout(
        barmode="group",
        bargap=0.25,
        height=max(360, 46 * len(centros) + 150),
        margin=dict(l=8, r=40, t=40, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONTE, size=13, color="#15163A"),
        separators=",.",
        legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="left", x=0, title_text="", traceorder="normal"),
        xaxis=dict(title="Média dos cursos do centro", ticksuffix="%", range=[0, 32], dtick=5, gridcolor="#E6E8F2",
                   zeroline=False),
        yaxis=dict(autorange="reversed", automargin=True, title=""),
        hoverlabel=dict(font=dict(family=FONTE)),
    )
    return _html(fig)


def construir(csv=CSV_PADRAO, saida=SAIDA):
    linhas = carregar_linhas(csv)
    cursos = com_meta(cursos_unicos(linhas))
    ativos = cursos_ativos(cursos)
    por_centro = status_por_centro(ativos)
    meta_centros = meta_por_centro(ativos)
    resumo_metas, com_dado = resumo_meta(ativos)
    base_extensao = cursos_com_extensao(ativos)
    resumo_comp, destaques = resumo_componentes(base_extensao)
    oferta = resumo_oferta(base_extensao)

    saida.mkdir(parents=True, exist_ok=True)
    (saida / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")
    for pasta in ("static", "../assets"):
        origem = Path(__file__).resolve().parent / pasta
        for arquivo in origem.glob("*"):
            if arquivo.suffix in {".css", ".js", ".png", ".svg"}:
                shutil.copy(arquivo, saida / arquivo.name)

    ambiente = Environment(
        loader=FileSystemLoader(Path(__file__).resolve().parent / "templates"),
        autoescape=select_autoescape(["html", "j2"]),
    )
    html = ambiente.get_template("index.html.j2").render(
        n_ativos=len(ativos),
        n_fora=len(cursos) - len(ativos),
        n_cursos=len(cursos),
        status=resumo_status(ativos),
        cores=CORES_STATUS,
        grafico=grafico_status_por_centro(por_centro),
        tabela_centros=[
            {"centro": centro, **{s: int(linha[s]) for s in PRIORIDADE_STATUS}, "total": int(linha["TOTAL"])}
            for centro, linha in por_centro.iterrows()
        ],
        rotulos=ROTULOS_STATUS,
        prioridade=PRIORIDADE_STATUS,
        metas=resumo_metas,
        n_com_dado=com_dado,
        cores_meta=CORES_META,
        rotulos_meta=ROTULOS_META,
        classes_meta=CLASSES_META,
        grafico_meta_centros=grafico_meta_por_centro(meta_centros),
        percentuais=linhas_percentuais(ativos),
        componentes=COMPONENTES,
        rotulos_componentes=ROTULOS_COMPONENTES,
        cores_componentes=CORES_COMPONENTES,
        resumo_componentes=resumo_comp,
        destaques=destaques,
        n_extensao=len(base_extensao),
        grafico_componentes=grafico_componentes_por_centro(componentes_por_centro(base_extensao)),
        linhas_componentes=linhas_componentes(base_extensao),
        oferta=oferta,
        cores_oferta=CORES_OFERTA,
        grafico_oferta=grafico_exigencia_oferta(oferta_por_centro(base_extensao)),
        linhas_oferta=linhas_oferta(base_extensao),
        cursos=linhas_tabela(cursos),
        centros=sorted(cursos["CENTRO"].unique()),
        contato=CONTATO,
        equipe=EQUIPE,
        azul=AZUL_PROEX,
        atualizado_em=datetime.now(FUSO_BRASILIA).strftime("%d/%m/%Y"),
    )
    (saida / "index.html").write_text(html, encoding="utf-8")
    return saida / "index.html"


if __name__ == "__main__":
    print(construir())
