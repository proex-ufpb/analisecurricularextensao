import csv
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).parent / "fixtures" / "analise_curricular_2026-09-24.csv"
README = (RAIZ / "README.md").read_text(encoding="utf-8")
DOCS = [RAIZ / "README.md"] + sorted((RAIZ / "docs").rglob("*.*"))


def test_documentacao_publica_nao_tem_dados_pessoais_nem_segredos():
    for arquivo in DOCS:
        texto = arquivo.read_text(encoding="utf-8")
        assert "creditacaodaextensaoufpb" not in texto, arquivo.name
        assert "github_pat_" not in texto and "ghp_" not in texto, arquivo.name
        assert "BEGIN PRIVATE KEY" not in texto, arquivo.name


def test_codigo_do_apps_script_publico_usa_marcador_no_lugar_do_e_mail():
    codigo = (RAIZ / "docs" / "apps-script" / "Codigo.gs").read_text(encoding="utf-8")
    assert 'const EMAIL_AUTORIZADO = "conta-autorizada@exemplo.com";' in codigo


def test_caminhos_citados_no_readme_existem():
    caminhos = re.findall(r"^\| `([^`|]+)`", README, re.M)
    assert len(caminhos) >= 10
    for caminho in caminhos:
        for parte in (p.strip() for p in caminho.split(",")):
            assert (RAIZ / parte).exists(), parte


def test_colunas_citadas_no_readme_existem_na_planilha():
    with FIXTURE.open(encoding="utf-8") as f:
        cabecalho = {c.strip() for c in next(csv.reader(f))}
    citadas = ["CÓDIGO E-MEC", "STATUS", "SITUAÇÃO", "% CH_INTEGRALIZADA_EXTENSAO", "%CH_EXT_DISPONÍVEL",
               "CH_TOTAL_EXT", "CH_UCE", "QTDE_UCE", "M.CURRICULAR", "PPC_ANO_NOVO", "PROCESSO", "RESOLUÇÃO"]
    for coluna in citadas:
        assert f"`{coluna}`" in README, coluna
        assert coluna in cabecalho, coluna


def test_segredos_citados_no_readme_sao_usados_pelos_workflows():
    workflows = "".join(p.read_text(encoding="utf-8") for p in (RAIZ / ".github" / "workflows").glob("*.yml"))
    segredos = ["GOOGLE_SERVICE_ACCOUNT_JSON", "SHEET_ID", "MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_TO"]
    for segredo in segredos:
        assert f"`{segredo}`" in README, segredo
        assert f"secrets.{segredo}" in workflows, segredo


def test_agendamento_descrito_no_readme_confere_com_o_workflow():
    workflow = (RAIZ / ".github" / "workflows" / "atualizar-dados.yml").read_text(encoding="utf-8")
    assert 'cron: "0 9 * * *"' in workflow  # 09:00 UTC = 06h de Brasília
    assert "06h" in README
