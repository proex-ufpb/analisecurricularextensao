import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader, select_autoescape
from plotly.offline import get_plotlyjs

from painel.dados import CSV_PADRAO, PRIORIDADE_STATUS, carregar_linhas, cursos_ativos, cursos_unicos
from painel.metricas import (
    COMPONENTES,
    LIMITE_MAXIMO,
    LIMITE_MINIMO,
    ROTULOS_COMPONENTES,
    ROTULOS_UCE,
    ROTULOS_STATUS,
    com_meta,
    componentes_por_centro,
    cursos_com_extensao,
    linhas_componentes,
    implantados_por_periodo,
    linhas_oferta,
    linhas_periodo,
    linhas_uce,
    linhas_tabela,
    oferta_por_centro,
    uce_por_centro,
    resumo_componentes,
    resumo_oferta,
    resumo_uce,
    resumo_status,
    status_por_centro,
)
from painel.tema import (
    AZUL_PROEX,
    CONTATO,
    COR_TEXTO_COMPONENTES,
    COR_TEXTO_NA_BARRA,
    CORES_COMPONENTES,
    COR_UCE,
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
                + ": %{x} curso(s) (%{customdata:.0f}% do Centro)<extra></extra>"
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
                + ": %{customdata:.0f} h (%{x:.0f}% da carga horária de extensão do Centro)<extra></extra>"
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
        xaxis=dict(title="Participação na carga horária de extensão do Centro", ticksuffix="%", range=[0, 100],
                   gridcolor="#E6E8F2", zeroline=False),
        yaxis=dict(autorange="reversed", automargin=True, title=""),
        hoverlabel=dict(font=dict(family=FONTE)),
    )
    return _html(fig)


def grafico_exigencia_oferta(tabela):
    """Média por Centro do % que o aluno integraliza e do % que o curso oferta, com a faixa de 10% a 15%."""
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
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="right", x=1, title_text="", traceorder="normal",
                    bgcolor="rgba(255,255,255,0.9)", bordercolor="#DDE0EE", borderwidth=1),
        xaxis=dict(title="Média dos cursos do Centro", ticksuffix="%", range=[0, 36], dtick=5, gridcolor="#E6E8F2",
                   zeroline=False),
        yaxis=dict(autorange="reversed", automargin=True, title=""),
        hoverlabel=dict(font=dict(family=FONTE)),
    )
    return _html(fig)


def grafico_uce_por_centro(tabela):
    centros = list(tabela.index)
    fig = go.Figure()
    fig.add_bar(
        y=centros,
        x=tabela["UCES"],
        orientation="h",
        marker=dict(color=COR_UCE, line=dict(color="#FFFFFF", width=1)),
        text=[f"{v:.0f}" for v in tabela["UCES"]],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=12, color="#15163A"),
        customdata=list(zip(tabela["COM_UCE"], tabela["CURSOS"], tabela["HORAS"], tabela["CREDITOS"])),
        hovertemplate=(
            "<b>%{y}</b><br>%{x:.0f} UCE(s)<br>%{customdata[0]} de %{customdata[1]} curso(s) com UCE"
            "<br>%{customdata[2]:.0f} h e %{customdata[3]:.1f} créditos<extra></extra>"
        ),
    )
    fig.update_layout(
        height=max(320, 34 * len(centros) + 90),
        margin=dict(l=8, r=40, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONTE, size=13, color="#15163A"),
        separators=",.",
        showlegend=False,
        xaxis=dict(title="Quantidade de UCEs", gridcolor="#E6E8F2", zeroline=False, rangemode="tozero"),
        yaxis=dict(autorange="reversed", automargin=True, title=""),
        hoverlabel=dict(font=dict(family=FONTE)),
    )
    return _html(fig)


def grafico_implantados_por_periodo(periodos):
    fig = go.Figure()
    fig.add_bar(
        x=[p["periodo"] for p in periodos],
        y=[p["total"] for p in periodos],
        marker=dict(color=CORES_STATUS["IMPLANTADO"], line=dict(color="#FFFFFF", width=1)),
        text=[str(p["total"]) if p["total"] else "" for p in periodos],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=13, color="#15163A"),
        hovertemplate="<b>PPC %{x}</b><br>%{y} curso(s) implantado(s)<extra></extra>",
    )
    fig.update_layout(
        height=380,
        margin=dict(l=8, r=8, t=24, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONTE, size=13, color="#15163A"),
        showlegend=False,
        bargap=0.3,
        xaxis=dict(title="Período do PPC novo (ano.semestre)", type="category", gridcolor="#E6E8F2"),
        yaxis=dict(title="Cursos implantados", gridcolor="#E6E8F2", zeroline=False, rangemode="tozero", dtick=2),
        hoverlabel=dict(font=dict(family=FONTE)),
    )
    return _html(fig)


def construir(csv=CSV_PADRAO, saida=SAIDA):
    linhas = carregar_linhas(csv)
    cursos = com_meta(cursos_unicos(linhas))
    ativos = cursos_ativos(cursos)
    por_centro = status_por_centro(ativos)
    base_extensao = cursos_com_extensao(ativos)
    resumo_comp, total_horas = resumo_componentes(base_extensao)
    oferta = resumo_oferta(base_extensao)
    periodos, sem_periodo = implantados_por_periodo(ativos)

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
        componentes=COMPONENTES,
        rotulos_componentes=ROTULOS_COMPONENTES,
        rotulos_uce=ROTULOS_UCE,
        cores_componentes=CORES_COMPONENTES,
        resumo_componentes=resumo_comp,
        total_horas=total_horas,
        n_extensao=len(base_extensao),
        grafico_componentes=grafico_componentes_por_centro(componentes_por_centro(base_extensao)),
        linhas_componentes=linhas_componentes(base_extensao),
        oferta=oferta,
        grafico_periodo=grafico_implantados_por_periodo(periodos),
        periodos=periodos,
        sem_periodo=sem_periodo,
        linhas_periodo=linhas_periodo(ativos),
        uce=resumo_uce(base_extensao),
        cor_uce=COR_UCE,
        grafico_uce=grafico_uce_por_centro(uce_por_centro(base_extensao)),
        linhas_uce=linhas_uce(base_extensao),
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
