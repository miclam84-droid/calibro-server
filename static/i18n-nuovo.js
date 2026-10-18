/* ============================================================================
   i18n-nuovo.js — motore di traduzione per il NUOVO frontend (it · en · es)
   ----------------------------------------------------------------------------
   Allineato alla convenzione di static/matter.js:
     - ciclo lingua it -> en -> es
     - scelta persistita in localStorage, chiave 'matter_lang' (la STESSA del
       vecchio app: così la scelta è condivisa fra i due frontend)
     - override via ?lang= nell'URL, poi lingua del dispositivo, poi 'it'
     - helper _L({it,en,es}) identico a quello di matter.js (riga ~2309)

   Uso in una pagina:
     1) definisci, PRIMA di includere questo file:
          window.I18N_DICT  = { chiave: {it:'…', en:'…', es:'…'}, … };
          window.I18N_TITLE = {it:'…', en:'…', es:'…'};        // opzionale: <title>
          window.onI18nApply = function(lang){ … };            // opzionale: ri-render JS
     2) marca il testo statico nel template con:
          data-i18n="chiave"        -> textContent
          data-i18n-html="chiave"   -> innerHTML (quando servono tag interni)
          data-i18n-ph="chiave"     -> placeholder
          data-i18n-aria="chiave"   -> aria-label
          data-i18n-title="chiave"  -> attributo title
     3) includi:  <script src="/static/i18n-nuovo.js"></script>

   Lo switcher (bottone #lang-switch) viene montato da solo nella .topbar-in e
   usa SOLO i token di matter3.css (pelle congelata). Nessuna dipendenza esterna.
   ========================================================================== */
