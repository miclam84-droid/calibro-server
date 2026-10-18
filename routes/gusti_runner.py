# ============================================================
# GUSTI-SEARCH-RUNNER — pagina admin che fa girare /admin/deriva-gusti-search
# a lotti IN SEQUENZA nel browser: UN clic invece di 150 chiamate a mano.
#
# NON reimplementa niente della logica USDA. È solo un'interfaccia che richiama
# ripetutamente l'endpoint esistente (deriva_gusti_search), legge `prossimo_offset`
# e `fine` dalla risposta e continua finché il grafo è esaurito, con una PAUSA tra
# un lotto e l'altro per rispettare il rate USDA (1000/h). Tutta la sicurezza
# (fill-only, backup, alta confidenza) resta nell'endpoint: qui si guida, non si forza.
#
# Secret: letto da `?s=` dell'URL della pagina stessa, così si apre con
#   /admin/gusti-search-runner?s=ADMIN_SECRET
# e il JS lo gira all'endpoint. Path RELATIVI: eredita l'host della pagina, quindi
# funziona identico su staging e su prod senza modifiche.
# ============================================================
from flask import Blueprint, Response

bp_gusti_runner = Blueprint("gusti_runner", __name__)

_PAGINA = r"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Runner derivazione gusti USDA</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    max-width: 760px; margin: 0 auto; padding: 24px 16px; line-height: 1.5;
    background: #faf9f7; color: #1c1b19;
  }
  @media (prefers-color-scheme: dark) {
    body { background: #16150f; color: #ece9e0; }
    .card, .riga-log { background: #211f17; border-color: #35322550; }
    code { background: #00000040; }
  }
  h1 { font-size: 1.3rem; margin: 0 0 4px; }
  p.sub { margin: 0 0 20px; opacity: .75; font-size: .92rem; }
  .card { background: #fff; border: 1px solid #e7e3d9; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
  button {
    font: inherit; font-weight: 600; padding: 10px 18px; border-radius: 9px; cursor: pointer;
    border: 1px solid transparent;
  }
  #avvia { background: #2f6f4f; color: #fff; }
  #avvia:disabled { opacity: .45; cursor: not-allowed; }
  #ferma { background: transparent; border-color: #b5452f; color: #b5452f; margin-left: 8px; }
  #ferma:disabled { opacity: .4; cursor: not-allowed; }
  .barra-esterna { height: 10px; background: #00000018; border-radius: 6px; overflow: hidden; margin: 14px 0 8px; }
  .barra-interna { height: 100%; width: 0; background: #2f6f4f; transition: width .35s ease; }
  .metriche { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-top: 12px; }
  .metrica { background: #00000008; border-radius: 9px; padding: 10px 12px; }
  .metrica .n { font-size: 1.5rem; font-weight: 700; font-variant-numeric: tabular-nums; }
  .metrica .et { font-size: .78rem; opacity: .7; }
  #stato { font-weight: 600; margin-top: 10px; min-height: 1.4em; }
  #stato.errore { color: #b5452f; }
  #stato.fatto { color: #2f6f4f; }
  #log { margin-top: 14px; max-height: 320px; overflow: auto; font-size: .82rem; }
  .riga-log { background: #fafafa; border: 1px solid #eee; border-radius: 7px; padding: 6px 10px; margin-bottom: 5px; font-variant-numeric: tabular-nums; }
  code { background: #00000010; padding: 1px 5px; border-radius: 4px; font-size: .85em; }
  .avviso { font-size: .85rem; opacity: .8; }
</style>
</head>
<body>
  <h1>Runner derivazione gusti USDA</h1>
  <p class="sub">Fa girare <code>/admin/deriva-gusti-search</code> a lotti, in sequenza, con pausa anti-rate. Un clic, non 150. Scrive solo i match ad alta confidenza (fill-only, backup) — la logica è tutta nell'endpoint, qui si guida soltanto.</p>

  <div class="card">
    <button id="avvia">Avvia</button>
    <button id="ferma" disabled>Ferma</button>
    <div class="barra-esterna"><div class="barra-interna" id="barra"></div></div>
    <div id="stato">Pronto. Premi Avvia.</div>

    <div class="metriche">
      <div class="metrica"><div class="n" id="m-offset">0</div><div class="et">offset corrente</div></div>
      <div class="metrica"><div class="n" id="m-ricerche">0</div><div class="et">ricerche USDA totali</div></div>
      <div class="metrica"><div class="n" id="m-scritti">0</div><div class="et">profili gusto scritti (alta)</div></div>
      <div class="metrica"><div class="n" id="m-senzaen">0</div><div class="et">saltati senza nome EN</div></div>
    </div>
  </div>

  <div id="log"></div>
  <p class="avviso">Pausa ~4s tra un lotto e l'altro per rispettare il limite USDA (1000 ricerche/ora). Lotti da 12 ricerche. Se un lotto fallisce, il runner si ferma e mostra l'errore — niente loop infinito.</p>

<script>
(function () {
  "use strict";

  // Secret dall'URL della pagina stessa (?s=...). Path relativi: eredita l'host,
  // così funziona identico su staging e su prod.
  var SEC = new URLSearchParams(location.search).get("s") || "";

  var LIMITE = 12;        // ricerche USDA per lotto (l'endpoint va in timeout oltre ~15)
  var PAUSA_MS = 4000;    // pausa anti-rate tra un lotto e l'altro

  var elAvvia = document.getElementById("avvia");
  var elFerma = document.getElementById("ferma");
  var elBarra = document.getElementById("barra");
  var elStato = document.getElementById("stato");
  var elLog = document.getElementById("log");
  var mOffset = document.getElementById("m-offset");
  var mRicerche = document.getElementById("m-ricerche");
  var mScritti = document.getElementById("m-scritti");
  var mSenzaEn = document.getElementById("m-senzaen");

  var inCorso = false;
  var fermato = false;
  var cumRicerche = 0, cumScritti = 0, cumSenzaEn = 0, lotti = 0;

  function stato(msg, cls) {
    elStato.textContent = msg;
    elStato.className = cls || "";
  }

  function log(msg) {
    var d = document.createElement("div");
    d.className = "riga-log";
    d.textContent = msg;
    elLog.insertBefore(d, elLog.firstChild);
  }

  function pausa(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  // Barra senza totale noto: avanza verso 95% in modo asintotico, 100% a 'fine'.
  function aggiornaBarra(fine) {
    if (fine) { elBarra.style.width = "100%"; return; }
    var p = 100 * (1 - Math.pow(0.82, lotti));   // 0,18,33,45... satura sotto 95
    if (p > 95) p = 95;
    elBarra.style.width = p.toFixed(1) + "%";
  }

  async function unLotto(offset) {
    var url = "/admin/deriva-gusti-search?s=" + encodeURIComponent(SEC) +
              "&limite=" + LIMITE + "&offset=" + offset + "&esegui=1";
    var resp = await fetch(url, { headers: { "Accept": "application/json" } });
    var testo = await resp.text();
    var dati;
    try { dati = JSON.parse(testo); }
    catch (e) { throw new Error("risposta non-JSON (HTTP " + resp.status + "): " + testo.slice(0, 160)); }
    if (!resp.ok || dati.errore) {
      throw new Error("HTTP " + resp.status + " — " + (dati.errore || testo.slice(0, 160)));
    }
    return dati;
  }

  async function avvia() {
    if (inCorso) return;
    if (!SEC) { stato("Manca il secret: apri la pagina con ?s=ADMIN_SECRET nell'URL.", "errore"); return; }

    inCorso = true; fermato = false;
    cumRicerche = 0; cumScritti = 0; cumSenzaEn = 0; lotti = 0;
    elAvvia.disabled = true; elFerma.disabled = false;
    elBarra.style.width = "0";
    elLog.innerHTML = "";
    stato("Avvio…");

    var offset = 0;
    try {
      while (!fermato) {
        lotti++;
        stato("Lotto " + lotti + " — offset " + offset + " (ricerca USDA in corso…)");
        var d = await unLotto(offset);

        cumRicerche += (d.ricerche_usda || 0);
        cumScritti += (d.scritti || 0);
        cumSenzaEn += (d.saltati_senza_nome_en || 0);

        mOffset.textContent = offset;
        mRicerche.textContent = cumRicerche;
        mScritti.textContent = cumScritti;
        mSenzaEn.textContent = cumSenzaEn;

        log("Lotto " + lotti + ": offset " + offset +
            " → ricerche " + (d.ricerche_usda || 0) +
            ", scritti-alta " + (d.scritti || 0) +
            ", senza-EN " + (d.saltati_senza_nome_en || 0) +
            (d.fine ? "  [FINE]" : ""));

        aggiornaBarra(!!d.fine);

        if (d.fine === true || d.prossimo_offset === null || d.prossimo_offset === undefined) {
          break;
        }
        offset = d.prossimo_offset;

        // pausa anti-rate prima del prossimo lotto
        stato("Pausa " + (PAUSA_MS / 1000) + "s (rispetto rate USDA)…");
        await pausa(PAUSA_MS);
      }

      if (fermato) {
        stato("Fermato. Profili gusto scritti finora: " + cumScritti + ".", "");
      } else {
        elBarra.style.width = "100%";
        stato("Completato. Profili gusto scritti (alta confidenza): " + cumScritti +
              " su " + cumRicerche + " ricerche USDA.", "fatto");
        log("RIEPILOGO — scritti " + cumScritti + ", ricerche " + cumRicerche +
            ", saltati senza EN " + cumSenzaEn + ".");
      }
    } catch (e) {
      stato("Errore, runner fermato: " + e.message, "errore");
      log("ERRORE: " + e.message);
    } finally {
      inCorso = false;
      elAvvia.disabled = false;
      elFerma.disabled = true;
    }
  }

  function ferma() {
    if (!inCorso) return;
    fermato = true;
    elFerma.disabled = true;
    stato("Interruzione richiesta: finisco il lotto in corso e mi fermo…");
  }

  elAvvia.addEventListener("click", avvia);
  elFerma.addEventListener("click", ferma);
})();
</script>
</body>
</html>"""


@bp_gusti_runner.route("/admin/gusti-search-runner")
def gusti_search_runner():
    """Serve la pagina HTML del runner (nessuna logica USDA qui, nessuna scrittura).
    Il secret arriva via ?s= ed è usato solo lato browser per chiamare l'endpoint
    esistente /admin/deriva-gusti-search, che fa il vero controllo di autorizzazione."""
    return Response(_PAGINA, mimetype="text/html; charset=utf-8")
