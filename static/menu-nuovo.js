/* ============================================================================
   menu-nuovo.js — CREATORE DI CARTE (Matter Bench)
   ----------------------------------------------------------------------------
   Due anime:
     1) VOCE LIBERA — l'utente scrive QUALSIASI voce (nome, prezzo, descrizione,
        sezione). Una pizza, un vino, un cocktail non sono preparazioni
        scientifiche: vanno scritti a mano.
     2) PREPARAZIONE PROFILATA — quando una voce E' una preparazione salvata
        (funzione="composer" nel Quaderno), la si aggancia. Tocco scientifico:
        gli ingredienti profilati arricchiscono la voce (allergeni dedotti).
   Poi un passo DESIGN & ESPORT: tipo carta, template, colore, logo, footer,
   anteprima HTML e PDF scaricabile (il deliverable).

   Backend (NON modificato): /v1/menu/crea · /v1/menu/<mid>/salva ·
   /v1/menu/upload-logo · /v1/menu/<mid>/render · /v1/menu/<mid>/pdf.
   Design congelato: solo i token di matter3.css. i18n it/en/es via _L().
   Anonimo: X-Device-Id da localStorage 'matter_device_id'.
   ========================================================================== */
(function () {
  "use strict";

  /* ─── identita' dispositivo (stesso pattern delle altre pagine nuove) ─── */
  function devId() {
    try {
      var d = localStorage.getItem("matter_device_id") || localStorage.getItem("matter_token");
      if (!d) {
        d = (window.crypto && crypto.randomUUID)
          ? crypto.randomUUID()
          : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
              var r = Math.random() * 16 | 0, v = c === "x" ? r : (r & 0x3 | 0x8);
              return v.toString(16);
            });
        localStorage.setItem("matter_device_id", d);
      }
      return d;
    } catch (e) { return "anon"; }
  }

  function L(o) { return (window._L ? window._L(o) : (o && (o.it || ""))); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function cap(s) { s = String(s || ""); return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }
  function dataOggi() {
    var dt = new Date(), z = function (n) { return (n < 10 ? "0" : "") + n; };
    return dt.getFullYear() + "-" + z(dt.getMonth() + 1) + "-" + z(dt.getDate());
  }
  function lang() { return window._lang || "it"; }

  /* ─── stato ─── */
  var voci = [];            // [{uid, tipo:'libera'|'profilata', nome, prezzo, descrizione, sezione, ricetta_id?, ingredienti?, prep_id?}]
  var disponibili = [];     // [{id, titolo, creato}]
  var _uidSeq = 0;
  var editUid = null;       // uid della voce in modifica in-place (null = nessuna)
  var stato = {
    tipoUI: "food",         // food | pizze | drink | vini
    mid: null,              // id del menu salvato
    tipoSalvato: null       // tipo_menu con cui il menu e' stato creato (per decidere crea vs salva)
  };
  var design = {
    template: "matter-verde",
    accent: "",             // hex con # (vuoto = usa quello del template)
    logoUrl: "",
    footer: "",
    font: "auto"            // auto | serif | sans
  };

  /* tipo UI -> tipo_menu del backend (pizze->food, food->food, drink->drink, vini->wine) */
  function tipoMenu() {
    return { food: "food", pizze: "food", drink: "drink", vini: "wine" }[stato.tipoUI] || "food";
  }

  /* ─── riferimenti DOM ─── */
  var segTipo, inpNome, inpLocale,
      lbNome, lbPrezzo, lbDesc, lbSez, btnAddLibera,
      dispStato, dispBox, dispToggle, dispWrap,
      vuoto, lista, btnSalva, salvaEsito,
      design3, dsTemplate, dsAccent, dsFooter, dsFont, dsLogoInput, dsLogoStato, dsLogoPrev,
      previewFrame, btnAnteprima, btnPdf, linkRender;

  function $(id) { return document.getElementById(id); }

  /* ─── SELETTORE TIPO CARTA ─── */
  function renderSegTipo() {
    if (!segTipo) return;
    var tipi = [
      { k: "food", lab: { it: "Food", en: "Food", es: "Food" } },
      { k: "pizze", lab: { it: "Pizze", en: "Pizzas", es: "Pizzas" } },
      { k: "drink", lab: { it: "Drink", en: "Drinks", es: "Tragos" } },
      { k: "vini", lab: { it: "Vini", en: "Wines", es: "Vinos" } }
    ];
    segTipo.innerHTML = "";
    tipi.forEach(function (t) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "seg-b" + (stato.tipoUI === t.k ? " is-on" : "");
      b.textContent = L(t.lab);
      b.setAttribute("aria-pressed", stato.tipoUI === t.k ? "true" : "false");
      b.addEventListener("click", function () {
        if (stato.tipoUI === t.k) return;
        stato.tipoUI = t.k;
        renderSegTipo();
        aggiornaSuggerimentoSezione();
      });
      segTipo.appendChild(b);
    });
  }

  /* suggerimento di sezione contestuale al tipo (solo placeholder, non vincola) */
  function aggiornaSuggerimentoSezione() {
    var ph = {
      food: { it: "es. Antipasti, Primi, Dolci", en: "e.g. Starters, Mains, Desserts", es: "p.ej. Entrantes, Principales, Postres" },
      pizze: { it: "es. Classiche, Speciali, Bianche", en: "e.g. Classic, Special, White", es: "p.ej. Clásicas, Especiales, Blancas" },
      drink: { it: "es. Signature, Classici, Analcolici", en: "e.g. Signature, Classics, Alcohol-free", es: "p.ej. Signature, Clásicos, Sin alcohol" },
      vini: { it: "es. lascia vuoto: li ordina da sé", en: "e.g. leave blank: auto-sorted", es: "p.ej. déjalo vacío: se ordena solo" }
    }[stato.tipoUI];
    var inp = $("vl-sezione");
    if (inp) inp.setAttribute("placeholder", L(ph));
  }

  /* ─── VOCE LIBERA: aggiungi ─── */
  function aggiungiLibera() {
    var nome = ($("vl-nome").value || "").trim();
    var errBox = $("vl-err");
    if (!nome) {
      errBox.hidden = false;
      errBox.textContent = L({ it: "Il nome della voce è obbligatorio.", en: "The item name is required.", es: "El nombre del elemento es obligatorio." });
      $("vl-nome").focus();
      return;
    }
    errBox.hidden = true;
    voci.push({
      uid: ++_uidSeq,
      tipo: "libera",
      nome: nome,
      prezzo: ($("vl-prezzo").value || "").trim(),
      descrizione: ($("vl-desc").value || "").trim(),
      sezione: ($("vl-sezione").value || "").trim()
    });
    // pulisco nome/prezzo/descrizione, lascio la sezione (si aggiungono piu' voci nella stessa)
    $("vl-nome").value = "";
    $("vl-prezzo").value = "";
    $("vl-desc").value = "";
    $("vl-nome").focus();
    renderVoci();
    invalidaSalvataggio();
  }

  /* ─── PREPARAZIONE PROFILATA: aggiungi (con arricchimento best-effort) ─── */
  function giaProfilata(prepId) {
    return voci.some(function (v) { return v.tipo === "profilata" && v.prep_id === prepId; });
  }
  function aggiungiProfilata(p, btn) {
    if (giaProfilata(p.id)) return;
    if (btn) { btn.disabled = true; btn.textContent = L({ it: "aggiungo…", en: "adding…", es: "añadiendo…" }); }
    // best-effort: leggo i componenti della preparazione per dedurre gli allergeni lato backend
    fetch("/v1/quaderno2/" + encodeURIComponent(p.id), {
      headers: { "Accept": "application/json", "X-Device-Id": devId() }
    })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; })
      .then(function (d) {
        var ingr = [];
        try {
          var si = d && d.record && d.record.stato_input;
          var comp = si && (si.componenti || si.ingredienti);
          if (Array.isArray(comp)) {
            ingr = comp.map(function (c) { return (c && (c.nome || c)) || ""; })
                       .filter(function (x) { return x && typeof x === "string"; });
          }
        } catch (e) { ingr = []; }
        voci.push({
          uid: ++_uidSeq,
          tipo: "profilata",
          nome: cap(p.titolo),
          prezzo: "",
          descrizione: "",
          sezione: "",
          ricetta_id: p.id,
          ingredienti: ingr,
          prep_id: p.id
        });
        renderVoci();
        renderDisp();
        invalidaSalvataggio();
      });
  }

  /* ─── RENDER: preparazioni profilate disponibili ─── */
  function renderDisp() {
    if (!dispBox) return;
    dispBox.innerHTML = "";
    disponibili.forEach(function (p) {
      var li = document.createElement("li");
      li.className = "prep";
      var corpo = document.createElement("div");
      corpo.className = "prep-corpo";
      var nome = document.createElement("div");
      nome.className = "prep-nome";
      nome.textContent = cap(p.titolo);
      corpo.appendChild(nome);
      var meta = document.createElement("span");
      meta.className = "prep-meta";
      meta.textContent = L({ it: "preparazione profilata", en: "profiled preparation", es: "preparación perfilada" }) + (p.creato ? " · " + p.creato : "");
      corpo.appendChild(meta);
      li.appendChild(corpo);

      var add = document.createElement("button");
      add.type = "button";
      add.className = "prep-add";
      var dentro = giaProfilata(p.id);
      add.textContent = dentro ? L({ it: "nel menu ✓", en: "in the menu ✓", es: "en el menú ✓" }) : L({ it: "+ nel menu", en: "+ to menu", es: "+ al menú" });
      add.disabled = dentro;
      add.setAttribute("aria-label", (dentro ? L({ it: "Già nel menu: ", en: "Already in the menu: ", es: "Ya en el menú: " }) : L({ it: "Aggiungi al menu: ", en: "Add to the menu: ", es: "Añadir al menú: " })) + cap(p.titolo));
      add.addEventListener("click", function () { aggiungiProfilata(p, add); });
      li.appendChild(add);
      dispBox.appendChild(li);
    });
  }

  /* ─── RENDER: lista voci del menu (riordinabili / eliminabili) ─── */
  function renderVoci() {
    if (!lista) return;
    lista.innerHTML = "";
    if (!voci.length) {
      vuoto.hidden = false; lista.hidden = true;
      btnSalva.disabled = true;
      return;
    }
    vuoto.hidden = true; lista.hidden = false;
    btnSalva.disabled = false;

    voci.forEach(function (v, idx) {
      // voce in modifica in-place: mostro il form precompilato al posto della riga
      if (editUid === v.uid) {
        lista.appendChild(formModifica(v, idx));
        return;
      }

      var li = document.createElement("li");
      li.className = "voce";

      var corpo = document.createElement("div");
      corpo.className = "voce-corpo";

      var riga = document.createElement("div");
      riga.className = "voce-riga";
      var nome = document.createElement("span");
      nome.className = "voce-nome";
      nome.textContent = v.nome;
      riga.appendChild(nome);
      if (v.prezzo) {
        var pr = document.createElement("span");
        pr.className = "voce-prezzo num";
        pr.textContent = v.prezzo;
        riga.appendChild(pr);
      }
      corpo.appendChild(riga);

      // meta: sezione + tipo (libera / profilata)
      var meta = document.createElement("div");
      meta.className = "voce-meta";
      var parti = [];
      if (v.sezione) parti.push(esc(v.sezione));
      if (v.tipo === "profilata") {
        parti.push('<span class="tag-prof">' + L({ it: "profilata", en: "profiled", es: "perfilada" }) + "</span>");
      }
      if (v.descrizione) parti.push('<span class="voce-desc">' + esc(v.descrizione) + "</span>");
      if (parti.length) { meta.innerHTML = parti.join(' <span class="sep">·</span> '); corpo.appendChild(meta); }

      li.appendChild(corpo);

      // controlli: modifica / su / giu / elimina
      var ctrl = document.createElement("div");
      ctrl.className = "voce-ctrl";
      var ed = document.createElement("button");
      ed.type = "button"; ed.className = "voce-mv"; ed.textContent = "✎";
      ed.setAttribute("aria-label", L({ it: "Modifica", en: "Edit", es: "Editar" }) + ": " + v.nome);
      ed.addEventListener("click", function () { apriModifica(v.uid); });
      ctrl.appendChild(ed);
      var up = document.createElement("button");
      up.type = "button"; up.className = "voce-mv"; up.textContent = "↑";
      up.disabled = idx === 0;
      up.setAttribute("aria-label", L({ it: "Sposta su", en: "Move up", es: "Subir" }) + ": " + v.nome);
      up.addEventListener("click", function () { muovi(idx, -1); });
      var dn = document.createElement("button");
      dn.type = "button"; dn.className = "voce-mv"; dn.textContent = "↓";
      dn.disabled = idx === voci.length - 1;
      dn.setAttribute("aria-label", L({ it: "Sposta giù", en: "Move down", es: "Bajar" }) + ": " + v.nome);
      dn.addEventListener("click", function () { muovi(idx, 1); });
      var x = document.createElement("button");
      x.type = "button"; x.className = "voce-x"; x.textContent = "✕";
      x.setAttribute("aria-label", L({ it: "Togli dal menu", en: "Remove from menu", es: "Quitar del menú" }) + ": " + v.nome);
      x.addEventListener("click", function () {
        voci.splice(idx, 1);
        renderVoci(); renderDisp(); invalidaSalvataggio();
      });
      ctrl.appendChild(up); ctrl.appendChild(dn); ctrl.appendChild(x);
      li.appendChild(ctrl);

      lista.appendChild(li);
    });
  }
  function muovi(idx, dir) {
    var j = idx + dir;
    if (j < 0 || j >= voci.length) return;
    var t = voci[idx]; voci[idx] = voci[j]; voci[j] = t;
    renderVoci(); invalidaSalvataggio();
  }

  /* ─── MODIFICA IN-PLACE di una voce già nella carta ───
     Riusa i campi e le validazioni del form di aggiunta (nome obbligatorio;
     sezione/prezzo/descrizione facoltativi). Per una voce PROFILATA cambia solo
     il testo visibile: uid, tipo, ricetta_id, ingredienti e prep_id restano
     intatti, così l'aggancio scientifico e gli allergeni dedotti non si perdono. */
  function campoText(id, etichetta, valore, maxlen) {
    var lab = document.createElement("label");
    lab.className = "campo"; lab.setAttribute("for", id);
    var sp = document.createElement("span"); sp.textContent = etichetta; lab.appendChild(sp);
    var inp = document.createElement("input");
    inp.type = "text"; inp.id = id; inp.maxLength = maxlen;
    inp.setAttribute("autocomplete", "off");
    inp.value = valore || "";
    lab.appendChild(inp);
    return lab;
  }
  function campoArea(id, etichetta, valore, maxlen) {
    var lab = document.createElement("label");
    lab.className = "campo"; lab.setAttribute("for", id);
    var sp = document.createElement("span"); sp.textContent = etichetta; lab.appendChild(sp);
    var ta = document.createElement("textarea");
    ta.id = id; ta.maxLength = maxlen;
    ta.value = valore || "";
    lab.appendChild(ta);
    return lab;
  }
  function apriModifica(uid) {
    editUid = uid;
    renderVoci();
    var f = $("vm-nome-" + uid);
    if (f) { try { f.focus(); var n = f.value.length; f.setSelectionRange(n, n); } catch (e) {} }
  }
  function annullaModifica() {
    editUid = null;
    renderVoci();
  }
  function salvaModifica(v) {
    var campoNome = $("vm-nome-" + v.uid);
    if (!campoNome) { editUid = null; renderVoci(); return; }
    var nome = (campoNome.value || "").trim();
    var errBox = $("vm-err-" + v.uid);
    if (!nome) {
      if (errBox) {
        errBox.hidden = false;
        errBox.textContent = L({ it: "Il nome della voce è obbligatorio.", en: "The item name is required.", es: "El nombre del elemento es obligatorio." });
      }
      try { campoNome.focus(); } catch (e) {}
      return;
    }
    // aggiorno SOLO il testo visibile; conservo gli altri campi (incl. ricetta_id/ingredienti/prep_id)
    v.nome = nome;
    v.prezzo = (($("vm-prezzo-" + v.uid) || {}).value || "").trim();
    v.descrizione = (($("vm-desc-" + v.uid) || {}).value || "").trim();
    v.sezione = (($("vm-sezione-" + v.uid) || {}).value || "").trim();
    editUid = null;
    renderVoci();
    invalidaSalvataggio();
  }
  function formModifica(v) {
    var li = document.createElement("li");
    li.className = "voce voce-edit";

    var box = document.createElement("div");
    box.className = "voce-corpo";
    box.style.width = "100%";

    var nomeLab = campoText("vm-nome-" + v.uid, L({ it: "Nome *", en: "Name *", es: "Nombre *" }), v.nome, 160);
    box.appendChild(nomeLab);
    var nomeInp = nomeLab.querySelector("input");
    if (nomeInp) {
      nomeInp.addEventListener("keydown", function (e) {
        if (e.key === "Enter") { e.preventDefault(); salvaModifica(v); }
        else if (e.key === "Escape") { e.preventDefault(); annullaModifica(); }
      });
    }

    var due = document.createElement("div");
    due.className = "libera-due";
    due.appendChild(campoText("vm-sezione-" + v.uid, L({ it: "Sezione", en: "Section", es: "Sección" }), v.sezione, 80));
    due.appendChild(campoText("vm-prezzo-" + v.uid, L({ it: "Prezzo", en: "Price", es: "Precio" }), v.prezzo, 24));
    box.appendChild(due);

    box.appendChild(campoArea("vm-desc-" + v.uid, L({ it: "Descrizione", en: "Description", es: "Descripción" }), v.descrizione, 500));

    // promemoria: per le voci profilate l'aggancio scientifico resta collegato
    if (v.tipo === "profilata") {
      var nota = document.createElement("p");
      nota.className = "voce-meta";
      nota.style.margin = "2px 0 10px";
      nota.innerHTML = '<span class="tag-prof">' + L({ it: "profilata", en: "profiled", es: "perfilada" }) + "</span> " +
        esc(L({ it: "l'aggancio alla preparazione e gli allergeni restano collegati.", en: "the link to the preparation and its allergens stay connected.", es: "el vínculo con la preparación y sus alérgenos se mantienen." }));
      box.appendChild(nota);
    }

    var err = document.createElement("div");
    err.className = "libera-err";
    err.id = "vm-err-" + v.uid;
    err.hidden = true;
    box.appendChild(err);

    var az = document.createElement("div");
    az.style.display = "flex"; az.style.gap = "10px"; az.style.flexWrap = "wrap";
    var bSalva = document.createElement("button");
    bSalva.type = "button"; bSalva.className = "btn"; bSalva.style.flex = "1 1 auto";
    bSalva.textContent = L({ it: "Salva modifica", en: "Save change", es: "Guardar cambio" });
    bSalva.addEventListener("click", function () { salvaModifica(v); });
    var bAnnulla = document.createElement("button");
    bAnnulla.type = "button"; bAnnulla.className = "btn btn--ghost"; bAnnulla.style.flex = "1 1 auto";
    bAnnulla.textContent = L({ it: "Annulla", en: "Cancel", es: "Cancelar" });
    bAnnulla.addEventListener("click", annullaModifica);
    az.appendChild(bSalva); az.appendChild(bAnnulla);
    box.appendChild(az);

    li.appendChild(box);
    return li;
  }

  /* se cambio il menu dopo averlo salvato, nascondo il passo esport finché non ri-salvo */
  function invalidaSalvataggio() {
    if (stato.mid && design3) {
      design3.classList.add("is-stale");
    }
  }

  /* ─── FETCH preparazioni profilate (funzione="composer") ─── */
  function mostraDispStato(txt, err) {
    dispBox.hidden = true;
    dispStato.hidden = false;
    dispStato.className = "stato" + (err ? " stato-err" : "");
    dispStato.innerHTML = txt;
  }
  function caricaDisponibili() {
    mostraDispStato(L({ it: "Carico le tue preparazioni salvate…", en: "Loading your saved preparations…", es: "Cargando tus preparaciones guardadas…" }));
    fetch("/v1/quaderno2/lista", { headers: { "Accept": "application/json", "X-Device-Id": devId() } })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { return { status: r.status, body: d }; }); })
      .then(function (res) {
        var d = res.body || {};
        if (res.status === 401) {
          mostraDispStato(L({ it: "Il Quaderno non ti ha riconosciuto: le preparazioni profilate non sono disponibili ora. Puoi comunque creare la carta con voci libere.", en: "The Quaderno didn't recognise you: profiled preparations aren't available now. You can still build the card with free items.", es: "El Quaderno no te reconoció: las preparaciones perfiladas no están disponibles ahora. Aún puedes crear la carta con elementos libres." }), true);
          return;
        }
        if (res.status < 200 || res.status >= 300) {
          mostraDispStato(L({ it: "Non sono riuscito a leggere le preparazioni (errore " + res.status + "). Puoi creare la carta con voci libere.", en: "I couldn't read the preparations (error " + res.status + "). You can build the card with free items.", es: "No he podido leer las preparaciones (error " + res.status + "). Puedes crear la carta con elementos libres." }), true);
          return;
        }
        var record = Array.isArray(d.record) ? d.record : (Array.isArray(d) ? d : []);
        disponibili = record
          .filter(function (r) { return r && r.funzione === "composer"; })
          .map(function (r) {
            return {
              id: r.id,
              titolo: r.titolo || L({ it: "(senza titolo)", en: "(untitled)", es: "(sin título)" }),
              creato: (r.creato_at || "").slice(0, 10) || null
            };
          });
        if (!disponibili.length) {
          mostraDispStato(L({ it: "Non hai ancora preparazioni profilate. ", en: "You have no profiled preparations yet. ", es: "Aún no tienes preparaciones perfiladas. " }) +
            '<a class="lk" href="/componi-nuovo">' + L({ it: "Componine una", en: "Compose one", es: "Compón una" }) + "</a>" +
            L({ it: " — oppure aggiungi voci libere qui sopra.", en: " — or add free items above.", es: " — o añade elementos libres arriba." }));
          return;
        }
        dispStato.hidden = true;
        dispBox.hidden = false;
        renderDisp();
      })
      .catch(function () {
        mostraDispStato(L({ it: "Il server non è raggiungibile ora: preparazioni profilate non caricate. Le voci libere funzionano lo stesso.", en: "The server is unreachable now: profiled preparations not loaded. Free items still work.", es: "El servidor no está disponible ahora: preparaciones perfiladas no cargadas. Los elementos libres funcionan igual." }), true);
      });
  }

  /* ─── SALVA il menu (crea o aggiorna) ─── */
  var salvaInCorso = false;
  function vociPayload() {
    return voci.map(function (v) {
      var o = { nome: v.nome };
      if (v.prezzo) o.prezzo = v.prezzo;
      if (v.descrizione) o.descrizione = v.descrizione;
      if (v.sezione) o.sezione = v.sezione;
      if (v.tipo === "profilata") {
        if (v.ricetta_id) o.ricetta_id = v.ricetta_id;
        if (v.ingredienti && v.ingredienti.length) o.ingredienti = v.ingredienti;
      }
      return o;
    });
  }
  function mostraEsito(html, tipo) {
    if (tipo === "pulisci") { salvaEsito.hidden = true; salvaEsito.innerHTML = ""; salvaEsito.className = "salva-esito"; return; }
    salvaEsito.hidden = false;
    salvaEsito.className = "salva-esito " + (tipo === "ok" ? "esito-ok" : "esito-err");
    salvaEsito.innerHTML = html;
  }
  function salvaMenu() {
    if (salvaInCorso) return;
    if (!voci.length) {
      mostraEsito(L({ it: "Aggiungi almeno una voce prima di salvare.", en: "Add at least one item before saving.", es: "Añade al menos un elemento antes de guardar." }), "err");
      return;
    }
    var tm = tipoMenu();
    var titolo = (inpNome.value || "").trim() || ("Menu — " + dataOggi());
    var locale = (inpLocale.value || "").trim();
    var payloadVoci = vociPayload();

    salvaInCorso = true;
    btnSalva.disabled = true;
    var testoOrig = btnSalva.textContent;
    btnSalva.textContent = L({ it: "Salvo…", en: "Saving…", es: "Guardando…" });
    mostraEsito("", "pulisci");

    // Prima volta, o tipo carta cambiato dopo la creazione -> /crea (cosi' tipo_menu è corretto,
    // es. l'auto-classificazione vini nel PDF). Altrimenti aggiorno con /salva.
    var nuovaCreazione = (!stato.mid || stato.tipoSalvato !== tm);
    var url, body;
    if (nuovaCreazione) {
      url = "/v1/menu/crea";
      body = { titolo: titolo, locale: locale, lingua: lang(), tipo_menu: tm, tema_grafico: design.template, voci: payloadVoci };
    } else {
      url = "/v1/menu/" + encodeURIComponent(stato.mid) + "/salva";
      body = { titolo: titolo, locale: locale, lingua: lang(), voci: payloadVoci };
    }

    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json", "X-Device-Id": devId() },
      body: JSON.stringify(body)
    })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { return { status: r.status, body: d }; }); })
      .then(function (res) {
        var d = res.body || {};
        var ok = res.status >= 200 && res.status < 300 && !d.errore;
        if (ok && nuovaCreazione && d.id) { stato.mid = d.id; stato.tipoSalvato = tm; }
        if (ok && !nuovaCreazione) { /* mid invariato */ }
        if (ok) {
          var h = '<div class="esito-t">✓ ' + L({ it: "Carta salvata", en: "Card saved", es: "Carta guardada" }) + "</div>";
          h += '<p class="esito-d">' + L({ it: "“%T” è pronta — %N voci. Allergeni dedotti dal backend (Reg. UE 1169/2011).", en: "“%T” is ready — %N items. Allergens deduced by the backend (EU Reg. 1169/2011).", es: "“%T” está lista — %N elementos. Alérgenos deducidos por el backend (Reg. UE 1169/2011)." })
            .replace("%T", esc(titolo)).replace("%N", voci.length) + "</p>";
          h += '<p class="esito-id">' + esc(stato.mid) + "</p>";
          mostraEsito(h, "ok");
          apriDesign();
        } else {
          var msg;
          if (res.status === 401) msg = L({ it: "Identità mancante: ricarica la pagina e riprova.", en: "Missing identity: reload the page and try again.", es: "Identidad ausente: recarga la página e inténtalo de nuevo." });
          else if (d && d.errore) msg = L({ it: "Non salvata: ", en: "Not saved: ", es: "No guardada: " }) + esc(String(d.errore));
          else msg = L({ it: "Non salvata (errore " + res.status + "). Riprova.", en: "Not saved (error " + res.status + "). Try again.", es: "No guardada (error " + res.status + "). Inténtalo de nuevo." });
          mostraEsito(msg, "err");
        }
      })
      .catch(function () {
        mostraEsito(L({ it: "Non salvata: il server non è raggiungibile ora. Nessun dato scritto.", en: "Not saved: the server is unreachable now. No data written.", es: "No guardada: el servidor no está disponible ahora. No se escribió ningún dato." }), "err");
      })
      .then(function () {
        salvaInCorso = false;
        btnSalva.disabled = (voci.length === 0);
        btnSalva.textContent = testoOrig;
      });
  }

  /* ─── PASSO DESIGN & ESPORT ─── */
  var templatiPDF = [
    { k: "matter-verde", lab: { it: "Matter (verde)", en: "Matter (green)", es: "Matter (verde)" } },
    { k: "gastro-bistrot", lab: { it: "Gastro-bistrot", en: "Gastro-bistro", es: "Gastro-bistró" } },
    { k: "minimal", lab: { it: "Minimal", en: "Minimal", es: "Minimal" } },
    { k: "elegante", lab: { it: "Elegante", en: "Elegant", es: "Elegante" } },
    { k: "scuro", lab: { it: "Scuro", en: "Dark", es: "Oscuro" } },
    { k: "minimal-blueprint", lab: { it: "Blueprint", en: "Blueprint", es: "Blueprint" } },
    { k: "enoteca-classica", lab: { it: "Enoteca", en: "Wine cellar", es: "Enoteca" } }
  ];
  function renderTemplati() {
    if (!dsTemplate) return;
    dsTemplate.innerHTML = "";
    templatiPDF.forEach(function (t) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "tpl-b" + (design.template === t.k ? " is-on" : "");
      b.textContent = L(t.lab);
      b.setAttribute("aria-pressed", design.template === t.k ? "true" : "false");
      b.addEventListener("click", function () {
        design.template = t.k;
        renderTemplati();
      });
      dsTemplate.appendChild(b);
    });
  }
  function apriDesign() {
    if (!design3) return;
    design3.hidden = false;
    design3.classList.remove("is-stale");
    renderTemplati();
    // niente apertura automatica dell'anteprima: la decide l'utente (rete/tempi)
    try { design3.scrollIntoView({ behavior: "smooth", block: "start" }); } catch (e) {}
  }
  function paramsEsport() {
    var p = new URLSearchParams();
    if (design.template) p.set("template", design.template);
    if (design.accent) p.set("accent", design.accent.replace(/^#/, ""));
    if (design.logoUrl) p.set("logo", design.logoUrl);
    if (design.footer) p.set("footer", design.footer);
    if (design.font && design.font !== "auto") p.set("font", design.font);
    return p.toString();
  }
  function urlRender() { return "/v1/menu/" + encodeURIComponent(stato.mid) + "/render?" + paramsEsport(); }
  function urlPdf() { return "/v1/menu/" + encodeURIComponent(stato.mid) + "/pdf?" + paramsEsport(); }

  function sincronizzaDesignDaUI() {
    if (dsAccent) design.accent = dsAccent.value || "";
    if (dsFooter) design.footer = (dsFooter.value || "").trim();
    if (dsFont) design.font = dsFont.value || "auto";
  }
  function aggiornaAnteprima() {
    if (!stato.mid) return;
    sincronizzaDesignDaUI();
    if (previewFrame) { previewFrame.hidden = false; previewFrame.src = urlRender(); }
    if (linkRender) { linkRender.hidden = false; linkRender.href = urlRender(); }
  }
  function scaricaPdf() {
    if (!stato.mid) return;
    sincronizzaDesignDaUI();
    // download: navigo verso l'URL del PDF (il backend risponde come attachment)
    window.location.href = urlPdf();
  }

  /* upload logo -> url -> ?logo= */
  function caricaLogo(file) {
    if (!file) return;
    if (file.size > 3 * 1024 * 1024) {
      dsLogoStato.hidden = false; dsLogoStato.className = "ds-logo-stato err";
      dsLogoStato.textContent = L({ it: "Logo troppo grande (max 3MB).", en: "Logo too large (max 3MB).", es: "Logo demasiado grande (máx 3MB)." });
      return;
    }
    dsLogoStato.hidden = false; dsLogoStato.className = "ds-logo-stato";
    dsLogoStato.textContent = L({ it: "Carico il logo…", en: "Uploading logo…", es: "Subiendo el logo…" });
    var fd = new FormData();
    fd.append("file", file);
    fetch("/v1/menu/upload-logo", { method: "POST", headers: { "X-Device-Id": devId() }, body: fd })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { return { status: r.status, body: d }; }); })
      .then(function (res) {
        var d = res.body || {};
        if (res.status >= 200 && res.status < 300 && d.url) {
          design.logoUrl = d.url;
          dsLogoStato.className = "ds-logo-stato ok";
          dsLogoStato.textContent = L({ it: "Logo caricato ✓", en: "Logo uploaded ✓", es: "Logo subido ✓" });
          if (dsLogoPrev) { dsLogoPrev.hidden = false; dsLogoPrev.src = d.url; }
        } else {
          dsLogoStato.className = "ds-logo-stato err";
          dsLogoStato.textContent = L({ it: "Upload non riuscito: ", en: "Upload failed: ", es: "Subida fallida: " }) + esc(String(d.errore || res.status));
        }
      })
      .catch(function () {
        dsLogoStato.className = "ds-logo-stato err";
        dsLogoStato.textContent = L({ it: "Upload non riuscito: server non raggiungibile.", en: "Upload failed: server unreachable.", es: "Subida fallida: servidor no disponible." });
      });
  }

  /* ─── ri-traduzione al cambio lingua ─── */
  var _prima = true;
  window.onI18nApply = function () {
    if (_prima) { _prima = false; return; }
    renderSegTipo();
    renderVoci();
    renderTemplati();
    aggiornaSuggerimentoSezione();
    // ricarico lo stato testuale dell'area disponibili se è uno stato-messaggio
    if (dispStato && !dispStato.hidden) caricaDisponibili();
  };

  /* ─── avvio ─── */
  function init() {
    segTipo = $("seg-tipo");
    inpNome = $("menu-nome"); inpLocale = $("menu-locale");
    btnAddLibera = $("vl-add");
    dispStato = $("disp-stato"); dispBox = $("disp");
    dispToggle = $("disp-toggle"); dispWrap = $("disp-wrap");
    vuoto = $("mio-vuoto"); lista = $("voci");
    btnSalva = $("btn-salva"); salvaEsito = $("salva-esito");
    design3 = $("design"); dsTemplate = $("ds-template"); dsAccent = $("ds-accent");
    dsFooter = $("ds-footer"); dsFont = $("ds-font");
    dsLogoInput = $("ds-logo-input"); dsLogoStato = $("ds-logo-stato"); dsLogoPrev = $("ds-logo-prev");
    previewFrame = $("preview-frame"); btnAnteprima = $("btn-anteprima"); btnPdf = $("btn-pdf"); linkRender = $("link-render");

    renderSegTipo();
    aggiornaSuggerimentoSezione();
    renderVoci();

    if (btnAddLibera) btnAddLibera.addEventListener("click", aggiungiLibera);
    // invio sul campo nome aggiunge la voce
    var nomeF = $("vl-nome");
    if (nomeF) nomeF.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); aggiungiLibera(); } });

    if (dispToggle && dispWrap) {
      dispToggle.addEventListener("click", function () {
        var aperto = dispWrap.hidden;
        dispWrap.hidden = !aperto;
        dispToggle.setAttribute("aria-expanded", aperto ? "true" : "false");
        dispToggle.classList.toggle("is-open", aperto);
        if (aperto && !disponibili.length && dispStato && dispStato.hidden !== false) {
          // primo apri: carico
        }
      });
    }

    if (btnSalva) btnSalva.addEventListener("click", salvaMenu);
    if (btnAnteprima) btnAnteprima.addEventListener("click", aggiornaAnteprima);
    if (btnPdf) btnPdf.addEventListener("click", scaricaPdf);
    if (dsLogoInput) dsLogoInput.addEventListener("change", function () { caricaLogo(dsLogoInput.files && dsLogoInput.files[0]); });

    caricaDisponibili();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
