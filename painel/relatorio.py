import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from painel.acoes import acoes_prioritarias
from painel.dados import CSV_PADRAO, carregar_linhas, cursos_ativos, cursos_unicos
from painel.metricas import com_meta, resumo_status
from painel.tema import AZUL_PROEX, CONTATO, URL_PAINEL

RAIZ = Path(__file__).resolve().parent.parent
SAIDA_RELATORIO = RAIZ / "relatorio"
FUSO_BRASILIA = timezone(timedelta(hours=-3))
NOMES_NIVEL = {1: "Prioridade 1 — ação imediata", 2: "Prioridade 2 — em tramitação", 3: "Prioridade 3 — a iniciar"}


def gerar(csv=CSV_PADRAO, saida=SAIDA_RELATORIO, solicitante="", agora=None):
    """Gera relatorio.html (corpo do e-mail) e assunto.txt. O relatório não é publicado no site."""
    agora = agora or datetime.now(FUSO_BRASILIA)
    cursos = com_meta(cursos_unicos(carregar_linhas(csv)))
    ativos = cursos_ativos(cursos)
    resultado = acoes_prioritarias(cursos)

    ambiente = Environment(
        loader=FileSystemLoader(Path(__file__).resolve().parent / "templates"),
        autoescape=select_autoescape(["html", "j2"]),
    )
    html = ambiente.get_template("relatorio.html.j2").render(
        data=agora.strftime("%d/%m/%Y"),
        hora=agora.strftime("%H:%M"),
        solicitante=solicitante,
        n_ativos=len(ativos),
        status=resumo_status(ativos),
        prioridades=resultado["prioridades"],
        alertas=resultado["alertas"],
        por_centro=resultado["por_centro"],
        nomes_nivel=NOMES_NIVEL,
        total_acoes=sum(len(p["itens"]) for p in resultado["prioridades"]),
        azul=AZUL_PROEX,
        contato=CONTATO,
        url_painel=URL_PAINEL,
    )
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "relatorio.html").write_text(html, encoding="utf-8")
    assunto = f"Relatório de Ações Prioritárias — Análise Curricular ({agora.strftime('%d/%m/%Y')})"
    (saida / "assunto.txt").write_text(assunto, encoding="utf-8")
    return saida / "relatorio.html"


def main():
    parser = argparse.ArgumentParser(description="Gera o Relatório de Ações Prioritárias.")
    parser.add_argument("--csv", type=Path, default=CSV_PADRAO)
    parser.add_argument("--saida", type=Path, default=SAIDA_RELATORIO)
    parser.add_argument("--solicitante", default="")
    argumentos = parser.parse_args()
    print(gerar(argumentos.csv, argumentos.saida, argumentos.solicitante))


if __name__ == "__main__":
    main()