(function(){
  "use strict";

  var OK = ["it", "en", "es"];

  function rileva(){
    try{
      var u = new URLSearchParams(location.search).get("lang");
      if (u && OK.indexOf(u) >= 0) return u;
      var s = localStorage.getItem("matter_lang");
      if (s && OK.indexOf(s) >= 0) return s;
    }catch(e){ /* storage non disponibile: proseguo */ }
    try{
      var n = (navigator.language || "it").slice(0, 2).toLowerCase();
      if (OK.indexOf(n) >= 0) return n;
    }catch(e){ /* niente navigator.language: resto su it */ }
    return "it";
  }

  var _lang = rileva();
  window._lang = _lang;

  /* helper identico a matter.js: ritorna la variante nella lingua corrente,
     con fallback all'italiano. Esposto come globale per le stringhe generate
     da JS nelle singole pagine. */
  function _L(o){
    if (!o) return "";
    return (o[_lang] != null) ? o[_lang] : o.it;
  }
  window._L = _L;

  /* vocabolario condiviso: termini di provenienza/stato ricorrenti in più
     pagine, così le traduzioni restano coerenti ovunque. _V('derivato')
     ritorna la parola nella lingua corrente; se la chiave non esiste
     ritorna il valore grezzo (dato dinamico dal backend non mappato). */
  var VOCAB = {
    verificato: {it:"verificato", en:"verified",  es:"verificado"},
    "da fonte": {it:"da fonte",   en:"from source", es:"de fuente"},
    derivato:   {it:"derivato",   en:"derived",    es:"derivado"},
    stimato:    {it:"stimato",    en:"estimated",  es:"estimado"},
    proposta:   {it:"proposta",   en:"proposal",   es:"propuesta"},
    supportato: {it:"supportato", en:"supported",  es:"respaldado"},
    alta:       {it:"alta",       en:"high",       es:"alta"},
    media:      {it:"media",      en:"medium",     es:"media"},
    bassa:      {it:"bassa",      en:"low",        es:"baja"}
  };
  function _V(raw){
    var k = String(raw == null ? "" : raw).toLowerCase().trim();
    return VOCAB[k] ? _L(VOCAB[k]) : String(raw == null ? "" : raw);
  }
  window._V = _V;

  function valore(dict, chiave){
    var e = dict[chiave];
    if (e == null) return null;
    return (e[_lang] != null) ? e[_lang] : e.it;
  }

  function applica(){
    var dict = window.I18N_DICT || {};
    try{ document.documentElement.lang = _lang; }catch(e){}

    document.querySelectorAll("[data-i18n]").forEach(function(el){
      var v = valore(dict, el.getAttribute("data-i18n"));
      if (v != null) el.textContent = v;
    });
    document.querySelectorAll("[data-i18n-html]").forEach(function(el){
      var v = valore(dict, el.getAttribute("data-i18n-html"));
      if (v != null) el.innerHTML = v;
    });
    document.querySelectorAll("[data-i18n-ph]").forEach(function(el){
      var v = valore(dict, el.getAttribute("data-i18n-ph"));
      if (v != null) el.setAttribute("placeholder", v);
    });
    document.querySelectorAll("[data-i18n-aria]").forEach(function(el){
      var v = valore(dict, el.getAttribute("data-i18n-aria"));
      if (v != null) el.setAttribute("aria-label", v);
    });
    document.querySelectorAll("[data-i18n-title]").forEach(function(el){
      var v = valore(dict, el.getAttribute("data-i18n-title"));
      if (v != null) el.setAttribute("title", v);
    });

    if (window.I18N_TITLE){
      var t = (window.I18N_TITLE[_lang] != null) ? window.I18N_TITLE[_lang] : window.I18N_TITLE.it;
      if (t != null) try{ document.title = t; }catch(e){}
    }

    var btn = document.getElementById("lang-switch");
    if (btn) btn.textContent = _lang.toUpperCase();

    // le pagine con contenuto generato da JS si ridisegnano qui
    if (typeof window.onI18nApply === "function"){
      try{ window.onI18nApply(_lang); }catch(e){ /* un hook che rompe non deve bloccare la UI */ }
    }
  }
  window.applyI18n = applica;

  function ciclo(){
    _lang = (_lang === "it") ? "en" : (_lang === "en" ? "es" : "it");
    window._lang = _lang;
    try{ localStorage.setItem("matter_lang", _lang); }catch(e){}
    applica();
  }
  window.cycleLang = ciclo;

  /* stile dello switcher: SOLO token di matter3.css (pelle congelata).
     Niente colori nuovi, niente blu/crema/rame. Bottone-pillola discreto,
     coerente con .btn--ghost. Inietto anche un margin-left:auto sull'eyebrow
     della topbar così lo switcher resta in alto a destra e il wordmark a
     sinistra — stesso aspetto di prima, solo con lo switcher accanto. */
  function iniettaStile(){
    if (document.getElementById("lang-switch-style")) return;
    var s = document.createElement("style");
    s.id = "lang-switch-style";
    s.textContent =
      ".topbar-in > .eyebrow{margin-left:auto}" +
      ".lang-switch{flex:0 0 auto;font-family:var(--sans);font-weight:700;" +
        "font-size:11px;letter-spacing:.08em;line-height:1;color:var(--verde);" +
        "background:transparent;border:1px solid var(--verde);border-radius:var(--r-pill);" +
        "padding:5px 10px;cursor:pointer;-webkit-appearance:none;appearance:none}" +
      ".lang-switch:hover{background:var(--tint)}" +
      ".lang-switch:focus-visible{outline:2px solid var(--ink);outline-offset:2px}";
    (document.head || document.documentElement).appendChild(s);
  }

  function montaSwitcher(){
    if (document.getElementById("lang-switch")) return;
    var barra = document.querySelector(".topbar-in") || document.querySelector(".topbar");
    if (!barra) return;
    var b = document.createElement("button");
    b.id = "lang-switch";
    b.type = "button";
    b.className = "lang-switch";
    b.setAttribute("aria-label", "Lingua / Language / Idioma");
    b.setAttribute("title", "Lingua · Language · Idioma");
    b.textContent = _lang.toUpperCase();
    b.addEventListener("click", ciclo);
    barra.appendChild(b);
  }

  function init(){
    iniettaStile();
    montaSwitcher();
    applica();
  }

  if (document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
