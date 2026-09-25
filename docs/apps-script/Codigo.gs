// Aplicativo web do Google Apps Script: botão "Enviar relatório" com login Google.
// Só a conta abaixo consegue disparar o envio. O token do GitHub fica em "Propriedades do script" (nunca no código).

// Troque pelo e-mail da conta Google autorizada a enviar o relatório (em minúsculas).
const EMAIL_AUTORIZADO = "conta-autorizada@exemplo.com";
const REPOSITORIO = "proex-ufpb/analisecurricularextensao";
const WORKFLOW = "enviar-relatorio.yml";

function emailDeQuemAcessa_() {
  return (Session.getActiveUser().getEmail() || "").toLowerCase();
}

function doGet() {
  const email = emailDeQuemAcessa_();
  const pagina = HtmlService.createTemplateFromFile("Pagina");
  pagina.email = email;
  pagina.autorizado = email === EMAIL_AUTORIZADO;
  pagina.ultimoEnvio = PropertiesService.getScriptProperties().getProperty("ULTIMO_ENVIO") || "";
  return pagina.evaluate().setTitle("Enviar relatório — PROEX/UFPB");
}

function enviarRelatorio() {
  const email = emailDeQuemAcessa_();
  if (email !== EMAIL_AUTORIZADO) {
    throw new Error("Conta não autorizada para enviar o relatório.");
  }
  const token = PropertiesService.getScriptProperties().getProperty("GITHUB_TOKEN");
  if (!token) {
    throw new Error("Token do GitHub não configurado nas propriedades do script.");
  }
  const resposta = UrlFetchApp.fetch(
    "https://api.github.com/repos/" + REPOSITORIO + "/actions/workflows/" + WORKFLOW + "/dispatches",
    {
      method: "post",
      contentType: "application/json",
      headers: {
        Authorization: "Bearer " + token,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      payload: JSON.stringify({ ref: "main", inputs: { solicitante: email } }),
      muteHttpExceptions: true,
    }
  );
  if (resposta.getResponseCode() !== 204) {
    throw new Error("O GitHub respondeu com o código " + resposta.getResponseCode() + ".");
  }
  const agora = Utilities.formatDate(new Date(), "America/Sao_Paulo", "dd/MM/yyyy 'às' HH:mm");
  PropertiesService.getScriptProperties().setProperty("ULTIMO_ENVIO", agora + " por " + email);
  return "Envio solicitado em " + agora + ". O relatório chega por e-mail em alguns minutos.";
}
