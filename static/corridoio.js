/* ============================================================
   corridoio.js — "il corridoio è un oggetto di lavoro che porta il contesto".
   Stub del modello: lo stato del lavoro corrente (es. l'ingrediente che
   stai guardando, le preparazioni in corso) viaggia con te tra le schermate.
   Qui salviamo/leggiamo quello stato in sessionStorage.
   R3 (Componi) userà corridoio.get() per sapere da dove arrivi e con cosa,
   e corridoio.set() per lasciare il contesto a chi viene dopo.
   ============================================================ */
(function (global) {
  "use strict";

  var CHIAVE = "matter:corridoio";

  var corridoio = {
    // salva lo stato del lavoro corrente, es. {ingrediente:"limone", preparazione:[]}
    set: function (stato) {
      try {
        sessionStorage.setItem(CHIAVE, JSON.stringify(stato || {}));
      } catch (e) {
        /* modalità privata / storage bloccato: il corridoio resta vuoto, nessun errore */
      }
      return stato;
    },

    // legge lo stato corrente; default coerente se non c'è nulla
    get: function () {
      try {
        var grezzo = sessionStorage.getItem(CHIAVE);
        return grezzo ? JSON.parse(grezzo) : { ingrediente: null, preparazione: [] };
      } catch (e) {
        return { ingrediente: null, preparazione: [] };
      }
    }
  };

  global.corridoio = corridoio;
})(window);
