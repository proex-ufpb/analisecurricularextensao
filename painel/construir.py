import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader, select_autoescape
from plotly.offline import get_plotlyjs

from painel.dados import CSV_PADRAO, PRIORIDADE_STATUS, carregar_linhas, cursos_ativos, cursos_unicos
from painel.metricas import (
    CLASSES_META,
    COLUNA_PERCENTUAL,
    LIMITE_MAXIMO,
    LIMITE_MINIMO,
    ROTULOS_META,
    ROTULOS_STATUS,
    com_meta,
    formatar_nome,
    formatar_percentual,
    linhas_tabela,
    meta_por_centro,
    resumo_meta,
    resumo_status,
    status_por_centro,
)
from painel.tema import (
    AZUL_PROEX,
    CONTATO,
    COR_TEXTO_META,
    COR_TEXTO_NA_BARRA,
    CORES_META,
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


def grafico_ranking_meta(ativos):
    """Um ponto por curso com percentual calculado, com a linha de 10% e a faixa de 10% a 15%."""
    dados = ativos[ativos[COLUNA_PERCENTUAL].notna()].sort_values(
        [COLUNA_PERCENTUAL, "CENTRO", "CURSO"], kind="stable"
    ).reset_index(drop=True)
    rotulos = [f"{formatar_nome(c['CURSO'])} ({c['CENTRO']})" for _, c in dados.iterrows()]

    fig = go.Figure()
    fig.add_vrect(x0=LIMITE_MINIMO * 100, x1=LIMITE_MAXIMO * 100, fillcolor="#2E9E4F", opacity=0.12, line_width=0, layer="below")
    fig.add_vline(x=LIMITE_MINIMO * 100, line=dict(color=AZUL_PROEX, width=2, dash="dash"))
    for classe in ("ABAIXO", "DENTRO", "ACIMA"):
        parte = dados[dados["META"] == classe]
        fig.add_scatter(
            x=parte[COLUNA_PERCENTUAL] * 100,
            y=parte.index,
            mode="markers",
            name=ROTULOS_META[classe],
            text=[rotulos[i] for i in parte.index],
            marker=dict(size=11, color=CORES_META[classe], line=dict(color="#FFFFFF", width=2)),
            hovertemplate="<b>%{text}</b><br>%{x:.2f}% da carga horária<extra></extra>",
        )
    fig.add_annotation(x=LIMITE_MINIMO * 100, y=1.0, yref="paper", xanchor="right", yanchor="bottom", showarrow=False,
                       text="Mínimo nacional: 10%", font=dict(color=AZUL_PROEX, size=12), xshift=-6)
    fig.add_annotation(x=(LIMITE_MINIMO + LIMITE_MAXIMO) / 2 * 100, y=1.0, yref="paper", xanchor="center", yanchor="bottom",
                       showarrow=False, text="Faixa UFPB: 10% a 15%", font=dict(color="#1E6B36", size=12), yshift=0)
    fig.update_layout(
        height=max(360, 24 * len(dados) + 150),
        margin=dict(l=8, r=16, t=48, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONTE, size=12, color="#15163A"),
        separators=",.",
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="left", x=0, title_text=""),
        xaxis=dict(range=[-0.5, 16], dtick=2, ticksuffix="%", gridcolor="#E6E8F2", zeroline=False,
                   title="Carga horária de extensão / carga horária do curso"),
        yaxis=dict(tickmode="array", tickvals=list(dados.index), ticktext=rotulos, autorange="reversed",
                   automargin=True, showgrid=True, gridcolor="#F0F1F8", title=""),
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
        grafico_ranking=grafico_ranking_meta(ativos),
        grafico_meta_centros=grafico_meta_por_centro(meta_centros),
        tabela_meta_centros=[
            {"centro": centro, **{k: int(linha[k]) for k in CLASSES_META}, "total": int(linha["TOTAL"]),
             "media": formatar_percentual(linha["MEDIA"])}
            for centro, linha in meta_centros.iterrows()
        ],
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
