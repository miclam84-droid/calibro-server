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
            // tengo le GRAMMATURE se ci sono (servono al food cost); accetto stringa o oggetto
            ingr = comp.map(function (c) {
              if (typeof c === "string") return { nome: c };
              if (c && typeof c === "object") return { nome: c.nome || "", quantita: c.quantita || c["quantità"] || c.qta || "", unita: c.unita || c["unità"] || "" };
              return null;
            }).filter(function (x) { return x && x.nome; });
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

  /* ─── STRUMENTI DEL BANCO (consolidati dal vecchio builder) ───
     accostamenti (grafo) · tecniche (disciplina) · filo · equilibrio · chiusura.
     Motori: /v1/menu/{proposte,tecniche,filo,analizza} · /v1/dolce-per-menu.
     Ragionano sulle voci della carta (ingredienti delle voci profilate). */
  function strumIngredienti() {
    var seen = {}, out = [];
    voci.forEach(function (v) {
      (v.ingredienti || []).forEach(function (x) {
        var n = (typeof x === "string" ? x : (x && x.nome) || "").trim();
        if (n && !seen[n.toLowerCase()]) { seen[n.toLowerCase()] = 1; out.push(n); }
      });
    });
    return out;
  }
  function strumDisc() {
    return ({ food: "cucina", pizze: "bakery", drink: "bar", vini: "cucina" })[stato.tipoUI] || "cucina";
  }
  function strumOut() { return $("strum-out"); }
  function strumPost(path, body) {
    return fetch(path, { method: "POST", headers: { "Content-Type": "application/json", "X-Device-Id": devId() }, body: JSON.stringify(body) })
      .then(function (r) { return r.json().catch(function () { return {}; }); });
  }

  function strumAccostamenti() {
    var out = strumOut(), ings = strumIngredienti();
    var lab = '<div class="strum-lab">◇ ' + L({ it: "Accostamenti dal grafo", en: "Pairings from the graph", es: "Combinaciones del grafo" }) + "</div>";
    if (ings.length < 2) {
      out.innerHTML = '<div class="strum-box">' + lab +
        '<div class="strum-fonte" style="margin-top:0;margin-bottom:9px">' + L({ it: "Servono almeno 2 ingredienti. Aggancia preparazioni profilate, o scrivili qui:", en: "Need at least 2 ingredients. Link profiled preparations, or type them:", es: "Hacen falta al menos 2 ingredientes. Vincula preparaciones perfiladas, o escríbelos:" }) + "</div>" +
        '<input class="strum-in" id="strum-acc-in" placeholder="pomodoro, basilico, mozzarella"><button class="strum-go" id="strum-acc-go">' + L({ it: "Trova", en: "Find", es: "Buscar" }) + "</button></div>";
      $("strum-acc-go").addEventListener("click", function () {
        var v = ($("strum-acc-in").value || "").split(",").map(function (s) { return s.trim(); }).filter(Boolean);
        if (v.length >= 2) strumAccFetch(v);
      });
      return;
    }
    strumAccFetch(ings.slice(0, 10));
  }
  function strumAccFetch(ings) {
    var out = strumOut();
    out.innerHTML = '<div class="strum-box"><div class="strum-lab">◇ ' + L({ it: "Accostamenti dal grafo", en: "Pairings from the graph", es: "Combinaciones del grafo" }) + '</div><div class="strum-fonte" id="strum-acc-body">' + L({ it: "Cerco…", en: "Searching…", es: "Buscando…" }) + "</div></div>";
    strumPost("/v1/menu/proposte", { ingredienti: ings, tipo: "piatto" }).then(function (j) {
      var pr = (j && j.proposte) || [], body = $("strum-acc-body");
      if (!body) return;
      if (!pr.length) { body.textContent = L({ it: "Nessun accostamento forte tra questi ingredienti.", en: "No strong pairing among these ingredients.", es: "Ninguna combinación fuerte entre estos ingredientes." }); return; }
      body.innerHTML = pr.slice(0, 8).map(function (p) {
        var espl = p.esplorativa || p.robustezza === "da esplorare", c = (p.connessioni != null ? p.connessioni : "");
        return '<div class="strum-item"><span class="n">' + esc(p.nome || "") + "</span>" +
          (!espl && c !== "" ? '<span class="b">' + esc(String(c)) + " " + L({ it: "composti condivisi", en: "shared compounds", es: "compuestos compartidos" }) + "</span>" : '<div class="m">' + L({ it: "da esplorare al banco", en: "to explore at the bench", es: "por explorar" }) + "</div>") + "</div>";
      }).join("") + '<div class="strum-fonte">' + esc(j.fonte || "") + "</div>";
    }).catch(function () { var body = $("strum-acc-body"); if (body) body.textContent = L({ it: "Non raggiungibile ora.", en: "Unreachable now.", es: "No disponible." }); });
  }

  function strumTecniche() {
    var out = strumOut(), disc = strumDisc();
    out.innerHTML = '<div class="strum-box"><div class="strum-lab">◇ ' + L({ it: "Tecniche del banco — ", en: "Bench techniques — ", es: "Técnicas — " }) + esc(disc) + '</div><div class="strum-fonte" id="strum-tec-body">' + L({ it: "Cerco…", en: "Searching…", es: "Buscando…" }) + "</div></div>";
    strumPost("/v1/menu/tecniche", { disciplina: disc }).then(function (j) {
      var tec = (j && j.tecniche) || [], body = $("strum-tec-body");
      if (!body) return;
      if (!tec.length) { body.textContent = L({ it: "Nessuna tecnica col numero-bersaglio per questa disciplina.", en: "No technique with a target number for this discipline.", es: "Ninguna técnica con número objetivo." }); return; }
      body.innerHTML = tec.slice(0, 12).map(function (t) {
        return '<div class="strum-item"><span class="n">' + esc(t.nome || "") + "</span>" + (t.famiglia ? '<div class="m">' + esc(t.famiglia) + "</div>" : "") + (t.numeri ? '<span class="b">' + esc(t.numeri) + "</span>" : "") + "</div>";
      }).join("");
    }).catch(function () { var body = $("strum-tec-body"); if (body) body.textContent = L({ it: "Non raggiungibile ora.", en: "Unreachable now.", es: "No disponible." }); });
  }

  var _filoTipo = "ingrediente";
  function strumFilo() {
    var out = strumOut();
    out.innerHTML = '<div class="strum-box"><div class="strum-lab">◇ ' + L({ it: "Filo conduttore", en: "Through-line", es: "Hilo conductor" }) + "</div>" +
      '<div class="strum-fonte" style="margin-top:0;margin-bottom:9px">' + L({ it: "Scegli attorno a cosa ruota la carta. Matter mostra le preparazioni che reggono il filo.", en: "Pick what the card revolves around. Matter shows the preparations that hold the through-line.", es: "Elige en torno a qué gira la carta." }) + "</div>" +
      '<div class="strum-seg"><button id="strum-filo-ing" class="on" type="button">' + L({ it: "Ingrediente", en: "Ingredient", es: "Ingrediente" }) + '</button><button id="strum-filo-fen" type="button">' + L({ it: "Fenomeno", en: "Phenomenon", es: "Fenómeno" }) + "</button></div>" +
      '<input class="strum-in" id="strum-filo-in" placeholder="es. pomodoro — oppure Maillard"><button class="strum-go" id="strum-filo-go">' + L({ it: "Trova il filo", en: "Find the through-line", es: "Buscar el hilo" }) + "</button>" +
      '<div id="strum-filo-body" style="margin-top:11px"></div></div>';
    _filoTipo = "ingrediente";
    $("strum-filo-ing").addEventListener("click", function () { _filoTipo = "ingrediente"; $("strum-filo-ing").className = "on"; $("strum-filo-fen").className = ""; });
    $("strum-filo-fen").addEventListener("click", function () { _filoTipo = "fenomeno"; $("strum-filo-fen").className = "on"; $("strum-filo-ing").className = ""; });
    $("strum-filo-go").addEventListener("click", strumFiloGo);
  }
  function strumFiloGo() {
    var tema = ($("strum-filo-in").value || "").trim(), body = $("strum-filo-body");
    if (!tema || !body) return;
    body.innerHTML = '<div class="strum-fonte">' + L({ it: "Cerco…", en: "Searching…", es: "Buscando…" }) + "</div>";
    strumPost("/v1/menu/filo", { tema: tema, tipo_filo: _filoTipo, preparazioni: [] }).then(function (j) {
      var sug = (j && j.suggeriti_per_il_filo) || [];
      if (!sug.length) { body.innerHTML = '<div class="strum-fonte">' + L({ it: "Nessuna preparazione regge il filo «", en: "No preparation holds the through-line «", es: "Ninguna preparación sostiene el hilo «" }) + esc(tema) + "». " + L({ it: "Prova un tema più comune.", en: "Try a more common theme.", es: "Prueba un tema más común." }) + "</div>"; return; }
      body.innerHTML = '<div class="strum-lab" style="margin-bottom:8px">' + L({ it: "Preparazioni che reggono «", en: "Preparations holding «", es: "Preparaciones que sostienen «" }) + esc(tema) + "»</div>" +
        sug.map(function (n) { return '<div class="strum-item"><span class="n">' + esc(n) + "</span></div>"; }).join("") +
        '<div class="strum-fonte">' + L({ it: "Dall'archivio preparazioni di Matter.", en: "From Matter's preparation archive.", es: "Del archivo de preparaciones de Matter." }) + "</div>";
    }).catch(function () { body.innerHTML = '<div class="strum-fonte">' + L({ it: "Non raggiungibile ora.", en: "Unreachable now.", es: "No disponible." }) + "</div>"; });
  }

  function strumEquilibrio() {
    var out = strumOut();
    if (voci.length < 2) { out.innerHTML = '<div class="strum-box"><div class="strum-fonte" style="margin-top:0">' + L({ it: "Aggiungi almeno 2 voci per analizzare l'equilibrio.", en: "Add at least 2 items to analyse the balance.", es: "Añade al menos 2 elementos para analizar el equilibrio." }) + "</div></div>"; return; }
    out.innerHTML = '<div class="strum-box"><div class="strum-lab">◇ ' + L({ it: "Equilibrio della carta", en: "Card balance", es: "Equilibrio de la carta" }) + '</div><div class="strum-fonte" id="strum-eq-body">' + L({ it: "Analizzo…", en: "Analysing…", es: "Analizando…" }) + "</div></div>";
    var payload = voci.map(function (v) { return { nome: v.nome, ingredienti: (v.ingredienti || []).map(function (x) { return typeof x === "string" ? x : (x && x.nome) || ""; }) }; });
    strumPost("/v1/menu/analizza", { voci: payload }).then(function (j) {
      var body = $("strum-eq-body"); if (!body) return;
      if (j && j.errore) { body.textContent = L({ it: "Analisi non disponibile ora.", en: "Analysis unavailable now.", es: "Análisis no disponible." }); return; }
      var bil = (j && j.bilanciamento) || {}, mod = (j && j.modifiche_consigliate) || [];
      var senza = voci.filter(function (v) { return !(v.ingredienti && v.ingredienti.length); }).length;
      var rows = ["carne", "pesce", "vegetariano", "dolce"].map(function (k) { return '<div class="strum-item"><span class="n">' + esc(k) + '</span><span class="b">' + (bil[k] || 0) + "</span></div>"; }).join("");
      var html = rows + (j.ripetizione_ingredienti_pct != null ? '<div class="strum-item"><span class="n">' + L({ it: "ripetizione ingredienti", en: "ingredient repetition", es: "repetición de ingredientes" }) + '</span><span class="b">' + j.ripetizione_ingredienti_pct + "%</span></div>" : "");
      if (mod.length) html += '<div class="strum-lab" style="margin-top:11px">' + L({ it: "Cosa migliorare", en: "What to improve", es: "Qué mejorar" }) + "</div>" + mod.map(function (m) { return '<div class="strum-item"><span class="m">→ ' + esc(m) + "</span></div>"; }).join("");
      else html += '<div class="strum-fonte">' + L({ it: "✓ Carta equilibrata.", en: "✓ Balanced card.", es: "✓ Carta equilibrada." }) + "</div>";
      if (senza) html += '<div class="strum-fonte">⚠ ' + senza + " " + L({ it: "voci senza ingredienti: l'equilibrio qui è indicativo.", en: "items without ingredients: the balance here is indicative.", es: "elementos sin ingredientes: el equilibrio aquí es indicativo." }) + "</div>";
      body.innerHTML = html;
    }).catch(function () { var body = $("strum-eq-body"); if (body) body.textContent = L({ it: "Non raggiungibile ora.", en: "Unreachable now.", es: "No disponible." }); });
  }

  function strumChiusura() {
    var out = strumOut();
    if (!voci.length) { out.innerHTML = '<div class="strum-box"><div class="strum-fonte" style="margin-top:0">' + L({ it: "Aggiungi qualche voce prima.", en: "Add a few items first.", es: "Añade algunos elementos primero." }) + "</div></div>"; return; }
    out.innerHTML = '<div class="strum-box"><div class="strum-lab">◇ ' + L({ it: "Come chiudere il menu", en: "How to close the menu", es: "Cómo cerrar el menú" }) + '</div><div class="strum-fonte" id="strum-chiu-body">' + L({ it: "Cerco la chiusura…", en: "Finding the close…", es: "Buscando el cierre…" }) + "</div></div>";
    strumPost("/v1/dolce-per-menu", { voci: voci.map(function (v) { return v.nome; }) }).then(function (j) {
      var body = $("strum-chiu-body"); if (!body) return;
      var dess = j && j.dessert_consigliato;
      if (!dess) { body.textContent = L({ it: "Nessun suggerimento di chiusura per ora.", en: "No closing suggestion for now.", es: "Ninguna sugerencia de cierre por ahora." }); return; }
      var lista = Array.isArray(dess) ? dess : [dess];
      body.innerHTML = lista.map(function (x) {
        var nome = typeof x === "string" ? x : (x.nome || ""), perche = typeof x === "object" ? (x.perche || "") : "";
        return '<div class="strum-item"><span class="n">' + esc(nome) + "</span>" + (perche ? '<div class="m">' + esc(perche) + "</div>" : "") + "</div>";
      }).join("");
    }).catch(function () { var body = $("strum-chiu-body"); if (body) body.textContent = L({ it: "Non raggiungibile ora.", en: "Unreachable now.", es: "No disponible." }); });
  }

  // DRINK COST (recupero funzione sepolta, revisore #2): per una carta drink il food cost
  // va in dosi (ml), non in grammi. Instrada su /v1/drink-cost (prezzi €/litro da bar),
  // convertendo cl→ml. Onesto dove manca un prezzo/dose: lo dichiara, non lo inventa.
  function _mlDaIngr(x) {
    if (typeof x === "string") return { nome: x, ml: 0 };
    var q = parseFloat(String(x.quantita != null ? x.quantita : "").replace(",", ".")) || 0;
    var u = String(x.unita || "").toLowerCase().trim();
    if (u === "cl") q = q * 10;           // cl → ml
    else if (u === "oz") q = q * 29.57;   // oz → ml
    // ml, o unità vuota: si assume ml (dose da bar)
    return { nome: x.nome || "", ml: Math.round(q * 100) / 100 };
  }
  function strumDrinkCost() {
    var out = strumOut();
    out.innerHTML = '<div class="strum-box"><div class="strum-lab">◇ ' + L({ it: "Drink cost della carta", en: "Card drink cost", es: "Drink cost de la carta" }) + '</div><div class="strum-fonte" id="strum-fc-body">' + L({ it: "Calcolo…", en: "Computing…", es: "Calculando…" }) + "</div></div>";
    Promise.all(voci.map(function (v) {
      var ingr = (v.ingredienti || []).map(_mlDaIngr).filter(function (i) { return i.nome; });
      if (!ingr.length) return Promise.resolve({ nome: v.nome, _vuoto: true });
      return strumPost("/v1/drink-cost", { nome: v.nome, ingredienti: ingr }).then(function (j) {
        return { nome: v.nome, costo: (j && j.costo_ingredienti != null) ? j.costo_ingredienti : null, mancanti: (j && j.ingredienti_senza_prezzo) || 0, nvoci: ingr.length };
      }).catch(function () { return { nome: v.nome, _err: true }; });
    })).then(function (ris) {
      var body = $("strum-fc-body"); if (!body) return;
      var tot = 0, nok = 0;
      var rows = ris.map(function (x) {
        if (x._vuoto) return '<div class="strum-item"><span class="n">' + esc(x.nome) + ' — <span class="b">—</span></span><div class="m">' + L({ it: "serve una preparazione profilata con le dosi in ml", en: "needs a profiled preparation with ml amounts", es: "necesita una preparación con dosis en ml" }) + "</div></div>";
        if (x._err || x.costo == null) return '<div class="strum-item"><span class="n">' + esc(x.nome) + ' — <span class="b">—</span></span><div class="m">' + L({ it: "prezzi insufficienti per un calcolo onesto", en: "not enough prices for an honest calc", es: "precios insuficientes" }) + "</div></div>";
        tot += Number(x.costo); nok++;
        var nota = x.mancanti ? (x.mancanti + " " + L({ it: "su", en: "of", es: "de" }) + " " + x.nvoci + " " + L({ it: "senza prezzo", en: "without price", es: "sin precio" })) : L({ it: "dosi × prezzi €/litro", en: "doses × €/litre prices", es: "dosis × precios €/litro" });
        return '<div class="strum-item"><span class="n">' + esc(x.nome) + ' — <span class="b">€ ' + Number(x.costo).toFixed(2) + '</span></span><div class="m">' + esc(nota) + "</div></div>";
      }).join("");
      var totLab = nok ? ('<div class="strum-lab" style="margin-top:11px">' + L({ it: "Totale drink calcolabili: ", en: "Total of computable drinks: ", es: "Total de tragos calculables: " }) + "€ " + tot.toFixed(2) + " · " + nok + "/" + voci.length + "</div>") : "";
      body.innerHTML = rows + totLab + '<div class="strum-fonte">' + L({ it: "Prezzi medi di distribuzione (orientativi). Aggiungi ghiaccio/guarnizione e usa i prezzi del tuo fornitore per il dato reale. Dove manca un prezzo o una dose, è dichiarato — mai inventato.", en: "Average distribution prices (indicative). Add ice/garnish and use your supplier's prices for the real figure. Where a price or dose is missing, it's declared — never invented.", es: "Precios medios de distribución (orientativos). Añade hielo/guarnición y usa los precios de tu proveedor para el dato real. Donde falta un precio o una dosis, se declara — nunca se inventa." }) + "</div>";
    });
  }
  function strumFoodCost() {
    var out = strumOut();
    if (!voci.length) { out.innerHTML = '<div class="strum-box"><div class="strum-fonte" style="margin-top:0">' + L({ it: "Aggiungi qualche voce prima.", en: "Add a few items first.", es: "Añade algunos elementos primero." }) + "</div></div>"; return; }
    // Carta drink → drink cost (dosi ml). Carta cibo/forno → food cost (grammi).
    if (strumDisc() === "bar") { strumDrinkCost(); return; }
    out.innerHTML = '<div class="strum-box"><div class="strum-lab">◇ ' + L({ it: "Food cost della carta", en: "Card food cost", es: "Food cost de la carta" }) + '</div><div class="strum-fonte" id="strum-fc-body">' + L({ it: "Calcolo…", en: "Computing…", es: "Calculando…" }) + "</div></div>";
    var payload = voci.map(function (v) { return { nome: v.nome, ingredienti: v.ingredienti || [] }; });
    strumPost("/v1/menu/food-cost", { voci: payload }).then(function (j) {
      var body = $("strum-fc-body"); if (!body) return;
      var vv = (j && j.voci) || [];
      var rows = vv.map(function (x) {
        var cost = (x.costo != null) ? ("€ " + Number(x.costo).toFixed(2)) : "—";
        var sotto = (x.costo != null)
          ? (x.fonte === "tuo" ? L({ it: "prezzi tuoi", en: "your prices", es: "tus precios" }) : x.fonte === "misto" ? L({ it: "prezzi misti", en: "mixed prices", es: "precios mixtos" }) : L({ it: "prezzi di riferimento (orientativi)", en: "reference prices (indicative)", es: "precios de referencia" }))
          : (x.stato === "senza_grammature" ? L({ it: "serve una preparazione profilata con le dosi", en: "needs a profiled preparation with amounts", es: "necesita una preparación perfilada con dosis" }) : L({ it: "prezzi insufficienti per un calcolo onesto", en: "not enough prices for an honest calc", es: "precios insuficientes para un cálculo honesto" }));
        return '<div class="strum-item"><span class="n">' + esc(x.nome) + ' — <span class="b">' + cost + '</span></span><div class="m">' + esc(sotto) + "</div></div>";
      }).join("");
      var tot = (j.totale_calcolato != null) ? ('<div class="strum-lab" style="margin-top:11px">' + L({ it: "Totale voci calcolabili: ", en: "Total of computable items: ", es: "Total de elementos calculables: " }) + "€ " + Number(j.totale_calcolato).toFixed(2) + " · " + j.n_calcolate + "/" + j.n_voci + "</div>") : "";
      body.innerHTML = rows + tot + '<div class="strum-fonte">' + esc(j.fonte || "") + ". " + L({ it: "Dove manca un prezzo o una dose, è dichiarato — mai inventato.", en: "Where a price or amount is missing, it's declared — never invented.", es: "Donde falta un precio o una dosis, se declara — nunca se inventa." }) + "</div>";
    }).catch(function () { var body = $("strum-fc-body"); if (body) body.textContent = L({ it: "Non raggiungibile ora.", en: "Unreachable now.", es: "No disponible." }); });
  }

  /* ─── NAMING: proponi un nome di fantasia dagli ingredienti (descrizione) ─── */
  function proponiNome() {
    var out = $("vl-naming-out"), btn = $("vl-naming");
    var desc = ($("vl-desc").value || "").trim();
    var ings = desc.split(/[,;\n]+/).map(function (s) { return s.trim(); }).filter(Boolean);
    if (!out) return;
    out.hidden = false;
    if (ings.length < 1) { out.textContent = L({ it: "Scrivi prima gli ingredienti nella descrizione, poi riprova.", en: "Write the ingredients in the description first, then retry.", es: "Escribe primero los ingredientes en la descripción, luego reinténtalo." }); return; }
    if (btn) btn.disabled = true;
    out.textContent = L({ it: "Penso a un nome…", en: "Thinking of a name…", es: "Pensando un nombre…" });
    var disc = strumDisc();
    strumPost("/v1/menu/naming", { ingredienti: ings, disciplina: disc }).then(function (j) {
      if (btn) btn.disabled = false;
      var nome = (j && j.nome || "").trim();
      if (!nome) { out.textContent = L({ it: "Nessun nome convincente — scrivilo tu.", en: "No convincing name — write it yourself.", es: "Ningún nombre convincente — escríbelo tú." }); return; }
      $("vl-nome").value = nome;
      out.innerHTML = "✓ " + L({ it: "Proposto: ", en: "Suggested: ", es: "Propuesto: " }) + "<b>" + esc(nome) + "</b> — " + L({ it: "modificalo se vuoi.", en: "edit it if you like.", es: "edítalo si quieres." });
    }).catch(function () { if (btn) btn.disabled = false; out.textContent = L({ it: "Non raggiungibile ora.", en: "Unreachable now.", es: "No disponible." }); });
  }

  /* ─── PROPOSTE DA FOTO: riconosci gli ingredienti da una foto (Vision, gratis) ─── */
  function riconosciFoto(files) {
    if (!files || !files.length) return;
    var out = $("vl-foto-out"); if (!out) return;
    out.hidden = false;
    out.textContent = L({ it: "Riconosco gli ingredienti…", en: "Recognising the ingredients…", es: "Reconociendo los ingredientes…" });
    var fd = new FormData();
    for (var i = 0; i < Math.min(files.length, 6); i++) fd.append("immagini", files[i]);
    fetch("/v1/menu/riconosci-ingredienti", { method: "POST", headers: { "X-Device-Id": devId() }, body: fd })
      .then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function (j) {
        var ings = (j && j.ingredienti) || [];
        if (!ings.length) { out.textContent = L({ it: "Nessun ingrediente riconosciuto. Riprova con una foto più chiara.", en: "No ingredient recognised. Try a clearer photo.", es: "Ningún ingrediente reconocido. Prueba con una foto más clara." }); return; }
        var nomi = ings.map(function (x) { return x.nome; });
        var d = $("vl-desc"); if (d) d.value = nomi.join(", ");
        out.innerHTML = L({ it: "Riconosciuti: ", en: "Recognised: ", es: "Reconocidos: " }) +
          ings.map(function (x) { return '<span class="strum-chip">' + esc(x.nome) + "</span>"; }).join("") +
          '<div class="strum-fonte" style="margin-top:6px">' + L({ it: "Li ho messi nella descrizione: dai un nome e aggiungi la voce, oppure guarda gli ", en: "I put them in the description: give it a name and add the item, or see the ", es: "Los puse en la descripción: dale un nombre y añade el elemento, o mira las " }) +
          '<a class="lk" id="vl-foto-acc" href="#">' + L({ it: "accostamenti", en: "pairings", es: "combinaciones" }) + "</a>.</div>";
        var acc = $("vl-foto-acc");
        if (acc) acc.addEventListener("click", function (e) { e.preventDefault(); strumAccFetch(nomi.slice(0, 10)); var so = $("strum-out"); if (so) so.scrollIntoView({ behavior: "smooth", block: "start" }); });
      })
      .catch(function () { out.textContent = L({ it: "Riconoscimento non riuscito ora.", en: "Recognition failed now.", es: "Reconocimiento fallido ahora." }); });
  }

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

    // strumenti del banco (builder unico)
    var _s;
    if ((_s = $("strum-acc"))) _s.addEventListener("click", strumAccostamenti);
    if ((_s = $("strum-tec"))) _s.addEventListener("click", strumTecniche);
    if ((_s = $("strum-filo"))) _s.addEventListener("click", strumFilo);
    if ((_s = $("strum-eq"))) _s.addEventListener("click", strumEquilibrio);
    if ((_s = $("strum-chiu"))) _s.addEventListener("click", strumChiusura);
    if ((_s = $("strum-fc"))) _s.addEventListener("click", strumFoodCost);
    if ((_s = $("vl-naming"))) _s.addEventListener("click", proponiNome);
    if ((_s = $("vl-foto-input"))) _s.addEventListener("change", function () { riconosciFoto(this.files); });

    caricaDisponibili();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
