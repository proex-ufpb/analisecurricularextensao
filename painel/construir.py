import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader, select_autoescape
from plotly.offline import get_plotlyjs

from painel.dados import CSV_PADRAO, PRIORIDADE_STATUS, carregar_linhas, cursos_ativos, cursos_unicos
from painel.metricas import ROTULOS_STATUS, linhas_tabela, resumo_status, status_por_centro
from painel.tema import AZUL_PROEX, CONTATO, COR_TEXTO_NA_BARRA, CORES_STATUS, EQUIPE

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "site"
FUSO_BRASILIA = timezone(timedelta(hours=-3))


def grafico_status_por_centro(tabela):
    centros = list(tabela.index)
    fig = go.Figure()
    for status in PRIORIDADE_STATUS:
        valores = tabela[status]
        fig.add_bar(
            y=centros,
            x=valores,
            orientation="h",
            name=ROTULOS_STATUS[status],
            marker=dict(color=CORES_STATUS[status], line=dict(color="#FFFFFF", width=2)),
            text=[str(v) if v else "" for v in valores],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color=COR_TEXTO_NA_BARRA[status], size=13),
            customdata=(valores / tabela["TOTAL"] * 100).round(0),
            hovertemplate=(
                "<b>%{y}</b><br>" + ROTULOS_STATUS[status]
                + ": %{x} curso(s) (%{customdata:.0f}% do centro)<extra></extra>"
            ),
        )
    fig.update_layout(
        barmode="stack",
        height=max(320, 34 * len(centros) + 110),
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Saira, sans-serif", size=13, color="#15163A"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text="", traceorder="normal"),
        xaxis=dict(title="Cursos ativos", gridcolor="#E6E8F2", zeroline=False, rangemode="tozero"),
        yaxis=dict(autorange="reversed", automargin=True, title=""),
        hoverlabel=dict(font=dict(family="Saira, sans-serif")),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False, "responsive": True})


def construir(csv=CSV_PADRAO, saida=SAIDA):
    linhas = carregar_linhas(csv)
    cursos = cursos_unicos(linhas)
    ativos = cursos_ativos(cursos)
    por_centro = status_por_centro(ativos)

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
