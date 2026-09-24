import csv
import json
import os
from pathlib import Path

import gspread
from gspread.utils import ValueRenderOption

ABA = "ANÁLISE CURRICULAR"
COLUNAS_EXCLUIDAS = {"NOTAS_FASE2"}
SAIDA = Path(__file__).resolve().parent.parent / "data" / "analise_curricular.csv"


def main():
    credenciais = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    planilha = gspread.service_account_from_dict(credenciais).open_by_key(os.environ["SHEET_ID"])
    linhas = planilha.worksheet(ABA).get_all_values(value_render_option=ValueRenderOption.unformatted)

    cabecalho = [c.strip() for c in linhas[1]]
    manter = [i for i, nome in enumerate(cabecalho) if nome and nome not in COLUNAS_EXCLUIDAS]

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with SAIDA.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow([cabecalho[i] for i in manter])
        for linha in linhas[2:]:
            if len(linha) > 0 and str(linha[0]).strip():
                escritor.writerow([linha[i] if i < len(linha) else "" for i in manter])


if __name__ == "__main__":
    main()
