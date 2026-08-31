/* ===== Silenzia gli AbortError delle fetch annullate al cambio tab =====
   Non sono veri errori: sono fetch della tab precedente interrotte di proposito. */
window.addEventListener('unhandledrejection', function(e){
  if(e && e.reason && (e.reason.name==='AbortError' || (''+e.reason).indexOf('abort')>=0)){
    e.preventDefault();
  }
});

/* ===== FUNNEL TRACKING — base per i KPI del pannello =====
   Cattura gli UTM all'arrivo (persistono in localStorage per l'attribuzione content→paid)
   e invia gli eventi chiave del funnel al backend. Silenzioso e non-bloccante. */
(function _catturaUTM(){
  try{
    var q = new URLSearchParams(window.location.search);
    var u = {};
    ['source','medium','campaign','content'].forEach(function(k){
      var v = q.get('utm_'+k); if(v) u[k]=v;
    });
    if(Object.keys(u).length){
      // first-touch: non sovrascrivo se già presente (il primo contatto conta)
      if(!localStorage.getItem('matter_utm')){
        localStorage.setItem('matter_utm', JSON.stringify(u));
      }
      // last-touch: sempre aggiornato
      localStorage.setItem('matter_utm_last', JSON.stringify(u));
    }
  }catch(_){}
})();
function _trackFunnel(evento, meta){
  try{
    var utm = {};
    try{ utm = JSON.parse(localStorage.getItem('matter_utm')||'{}'); }catch(_){}
    var email = localStorage.getItem('matter_email') || null;
    // non blocco l'esperienza utente: fire-and-forget
    fetch('/v1/funnel/track', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ evento: evento, email: email, meta: meta||null, utm: utm })
    }).catch(function(){});
  }catch(_){}
}

/* Matter — logica principale (estratta da index.html) */

/* Logging errori centralizzato: un punto solo invece di console.error sparsi.
   In produzione resta silenzioso per l'utente; utile in sviluppo. */
function _logErr(ctx, err){
  try{
    if(window.location && window.location.hostname === 'localhost'){
      console.error('[Matter:'+ctx+']', err);
    }
    // in produzione: silenzioso (in futuro si può inviare a un endpoint di telemetria)
  }catch(_){}
}

/* ===== blocco 1 (da index.html) ===== */
const STRINGS_ES = {
    scopri_ey:'Fenómeno del día',
    scopri_cta:'Estudia este fenómeno',
    scopri_errore_eyebrow:'Error al cargar',
    scopri_errore_titolo:'Sin conexión',
    les_step:'Paso',
    les_di:'de',
    les_quiz_titolo:'Quiz',
    les_quiz_btn:'Comprobar',
    les_quiz_corr:'¡Correcto!',
    les_quiz_err:'No exactamente.',
    chiedi_title:'Preguntar',
    chiedi_sub:'Un fenómeno físico para cada gesto profesional',
    chiedi_al_grafo:'Preguntar a Matter Bench',
    calcola:'Calcular',
    onb_s1_title:'La física del oficio',
    onb_s1_sub:'Fenómenos físicos y químicos bajo cada gesto profesional.',
    onb_s2_title:'Números objetivo',
    onb_s2_sub:'Cada fenómeno tiene un número medible. Matter Bench te lo da.',
    onb_s3_title:'Preguntar a Matter Bench',
    onb_s3_sub:'Haz preguntas reales del trabajo diario.',
    auth_email:'Email',
    auth_pwd:'Contraseña',
    auth_login:'Iniciar sesión',
    auth_reg:'Crear cuenta',
    auth_reg_ok:'Cuenta creada. ¡Bienvenido a Matter Bench!',
    auth_errore_rete:'Error de red. Inténtalo de nuevo.',
    auth_inserisci:'Introduce email y contraseña',
    auth_logout:'Cerrar sesión',
    payoff:'Science & Craft',
    mappa_title:'Mapa de conocimiento',
    flavor_title:'Red de sabores',
    flavor_cerca:'buscar ingrediente...',
    flavor_btn:'Buscar',
    contrasto_title:'Maridaje por contraste',
    quaderno_title:'Cuaderno',
    quaderno_vuoto:'Sin experimentos guardados.',
    quaderno_salva:'Guardar en el cuaderno',
    supporto:'Soporte',
    ct_cookie_txt:'Matter Bench usa cookies técnicas y registra las preguntas para mejorar el servicio.',
    ct_disc_sicurezza:'Seguridad alimentaria',
    ct_disc_sicurezza_sub:'HACCP · Aw · vida útil · zonas de peligro',
    accedi:'Acceder',
    acido_citrico:'g de ácido cítrico.',
    aggiungi_acido:'Añadir',
    aggiungi_ing:'Añade un ingrediente.',
    auth_ok:'Sesión iniciada.',
    auth_pwd_corta:'La contraseña debe tener al menos 8 caracteres.',
    avanti:'Siguiente →',
    caricamento:'cargando…',
    chat_grado:'grado final (era ',
    chat_thinking:'consultando Matter Bench',
    chiedi_btn:'Preguntar',
    onb_nudge_title:'¿Listo en el banco?',
    ai_disclosure:'Respuestas generadas por un asistente de IA.',
    foto_analisi_titolo:'Análisis de foto',
    foto_analisi_loading:'Identificando ingredientes y botellas…',
    chiedi_placeholder:'pregunta a Matter Bench…',
    continua_free:'Continuar con el plan gratuito',
    continua_senza:'← Continuar sin registrarse',
    ct_acido:'ácido %',
    ct_acqua_g:'agua g',
    ct_acqua_pre:'Agua pre-dilución',
    ct_add:'+ añadir ingrediente',
    ct_batch:'Lote',
    ct_bevanda_g:'bebida g',
    ct_bot:'bot. ml',
    ct_botg:'Embotellado',
    ct_botg_s:'agua ahora',
    ct_bq_serv:'porciones',
    ct_bq_vol:'volumen ml',
    ct_cookie_no:'Solo esenciales',
    ct_cookie_ok:'Aceptar',
    ct_dose_ey:'dosis g',
    ct_dose_ratio:'dosis g',
    ct_drink:'El cóctel',
    ct_drinkcost_label:'coste total orientativo · fuente ISMEA',
    ct_drinkcost_note:'Precios de mercado orientativos. Para coste real usa Cifra.',
    ct_drinkcost_title:'Drink cost orientativo',
    ct_extra:'extra %',
    ct_extra_lbl:'extra',
    ct_farina:'harina g',
    ct_flavor_btn:'Buscar',
    ct_flavor_placeholder:'ej. limón, café, mantequilla…',
    ct_foodcost_label:'coste total orientativo · fuente ISMEA',
    ct_foodcost_note:'Precios de mercado orientativos. Para coste real usa Cifra.',
    ct_foodcost_title:'Food cost orientativo',
    ct_hint_dil:'Punto de partida. Para calibrar: pesa el cóctel antes y después.',
    ct_ice:'Con hielo',
    ct_ice_s:'agua después',
    ct_idr_out:'Hidratación',
    ct_include:'incluye',
    ct_ing:'ingrediente',
    ct_mesc:'Mezclado',
    ct_par:'Equilibrador de acidez',
    ct_par_hint:'Lleva cualquier zumo al 6% como el lima.',
    ct_perporz:'Por porciones',
    ct_pervol:'Por volumen',
    ct_ph:'pH masa madre',
    ct_q10:'Q10 — tiempo de fermentación',
    ct_q10_caldo:'más cálido — fermentación más rápida',
    ct_q10_freddo:'más frío — fermentación más lenta',
    ct_q10_out:'Tiempo estimado',
    ct_quad_empty_sub:'Usa los calculadores y guarda tus medidas físicas.',
    ct_quad_empty_title:'Sin experimentos guardados',
    ct_quad_title:'Cuaderno',
    ct_ratio:'ratio 1:',
    ct_salva_btn:'+ Guardar en cuaderno',
    ct_salva_confirm:'Guardar',
    ct_salva_nome:'Nombre del experimento',
    ct_salva_note:'Notas (opcional)',
    ct_shak:'Agitado',
    ct_sic_aw:'Aw',
    ct_sic_cold:'Cadena de frío — riesgo zona de peligro',
    ct_sic_cold_disc:'Límite de seguridad: máx. 2 horas acumuladas en zona de peligro.',
    ct_sic_cold_hint:'Tiempo acumulado en zona de peligro (4°C–60°C).',
    ct_sic_cold_t:'Temperatura °C',
    ct_sic_cold_time:'Tiempo (min)',
    ct_sic_disc_uk:'This tool provides indicative estimates only.',
    ct_sic_past:'Pasteurización — reducción logarítmica',
    ct_sic_past_hint:'Tiempo necesario para reducir la carga bacteriana a la temperatura indicada.',
    ct_sic_past_t:'Temperatura °C',
    ct_sic_past_time:'Tiempo (min)',
    ct_sic_ph:'pH',
    ct_sic_shelf:'Vida útil orientativa',
    ct_sic_shelf_disc:'Estimación orientativa — no sustituye pruebas microbiológicas.',
    ct_sic_shelf_hint:'Estimación basada en Aw, pH y temperatura de conservación.',
    ct_sic_temp:'T conserv. °C',
    ct_sour:'Sour',
    ct_succo:'zumo ml',
    ct_syr1:'Almíbar 1:1 (50 Brix)',
    ct_syr2:'Almíbar 2:1 (65 Brix)',
    ct_tab_sic:'Seguridad',
    ct_target:'objetivo %',
    ct_tds:'TDS %',
    ct_tecnica:'Técnica',
    ct_totale:'Total',
    disc_bakery:'Panadería',
    disc_caffetteria:'Café',
    domande_esaurite:'Has usado las 5 preguntas gratuitas de hoy.',
    fenomeno_giorno:'fenómeno del día',
    il_percorso:'Tu recorrido',
    indietro:'← Atrás',
    les_caricamento:'cargando…',
    les_errore:'Error al cargar — inténtalo de nuevo.',
    les_fenomeno:'Fenómeno',
    mappa_caricamento:'Cargando…',
    mappa_errore:'Error al cargar el mapa. Inténtalo de nuevo.',
    mappa_nessun_fen:'No se encontraron fenómenos para esta disciplina.',
    mappa_percorso:'Tu recorrido — ',
    mappa_scegli:'Elige una disciplina en Descubrir para ver tu recorrido.',
    num_bersaglio:'número objetivo',
    onb_complete_btn:'Ir al Mapa',
    onb_complete_sub:'Completaste la lección. Ve al Mapa para ver tu recorrido.',
    onb_complete_title:'Excelente trabajo.',
    onb_nudge_sub:'Selecciona tu disciplina abajo para comenzar tu recorrido.',
    onb_ovl_cta:'Empezar',
    onb_ovl_title:'Cómo funciona Matter Bench',
    onb_s1_sub:'Bar, Panadería, Cocina, Café — cada disciplina tiene sus fenómenos.',
    onb_s1_title:'Elige tu disciplina',
    onb_s2_sub:'Cada lección tiene un número objetivo — el parámetro físico que mides en el trabajo.',
    onb_s2_title:'Estudia el fenómeno',
    onb_s3_sub:'Haz una pregunta real — un problema de tu trabajo. Respondo con números, no con opiniones.',
    onb_s3_title:'Pregunta a Matter Bench',
    passa_pro:'Pasar a Pro',
    perche_insieme:'Por qué funcionan juntos',
    ponte_cifra:'El puente hacia Cifra',
    principi_trasv:'Principios transversales',
    principio_del_giorno:'Principio del día',
    pro_desc:'Con Matter Pro continúas sin límites — lecciones, preguntas y calidad profesional.',
    prova:'Prueba:',
    registrati:'Registrarse',
    salvato:'✓ Guardado',
    scegli:'Elige tu disciplina',
    scegli_disc_mappa:'Elige una disciplina en Descubrir para ver tu recorrido.',
    sup_invia:'Enviar solicitud',
    sup_placeholder:'Ej. No puedo abrir la lección…',
    sup_sub:'Describe el problema. Te responderemos enseguida.',
    sup_titolo:'¿Necesitas ayuda?',
    vai_mappa:'Ir al Mapa →',
    vedi_mappa:'Ver el principio en el Mapa →'
  };

/* ===== blocco 3 (da index.html) ===== */
/* ── NAVIGAZIONE ──────────────────────────────────────── */
let _subtab = 'chat';   // subtab attivo dentro "Chiedi": 'chat' | 'calc'

function playIntro(screenId){
  // fa (ri)partire l'ingresso in sequenza di una schermata
  const s=document.getElementById(screenId);
  if(!s) return;
  s.classList.remove('intro'); void s.offsetWidth; s.classList.add('intro');
}
function _renderRicette(ricette){
  const el=document.getElementById('ricette-list');
  if(!el) return;
  if(!ricette || !ricette.length){
    el.innerHTML='<div style="padding:20px 0;color:var(--ink-muted);font-family:var(--mono);font-size:11px;text-align:center">Nessuna ricetta disponibile per questa disciplina.</div>';
    return;
  }
  const esc=s=>(s==null?'':String(s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const twLabel=disc=>{const d=(disc||'').toLowerCase();return /bar|drink|cocktail|mixolog|caff|coffee/.test(d)?'Twist':'Rivisitazione';};
  el.innerHTML=ricette.map(r=>{
    const foto = r.immagine ? `<div class="ric-foto"><img src="${esc(r.immagine)}" alt="${esc(r.nome)}" loading="lazy" onerror="this.closest('.ric-foto').remove()">${r.immagine_autore?`<div class="ric-foto-credit">${r.immagine_url_fonte?`<a href="${esc(r.immagine_url_fonte)}" target="_blank" rel="noopener">${esc(r.immagine_autore)}</a>`:esc(r.immagine_autore)}</div>`:''}</div>` : '';
    const numeri = (r.numeri && Object.keys(r.numeri).length) ? `<div class="ric-numeri"><div class="ric-numeri-lab">Numeri bersaglio</div>${Object.entries(r.numeri).map(([k,v])=>`<div class="ric-num-row"><span class="ric-num-k">${esc(k)}</span><span class="ric-num-v">${esc(v)}</span></div>`).join('')}</div>` : '';
    const critico = r.punto_critico ? `<div class="ric-critico"><div class="ric-critico-lab">Qui sbagliano quasi tutti</div><div class="ric-critico-txt">${esc(r.punto_critico)}</div></div>` : '';
    const esperimento = r.esperimento ? `<div class="ric-exp"><div class="ric-exp-lab">Provalo così</div><div class="ric-exp-txt">${esc(r.esperimento)}</div></div>` : '';
    const proc = (r.procedimento && r.procedimento.length) ? `<div class="ric-proc"><div class="ric-proc-lab">Procedimento</div>${r.procedimento.map(p=>`<div class="ric-step"><span class="ric-step-n">${esc(p.n)}</span><div class="ric-step-b"><span class="ric-step-t">${esc(p.testo)}</span>${p.numero_chiave?`<span class="ric-step-key">${esc(p.numero_chiave)}</span>`:''}</div></div>`).join('')}</div>` : '';
    const tecniche = (r.tecniche && r.tecniche.length) ? `<div class="ric-tec"><div class="ric-tec-lab">Tecniche</div><div class="ric-tec-chips">${r.tecniche.map(t=>`<span class="ric-tec-chip">${esc(t)}</span>`).join('')}</div></div>` : '';
    const limite = r.limite ? `<div class="ric-limite"><div class="ric-limite-lab">Qui il numero non basta</div><div class="ric-limite-txt">${esc(r.limite)}</div></div>` : '';
    const twist = r.twist ? `<div class="ric-twist"><div class="ric-twist-lab">${twLabel(r.disciplina)}</div><div class="ric-twist-txt">${esc(r.twist)}</div></div>` : '';
    const ab = (r.abbinamenti && (r.abbinamenti.analogia || r.abbinamenti.contrasto)) ? `<div class="ric-abb"><div class="ric-abb-lab">Abbinamenti</div><div class="ric-abb-cols">${r.abbinamenti.analogia?`<div class="ric-abb-col"><span class="ric-abb-k">In analogia</span><span class="ric-abb-v">${esc(r.abbinamenti.analogia)}</span></div>`:''}${r.abbinamenti.contrasto?`<div class="ric-abb-col"><span class="ric-abb-k">In contrasto</span><span class="ric-abb-v">${esc(r.abbinamenti.contrasto)}</span></div>`:''}</div></div>` : '';
    return `
    <div class="ric-card" id="ric-${r.id}" onclick="toggleRicetta('${r.id}')">
      ${foto}
      <div class="ric-disc">${esc(r.disciplina)}</div>
      <div class="ric-nome">${esc(r.nome)}</div>
      <div class="ric-desc">${esc(r.descrizione||'')}</div>
      <div class="ric-fenomeni">${(r.fenomeni||[]).map(f=>`<span class="ric-fen-tag">${esc(f.replace('fen-','').replace(/-/g,' '))}</span>`).join('')}</div>
      <div class="ric-body">
        ${numeri}
        ${critico}
        ${esperimento}
        ${proc}
        ${tecniche}
        ${limite}
        ${twist}
        ${ab}
      </div>
      <div class="ric-toggle">Vedi dettagli ↓</div>
    </div>`;
  }).join('');
}

function toggleRicetta(id){
  const card=document.getElementById('ric-'+id);
  if(!card) return;
  const exp=card.classList.toggle('ric-expanded');
  const tog=card.querySelector('.ric-toggle');
  if(tog) tog.textContent=exp?'Chiudi ↑':'Vedi dettagli ↓';
}

let _ricetteDisciplina='';
function filtraRicette(disc){
  _ricetteDisciplina=disc;
  document.querySelectorAll('.ric-disc-btn').forEach(b=>{
    b.classList.toggle('active',b.dataset.disc===disc);
  });
  _caricaRicette(disc);
}

function _caricaRicette(disc){
  const lang=_lang||'it';
  const url='/v1/ricette'+(disc?'?disc='+disc:'')+(disc?'&lang=':'?lang=')+lang;
  fetch(url).then(r=>r.json()).then(j=>{
    if(Array.isArray(j)) _renderRicette(j);
    else _renderRicette([]);
  }).catch(()=>_renderRicette([]));
}

function switchMappaTab(tab){
  // tab buttons
  document.querySelectorAll('.mappa-tab').forEach(b=>b.classList.toggle('active',b.id==='mtab-'+tab));
  // pannelli
  document.querySelectorAll('.mappa-panel').forEach(p=>p.classList.toggle('active',p.id==='mpanel-'+tab));
  // se si va su Flavor, focus sull'input
  if(tab==='flavor'){
    setTimeout(()=>{const i=document.getElementById('flavor-query');if(i)i.focus();},200);
  }
  // se si va su Ricette, carica il contenuto
  if(tab==='ricette'){
    _caricaRicette(_ricetteDisciplina||'');
  }
  // se si va su Strumenti, caricali (default bar se nessuna disciplina) — Parte A
  if(tab==='strumenti'){
    caricaStrumenti(Matter.disciplina || '');
  }
}

/* ═══ ATLANTE A 4 PORTE (rifinitura review: da voci sparse a 4 gruppi) ═══
   CAPIRE · USARE · CREARE · MISURARE — ogni porta raggruppa le voci esistenti. */
var _PORTE = {
  capire:   { label:'Capire',   sub:'Perché succede', voci:[
                {t:'Fenomeni', d:'Il percorso della disciplina', act:function(){switchMappaTab('fenomeni');}},
                {t:'Principi', d:'Le leggi fisiche di fondo', act:function(){switchMappaTab('principi');}},
                {t:'Tecniche Avanzate', d:'Fat washing, koji, nixtamal…', act:function(){if(typeof apriAvanzate==='function')apriAvanzate();}} ]},
  usare:    { label:'Usare',    sub:'Come si fa al banco', voci:[
                {t:'Ricettario', d:'454 ricette certificate', act:function(){if(typeof apriRicettario==='function')apriRicettario();}},
                {t:'Strumenti', d:'Cosa serve per misurare', act:function(){switchMappaTab('strumenti');}} ]},
  creare:   { label:'Creare',   sub:'Combina e scopri', voci:[
                {t:'Flavour Network', d:'Con cosa dialoga un ingrediente', act:function(){if(typeof apriFlavour==='function')apriFlavour();}},
                {t:'Ponti tra discipline', d:'Vino, birra, dolce per piatto', act:function(){if(typeof apriPonti==='function')apriPonti();}},
                {t:'Menu Lab', d:'Costruisci il tuo menu', act:function(){if(typeof apriMenuBuilder==='function')apriMenuBuilder();}},
                {t:'Recupera scarti', d:'Riusa gli scarti, cross-utilization', act:function(){if(typeof apriScarti==='function')apriScarti();}} ]},
  misurare: { label:'Misurare', sub:'Centra il bersaglio', voci:[
                {t:'Calcolatori', d:'Impasto, teglie, food cost', act:function(){if(typeof apriCalcolatori==='function')apriCalcolatori();}},
                {t:'Il Quaderno', d:'Le tue misure salvate', act:function(){switchTab('quaderno');}},
                {t:'Flavour del giorno', d:'Parti da un ingrediente', act:function(){switchMappaTab('flavor');}} ]}
};
function apriPorta(porta){
  var p = _PORTE[porta]; if(!p) return;
  document.querySelectorAll('.mappa-tab').forEach(b=>b.classList.toggle('active', b.id==='mtab-'+porta));
  var cont = document.getElementById('porta-voci');
  if(cont){
    cont.innerHTML = '<div class="porta-sub">'+p.sub+'</div>' + p.voci.map(function(v,i){
      return '<button class="porta-voce" onclick="_portaVoce(\''+porta+'\','+i+')"><span class="porta-voce-t">'+v.t+'</span><span class="porta-voce-d">'+v.d+'</span><span class="porta-voce-arr">›</span></button>';
    }).join('');
  }
  // apro automaticamente la prima voce della porta
  if(porta==='creare'){ apriCrea(); return; }
  _portaVoce(porta, 0);
}
function _portaVoce(porta, i){
  var p = _PORTE[porta]; if(!p||!p.voci[i]) return;
  // evidenzia la voce scelta
  var cont=document.getElementById('porta-voci');
  if(cont){ cont.querySelectorAll('.porta-voce').forEach(function(b,idx){ b.classList.toggle('sel', idx===i); }); }
  p.voci[i].act();
}

function playIntroScopri(){ playIntro('screen-scopri'); }

function _quandoCasi(nome, disc){
  // mappa fenomeno → casi pratici "quando ti serve"
  const n=(nome||'').toLowerCase();
  const d=(disc||'').toLowerCase();
  const MAP={
    'acidit': ['Il tuo sour è diverso ogni settimana','Il lievito madre non sale come ieri','La confettura non gelifica','Il mash della birra non fermenta bene'],
    'ph': ['Il tuo sour è diverso ogni settimana','Il lievito madre non sale come ieri','La confettura non gelifica','Il mash della birra non fermenta bene'],
    'dilui': ['Il cocktail esce troppo alcolico o troppo piatto','L\'ABV finale non corrisponde alla ricetta','Il ghiaccio cambia il drink in modo inatteso'],
    'carbonat': ['La birra perde gas troppo in fretta','Il cocktail gassato non regge nel bicchiere','La pressione in fusto non è costante'],
    'emulsio': ['La maionese si rompe','Il condimento si separa','La crema non monta','La ganache impazzisce'],
    'carameliz': ['La crostatura è pallida anche ad alta temperatura','Il caramello cristallizza','Il colore del pane non è uniforme'],
    'ferment': ['Il lievito madre non cresce','La birra non fermenta','Il vino si arresta prima del previsto'],
    'estrazion': ['L\'espresso è sottoestratto o sovrastratto','Il caffè filtro è amaro o piatto','La resa non è costante tra le sessioni'],
    'gelat': ['Il gelato è troppo duro appena fuori dal blast','La texture cambia dopo il mantenimento','Il prodotto cede troppo velocemente'],
    'cristall': ['Il cioccolato ha le venature bianche','Il gelato fa i cristalli di ghiaccio','La ganache è granulosa'],
    'q10': ['La fermentazione va troppo veloce o troppo lenta','La maturazione cambia a seconda della stagione','La shelf life non è costante'],
    'attivit': ['Il prodotto ammuffisce prima del previsto','La conserva non regge i tempi dichiarati','Il pane secco troppo in fretta'],
    'brix': ['Lo sciroppo è più dolce o meno dolce del solito','La frutta ha resa diversa tra lotti','Il dessert è troppo dolce o insipido'],
    'maillard': ['La carne non prende colore','Il pane ha la crosta pallida','Il caffè tostato ha note piatte'],
    'grasso': ['La fat washing non rende gli aromi attesi','L\'infusione lipofila è debole','Il burro aromatizzato perde profumo'],
    'colloide': ['La salsa è troppo liquida o troppo densa','Il brodo non lega','La crema si separa in cottura'],
    'proteina': ['La meringa piange','Il soufflé si sgonfia','La crema si straccia'],
    'meringa': ['La meringa piange','Il soufflé si sgonfia','La crema si straccia'],
  };
  for(const key in MAP){ if(n.includes(key)) return MAP[key]; }
  // fallback per disciplina
  const DISC={
    'bar': ['Il cocktail non è replicabile tra un turno e l\'altro','L\'ABV non corrisponde alla ricetta','Il bilanciamento acido-dolce cambia'],
    'panificazione': ['L\'impasto non lievita come ieri','La crosta non è uniforme','Il pane perde umidità troppo in fretta'],
    'pasticceria': ['La crema si straccia','Il cioccolato non tempera','Il biscotto è troppo duro o troppo morbido'],
    'cucina': ['La salsa si separa','La carne non prende colore','Il brodo non ha struttura'],
    'gelateria': ['Il gelato è troppo duro','La texture cambia dopo il mantenimento','Il prodotto cede troppo in vetrina'],
    'caffe': ['L\'espresso non è costante','La resa cambia tra le sessioni','Il latte non monta bene'],
    'vino': ['La fermentazione si arresta','Il vino ossidata troppo in fretta','L\'acidità non è bilanciata'],
    'birra': ['La fermentazione va troppo veloce','La birra perde gas in fretta','Il mash non fermenta bene'],
  };
  for(const key in DISC){ if(d.includes(key)) return DISC[key]; }
  return [];
}
// AbortController globale: al cambio tab annulla le fetch pendenti della tab precedente
// (elimina le race condition / errori JS navigando velocemente tra le tab)
var _tabAbort = null;
function _tabSignal(){
  if(_tabAbort) try{ _tabAbort.abort(); }catch(e){}
  _tabAbort = (typeof AbortController!=='undefined') ? new AbortController() : null;
  return _tabAbort ? _tabAbort.signal : undefined;
}
// wrapper fetch che ignora silenziosamente l'errore di abort (non è un vero errore)
function _afetch(url, opts){
  opts = opts || {};
  if(_tabAbort) opts.signal = _tabAbort.signal;
  return fetch(url, opts).catch(function(e){
    if(e && e.name==='AbortError'){ return {ok:false, _aborted:true, json:function(){return Promise.resolve(null);}}; }
    throw e;
  });
}
function switchTab(t){
  _tabSignal(); // annulla le fetch della tab precedente
  // P0.2 — chiudo ogni overlay/vista aperto prima di cambiare schermata
  if(typeof chiudiVista==='function') chiudiVista();
  document.querySelectorAll('.vista-overlay').forEach(function(o){ o.classList.add('hidden'); });
  var _onb=document.getElementById('onb-overlay'); if(_onb) _onb.classList.add('hidden');
  var _onb4=document.getElementById('onb4'); if(_onb4){ _onb4.classList.remove('show'); }
  ['scopri','lezione','mappa','chiedi','auth','quaderno'].forEach(s=>{
    document.getElementById('screen-'+s).classList.toggle('active',s===t);
  });
  // le tab visibili sono 4: scopri, mappa(=Lab), chiedi, quaderno. Lezione non ha tab propria.
  ['scopri','mappa','chiedi','quaderno'].forEach(s=>{
    const tb=document.getElementById('tab-'+s);
    if(tb) tb.classList.toggle('active', s===t || (t==='lezione' && s==='scopri'));
  });
  // la barra domanda serve solo in Chiedi → chat
  const askBar=document.getElementById('ask-bar');
  askBar.style.display=(t==='chiedi' && _subtab==='chat')?'block':'none';
  // caricamento pigro per schermata (niente fetch inutili all'avvio)
  if(t==='scopri'){ caricaHome(); }
  if(t==='lezione') caricaLezioneStep(Matter.step);
  if(t==='mappa'){
    const _disc = Matter.disciplina || 'bar';
    if(typeof apriPorta==='function') apriPorta('capire');
    caricaMappa(_disc);
    caricaStrumenti(_disc);
    if(!Matter.disciplina) document.getElementById('mappa-label').textContent = _t('mappa_scegli');
  }
  if(t==='quaderno') caricaQuaderno();
  // ingresso in sequenza per la schermata attivata (movimento coerente ovunque)
  playIntro('screen-'+t);
  // posizione deterministica: la schermata parte sempre dall'alto
  window.scrollTo(0,0);
}

/* ── SUBTAB dentro Chiedi (chat ↔ calcolatori) ────────── */
function switchSubtab(name){
  _subtab = name;
  ['chat','calc'].forEach(s=>{
    const panel=document.getElementById('panel-'+s);
    if(panel) panel.classList.toggle('active',s===name);
    const btn=document.getElementById('subtab-'+s);
    if(btn) btn.classList.toggle('active',s===name);
  });
  // la barra domanda ha senso solo nella chat
  document.getElementById('ask-bar').style.display=(name==='chat')?'block':'none';
}

/* ── STATO GLOBALE ────────────────────────────────────── */
const Matter = {
  disciplina: null,   // null finché l'utente non sceglie una disciplina
  step: 0,
  totale: 0,
  fenomenoId: null
};

let _lang = (function(){
  const ok = ['it','en','es'];
  try {
    // 1. lingua esplicita nell'URL (?lang=)
    const u = new URLSearchParams(location.search).get('lang');
    if (u && ok.includes(u)) return u;
    // 2. scelta salvata dall'utente (toggle, persiste)
    const s = localStorage.getItem('matter_lang');
    if (s && ok.includes(s)) return s;
  } catch(e){}
  // 3. default: Matter è italiano-first. NON usiamo navigator.language
  //    (un italiano col telefono in inglese deve vedere l'app in italiano).
  return 'it';
})();

/* ── TOGGLE LINGUA IT/EN (GT5) ────────────────────────── */
function toggleLang(){
  _lang = _lang === 'it' ? 'en' : (_lang === 'en' ? 'es' : 'it');
  try { localStorage.setItem('matter_lang', _lang); } catch(e){}
  applicaStringheUI();
  // invalida cache e ricarica
  _homeCached = null;
  Object.keys(_mappaCache).forEach(k => delete _mappaCache[k]);
  if(document.getElementById('screen-scopri').classList.contains('active')) caricaHome();
  if(document.getElementById('screen-lezione').classList.contains('active')) caricaLezioneStep(Matter.step);
  if(document.getElementById('screen-mappa').classList.contains('active') && Matter.disciplina) caricaMappa(Matter.disciplina);
}

/* ── ONBOARDING ───────────────────────────────────────── */
function _isFirstVisit(){
  return !localStorage.getItem('matter_onb_done');
}
function _segnaOnboardingFatto(){
  localStorage.setItem('matter_onb_done','1');
}

function mostraNudgeSeNecessario(){
  // mostra il nudge solo al primo accesso e se non ha ancora scelto una disciplina
  if(_isFirstVisit() && !Matter.disciplina){
    document.getElementById('onb-nudge').style.display='flex';
  }
}
function chiudiNudge(){
  document.getElementById('onb-nudge').style.display='none';
}

function mostraCompletamentoLezione(haSuccessivo){
  const nudge = document.getElementById('les-complete-nudge');
  if(!haSuccessivo && nudge){
    nudge.style.display='flex';
    _segnaOnboardingFatto();
  } else if(nudge){
    nudge.style.display='none';
  }
}

/* ── SCOPRI DINAMICA (FE5) ────────────────────────────── */
let _homeCached = null;
async function caricaHome(){
  if(_homeCached){ renderHome(_homeCached); return; }
  { const _h=document.getElementById('scopri-hero'); if(_h) _h.classList.add('loading'); }
  try {
    const r = await fetch('/home?lang='+_lang);
    if(!r.ok) throw new Error('server error');
    const j = await r.json();
    _homeCached = j;
    renderHome(j);
    // carica conteggio discipline in parallelo
    ['bar','bakery','cucina','caffetteria','pasticceria','gelateria','vino','birra'].forEach(caricaContDisciplina);
  } catch(e){
    document.getElementById('scopri-ey').textContent = _t('scopri_errore_eyebrow');
    document.getElementById('scopri-titolo').textContent = _t('scopri_errore_titolo');
  }
}

// Cruscotto operativo: bersaglio del giorno · ultima misura salvata · esperimento
function _popolaCruscotto(f){
  f = f || {};
  var t=document.getElementById('crus-target');
  var ts=document.getElementById('crus-target-sub');
  var tgt='';
  var T=f.target;
  if(T && typeof T==='object'){ tgt = T.numero || T.valore || T.raw || T.testo || ''; }
  else if(typeof T==='string'){ tgt = T; }
  tgt = String(tgt||'').trim();
  // Il FENOMENO è il protagonista, non il numero (la svolta). Nome grande, numero come dettaglio.
  if(t){
    var nome = f.nome || '—';
    // nome può essere lungo: riduco il font se serve
    t.textContent = nome;
    t.style.fontSize = nome.length>22 ? '20px' : (nome.length>14 ? '24px' : '');
    t.classList.remove('crus-target-blurred');
  }
  if(ts){
    // sotto: il numero se c'è (nitido), altrimenti niente
    ts.textContent = (tgt && tgt.length<=16) ? (tgt + (f.unita? f.unita : '')) : '';
  }
  // ultima misura salvata dal Quaderno
  var m=document.getElementById('crus-misura');
  if(m){
    var misure=[];
    try{ misure=JSON.parse(localStorage.getItem('matter_quaderno')||'[]'); }catch(e){}
    if(misure.length){
      var u=misure[misure.length-1]||{};
      var val = (u.valore!=null) ? (u.valore+(u.unita?' '+u.unita:'')) : (u.nome||'salvata');
      m.textContent = String(val).slice(0,12);
      m.classList.remove('crus-invito');
    } else { m.innerHTML='Fai la prima misura →'; m.classList.add('crus-invito'); }
  }
  // esperimento in corso (stato locale)
  var e=document.getElementById('crus-exp');
  if(e){
    var exp=null; try{ exp=localStorage.getItem('matter_exp_corso'); }catch(x){}
    if(exp){ e.textContent='In corso'; e.classList.remove('crus-invito'); }
    else { e.innerHTML='Prova un esperimento →'; e.classList.add('crus-invito'); }
  }
}
function renderHome(j){
  const f = j.fenomeno || {};
  { const _h=document.getElementById('scopri-hero'); if(_h) _h.classList.remove('loading'); }
  // CRUSCOTTO OPERATIVO — il colpo d'occhio (fenomeno + numero + misura + esperimento)
  _popolaCruscotto(f);
  // CARD HERO SOTTO = l'approfondimento: capire il fenomeno (NO numero duplicato, quello è nel cruscotto)
  document.getElementById('scopri-ey').textContent =
    'capisci il fenomeno · ' + (f.dominio||'');
  document.getElementById('scopri-titolo').textContent = f.nome || '—';
    const _loop = document.getElementById('loop-guidato');
    const _loopFen = document.getElementById('loop-fen-nome');
    if(_loop) _loop.style.display='none';
    if(_loopFen) _loopFen.textContent = f.nome || 'Fenomeno';
  // il numero NON si ripete qui (è già nel cruscotto): la card sotto racconta la scienza
  const numBox = document.getElementById('scopri-num');
  if(numBox) numBox.style.display='none';
  // il PERCHÉ (descrizione) è il cuore della card: la scienza del fenomeno
  document.getElementById('scopri-desc').textContent = f.scheda_intro || '';
  Matter.fenomenoId = f.id;
  // onboarding: mostra nudge se primo accesso
  mostraNudgeSeNecessario();
  // principio
  const pc = document.getElementById('scopri-principio');
  if(j.principio){
    document.getElementById('princ-nome').textContent = j.principio.nome;
    document.getElementById('princ-desc').textContent = j.principio.scheda_intro || '';
    pc.style.display='block';
  } else { pc.style.display='none'; }
}

async function caricaContDisciplina(nome){
  try {
    const r = await fetch('/disciplina/'+nome);
    const j = await r.json();
    const n = j.totale||0;
    const key = nome.replace('caffetteria','caffe');
    const elM = document.getElementById('disc-'+key+'-m');
    if(elM) elM.textContent = n + ' fenomeni';
    const elChip = document.getElementById('disc-'+key+'-chip');
    if(elChip) elChip.textContent = n;
  } catch(e){}
}

function selezionaDisciplina(nome){
  Matter.disciplina = nome;
  Matter.step = 0;
  chiudiNudge();
  switchTab('lezione');
}

function avviaLezione(){
  // naviga alla lezione del fenomeno del giorno se disponibile
  const disc = Matter.disciplina || localStorage.getItem('matter_disc') || 'bar';
  const fenId = Matter.fenomenoId;
  switchTab('lezione');
  if(fenId && disc){
    // trova lo step del fenomeno nella disciplina e carica direttamente
    setTimeout(()=>{ _caricaLezionePerId(disc, fenId); }, 100);
  }
}

/* ── LEZIONE DINAMICA (FE6) ───────────────────────────── */
// Cache fenomeni lato client per navigazione istantanea
const _lesCache = {};

async function _precaricaLezione(disc, lang, tok) {
  // Precarica i fenomeni in background dopo il primo caricamento
  try {
    const jobs = [];
    for(let i = 1; i < (Matter.totale || 30); i++) {
      if(!_lesCache[disc+'_'+i]) {
        jobs.push(
          fetch(`/lezione/${disc}/${i}?lang=${lang}&token=${tok}`)
            .then(r => r.ok ? r.json() : null)
            .then(j => { if(j && !j.errore && !j.paywall) _lesCache[disc+'_'+i] = j; })
            .catch(()=>{})
        );
      }
      if(jobs.length >= 3) { await Promise.all(jobs.splice(0,3)); }
    }
    if(jobs.length) await Promise.all(jobs);
  } catch(e) {}
}

async function _caricaLezionePerId(disc, fenId){
  // trova lo step del fenomeno nella disciplina e carica la lezione giusta
  try {
    const r = await fetch(`/disciplina/${disc}?lang=${_lang}`);
    if(!r.ok) return;
    const j = await r.json();
    const fenomeni = j.fenomeni || [];
    const idx = fenomeni.findIndex(f => f.id === fenId);
    if(idx >= 0){
      Matter.disciplina = disc;
      Matter.step = idx;
      Matter.totale = fenomeni.length;
      caricaLezioneStep(idx);
    } else {
      caricaLezioneStep(0);
    }
  } catch(e){ caricaLezioneStep(0); }
}

async function caricaLezioneStep(step){
  const disc = Matter.disciplina || 'bar';
  var _discMap={'bar':'disc_bar','cucina':'disc_cucina','panificazione':'disc_panificazione',
    'pasticceria':'disc_pasticceria','gelateria':'disc_gelateria','caffe':'disc_caffe',
    'vino':'disc_vino','birra':'disc_birra','sicurezza':'disc_sicurezza'};
  var _discKey=_discMap[disc];
  var _discNomeUI=(_discKey&&_lang!=='it')?(_t(_discKey)||disc.charAt(0).toUpperCase()+disc.slice(1)):(disc.charAt(0).toUpperCase()+disc.slice(1));
  document.getElementById('les-disciplina-label').textContent = _discNomeUI;
  document.getElementById('les-step-label').textContent = _t('les_caricamento');
  const _lNome=document.getElementById('les-nome');
  const _lSch=document.getElementById('les-scheda');
  const _lTgt=document.getElementById('les-target');
  _lNome.textContent='\u00a0'; _lNome.classList.add('skel');
  _lSch.textContent='\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0'; _lSch.classList.add('skel');
  if(_lTgt){ _lTgt.textContent='\u00a0\u00a0\u00a0\u00a0'; _lTgt.classList.add('skel'); }
  document.getElementById('les-quiz-box').style.display='none';
  try {
    const tok = localStorage.getItem('matter_token')||'';
    // Usa cache se disponibile (precaricamento in background)
    let j = _lesCache[disc+'_'+step];
    if(!j) {
      const r = await fetch(`/lezione/${disc}/${step}?lang=${_lang}&token=${tok}`);
      if(r.status===402){ mostraPopupPro('lezione'); return; }
      if(!r.ok) throw new Error('server');
      j = await r.json();
      _lesCache[disc+'_'+step] = j;
    }
    if(j.paywall){ mostraPopupPro('lezione_locked'); return; }
    if(j.errore){ document.getElementById('les-nome').textContent = j.errore; return; }
    Matter.step = j.step;
    Matter.totale = j.totale_passi;
    Matter.nodoCorrente = j.fenomeno.id;
    // header
    document.getElementById('les-pos').textContent = `${_t('les_fenomeno')} ${j.step+1} ${_t('les_di')} ${j.totale_passi}`;
    // aggiorna progress bar
    const pct = j.totale_passi > 0 ? Math.round((j.step+1)/j.totale_passi*100) : 0;
    const barFill = document.getElementById('les-bar-fill');
    if(barFill) barFill.style.width = pct + '%';
    document.getElementById('les-step-label').textContent =
      (j.fenomeno.dominio||'') + ' · fenomeno ' + (j.step+1);
    ['les-nome','les-scheda','les-target'].forEach(id=>{
      const el=document.getElementById(id); if(el) el.classList.remove('skel');
    });
    document.getElementById('les-nome').textContent = j.fenomeno.nome;
    // popola "Quando ti serve"
    const _wbox=document.getElementById('les-quando-box');
    const _wlist=document.getElementById('les-quando-list');
    if(_wbox && _wlist){
      const _casi = _quandoCasi(j.fenomeno.nome, j.fenomeno.disciplina||Matter.disciplina||'');
      if(_casi.length){
        _wlist.innerHTML=_casi.map(c=>`<div class="sl-quando-item">${c}</div>`).join('');
        _wbox.style.display='block';
      } else { _wbox.style.display='none'; }
    }
    _formattaScheda(document.getElementById('les-scheda'), j.fenomeno.scheda || 'Scheda in aggiornamento.');
    // domanda-gancio sopra la scheda (apre col "perché", non col "cos'è")
    var _gel = document.getElementById('les-gancio');
    if(_gel){
      if(j.fenomeno.gancio){ _gel.textContent = j.fenomeno.gancio; _gel.style.display='block'; }
      else { _gel.style.display='none'; }
    }
    // target — mostra la box solo se il fenomeno ha un numero-bersaglio,
    // coerente con lo Scopri; niente "—" spoglio quando il dato non c'è
    const datoBox = document.getElementById('les-dato-box');
    if(j.fenomeno.target){
      _renderTarget(document.getElementById('les-target'), j.fenomeno.target, false);
      var _mi=document.getElementById('les-mirino-intro');
      renderMirino(document.getElementById('les-mirino'), j.fenomeno.nome, j.fenomeno.target);
      if(_mi) _mi.style.display = document.getElementById('les-mirino').style.display==='none'?'none':'';
      datoBox.style.display = '';
      _caricaStrumentoPerFenomeno(disc, j.fenomeno.nome, j.fenomeno.target);
    } else {
      datoBox.style.display = 'none';
      var _mir=document.getElementById('les-mirino'); if(_mir) _mir.style.display='none';
      var _mii=document.getElementById('les-mirino-intro'); if(_mii) _mii.style.display='none';
      var sb=document.getElementById('les-strumento-box'); if(sb) sb.style.display='none';
    }
    // stepper a puntini: quanti fenomeni, dove sei, salto diretto
    renderLesDots(j.step, j.totale_passi);
    // ═══ PAYWALL PER-PARTI (pro_locked): sfoca SOLO il numero del Mirino, la scienza è gratis ═══
    _applicaPaywallLezione(j.pro_locked === true);
    // principio
    const pb = document.getElementById('les-principio-box');
    if(j.principio){
      document.getElementById('les-principio-testo').textContent = j.principio.testo||'';
      pb.style.display='block';
    } else { pb.style.display='none'; }
    // ═══ SCAVA — le quattro porte per andare più a fondo (longevità) ═══
    renderScava(j.scava, j.fenomeno.nome);
    // quiz: caricato a parte (lazy), così la lezione appare subito.
    // La prima volta il server lo genera, poi è in cache e istantaneo.
    caricaQuizLezione(j.fenomeno.id);
    // bottoni nav
    document.getElementById('les-btn-prec').style.opacity = j.ha_precedente?'1':'0.4';
    document.getElementById('les-btn-succ').textContent =
      j.ha_successivo ? 'Avanti →' : 'Vai all\'Atlante →';
    // onboarding: nudge completamento all'ultimo fenomeno
    mostraCompletamentoLezione(j.ha_successivo);
    // Precarica i prossimi step in background
    if(step === 0) {
      setTimeout(() => _precaricaLezione(disc, _lang, localStorage.getItem('matter_token')||''), 500);
    }
  } catch(e){
    ['les-nome','les-scheda','les-target'].forEach(id=>{
      const el=document.getElementById(id); if(el) el.classList.remove('skel');
    });
    document.getElementById('les-nome').textContent = _t('les_errore');
  }
}

// Paywall per-parti nella lezione: sfoca il numero del Mirino al free (la scienza resta gratis)
function _applicaPaywallLezione(locked){
  var mirino = document.getElementById('les-mirino');
  var datoBox = document.getElementById('les-dato-box');
  var target = document.getElementById('les-target');
  // rimuovo eventuale overlay precedente
  var vecchio = document.getElementById('les-mirino-lock'); if(vecchio) vecchio.remove();
  if(!locked){
    if(mirino) mirino.classList.remove('les-mirino-blur');
    if(target) target.classList.remove('les-mirino-blur');
    return;
  }
  // sfoco il numero e aggiungo l'overlay "Sblocca con Pro"
  var box = datoBox && datoBox.style.display!=='none' ? datoBox : mirino;
  if(box && box.style.display!=='none'){
    if(target) target.classList.add('les-mirino-blur');
    if(mirino) mirino.classList.add('les-mirino-blur');
    var lock=document.createElement('div');
    lock.id='les-mirino-lock'; lock.className='les-mirino-lockbox';
    lock.innerHTML='<span class="les-lock-ico">🔒</span><span>Il numero-bersaglio esatto è Pro</span>';
    lock.onclick=function(){ mostraPopupPro('numero'); };
    box.style.position='relative';
    box.appendChild(lock);
  }
}
function renderLesDots(step, totale){
  const box = document.getElementById('les-dots');
  if(!box) return;
  if(!totale || totale < 2){ box.innerHTML=''; return; }
  let html='';
  for(let i=0;i<totale;i++){
    const cls = i===step ? 'current' : (i<step ? 'done' : '');
    html += `<div class="les-dot ${cls}" onclick="caricaLezioneStep(${i})">${i+1}</div>`;
  }
  box.innerHTML = html;
}

async function caricaQuizLezione(nodeId){
  const box = document.getElementById('les-quiz-box');
  box.style.display='none';
  try {
    const r = await fetch(`/quiz/${nodeId}?lang=${_lang}`);
    if(!r.ok) return;
    const j = await r.json();
    // guardia anti-race: se hai già cambiato passo, non mostrare un quiz vecchio
    if(j.quiz && Matter.nodoCorrente === nodeId){
      renderQuizLezione(j.quiz);
      box.style.display='block';
    }
  } catch(e){ /* nessun quiz: la lezione resta comunque completa */ }
}

function renderQuizLezione(q){
  document.getElementById('quiz-domanda').textContent = q.domanda||'';
  const opts = document.getElementById('quiz-opzioni');
  opts.innerHTML='';
  document.getElementById('quiz-spiegazione').style.display='none';
  (q.opzioni||[]).forEach((op,i)=>{
    const div=document.createElement('div');
    div.className='q2-opt';
    div.innerHTML=`<span class="q2-dot"></span>${esc(op)}
      ${i===q.corretta?'<span class="q2-chk"><svg viewBox="0 0 24 24"><path d="M5 12l5 5L20 6"/></svg></span>':''}`;
    div.onclick=()=>{
      opts.querySelectorAll('.q2-opt').forEach(o=>o.classList.remove('correct'));
      if(i===q.corretta){
        div.classList.add('correct');
        const sp=document.getElementById('quiz-spiegazione');
        sp.textContent=q.spiegazione||'';
        sp.style.display='block';
      }
    };
    opts.appendChild(div);
  });
}

function lesStep(dir){
  const newStep = Matter.step + dir;
  if(newStep < 0){ switchTab('scopri'); return; }
  if(newStep >= Matter.totale){ switchTab('mappa'); return; }
  caricaLezioneStep(newStep);
}

/* ── MAPPA DINAMICA (FE6b) ────────────────────────────── */
const _mappaCache = {};   // { disciplina: [fenomeni] } — niente flicker al rientro

function renderMappa(disc, fens, casi){
  const label = document.getElementById('mappa-label');
  const cont = document.getElementById('mappa-percorso');
  label.textContent = _t('mappa_percorso') + disc;
  if(!fens.length){
    cont.innerHTML='<div style="padding:14px;color:var(--ink-muted);font-size:13px">'+_t('mappa_nessun_fen')+'</div>';
    return;
  }
  casi = casi || [];
  var html = fens.map(function(f,i){
    var isFirst = i===0;
    var stato = f.stato||'libero';
    var su = f.stato_utente||'mai_aperto';   // stato dinamico per-utente (backend)
    // PAYWALL PER-PARTI: il fenomeno NON si blocca mai — la scheda si apre sempre (scienza gratis).
    // Il Pro è solo dentro (numero + errori). Niente più lucchetto sull'intero fenomeno.
    var isLock = false;
    var nodeClass = stato==='completato'?'done':isFirst?'active':'libero';
    var muClass = 'mu-'+su;
    var apps = f.applicazioni || [];
    var tagHtml = stato==='completato'
      ? '<span class="p-tag done">completato</span>'
      : isFirst ? '<span class="p-tag active">inizia da qui</span>'
      : '';
    // Mirino a stati: sempre crosshair (il fenomeno è sempre apribile)
    var svgIcon = '<svg class="mu-ring" viewBox="0 0 24 24" fill="none">'
        + '<circle class="mu-r" cx="12" cy="12" r="9" stroke-width="1.4"/>'
        + '<circle class="mu-d" cx="12" cy="12" r="2.6"/>'
        + '<path class="mu-cross" d="M12 1v3M12 20v3M1 12h3M20 12h3" stroke-width="1.4"/></svg>';
    var nodeStyle = '';
    // pill applicazioni: se la madre ne ha, mostra il contatore che espande
    var appsPill = apps.length
      ? '<button class="p-apps-toggle" onclick="event.stopPropagation();toggleApps(this)">'
        + apps.length + ' applicazion' + (apps.length===1?'e':'i') + '<span class="p-apps-caret">\u203A</span></button>'
      : '';
    var appsList = apps.length
      ? '<div class="p-apps-list" style="display:none">'
        + apps.map(function(a){
            return '<div class="p-app" onclick="event.stopPropagation();avviaApplicazione(\''+esc(a.id)+'\')">'
              + '<span class="p-app-dot"></span><span class="p-app-nome">'+esc(a.nome)+'</span></div>';
          }).join('')
        + '</div>'
      : '';
    return '<div class="p-step '+(stato==='completato'?'done':'')+'">'
      + '<div class="p-step-main" style="cursor:pointer" onclick="vaiAStep('+i+')">'
      + '<div class="pnode '+nodeClass+' '+muClass+'" style="'+nodeStyle+'">'+svgIcon+'</div>'
      + '<div class="p-info"><div class="p-name-row"><span class="p-name">'+esc(f.nome)+'</span>'+tagHtml+'</div>'
      + appsPill + '</div></div>'
      + appsList
      + '</div>';
  }).join('');
  // sezione CASI reali (proc-*): dimostrazioni del metodo all'opera
  if(casi.length){
    html += '<div class="casi-sec"><div class="casi-lab">Casi reali</div>'
      + casi.map(function(c){
          return '<div class="caso-card" onclick="avviaApplicazione(\''+esc(c.id)+'\')">'
            + '<span class="caso-icon">\u25C9</span><span class="caso-nome">'+esc(c.nome)+'</span></div>';
        }).join('')
      + '</div>';
  }
  cont.innerHTML = html;
}

// espande/chiude le applicazioni sotto una madre
function toggleApps(btn){
  var step = btn.closest('.p-step');
  var list = step ? step.querySelector('.p-apps-list') : null;
  if(!list) return;
  var open = list.style.display !== 'none';
  list.style.display = open ? 'none' : 'block';
  btn.classList.toggle('aperto', !open);
}

// apre una applicazione o un caso come lezione diretta (per id)
function avviaApplicazione(fenId){
  var disc = Matter.disciplina || 'bar';
  switchTab('lezione');
  setTimeout(function(){ _caricaLezionePerId(disc, fenId); }, 100);
}

// device-id anonimo persistente (per stato_utente prima del login). Fallback in memoria.
var _memDeviceId = null;
function _deviceId(){
  try{
    var d = localStorage.getItem('matter_device_id');
    if(!d){ d = _uuidv4(); localStorage.setItem('matter_device_id', d); }
    return d;
  }catch(e){
    if(!_memDeviceId) _memDeviceId = _uuidv4();
    return _memDeviceId;
  }
}
function _uuidv4(){
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){
    var r = Math.random()*16|0, v = c==='x'?r:(r&0x3|0x8); return v.toString(16);
  });
}
// header standard per lo stato per-utente (device sempre, token se loggato)
function _statoHeaders(extra){
  var h = extra || {};
  h['X-Device-Id'] = _deviceId();
  try{ var tk = localStorage.getItem('matter_token'); if(tk) h['X-Token'] = tk; }catch(e){}
  return h;
}

// l'utente fissa una misura su un fenomeno → POST /v1/misura → scarto + accende il Mirino
async function fissaMisura(btn){
  var box = btn.closest('.s-misura');
  if(!box) return;
  var input = box.querySelector('.s-misura-input');
  var esito = box.querySelector('.s-misura-esito');
  var grezzo = (input.value||'').trim();
  if(!grezzo){ input.focus(); return; }
  var valore = parseFloat(grezzo.replace(',','.'));
  var fen = box.getAttribute('data-fen');
  var unita = box.getAttribute('data-unita')||'';
  var target = box.getAttribute('data-target')||'';
  esito.innerHTML = '<span class="s-misura-loading">salvo…</span>';
  try{
    var r = await fetch('/v1/misura',{
      method:'POST',
      headers:_statoHeaders({'Content-Type':'application/json'}),
      body:JSON.stringify({ fenomeno:fen, valore:isNaN(valore)?null:valore, unita:unita||null, grezzo:grezzo, lang:_vistaLang() })
    });
    var j = await r.json();
    // scarto dal target (calcolo locale per il feedback immediato; il backend conferma in_finestra)
    var nums = String(target).split(/[–-]/).map(function(x){return parseFloat(x);});
    var lo = nums[0], hi = nums[1]||nums[0];
    var esitoTxt, esitoCls, statoBadge;
    if(j.in_finestra===true || (!isNaN(valore) && valore>=lo && valore<=hi)){
      esitoCls='dentro'; esitoTxt='Sei nel bersaglio. Questo è il valore che rende il risultato ripetibile.';
      statoBadge = 'DENTRO FINESTRA'+(isNaN(valore)?'':' · '+valore+(unita?' '+unita:''));
      // accendo il numero-bersaglio di terracotta caldo (il cuore operativo si scalda)
      var numBoxEl = btn.closest('.s-num-box') || (esito.closest && esito.closest('.s-num-box'));
      if(numBoxEl){ numBoxEl.classList.add('in-window'); }
    } else if(!isNaN(valore)){
      var scarto = valore<lo ? (valore-lo) : (valore-hi);
      esitoCls='fuori'; esitoTxt='Fuori finestra: '+(scarto>0?'+':'')+scarto.toFixed(1)+(unita?' '+unita:'')+'. Un\'osservazione, non un errore.';
      statoBadge = 'FUORI FINESTRA '+(scarto>0?'+':'')+scarto.toFixed(1)+(unita?' '+unita:'');
      var nb2 = btn.closest('.s-num-box'); if(nb2){ nb2.classList.remove('in-window'); }
    } else {
      esitoCls='fuori'; esitoTxt='Misura salvata.'; statoBadge='';
    }
    esito.innerHTML = '<div class="s-misura-out '+esitoCls+'">'+esitoTxt+'</div>'+(statoBadge?'<div class="s-stato-badge '+esitoCls+'">'+statoBadge+'</div>':'')
      + '<button class="s-salva-misura" onclick="apriSalvaMisura(\''+String(fen||'').replace(/'/g,"\\'")+'\',\''+String(target||'').replace(/'/g,"\\'")+'\',\''+String(unita||'').replace(/'/g,"\\'")+'\')">Salva questa misura nel Quaderno</button>';
    // evento interno: l'Atlante, se montato, ricarica e riaccende il Mirino
    try{ window.dispatchEvent(new CustomEvent('measurement_saved',{detail:{fenomeno:fen}})); }catch(e){}
    // invalida la cache mappa così alla riapertura lo stato è fresco
    if(typeof _mappaCache!=='undefined' && Matter && Matter.disciplina){ delete _mappaCache[Matter.disciplina]; }
  }catch(e){
    esito.innerHTML = '<div class="s-misura-out fuori">Errore nel salvataggio. Riprova.</div>';
  }
}

async function caricaMappa(disc){
  // rientro: se già in cache, render immediato, zero placeholder = zero salto
  if(_mappaCache[disc]){ var _c=_mappaCache[disc]; renderMappa(disc, _c.fens||_c, _c.casi||[]); return; }
  const cont = document.getElementById('mappa-percorso');
  document.getElementById('mappa-label').textContent = _t('mappa_percorso') + disc;
  // altezza minima durante il load: le sezioni sotto non si spostano
  cont.innerHTML = `<div style="display:flex;flex-direction:column;gap:10px;padding:4px 0">`
    +['80%','65%','75%','55%'].map(w=>`<div class="skel" style="height:52px;border-radius:10px;width:${w}">&nbsp;</div>`).join('')
    +'</div>';
  try {
    const r = await fetch('/mappa/'+disc, { headers: _statoHeaders() });
    if(!r.ok) throw new Error('server');
    const j = await r.json();
    const fens = j.fenomeni||[];
    _mappaCache[disc] = {fens:fens, casi:j.casi||[]};
    renderMappa(disc, fens, j.casi||[]);
  } catch(e){
    cont.innerHTML=`<div style="padding:14px;color:var(--e700);font-size:13px">${_t('mappa_errore')}</div>`;
  }
}

function vaiAStep(idx){
  Matter.step = idx;
  switchTab('lezione');
}

/* ── CHAT / GRAFO ─────────────────────────────────────── */
const DOMCOL={bar:'#245979',cucina:'#12545D',bakery:'#12545D',caffetteria:'#3E4E52',fermentazione:'#5E9BA3',trasversale:'#5A6C70'};
let busy=false;
function setBusy(b){busy=b;document.getElementById('ask-btn').disabled=b;}
function invia(){const q=document.getElementById('q').value.trim();if(!q||busy)return;document.getElementById('q').value='';chiediTesto(q);}

// mini-history: ultimi 3 scambi in memoria (resettata al refresh, zero DB)
const _chatHistory=[];
const _HISTORY_MAX=3;

function chiediTesto(q){
  if(busy)return;
  if(!_isPro()){
    const usate=_getDomande();
    if(usate>=FREE_LIMIT){ apriPaywall(); return; }
  }
  const e=document.getElementById('empty-state');if(e)e.remove();
  switchTab('chiedi');switchSubtab('chat');
  setBusy(true);
  // provo lo streaming; se fallisce, fallback alla chat normale
  _chiediStream(q).catch(function(){ _chiediNonStream(q); });
}

// ═══ CHAT STREAMING (P8) — SSE con token che scorrono + widget inline ═══
async function _chiediStream(q){
  const history=_chatHistory.slice(-_HISTORY_MAX);
  const _tok=localStorage.getItem('matter_token')||'';
  const _ctx = _ctxChat || window._chatContesto || null;
  // creo la scheda risposta che si riempie man mano
  var card=document.createElement('div'); card.className='scheda scheda-stream';
  var flusso=document.createElement('div'); flusso.className='stream-flusso';
  card.appendChild(flusso);
  var statusEl=document.createElement('div'); statusEl.className='stream-status';
  statusEl.innerHTML='<span class="t-dots"><span class="t-dot"></span><span class="t-dot"></span><span class="t-dot"></span></span> <span id="stream-status-txt"></span>';
  card.appendChild(statusEl);
  document.getElementById('schede').prepend(card);
  card.scrollIntoView({behavior:'smooth',block:'start'});

  var resp = await fetch('/chiedi/stream?lang='+(typeof _lang!=='undefined'?_lang:'it'),
    {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}),
     body:JSON.stringify({domanda:q, history:history, token:_tok, contesto:_ctx})});
  if(resp.status===402){ card.remove(); var j=await resp.json(); mostraPopupPro('esaurito'); throw {handled:true}; }
  if(!resp.ok || !resp.body){ card.remove(); throw new Error('no stream'); }

  var reader=resp.body.getReader();
  var dec=new TextDecoder();
  var buf=''; var testoAccumulato=''; var txtEl=null; var erroreVisto=false;
  var curTxt=function(){ if(!txtEl){ txtEl=document.createElement('div'); txtEl.className='stream-txt'; flusso.appendChild(txtEl); } return txtEl; };

  while(true){
    var chunk=await reader.read();
    if(chunk.done) break;
    buf += dec.decode(chunk.value, {stream:true});
    var parti=buf.split('\n\n');
    buf=parti.pop();
    for(var i=0;i<parti.length;i++){
      var linea=parti[i].trim();
      if(!linea.indexOf('data:')===0 && linea.indexOf('data:')!==0) continue;
      var jsonStr=linea.replace(/^data:\s*/,'');
      if(!jsonStr) continue;
      var ev; try{ ev=JSON.parse(jsonStr); }catch(e){ continue; }
      if(ev.tipo==='status'){
        var st=document.getElementById('stream-status-txt'); if(st) st.textContent=ev.testo||'';
      } else if(ev.tipo==='token'){
        testoAccumulato += (ev.delta||'');
        curTxt().innerHTML = _formattaRispostaChat(testoAccumulato);
        card.scrollIntoView({behavior:'smooth',block:'nearest'});
      } else if(ev.tipo==='widget'){
        txtEl=null; // i prossimi token vanno sotto il widget
        if(ev.widget==='fenomeno' && ev.id){ _streamWidgetFenomeno(flusso, ev.id); }
        else if(ev.widget==='calcolatore'){ _streamWidgetCalcolo(flusso, ev); }
      } else if(ev.tipo==='error'){
        erroreVisto=true;
      } else if(ev.tipo==='done'){
        // chiudo
      }
    }
  }
  statusEl.remove();
  setBusy(false);
  _incDomande();
  if(erroreVisto && !testoAccumulato){ card.remove(); throw new Error('stream error'); }
  if(testoAccumulato){ _chatHistory.push({q:q, r:testoAccumulato.slice(0,300)}); if(_chatHistory.length>_HISTORY_MAX*2) _chatHistory.splice(0,2); }
}
// formatta il testo in prosa fluida: i marcatori PROBLEMA/PERCHÉ diventano paragrafi spaziati,
// non etichette stampatello. Markdown leggero + grassetti mirati.
function _formattaRispostaChat(t){
  var e=_escV(t);
  // i vecchi marcatori diventano separatori di paragrafo morbidi (non stampatello urlato)
  e=e.replace(/\s*(PROBLEMA|PERCHÉ|PERCHE|NUMERO|MISURA|AZIONE)\s*:\s*/g, function(m,p){
    return '</p><p class="chat-par">';
  });
  // markdown grassetto **parola** → <strong>
  e=e.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
  e=e.replace(/\n\n/g,'</p><p class="chat-par">').replace(/\n/g,'<br>');
  return '<p class="chat-par">'+e+'</p>';
}
async function _streamWidgetFenomeno(flusso, id){
  var ph=document.createElement('div'); ph.className='stream-widget'; ph.innerHTML='<div class="calc-loading">Carico la scheda…</div>';
  flusso.appendChild(ph);
  try{
    var r=await fetch('/nodo?traccia=1',{method:'POST',headers:_statoHeaders({'Content-Type':'application/json'}),body:JSON.stringify({id:id})});
    var j=await r.json();
    if(j && j.tipo_fenomeno){ ph.innerHTML=''; ph.appendChild(_costruisciMiniSchedaFenomeno(j, id)); }
    else { ph.remove(); }
  }catch(e){ ph.remove(); }
}
function _streamWidgetCalcolo(flusso, ev){
  var d=ev.dati||{};
  var wrap=document.createElement('div'); wrap.className='stream-widget';
  var num = d.numero || d.risultato || '';
  var h='<div class="stream-calc"><div class="stream-calc-lab">'+_escV(ev.calcolo||'calcolo')+'</div>';
  if(num) h+='<div class="stream-calc-num">'+_escV(String(num))+'</div>';
  if(d.interpretazione) h+='<div class="calc-interp">'+_escV(d.interpretazione)+'</div>';
  if(d.leva_azione) h+='<div class="calc-leva"><span class="calc-leva-lab">Cosa fare</span>'+_escV(d.leva_azione)+'</div>';
  if(d.fenomeno_id) h+='<button class="calc-fen-link" onclick="apriNodo(\''+_escV(d.fenomeno_id)+'\',\'\')">Studia il fenomeno →</button>';
  h+='</div>';
  wrap.innerHTML=h;
  flusso.appendChild(wrap);
}
// mini-scheda fenomeno compatta per la chat (riusa la logica principale)
function _costruisciMiniSchedaFenomeno(j, id){
  var div=document.createElement('div'); div.className='stream-fen';
  var e=_escV;
  var principio = (j.principi_diretti&&j.principi_diretti[0]) ? j.principi_diretti[0].nome : '';
  div.innerHTML='<div class="stream-fen-nome" onclick="apriNodo(\''+e(id)+'\',\'\')">'+e(j.titolo||'Fenomeno')+' →</div>'
    + (principio?'<div class="stream-fen-princ">'+e(principio)+'</div>':'')
    + (j.target_numero?'<div class="stream-fen-num">'+e(String(j.target_numero))+(j.unita?' '+e(j.unita):'')+'</div>':'');
  return div;
}
function _chiediNonStream(q){
  aggiungiThinking(); setBusy(true);
  // passa gli ultimi scambi per dare continuità alla conversazione
  const history=_chatHistory.slice(-_HISTORY_MAX);
  const _tok=localStorage.getItem('matter_token')||'';
  // contesto: da scheda ricetta/menu (FLUSSO 2) o da lezione
  const _ctx = _ctxChat || window._chatContesto || null;
  fetch('/chiedi',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({domanda:q, history, token:_tok, contesto:_ctx})})
    .then(r=>{
      if(r.status===402) return r.json().then(j=>{throw {trial:true,...j};});
      return r.json();
    }).then(j=>{
      _incDomande();
      if(j.risposta){
        _chatHistory.push({q, r:j.risposta.slice(0,300)});
        if(_chatHistory.length>_HISTORY_MAX*2) _chatHistory.splice(0,2);
      }
      // Gestione trial
      const tr=j.trial||{};
      if(tr.notifica){
        mostraNotificaTrial(tr.chat_rimaste);
      }
      if(tr.ultimo){
        mostraPopupPro('ultima_chat');
      }
      renderRisp(q,j);
    }).catch(e=>{
      if(e&&e.trial){
        mostraPopupPro('esaurito');
        const t=document.getElementById('thinking');if(t)t.remove();
      } else {
        renderErr();
      }
    }).finally(()=>setBusy(false));
}
function apriNodo(id,nome){
  if(busy)return;
  aggiungiThinking();setBusy(true);
  fetch('/nodo?traccia=1',{method:'POST',headers:_statoHeaders({'Content-Type':'application/json'}),body:JSON.stringify({id})})
    .then(r=>r.json()).then(j=>{
      // NUOVA SCHEDA FENOMENO: principio in cima, Mirino adattivo. Se il nodo è un fenomeno
      // (ha tipo_fenomeno + principi), uso il renderer dedicato; altrimenti la risposta chat.
      if(j && j.tipo_fenomeno && (j.principi||j.titolo)){ _renderSchedaFenomeno(j); }
      else { renderRisp(nome,j,true); }
    }).catch(()=>renderErr()).finally(()=>setBusy(false));
}
function rimuoviThinking(){ var t=document.getElementById("thinking"); if(t) t.remove(); }

// ═══ NUOVA SCHEDA FENOMENO — il principio è il protagonista, non il numero ═══
// estrae una sezione (PERCHÉ, PROBLEMA…) dalla risposta strutturata
function _estraiSezione(risposta, chiave){
  if(!risposta) return '';
  var re = new RegExp(chiave+'\\s*:([\\s\\S]*?)(?=\\n?[A-ZÀ-Ù]{4,}\\s*:|$)');
  var m = risposta.match(re);
  return m ? m[1].trim() : '';
}
// ═══ DIAGRAMMI SVG MATTER — blueprint scientifici per fenomeno (B4) ═══
var _DIAGRAMMI = ['caramello','coagulazione','denaturazione','diluizione','emulsione',
  'equilibrio-sour','espresso','forza-farina','frittura','gelatinizzazione','maillard',
  'ph-scala','temperaggio'];
function _diagrammaPer(nome, principi){
  var s = ((nome||'')+' '+(principi||'')).toLowerCase();
  // mappa per parole chiave (nome fenomeno o principio → chiave diagramma)
  var mappe = [
    [/maillard|rosolatura|searing|crosta/, 'maillard'],
    [/caramell|zucchero.*calore|imbrunimento zucchero/, 'caramello'],
    [/coagul|uova|tuorlo|albume/, 'coagulazione'],
    [/denatur|proteic|proteine/, 'denaturazione'],
    [/emulsion|maionese|tensioattiv|ganache/, 'emulsione'],
    [/diluizion|acqua.*ghiaccio|dilut/, 'diluizione'],
    [/gelatinizz|amid|addensa/, 'gelatinizzazione'],
    [/frittura|frying|olio.*temperatura/, 'frittura'],
    [/espresso|estrazione.*caff|percolazion/, 'espresso'],
    [/temperagg|cioccolato.*cristall|tempering/, 'temperaggio'],
    [/ph|acidit|acido.*base|equilibri acido/, 'ph-scala'],
    [/sour|equilibrio.*acid|bilanciamento drink/, 'equilibrio-sour'],
    [/forza.*farina|glutine|w farina|impasto.*forza/, 'forza-farina']
  ];
  for(var k=0;k<mappe.length;k++){ if(mappe[k][0].test(s)) return mappe[k][1]; }
  return null;
}
function _diagrammaHtml(nome, principi){
  var d = _diagrammaPer(nome, principi);
  if(!d) return '';
  return '<div class="fen-diagramma"><img src="/static/diagrammi/'+d+'.svg" alt="Diagramma '+_escV(nome||'')+'" loading="lazy"></div>';
}
function _renderSchedaFenomeno(j){
  rimuoviThinking();
  var e=_escV;
  var tipo = j.tipo_fenomeno || 'misurabile';
  var isMis = tipo==='misurabile';
  // paywall per-parti: usa pro_locked del backend quando c'è, altrimenti lo stato Pro locale
  var locked = (typeof j.pro_locked==='boolean') ? j.pro_locked : ((typeof _isPro==='function') && !_isPro());

  // --- HEADER: titolo (Space Grotesk) + disciplina + badge tipo ---
  var badge = isMis
    ? '<span class="fen-badge fen-badge-mis">🧪 Misurabile</span>'
    : '<span class="fen-badge fen-badge-oss">👁 Stato</span>';
  var disc = j.grandezza || j.disciplina || '';

  // --- PRINCIPIO (il cuore) — principi_diretti[0] ---
  var perche = _estraiSezione(j.risposta, 'PERCHÉ') || _estraiSezione(j.risposta, 'PERCHE');
  var principi = (j.principi_diretti && j.principi_diretti.length ? j.principi_diretti : (j.principi||[])).slice(0,2);
  var principiChip = principi.map(function(p){
    return '<span class="fen-princ-chip" onclick="apriNodo(\''+e(String(p.id))+'\',\''+e(String(p.nome)).replace(/'/g,"\\'")+'\')">'+e(p.nome)+'</span>';
  }).join('');
  var boxPrincipio =
    '<div class="fen-principio">'
    + '<div class="fen-principio-lab">Il principio</div>'
    + (principiChip?'<div class="fen-princ-chips">'+principiChip+'</div>':'')
    + (perche?'<div class="fen-principio-txt">'+e(perche)+'</div>':'')
    + '</div>';

  // --- MIRINO ADATTIVO: il NUMERO si sfoca al free (paywall per-parti), lo STATO no ---
  var mirino;
  if(isMis && j.target_numero){
    var valNum = '<div class="fen-mirino-val">'+e(String(j.target_numero))+(j.unita?'<span class="fen-mirino-u">'+e(j.unita)+'</span>':'')+'</div>';
    if(locked){
      valNum = '<div class="fen-mirino-locked" onclick="mostraPopupPro(\'numero\')">'
        + '<div class="fen-mirino-val fen-mirino-blur">'+e(String(j.target_numero))+(j.unita?'<span class="fen-mirino-u">'+e(j.unita)+'</span>':'')+'</div>'
        + '<span class="fen-mirino-lock">🔒 Sblocca con Pro</span></div>';
    }
    mirino =
      '<div class="fen-mirino fen-mirino-num">'
      + '<div class="fen-mirino-lab">finestra operativa</div>'
      + valNum
      + (j.target && j.target.length>String(j.target_numero).length+2 ? '<div class="fen-mirino-sub">'+e(j.target)+'</div>' : '')
      + '</div>';
  } else {
    var statoTxt = j.target || _estraiSezione(j.risposta,'NUMERO') || '';
    var punti = statoTxt.split(/[·;]|\bpoi\b/).map(function(x){return x.trim();}).filter(function(x){return x.length>3;});
    var checklist = punti.length>1
      ? '<div class="fen-stato-list">'+punti.map(function(x){return '<div class="fen-stato-item">'+e(x)+'</div>';}).join('')+'</div>'
      : '<div class="fen-stato-txt">'+e(statoTxt)+'</div>';
    mirino =
      '<div class="fen-mirino fen-mirino-stato">'
      + '<div class="fen-mirino-lab">lo stato da riconoscere</div>'
      + checklist
      + '</div>';
  }

  // --- TECNICHE (SPOSTATE QUI, subito sotto il Mirino — sempre visibili, la scienza è gratis) ---
  var tecniche = j.tecniche||[];
  var tecnicheHtml = '';
  if(tecniche.length){
    tecnicheHtml = '<div class="fen-sez"><div class="fen-sez-lab">Tecniche collegate</div><div class="fen-chips">'
      + tecniche.map(function(t){ return '<span class="fen-chip" onclick="apriNodo(\''+e(String(t.id))+'\',\''+e(String(t.nome)).replace(/'/g,"\\'")+'\')">'+e(t.nome)+'</span>'; }).join('')
      + '</div></div>';
  }

  // --- SPIEGAZIONE (sempre visibile) ---
  var problema = _estraiSezione(j.risposta,'PROBLEMA');
  var azione = _estraiSezione(j.risposta,'AZIONE') || _estraiSezione(j.risposta,'MISURA');
  var spiegazione = '';
  if(problema) spiegazione += '<div class="fen-sez"><div class="fen-sez-lab">Il problema</div><div class="fen-sez-txt">'+e(problema)+'</div></div>';
  if(azione) spiegazione += '<div class="fen-sez"><div class="fen-sez-lab">Cosa fare</div><div class="fen-sez-txt">'+e(azione)+'</div></div>';

  // --- ERRORI DA BANCO (box nero, barriera Pro: sfocato al free) ---
  var errori = j.errori||[];
  var erroriHtml = '';
  if(errori.length){
    if(locked){
      erroriHtml = '<div class="fen-errori-box fen-errori-locked" onclick="mostraPopupPro(\'errori\')">'
        + '<div class="fen-errori-lab">⚠ Errori da banco</div>'
        + '<div class="fen-errori-blur">'
        + errori.slice(0,2).map(function(er){ return '<div class="fen-errore-nome">'+e(er.nome||er.causa||'')+'</div>'; }).join('')
        + '</div>'
        + '<div class="fen-errori-cta">🔒 '+errori.length+' errori da banco che ti salvano il servizio — Pro</div>'
        + '</div>';
    } else {
      erroriHtml = '<div class="fen-errori-box"><div class="fen-errori-lab">⚠ Errori da banco</div>'
        + errori.map(function(er){
            return '<div class="fen-errore"><div class="fen-errore-nome">'+e(er.nome||er.causa||'')+'</div>'
              + (er.sintomo?'<div class="fen-errore-sint">'+e(er.sintomo)+'</div>':'')
              + (er.causa && er.nome?'<div class="fen-errore-causa">'+e(er.causa)+'</div>':'')+'</div>';
          }).join('')
        + '</div>';
    }
  }

  // --- DOVE SI APPLICA ---
  var connessi = j.connessi||[];
  var connessiHtml = connessi.length
    ? '<div class="fen-sez"><div class="fen-sez-lab">Dove si applica</div><div class="fen-chips">'
      + connessi.slice(0,8).map(function(c){ return '<span class="fen-chip fen-chip-app">'+e(c.nome||c)+'</span>'; }).join('')+'</div></div>'
    : '';

  // ORDINE FISSO: Fenomeno → Principio → [Diagramma] → Mirino → Tecniche → Errori(Pro) → spiegazione → dove
  var nomePrincipio = principi.length ? principi[0].nome : '';
  var diagramma = _diagrammaHtml(j.titolo, nomePrincipio);
  var html =
    '<div class="fen-scheda">'
    + '<div class="fen-header"><div class="fen-titolo">'+e(j.titolo||'Fenomeno')+'</div>'
    +   '<div class="fen-tags">'+(disc?'<span class="fen-disc">'+e(disc)+'</span>':'')+badge+'</div></div>'
    + boxPrincipio
    + diagramma
    + mirino
    + tecnicheHtml
    + erroriHtml
    + spiegazione
    + connessiHtml
    + '</div>';

  var card=document.createElement('div');card.className='scheda';card.innerHTML=html;
  document.getElementById('schede').prepend(card);
  card.scrollIntoView({behavior:'smooth',block:'start'});
}
function aggiungiThinking(){
  const d=document.createElement('div');d.className='scheda';d.id='thinking';
  d.innerHTML=`<div class="thinking"><span class="t-dots"><span class="t-dot"></span><span class="t-dot"></span><span class="t-dot"></span></span><span class="t-step" id="t-step">${_t('chat_thinking')}</span></div>`;
  document.getElementById('schede').prepend(d);
  const fasi=[_t('chat_thinking'), _lang==='it'?'raccolgo i fenomeni':'gathering phenomena', _lang==='it'?'scrivo la risposta':'writing the answer'];
  let i=0;
  const tmr=setInterval(()=>{
    i=(i+1)%fasi.length;
    const el=document.getElementById('t-step');
    if(!el){clearInterval(tmr);return;}
    el.style.opacity=0;setTimeout(()=>{if(el){el.textContent=fasi[i];el.style.opacity=1;}},250);
  },1100);
  const obs=new MutationObserver(()=>{if(!document.getElementById('thinking')){clearInterval(tmr);obs.disconnect();}});
  obs.observe(document.getElementById('schede'),{childList:true});
}
function renderRisp(domanda,j,fromNode){
  const t=document.getElementById('thinking');if(t)t.remove();
  if(!j.risposta){renderNota(domanda,j.nota,j.connessi);return;}
  // REGOLA 1 — la chat è un ponte, non il laboratorio: se il backend segnala crea_ricetta,
  // mostro la frase breve + un pulsante grande [GENERA SCHEDA RICETTA] invece di generare qui.
  if(j._azione==='crea_ricetta'){
    const rich = (j._richiesta||domanda||'').replace(/'/g,"\\'");
    const card=document.createElement('div');card.className='scheda';
    card.innerHTML=`<div class="s-q"><b>${esc(domanda)}</b></div>
      <div class="s-body" style="padding-bottom:6px">${esc(j.risposta)}</div>
      <button class="rg-btn rg-btn-salva" style="margin:4px 14px 14px;width:calc(100% - 28px)" onclick="_generaDaChat('${rich}')">Genera scheda ricetta →</button>`;
    document.getElementById('schede').prepend(card);
    card.scrollIntoView({behavior:'smooth',block:'start'});
    _chatHistory.push({q:domanda,a:j.risposta});
    return;
  }
  const fens=(j.trovato||[]).map(f=>{
    const match=(j.connessi||[]).find(c=>c.nome===f);
    const fid=match?match.id:'';
    return `<span class="fenchip" style="cursor:pointer;text-decoration:underline dotted" onclick="${fid?`apriNodo('${fid}','${f.replace(/'/g,"\'")}')`:'switchTab(\"lezione\")'}" title="Esplora fenomeno">${esc(f)}</span>`;
  }).join('');
  const conns=(j.connessi||[]).map(c=>{
    const col=DOMCOL[c.dominio]||'#5A6C70';
    const tg=c.target?`<span class="tg">${esc(c.target)}</span>`:'';
    return `<span class="conn" onclick="apriNodo('${c.id}','${(c.nome||'').replace(/'/g,"\\'")}')"><span class="dot" style="background:${col}"></span>${esc(c.nome)}${tg}</span>`;
  }).join('');
  // FL4b: chip flavor dal primo fenomeno trovato
  const trovati = j.trovato || [];
  const flavorChip = trovati.length > 0
    ? `<div class="s-conn" style="border-top:1px solid var(--border)">
        <div class="s-conn-lab" style="color:var(--flavor)">cerca abbinamenti nell'Atlante →</div>
        <div class="conns"><span class="conn" style="color:var(--flavor);border-color:var(--flavor-border)" onclick="switchTab('mappa')">
          <span class="dot" style="background:var(--flavor)"></span>Vai all'Atlante aromatico →
        </span></div>
      </div>` : '';
  // AC5: feedback
  const logId = j.log_id;
  const feedbackHtml = logId ? `<div class="s-feedback">
    <span>Risposta utile?</span>
    <button onclick="inviaFeedback(${logId},1,this)"><i class="ph ph-thumbs-up"></i></button>
    <button onclick="inviaFeedback(${logId},-1,this)"><i class="ph ph-thumbs-down"></i></button>
  </div>` : '';
  const card=document.createElement('div');card.className='scheda';
  // Estrai numero bersaglio dalla risposta se disponibile
  const numBersaglio = j.numero_bersaglio || j.target || '';
  // dati per il form di misura (dal backend /nodo)
  const fenId = j.id || '';
  const targetNum = j.target_numero || null;   // null = fenomeno "si assaggia", niente confronto
  const targetUnita = j.unita || '';
  let numBox = '';
  if(fromNode && fenId && targetNum){
    // fenomeno misurabile: bersaglio + campo "la tua misura" con confronto
    numBox = `<div class="s-num-box">
      <div class="s-num-head"><svg class="s-num-mirino" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.6" stroke="#5EA0C8" stroke-width="1.2"/><circle cx="7" cy="7" r="2" fill="#5EA0C8"/><path d="M7 0v2.2M7 11.8V14M0 7h2.2M11.8 7H14" stroke="#5EA0C8" stroke-width="1.2"/></svg><div class="s-num-label">bersaglio</div></div>
      <div class="s-num-val">${esc(targetNum)}${targetUnita?' <span class="s-num-u">'+esc(targetUnita)+'</span>':''}</div>
      <div class="s-misura" data-fen="${esc(fenId)}" data-target="${esc(targetNum)}" data-unita="${esc(targetUnita)}">
        <div class="s-misura-lab">la tua misura</div>
        <div class="s-misura-row">
          <input type="text" inputmode="decimal" class="s-misura-input" placeholder="${esc(String(targetNum).split(/[–-]/)[0])}" onkeydown="if(event.key==='Enter')fissaMisura(this)">
          ${targetUnita?'<span class="s-misura-u">'+esc(targetUnita)+'</span>':''}
          <button class="s-misura-btn" onclick="fissaMisura(this)">Fissa</button>
        </div>
        <div class="s-misura-esito"></div>
      </div>
    </div>`;
  } else if(numBersaglio){
    // Il box Mirino "bersaglio" deve contenere un NUMERO/valore corto, non una frase.
    // Se il backend manda testo descrittivo (contiene freccia, punti elenco, o è lungo),
    // NON mostro il box bersaglio: un Mirino con dentro un paragrafo è sbagliato.
    const numStr = String(numBersaglio).trim();
    const sembraFrase = numStr.length > 24 || /→|·|:|,/.test(numStr) || numStr.split(/\s+/).length > 4;
    if(!sembraFrase){
      numBox = `<div class="s-num-box">
        <div class="s-num-head"><svg class="s-num-mirino" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.6" stroke="#5EA0C8" stroke-width="1.2"/><circle cx="7" cy="7" r="2" fill="#5EA0C8"/><path d="M7 0v2.2M7 11.8V14M0 7h2.2M11.8 7H14" stroke="#5EA0C8" stroke-width="1.2"/></svg><div class="s-num-label">bersaglio</div></div>
        <div class="s-num-val">${esc(numBersaglio)}</div>
      </div>`;
    }
  }
  
  card.innerHTML=`<div class="s-q">${fromNode?'<i class=\'ph ph-caret-right\'></i> ':''}<b>${esc(domanda)}</b></div>
    <div class="fenchips">${fens}</div>
    ${numBox}
    ${(()=>{
      const r = j.risposta || '';
      // Prova a parsare risposta strutturata con label IT/EN/ES
      const labelsIT = ['PROBLEMA','PERCHÉ','NUMERO','MISURA','AZIONE'];
      const labelsEN = ['PROBLEM','WHY','NUMBER','MEASURE','ACTION'];
      const labelsES = ['PROBLEMA','POR QUÉ','NÚMERO','MIDE','ACCIÓN'];
      const allLabels = [...labelsIT, ...labelsEN, ...labelsES];
      const labelColors = {
        'PROBLEMA':'var(--ink-muted)','PROBLEM':'var(--ink-muted)','PROBLEMA':'var(--ink-muted)',
        'PERCHÉ':'var(--ink-muted)','WHY':'var(--ink-muted)','POR QUÉ':'var(--ink-muted)',
        'NUMERO':'var(--e700)','NUMBER':'var(--e700)','NÚMERO':'var(--e700)',
        'MISURA':'var(--teal)','MEASURE':'var(--teal)','MIDE':'var(--teal)',
        'AZIONE':'var(--ink)','ACTION':'var(--ink)','ACCIÓN':'var(--ink)',
      };
      // Cerca se la risposta ha la struttura con label
      const hasStructure = allLabels.some(l => r.includes(l + ':'));
      if(!hasStructure) {
        // risposta libera (non strutturata): rendo in paragrafi puliti invece
        // di un blocco unico grezzo che sembra "codice rotto"
        const paragrafi = r.split(/\n{2,}/).map(p => p.trim()).filter(p => p);
        if(paragrafi.length <= 1) return '<div class="s-body">'+esc(r)+'</div>';
        return '<div class="s-body">' + paragrafi.map(p => '<p style="margin:0 0 10px 0">'+esc(p)+'</p>').join('') + '</div>';
      }
      // Parsa i blocchi
      const lines = r.split('\n').filter(l => l.trim());
      let html = '<div class="s-blocks">';
      lines.forEach(line => {
        const match = line.match(/^([A-ZÀÁÉÍÓÚÜÑ\s]+?):\s*(.+)$/);
        if(match && allLabels.some(l => match[1].trim() === l)) {
          const label = match[1].trim();
          const val = match[2].trim();
          const col = labelColors[label] || 'var(--ink-muted)';
          const isNum = label === 'NUMERO' || label === 'NUMBER' || label === 'NÚMERO';
          const isAct = label === 'AZIONE' || label === 'ACTION' || label === 'ACCIÓN' || label === 'NUMERO' || label === 'NUMBER' || label === 'NÚMERO';
        const tagBg = isAct ? '#12545D' : '#5E9BA3';
        html += '<div class="s-block">' +
            '<div class="s-block-label" style="background:'+tagBg+'">' + esc(label) + '</div>' +
            '<div class="s-block-body"' + (isNum ? ' style="font-family:var(--mono);font-size:15px;font-weight:700;color:var(--e700)"' : '') + '>' + esc(val) + '</div>' +
            '</div>';
        } else {
          html += '<div class="s-block"><div class="s-block-body">' + esc(line) + '</div></div>';
        }
      });
      html += '</div>';
      return html;
    })()}
    <div class="s-ai-label">Risposta generata da AI · Matter usa modelli linguistici per elaborare le risposte</div>
    ${conns?`<div class="s-conn"><div class="s-conn-lab">esplora le connessioni</div><div class="conns">${conns}</div></div>`:''}
    ${flavorChip}
    ${feedbackHtml}
    <div class="s-actions">
      <button class="s-action-btn" onclick="copiaRisposta(this)" title="Copia testo"><i class="ph ph-copy"></i> Copia</button>
      <button class="s-action-btn" onclick="scaricaPDF(this)" title="Salva PDF">⬇ PDF</button>
    </div>
    `;
  document.getElementById('schede').prepend(card);
}
function renderNota(domanda,nota,connessi){
  const card=document.createElement('div');card.className='scheda';
  const conns=(connessi||[]).map(c=>{
    const col=DOMCOL[c.dominio]||'#5A6C70';
    return `<span class="conn" onclick="apriNodo('${c.id}','${(c.nome||'').replace(/'/g,"\\'")}')"><span class="dot" style="background:${col}"></span>${esc(c.nome)}</span>`;
  }).join('');
  card.innerHTML=`<div class="s-q"><b>${esc(domanda)}</b></div>
    <div class="s-body" style="color:var(--ink-muted)">${esc(nota||'Niente trovato nel grafo.')}</div>
    ${conns?`<div class="s-conn"><div class="s-conn-lab">parti da un fenomeno</div><div class="conns">${conns}</div></div>`:''}`;
  document.getElementById('schede').prepend(card);
}
function renderErr(){const t=document.getElementById('thinking');if(t)t.remove();const card=document.createElement('div');card.className='scheda';card.innerHTML=`<div class="s-body" style="color:var(--ink-muted)">${_t('auth_errore_rete')}</div>`;document.getElementById('schede').prepend(card);}
function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML;}

/* ── CORE CALCOLATORI ─────────────────────────────────── */
const Core=(()=>{
  const vt=i=>i.reduce((s,x)=>s+(+x.vol||0),0);
  const et=i=>i.reduce((s,x)=>s+(+x.vol||0)*(+x.abv||0)/100,0);
  const abv=(a,v)=>v?a/v*100:0;
  const dil=(vol,p)=>{const w=vol*p/100;return{acqua:w,vf:vol+w};};
  const conc=(g,v)=>v?g/v*100:0;
  const par=(v,a,t)=>Math.max(0,(t-a)/100*v);
  const zuc=(v,b,d)=>v*d*b/100;
  const afus=(m)=>m*3.9*20/334;
  return{vt,et,abv,dil,conc,par,zuc,afus};
})();

/* ── APP CALCOLATORI ──────────────────────────────────── */
const App=(()=>{
  let ing=[{n:'Gin',vol:30,abv:40},{n:'Campari',vol:30,abv:25},{n:'Vermouth',vol:30,abv:16}];
  let dil=22,bm='serv',srv='ice';
  const $=id=>document.getElementById(id);
  const fmt=(n,d=1)=>isNaN(n)?'—':n.toFixed(d);

  function renderIng(){
    const c=$('ing-list');c.innerHTML='';
    ing.forEach((it,i)=>{
      const r=document.createElement('div');r.className='row';
      r.innerHTML=`<input class="c-input c-input-name" value="${esc(it.n)}" oninput="App.upd(${i},'n',this.value)">
        <input class="c-input" type="number" inputmode="decimal" value="${it.vol}" oninput="App.upd(${i},'vol',+this.value||0)">
        <input class="c-input" type="number" inputmode="decimal" value="${it.abv}" oninput="App.upd(${i},'abv',+this.value||0)">
        <button class="del-btn" onclick="App.delIng(${i})">×</button>`;
      c.appendChild(r);
    });
    calcDil();
  }
  function upd(i,k,v){ing[i][k]=k==='n'?v:Math.max(0,+v||0);if(k!=='n')calcDil();}
  function addIng(){ing.push({n:'',vol:30,abv:0});renderIng();}
  function delIng(i){ing.splice(i,1);renderIng();}

  function setTech(el,d){
    document.querySelectorAll('.chip[data-dil]').forEach(c=>c.setAttribute('aria-pressed','false'));
    el.setAttribute('aria-pressed','true');dil=d;$('dil-range').value=d;$('dil-v').textContent=d+'%';calcDil();
  }
  function setRange(v){
    dil=+v;$('dil-v').textContent=v+'%';
    document.querySelectorAll('.chip[data-dil]').forEach(c=>c.setAttribute('aria-pressed',(+c.dataset.dil===+v)+''));
    calcDil();
  }

  function calcDil(){
    if(!ing.length){$('dil-out').innerHTML=`<p class="hint" style="padding:16px">${_t('aggiungi_ing')}</p>`;calcBatch();return;}
    const V0=Core.vt(ing),al=Core.et(ing);
    const{acqua,vf}=Core.dil(V0,dil);
    const abv0=Core.abv(al,V0),abvF=Core.abv(al,vf),tg=Core.afus(V0);
    $('dil-out').innerHTML=`<div class="readout-big"><div class="readout-num">${fmt(abvF)}<span class="readout-unit">%</span></div><div class="readout-lab">${_t('chat_grado')}${fmt(abv0)}%)</div></div>
      <div class="grid2"><div class="stat"><div class="s-n">${fmt(vf,0)} ml</div><div class="s-l">volume nel bicchiere</div></div><div class="stat"><div class="s-n">${fmt(acqua,0)} ml</div><div class="s-l">acqua di fusione</div></div></div>`;
    calcBatch();
    // aggiorna drink cost in background (non blocca l'UI)
    aggiornDrinkCost(ing);
  }

  function setBM(m){bm=m;$('bm-serv').setAttribute('aria-pressed',m==='serv');$('bm-vol').setAttribute('aria-pressed',m==='vol');$('bq-lab').textContent=m==='serv'?_t('ct_bq_serv'):_t('ct_bq_vol');calcBatch();}
  function setServe(s){srv=s;$('ps-ice').setAttribute('aria-pressed',s==='ice');$('ps-bot').setAttribute('aria-pressed',s==='bot');calcBatch();}

  function calcBatch(){
    const qty=+$('b-qty').value||0,over=+$('b-over').value||0,bot=+$('b-bot').value||0;
    const V0=Core.vt(ing);if(qty<=0||V0<=0){$('batch-out').innerHTML='';return;}
    const wPer=srv==='bot'?Core.dil(V0,dil).acqua:0;
    const sv=V0+wPer,o=1+over/100;
    const Neff=bm==='serv'?qty*o:(sv?qty/sv*o:0);
    const rows=ing.map(x=>`<div class="b-row"><span>${esc(x.n||'—')}</span><b>${fmt(x.vol*Neff,0)} ml</b></div>`).join('');
    const wTotal=wPer*Neff,volTot=sv*Neff;
    $('batch-out').innerHTML=rows+(wPer>0?`<div class="b-row"><span>${_t('ct_acqua_pre')}</span><b>${fmt(wTotal,0)} ml</b></div>`:'')+
      `<div class="b-sum">${_t('ct_totale')} <b>${fmt(volTot/1000,2)} L</b> · ${_t('ct_include')} ${over}% ${_t('ct_extra_lbl')}</div>`;
  }

  function gauge(name,val,z){
    const pos=Math.min(100,Math.max(0,val/z.sc*100));
    const zl=z.min/z.sc*100,zw=(z.max-z.min)/z.sc*100;
    const ok=val>=z.min&&val<=z.max;
    return{html:`<div class="gauge"><div class="g-top"><span class="g-name">${name}</span><span class="g-val" style="color:${ok?'var(--s500)':'var(--e700)'}">${fmt(val,z.dec||1)}${z.u}</span></div><div class="track"><div class="zone" style="left:${zl}%;width:${zw}%"></div><div class="needle" style="left:${pos}%"></div></div></div>`,ok};
  }

  function calcBil(){
    const rd=id=>Math.max(0,+$(id).value||0);
    const[brix,dens]=$('b-y-type').value.split('|').map(Number);
    const sv=rd('b-s-vol'),sa=Math.min(100,rd('b-s-abv'));
    const av=rd('b-a-vol'),aa=rd('b-a-acid');
    const yv=rd('b-y-vol'),bd=rd('b-dil');
    const sub=sv+av+yv,{vf}=Core.dil(sub,bd);
    const abvF=Core.abv(sv*sa/100,vf);
    const z=Core.zuc(yv,brix,dens),brixF=Core.conc(z,vf);
    const acidF=Core.conc(av*aa/100,vf);
    const gF=gauge('Forza · alcol',abvF,{min:14,max:19,sc:30,u:'%',dec:1});
    const gD=gauge('Dolce · Brix',brixF,{min:9,max:14,sc:25,u:' g/100ml',dec:1});
    const gA=gauge('Acido',acidF,{min:0.9,max:1.4,sc:2.5,u:'%',dec:2});
    const off=[gF,gD,gA].filter(g=>!g.ok);
    const v=off.length===0?'In equilibrio — i tre assi cadono nella zona classica del sour.':'Fuori equilibrio: '+[gF.ok?'':'forza',gD.ok?'':'dolce',gA.ok?'':'acido'].filter(Boolean).join(', ')+' da correggere.';
    $('bil-out').innerHTML=gF.html+gD.html+gA.html+`<div class="verdict ${off.length?'off':'ok'}">${v}</div>`;
  }

  function calcAA(){
    const g=Core.par(+$('aa-vol').value||0,+$('aa-cur').value||0,+$('aa-tgt').value||0);
    $('aa-out').innerHTML=`${_t('aggiungi_acido')} <b style="color:var(--e700)">${fmt(g,1)} g</b> ${_t('acido_citrico')}`;
  }

  function setTool(t){
    ['dil','bil','bak','caf','sic'].forEach(p=>{
      const el=document.getElementById('cpanel-'+p);
      if(el) el.style.display=p===t?'block':'none';
      const btn=document.getElementById('ctab-'+p);
      if(btn) btn.classList.toggle('active',p===t);
    });
    // SEC13 — gate Pro-only per sicurezza
    if(t==='sic') _aggiornaSicGate();
  }

  function _aggiornaSicGate(){
    const gate = document.getElementById('sic-gate');
    const content = document.getElementById('sic-content');
    if(!gate || !content) return;
    const isPro = _isPro();
    gate.style.display = isPro ? 'none' : 'block';
    content.style.display = isPro ? 'block' : 'none';
    if(isPro){
      calcShelfLife();
      calcPastorizzazione();
      calcCatenaFreddo();
    }
  }

  // ── BAKERY ──────────────────────────────────────────────
  function calcBak(){
    const flour=+$('bk-flour').value||0, water=+$('bk-water').value||0;
    if(!flour){$('bk-idr-out').innerHTML='';return;}
    const idr=(water/flour*100).toFixed(1);
    let zona='—';
    const n=+idr;
    if(n<65) zona='bassa — pane compatto, crosta dura';
    else if(n<=72) zona='pane comune';
    else if(n<=75) zona='zona di transizione';
    else if(n<=85) zona='alta — ciabatta, focaccia, pizza teglia';
    else zona='molto alta — impasto-pastella';
    $('bk-idr-out').innerHTML=`${_t('ct_idr_out')} <b style="color:var(--e700)">${idr}%</b> · ${zona}`;
    // aggiorna food cost bakery in background
    aggiornFoodCostBak([{n:'farina',vol:flour},{n:'acqua',vol:water}]);
  }
  function calcQ10(){
    const tBase=+$('bk-t-base').value||0;
    const tRef=+$('bk-t-ref').value||24;
    const tReal=+$('bk-t-real').value||18;
    if(!tBase){$('bk-q10-out').innerHTML='';return;}
    const tNew=tBase*Math.pow(2,(tRef-tReal)/8);
    const dir=tReal<tRef?_t('ct_q10_freddo'):_t('ct_q10_caldo');
    $('bk-q10-out').innerHTML=`${_t('ct_q10_out')} <b style="color:var(--e700)">${tNew.toFixed(1)} h</b> · ${dir}`;
  }
  function calcPH(){
    const ph=+$('bk-ph').value||0;
    if(!ph){$('bk-ph-out').innerHTML='';return;}
    let stato='',col='var(--ink-muted)';
    if(ph>5.2){stato='appena rinfrescata — aspetta';col='var(--ink-muted)';}
    else if(ph>4.2){stato='giovane — non ancora pronta';col='var(--e300)';}
    else if(ph>=3.7){stato='matura — usala adesso';col='var(--s500)';}
    else{stato='sovramatura — troppo acida, rinfresca';col='var(--e700)';}
    $('bk-ph-out').innerHTML=`<span style="color:${col};font-weight:600">${stato}</span>`;
  }

  // ── CAFFETTERIA ──────────────────────────────────────────
  function calcEY(){
    const dose=+$('cf-dose').value||0;
    const bev=+$('cf-bev').value||0;
    const tds=+$('cf-tds').value||0;
    if(!dose||!bev||!tds){$('cf-ey-out').innerHTML='';$('cf-diag').innerHTML='—';return;}
    const ey=bev*tds/dose;
    $('cf-ey-out').innerHTML=`EY <b style="color:var(--e700)">${ey.toFixed(1)}%</b>`;
    // diagnostica a 4 quadranti
    let diag='';
    if(ey<18 && tds<7) diag='<b>Sottoestratto e debole</b> — macinatura più fine o più dose.';
    else if(ey<18 && tds>=7) diag='<b>Sottoestratto ma concentrato</b> — macinatura più fine, meno dose.';
    else if(ey>22 && tds<7) diag='<b>Sovrestratto e debole</b> — macinatura più grossa, più dose.';
    else if(ey>22 && tds>=7) diag='<b>Sovrestratto e concentrato</b> — macinatura più grossa o meno tempo.';
    else diag=`<b style="color:var(--s500)">Nella zona di equilibrio</b> — EY ${ey.toFixed(1)}%, TDS ${tds}%.`;
    $('cf-diag').innerHTML=diag;
  }
  function calcRatio(){
    const dose=+$('cf-r-dose').value||0;
    const ratio=+$('cf-r-ratio').value||0;
    if(!dose||!ratio){$('cf-ratio-out').innerHTML='';return;}
    const vol=dose*ratio;
    $('cf-ratio-out').innerHTML=`<b style="color:var(--e700)">${vol.toFixed(0)} g</b> di acqua (o bevanda finale)`;
  }

  document.addEventListener('DOMContentLoaded',()=>{
    renderIng();setServe('ice');calcBil();calcAA();
    calcBak();calcQ10();calcPH();calcEY();calcRatio();
    // bottone torna-su: appare dopo 400px di scroll
    var _ts=document.getElementById('torna-su');
    if(_ts){ window.addEventListener('scroll',function(){ _ts.classList.toggle('visibile', window.scrollY>400); }, {passive:true}); }
    // schermata iniziale = Scopri. La Lezione si carica pigra quando apri la tab.
    switchTab('scopri');
    caricaHome();
    aggiornaTopbarLogin();
    mostraOnbOverlay();
    aggiornaPills();
    applicaStringheUI();
    playIntroScopri();
    // IN3 — keep-alive: ping ogni 4 minuti per evitare il cold start di Railway
    setInterval(()=>fetch('/health').catch(()=>{}), 4*60*1000);
  });
  return{upd,addIng,delIng,setTech,setRange,calcDil,setBM,setServe,calcBatch,calcBil,calcAA,setTool,calcBak,calcQ10,calcPH,calcEY,calcRatio,getIng:()=>ing};
})();

/* ── PAYWALL — 5 domande/giorno (D1) ─────────────────── */
function _oggiKey(){ return 'mq_'+new Date().toISOString().slice(0,10); }
function _getDomande(){ return parseInt(localStorage.getItem(_oggiKey())||'0',10); }
function _incDomande(){ localStorage.setItem(_oggiKey(), _getDomande()+1); }
const FREE_LIMIT = 5;

function _isPro(){
  // legge piano utente da localStorage (impostato al login/webhook Stripe)
  return localStorage.getItem('matter_piano')==='pro';
}

function apriPaywall(){
  document.getElementById('paywall-overlay').classList.remove('hidden');
}
function chiudiPaywall(){
  document.getElementById('paywall-overlay').classList.add('hidden');
}
function vaiAPro(){
  chiudiPaywall();
  if(typeof apriPrezzi==='function'){ apriPrezzi(); return; }
  // se non loggato, prima registrazione
  if(!localStorage.getItem('matter_token')){
    switchTab('auth');
    switchAuthTab('reg');
  } else {
    // utente già loggato → vai a Stripe
    const _tk = localStorage.getItem('matter_token')||'';
    fetch('/v1/stripe/checkout',{method:'POST',
      headers:{'Content-Type':'application/json','X-Token':_tk,'Authorization':'Bearer '+_tk},
      body:JSON.stringify({token:_tk})})
      .then(r=>r.json()).then(j=>{ if(j.url) window.location.href=j.url; else if(j.checkout_url) window.location.href=j.checkout_url; })
      .catch(()=>{});
  }
}

/* ── AUTH — LOGIN / REGISTRAZIONE (AC2) ──────────────── */
function switchAuthTab(t){
  ['login','reg'].forEach(s=>{
    document.getElementById('auth-panel-'+s).style.display = s===t?'block':'none';
    document.getElementById('auth-tab-'+s).classList.toggle('active',s===t);
  });
}

async function doLogin(){
  const email=document.getElementById('login-email').value.trim();
  const pwd=document.getElementById('login-pwd').value;
  const msg=document.getElementById('login-msg');
  msg.className='auth-msg'; msg.textContent='';
  if(!email||!pwd){msg.className='auth-msg err';msg.textContent=_t('auth_inserisci');return;}
  try {
    const r=await fetch('/v1/auth/login',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({email,password:pwd})});
    const j=await r.json();
    if(j.token){
      localStorage.setItem('matter_token',j.token);
      localStorage.setItem('matter_email',email);
      if(j.piano) localStorage.setItem('matter_piano',j.piano);
      aggiornaTopbarLogin();
      msg.className='auth-msg ok';msg.textContent=_t('auth_ok');
      setTimeout(()=>switchTab('scopri'),800);
    } else {
      msg.className='auth-msg err';msg.textContent=j.errore||_t('auth_inserisci');
    }
  } catch(e){
    msg.className='auth-msg err';msg.textContent=_t('auth_errore_rete');
  }
}

async function doRegistra(){
  const email=document.getElementById('reg-email').value.trim();
  const pwd=document.getElementById('reg-pwd').value;
  const msg=document.getElementById('reg-msg');
  msg.className='auth-msg'; msg.textContent='';
  if(!email||!pwd){msg.className='auth-msg err';msg.textContent=_t('auth_inserisci');return;}
  if(pwd.length<8){msg.className='auth-msg err';msg.textContent=_t('auth_pwd_corta');return;}
  try {
    const r=await fetch('/v1/auth/registra',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({email,password:pwd})});
    const j=await r.json();
    if(j.ok||j.token){
      if(j.verifica_richiesta){
        msg.className='auth-msg ok';msg.textContent='Account creato! Controlla la tua email per attivarlo.';
      } else if(j.token){localStorage.setItem('matter_token',j.token);localStorage.setItem('matter_email',email);_trackFunnel('signup');aggiornaTopbarLogin();msg.className='auth-msg ok';msg.textContent=_t('auth_reg_ok');setTimeout(()=>switchTab('scopri'),900);}
    } else {
      msg.className='auth-msg err';msg.textContent=j.errore||'Registrazione non riuscita.';
    }
  } catch(e){
    msg.className='auth-msg err';msg.textContent=_t('auth_errore_rete');
  }
}

/* ── STRINGHE EN INTERFACCIA (GT5b) ──────────────────── */
const _strings = {
  it:{
    payoff:'Science &amp; Craft',
    scopri:'Banco', lezione:'Lezione', mappa:'Mappa', db_fenomeni:'Fenomeni',
    tab_atlante:'Atlante', tab_chiedi:'Assistente', tab_quaderno:'Quaderno',
    db_ingredienti:'Ingredienti',
    db_connessioni:'Connessioni aromatiche',
    db_calcolatori:'Calcolatori',
    chiedi:'Chiedi',
    studia:'Studia il fenomeno →', nologin:'',
    disc_kw_bar:'Acidità · Diluizione · Carbonatazione · Emulsione',
    disc_kw_bakery:'Struttura · Fermentazione · Osmosi · Retrogradazione',
    disc_kw_cucina:'Maillard · Denaturazione · Calore · Emulsione',
    disc_kw_caffe:'Estrazione · Tostatura · Pressione · Solubilità',
    disc_kw_pasticceria:'Cristallizzazione · Struttura · Caramellizzazione · Montaggio',
    disc_kw_gelateria:'Crioscopia · Overrun · Cristalli · PAC',
    disc_kw_vino:'Fermentazione · Malolattica · Acidità · Chiarificazione',
    disc_kw_birra:'Mash · Luppolo · Fermentazione · Carbonatazione',
    db_numbers:'52 fenomeni · 1.530 ingredienti · 33.696 connessioni · 6 calcolatori',
    scegli:'Scegli la tua disciplina', caricamento:'caricamento…',
    fenomeno_giorno:'fenomeno del giorno',
    num_bersaglio:'bersaglio',
    indietro:'← Indietro', avanti:'Avanti →', vai_mappa:'Vai all\'Atlante →',
    principio_del_giorno:'Principio del giorno',
    vedi_mappa:'Vedi il principio nell\'Atlante →',
    chiedi_placeholder:'Scrivi un problema al banco (es. ganache separata)…',
    chiedi_btn:'Chiedi',
    onb_nudge_title:'Postazione Attiva',
    ai_disclosure:'Risposte generate da un assistente AI.',
    foto_analisi_titolo:'Analisi foto',
    foto_analisi_loading:'Riconosco ingredienti e bottiglie…',
    chiedi_title:'Chiedi a Matter Bench',
    chiedi_sub:'Un problema reale del tuo lavoro — rispondo con i numeri, non con le opinioni.',
    sup_titolo:'Hai bisogno di aiuto?',
    sup_sub:'Descrivi il problema. Ti risponderemo entro 24 ore via email.',
    sup_placeholder:'Es. Non riesco ad aprire la lezione…',
    sup_invia:'Invia richiesta',
    disc_bar:'Bar', disc_bakery:'Panificazione', disc_cucina:'Cucina',
    disc_caffetteria:'Caffè', disc_pasticceria:'Pasticceria',
    disc_gelateria:'Gelateria', disc_vino:'Vino', disc_birra:'Birra',
    chiedi_al_grafo:'Chiedi a Matter Bench',
    calcola:'Calcola',
    prova:'Prova:',
    il_percorso:'Il tuo percorso',
    scegli_disc_mappa:'Scegli una disciplina in Scopri per vedere il percorso',
    principi_trasv:'Principi trasversali',
    perche_insieme:'Perché funzionano insieme',
    ponte_cifra:'Il ponte verso Cifra',
    accedi:'Accedi', registrati:'Registrati',
    continua_senza:'← Continua senza registrarti',
    domande_esaurite:'Hai usato le chat gratuite del tuo trial.',
    pro_desc:'Con Matter Pro: chat illimitata · 91 fenomeni completi · Flavor Network · Ricette scientifiche.',
    passa_pro:'Passa a Pro',
    continua_free:'Continua con il piano gratuito',
    // calcolatori
    ct_drink:'Il drink', ct_ing:'ingrediente', ct_add:'+ aggiungi ingrediente',
    ct_tecnica:'Tecnica', ct_mesc:'Mescolato', ct_shak:'Shakerato',
    ct_hint_dil:'Zona di partenza. Per tararla: pesa lo shaker prima e dopo.',
    ct_batch:'Batch', ct_perporz:'Per porzioni', ct_pervol:'Per volume',
    ct_extra:'extra %', ct_bot:'bot. ml', ct_bq_serv:'porzioni', ct_bq_vol:'volume ml',
    ct_ice:'Col ghiaccio', ct_ice_s:'acqua dopo',
    ct_botg:'Imbottigliato', ct_botg_s:'acqua ora',
    ct_sour:'Sour', ct_syr1:'Sciroppo 1:1 (50 Brix)', ct_syr2:'Sciroppo 2:1 (65 Brix)',
    ct_par:'Pareggiatore acidità',
    ct_par_hint:'Porta qualsiasi succo al 6% del lime.',
    ct_succo:'succo ml', ct_acido:'acido %', ct_target:'target %',
    ct_idr:"Idratazione (baker's %)",
    ct_q10:'Q10 — tempo di fermentazione',
    ct_ph:'pH madre',
    ct_farina:'farina g', ct_acqua_g:'acqua g',
    ct_dose_ey:'dose g', ct_bevanda_g:'bevanda g', ct_tds:'TDS %',
    ct_dose_ratio:'dose g', ct_ratio:'ratio 1:',
    // output calcolatori
    ct_idr_out:'Idratazione',
    ct_q10_freddo:'più freddo — fermentazione più lenta',
    ct_q10_caldo:'più caldo — fermentazione più veloce',
    ct_q10_out:'Tempo previsto',
    // cookie
    ct_cookie_ok:'Accetto', ct_cookie_no:'Solo essenziali',
    ct_cookie_txt:'Matter Bench usa cookie tecnici per funzionare e registra le domande per migliorare il servizio. Nessun cookie di profilazione. Le risposte sono generate da AI (Anthropic/Mistral).',
    // batch output
    ct_acqua_pre:'Acqua pre-diluizione',
    ct_totale:'Totale',
    ct_include:'include',
    ct_extra_lbl:'extra',
    // onboarding
    onb_ovl_title:'Come funziona Matter Bench',
    onb_s1_title:'Scegli la tua disciplina',
    onb_s1_sub:'Bar, Panificazione, Cucina, Caffetteria e altro — ogni disciplina ha le sue leggi fisiche.',
    onb_s2_title:'Studia il fenomeno',
    onb_s2_sub:'Ogni fenomeno ha un bersaglio: a volte un numero da misurare, a volte uno stato da riconoscere. Quello che devi sapere quando qualcosa non torna.',
    onb_s3_title:'Chiedi a Matter Bench',
    onb_s3_sub:'Descrivi un problema del tuo lavoro. Ricevi cosa misurare o riconoscere e azioni concrete — non consigli generici.',
    onb_ovl_cta:'Inizia',
    onb_nudge_sub:'Seleziona la tua disciplina qui sotto per la prima lezione',
    onb_complete_title:'Percorso completato.',
    onb_complete_sub:'Hai completato la lezione. Vai all\'Atlante per vedere il tuo percorso.',
    onb_complete_btn:'Vai all\'Atlante',
    // quaderno
    ct_quad_title:'Quaderno',
    ct_quad_empty_title:'Nessun esperimento salvato',
    ct_quad_empty_sub:'Usa i calcolatori e salva le tue misure fisiche qui.',
    ct_salva_btn:'+ Salva nel quaderno',
    ct_salva_nome:'Nome esperimento',
    ct_salva_note:'Note (opzionale)',
    ct_salva_confirm:'Salva',
    // drink cost (bar)
    ct_drinkcost_title:'Drink cost orientativo',
    ct_drinkcost_label:'costo totale orientativo · fonte ISMEA',
    ct_drinkcost_note:'Prezzi medi di mercato orientativi. Per il drink cost reale usa i prezzi del tuo fornitore in Cifra.',
    // food cost (bakery)
    ct_foodcost_title:'Food cost orientativo',
    ct_foodcost_label:'costo totale orientativo · fonte ISMEA',
    ct_foodcost_note:'Prezzi medi di mercato orientativi. Per il food cost reale usa i prezzi del tuo fornitore in Cifra.',
    // flavor mappa
    ct_flavor_btn:'Cerca',
    ct_flavor_placeholder:'es. limone, caffè, burro…',
    ct_disc_sicurezza:'Sicurezza alimentare',
    ct_disc_sicurezza_sub:'prossimamente',
    // stringhe dinamiche JS
    mappa_scegli:'Scegli una disciplina in Scopri per vedere il percorso',
    mappa_percorso:'Il tuo percorso — ',
    mappa_nessun_fen:'Nessun fenomeno trovato per questa disciplina.',
    mappa_caricamento:'Caricamento…',
    mappa_errore:'Errore caricamento mappa. Riprova.',
    les_caricamento:'caricamento…',
    les_errore:'Errore caricamento — riprova.',
    les_fenomeno:'Fenomeno',
    les_di:'di',
    scopri_errore_titolo:'Riprova tra poco.',
    scopri_errore_eyebrow:'errore caricamento',
    chat_thinking:'consulto Matter Bench',
    chat_grado:'grado finale (era ',
    aggiungi_ing:'Aggiungi un ingrediente.',
    aggiungi_acido:'Aggiungi',
    acido_citrico:'g di acido citrico.',
    auth_inserisci:'Inserisci email e password.',
    auth_pwd_corta:'Password minimo 8 caratteri.',
    auth_ok:'Accesso effettuato.',
    auth_reg_ok:'Account creato. Benvenuto in Matter.',
    auth_errore_rete:'Il grafo non risponde. Riprova tra un momento.',
    salvato:'✓ Salvato',
    // disclaimer sicurezza EN con adattamento UK/US
    ct_sic_disc_uk:'This tool provides indicative estimates based on scientific models. It does not replace official food safety management procedures, HACCP plans, or the advice of a qualified food safety professional.',
    // sicurezza calcolatori
    ct_tab_sic:'Sicurezza',
    ct_sic_shelf:'Shelf life orientativa',
    ct_sic_shelf_hint:'Stima basata su Aw, pH e temperatura di conservazione.',
    ct_sic_aw:'Aw',
    ct_sic_ph:'pH',
    ct_sic_temp:'T conserv. °C',
    ct_sic_shelf_disc:'Stima orientativa — non sostituisce test microbiologici né certificazioni.',
    ct_sic_past:'Pastorizzazione — riduzione logaritmica',
    ct_sic_past_hint:'Tempo necessario per ridurre la carica batterica a una data temperatura.',
    ct_sic_past_t:'Temperatura °C',
    ct_sic_past_time:'Tempo (min)',
    ct_sic_cold:'Catena del freddo — rischio zona pericolo',
    ct_sic_cold_hint:'Tempo cumulativo in zona di pericolo (4°C–60°C).',
    ct_sic_cold_t:'Temperatura °C',
    ct_sic_cold_time:'Tempo (min)',
    ct_sic_cold_disc:'Limite sicurezza: max 2 ore cumulative in zona pericolo.',
    ct_sic_gate_title:'Modulo sicurezza alimentare',
    ct_sic_gate_desc:'Shelf life orientativa, pastorizzazione e catena del freddo. Disponibile con Matter Bench Pro.',
    ct_sic_gate_btn:'Passa a Pro — €19,99/mese',
  },
  en:{
    payoff:'The science behind the craft',
    scopri:'Bench', lezione:'Lesson', mappa:'Map', db_fenomeni:'Phenomena',
    tab_atlante:'Atlas', tab_chiedi:'Assistant', tab_quaderno:'Notebook',
    db_ingredienti:'Ingredients',
    db_connessioni:'Aromatic connections',
    db_calcolatori:'Calculators',
    chiedi:'Ask',
    studia:'Explore the phenomenon', nologin:'No registration required.',
    disc_kw_bar:'Acidity · Dilution · Carbonation · Emulsion',
    disc_kw_bakery:'Structure · Fermentation · Osmosis · Retrogradation',
    disc_kw_cucina:'Maillard · Denaturation · Heat · Emulsion',
    disc_kw_caffe:'Extraction · Roasting · Pressure · Solubility',
    disc_kw_pasticceria:'Crystallization · Structure · Caramelization · Mounting',
    disc_kw_gelateria:'Cryoscopy · Overrun · Crystals · PAC',
    disc_kw_vino:'Fermentation · Malolactic · Acidity · Clarification',
    disc_kw_birra:'Mash · Hops · Fermentation · Carbonation',
    db_numbers:'52 phenomena · 1,530 ingredients · 33,696 connections · 6 calculators',
    scegli:'Choose your discipline', caricamento:'loading…',
    fenomeno_giorno:'phenomenon of the day',
    num_bersaglio:'target number',
    indietro:'← Back', avanti:'Next →', vai_mappa:'Go to Atlas →',
    principio_del_giorno:'Principle of the day',
    vedi_mappa:'See the principle in the Map →',
    chiedi_placeholder:'ask Matter Bench…',
    chiedi_btn:'Ask',
    onb_nudge_title:'Ready at the bench?',
    ai_disclosure:'Responses generated by an AI assistant.',
    foto_analisi_titolo:'Photo analysis',
    foto_analisi_loading:'Identifying ingredients and bottles…',
    chiedi_title:'Ask Matter Bench',
    disc_bar:'Bar', disc_cucina:'Kitchen', disc_panificazione:'Baking',
    disc_pasticceria:'Pastry', disc_gelateria:'Gelato', disc_caffe:'Coffee',
    disc_vino:'Wine', disc_birra:'Beer', disc_sicurezza:'Food safety',
    chiedi_sub:'A real question from your work — I answer with numbers, not opinions.',
    sup_titolo:'Need help?',
    sup_sub:'Describe the problem. We\'ll reply within 24 hours by email.',
    sup_placeholder:'E.g. I can\'t open the lesson…',
    sup_invia:'Send request',
    disc_bar:'Bar', disc_bakery:'Baking', disc_cucina:'Cooking',
    disc_caffetteria:'Coffee', disc_pasticceria:'Pastry',
    disc_gelateria:'Gelato', disc_vino:'Wine', disc_birra:'Beer',
    chiedi_al_grafo:'Ask Matter Bench',
    calcola:'Calculate',
    prova:'Try:',
    il_percorso:'Your path',
    scegli_disc_mappa:'Choose a discipline in Discover to see your path',
    principi_trasv:'Cross-domain principles',
    perche_insieme:'Why they work together',
    ponte_cifra:'The bridge to Cifra',
    accedi:'Sign in', registrati:'Sign up',
    continua_senza:'← Continue without signing in',
    domande_esaurite:"You've used your 5 free questions today.",
    pro_desc:'With Matter Pro, continue without limits — unlimited chat, Flavor Network, measurements notebook.',
    passa_pro:'Upgrade to Pro',
    continua_free:'Continue with free plan',
    // calculators
    ct_drink:'The drink', ct_ing:'ingredient', ct_add:'+ add ingredient',
    ct_tecnica:'Technique', ct_mesc:'Stirred', ct_shak:'Shaken',
    ct_hint_dil:'Starting point. To calibrate: weigh the shaker before and after.',
    ct_batch:'Batch', ct_perporz:'By servings', ct_pervol:'By volume',
    ct_extra:'extra %', ct_bot:'bot. ml', ct_bq_serv:'servings', ct_bq_vol:'volume ml',
    ct_ice:'With ice', ct_ice_s:'water added later',
    ct_botg:'Bottled', ct_botg_s:'water added now',
    ct_sour:'Sour', ct_syr1:'Syrup 1:1 (50 Brix)', ct_syr2:'Syrup 2:1 (65 Brix)',
    ct_par:'Acidity equaliser',
    ct_par_hint:'Bring any juice to 6% like lime.',
    ct_succo:'juice ml', ct_acido:'acid %', ct_target:'target %',
    ct_idr:"Hydration (baker's %)",
    ct_q10:'Q10 — fermentation time',
    ct_ph:'Starter pH',
    ct_farina:'flour g', ct_acqua_g:'water g',
    ct_dose_ey:'dose g', ct_bevanda_g:'beverage g', ct_tds:'TDS %',
    ct_dose_ratio:'dose g', ct_ratio:'ratio 1:',
    // calc outputs
    ct_idr_out:'Hydration',
    ct_q10_freddo:'cooler — slower fermentation',
    ct_q10_caldo:'warmer — faster fermentation',
    ct_q10_out:'Estimated time',
    // cookie
    ct_cookie_ok:'Accept', ct_cookie_no:'Essential only',
    ct_cookie_txt:'Matter Bench uses technical cookies and logs questions to improve the service. No profiling cookies. Responses are AI-generated (Anthropic/Mistral).',
    // batch output
    ct_acqua_pre:'Pre-dilution water',
    ct_totale:'Total',
    ct_include:'includes',
    ct_extra_lbl:'extra',
    // onboarding
    onb_ovl_title:'How Matter Bench works',
    onb_s1_title:'Choose your discipline',
    onb_s1_sub:'Bar, Bakery, Kitchen, Coffee — each discipline has its own path through physical phenomena.',
    onb_s2_title:'Study the phenomenon',
    onb_s2_sub:'Each lesson has a target number — the physical parameter that governs that gesture at the bench.',
    onb_s3_title:'Ask Matter Bench',
    onb_s3_sub:'Ask a real question — a problem from your work. Matter answers with numbers, not opinions.',
    onb_ovl_cta:'Start',
    onb_nudge_sub:'Select your discipline below to begin your first lesson',
    onb_complete_title:'Great work.',
    onb_complete_sub:'You completed the lesson. Go to the Map to see your path.',
    onb_complete_btn:'Go to Map',
    // quaderno
    ct_quad_title:'Notebook',
    ct_quad_empty_title:'No saved experiments',
    ct_quad_empty_sub:'Use the calculators and save your physical measurements here.',
    ct_salva_btn:'+ Save to notebook',
    ct_salva_nome:'Experiment name',
    ct_salva_note:'Notes (optional)',
    ct_salva_confirm:'Save',
    // drink cost (bar)
    ct_drinkcost_title:'Drink cost (indicative)',
    ct_drinkcost_label:'estimated total · ISMEA source',
    ct_drinkcost_note:'Indicative market prices. For real drink cost use your supplier prices in Cifra.',
    // food cost (bakery)
    ct_foodcost_title:'Food cost (indicative)',
    ct_foodcost_label:'estimated total · ISMEA source',
    ct_foodcost_note:'Indicative market prices. For real food cost use your supplier prices in Cifra.',
    // flavor mappa
    ct_flavor_btn:'Search',
    ct_flavor_placeholder:'e.g. lemon, coffee, butter…',
    ct_disc_sicurezza:'Food safety',
    ct_disc_sicurezza_sub:'coming soon',
    // dynamic JS strings
    mappa_scegli:'Choose a discipline in Discover to see your path',
    mappa_percorso:'Your path — ',
    mappa_nessun_fen:'No phenomena found for this discipline.',
    mappa_caricamento:'Loading…',
    mappa_errore:'Error loading map. Try again.',
    les_caricamento:'loading…',
    les_errore:'Loading error — try again.',
    les_fenomeno:'Phenomenon',
    les_di:'of',
    scopri_errore_titolo:'Try again in a moment.',
    scopri_errore_eyebrow:'loading error',
    chat_thinking:'asking Matter Bench',
    chat_grado:'final degree (was ',
    aggiungi_ing:'Add an ingredient.',
    aggiungi_acido:'Add',
    acido_citrico:'g of citric acid.',
    auth_inserisci:'Enter your email and password.',
    auth_pwd_corta:'Password must be at least 8 characters.',
    auth_ok:'Signed in.',
    auth_reg_ok:'Account created. Welcome to Matter.',
    auth_errore_rete:'The graph is not responding. Try again in a moment.',
    salvato:'✓ Saved',
    ct_sic_disc_uk:'This tool provides indicative estimates based on scientific models. It does not replace official food safety management procedures, HACCP plans, or the advice of a qualified food safety professional.',
    // sicurezza calcolatori
    ct_tab_sic:'Safety',
    ct_sic_shelf:'Indicative shelf life',
    ct_sic_shelf_hint:'Estimate based on Aw, pH and storage temperature.',
    ct_sic_aw:'Aw',
    ct_sic_ph:'pH',
    ct_sic_temp:'Storage T °C',
    ct_sic_shelf_disc:'Indicative estimate — does not replace microbiological testing or certifications.',
    ct_sic_past:'Pasteurisation — log reduction',
    ct_sic_past_hint:'Time needed to reduce bacterial load at a given temperature.',
    ct_sic_past_t:'Temperature °C',
    ct_sic_past_time:'Time (min)',
    ct_sic_cold:'Cold chain — danger zone risk',
    ct_sic_cold_hint:'Cumulative time in the danger zone (4°C–60°C).',
    ct_sic_cold_t:'Temperature °C',
    ct_sic_cold_time:'Time (min)',
    ct_sic_cold_disc:'Safety limit: max 2 cumulative hours in danger zone.',
    ct_sic_gate_title:'Food safety module',
    ct_sic_gate_desc:'Indicative shelf life, pasteurisation and cold chain. Available with Matter Pro.',
    ct_sic_gate_btn:'Upgrade to Pro — €19.99/month',
  },
  es:{
    payoff:'Science & Craft',
    scopri:'Banco', lezione:'Lección', mappa:'Mapa', db_fenomeni:'Fenómenos',
    tab_atlante:'Atlas', tab_chiedi:'Asistente', tab_quaderno:'Cuaderno',
    foto_analisi_titolo:'Análisis foto', foto_analisi_loading:'Reconozco ingredientes y botellas…',
    db_ingredienti:'Ingredientes',
    db_connessioni:'Conexiones aromáticas',
    db_calcolatori:'Calculadoras',
    chiedi:'Preguntar',
    studia:'Explora el fenómeno', nologin:'Empieza sin registrarte.',
    disc_kw_bar:'Acidez · Dilución · Carbonatación · Emulsión',
    disc_kw_bakery:'Estructura · Fermentación · Ósmosis · Retrogradación',
    disc_kw_cucina:'Maillard · Desnaturalización · Calor · Emulsión',
    disc_kw_caffe:'Extracción · Tostado · Presión · Solubilidad',
    disc_kw_pasticceria:'Cristalización · Estructura · Caramelización · Montaje',
    disc_kw_gelateria:'Crioscopia · Overrun · Cristales · PAC',
    disc_kw_vino:'Fermentación · Maloláctica · Acidez · Clarificación',
    disc_kw_birra:'Mash · Lúpulo · Fermentación · Carbonatación',
    db_numbers:'52 fenómenos · 1.530 ingredientes · 33.696 conexiones · 6 calculadoras',
    scopri_ey:'Fenómeno del día', scopri_cta:'Estudia este fenómeno',
    scopri_errore_eyebrow:'Error al cargar', scopri_errore_titolo:'Sin conexión',
    les_step:'Paso', les_di:'de',
    les_quiz_titolo:'Quiz', les_quiz_btn:'Comprobar',
    les_quiz_corr:'¡Correcto!', les_quiz_err:'No exactamente.',
    chiedi_title:'Preguntar a Matter Bench',
    disc_bar:'Bar', disc_cucina:'Cocina', disc_panificazione:'Panadería',
    disc_pasticceria:'Pastelería', disc_gelateria:'Heladería', disc_caffe:'Café',
    disc_vino:'Vino', disc_birra:'Cerveza', disc_sicurezza:'Seguridad alimentaria',
    chiedi_sub:'Un fenómeno físico para cada gesto profesional',
    chiedi_al_grafo:'Preguntar', calcola:'Calcular',
    auth_email:'Email', auth_pwd:'Contraseña',
    auth_login:'Iniciar sesión', auth_reg:'Crear cuenta',
    auth_reg_ok:'¡Cuenta creada. Bienvenido a Matter Bench!',
    auth_errore_rete:'Error de red.', auth_inserisci:'Introduce email y contraseña',
    auth_logout:'Cerrar sesión',
    mappa_title:'Mapa de conocimiento F&B',
    flavor_title:'Red de sabores',
    flavor_cerca:'buscar ingrediente...',
    contrasto_title:'Maridaje por contraste',
    quaderno_title:'Cuaderno',
    quaderno_vuoto:'Sin experimentos guardados.',
    quaderno_salva:'Guardar en el cuaderno',
    supporto:'Soporte',
    ct_cookie_txt:'Matter Bench usa cookies técnicas para funcionar.',
    ct_disc_sicurezza:'Seguridad alimentaria',
    ct_disc_sicurezza_sub:'HACCP · Aw · vida útil · zonas de peligro',
    ct_sic_gate_title:'Módulo de seguridad alimentaria',
    ct_sic_gate_desc:'Shelf life orientativa, pasteurización y cadena de frío.',
    ct_sic_gate_btn:'Mejorar a Pro — €19,99/mes',
    accedi:'Acceder',
    acido_citrico:'g de ácido cítrico.',
    aggiungi_acido:'Añadir',
    aggiungi_ing:'Añade un ingrediente.',
    auth_ok:'Sesión iniciada.',
    auth_pwd_corta:'La contraseña debe tener al menos 8 caracteres.',
    avanti:'Siguiente →',
    caricamento:'cargando…',
    chat_grado:'grado final (era ',
    chat_thinking:'consultando Matter Bench',
    chiedi_btn:'Preguntar',
    onb_nudge_title:'¿Listo en el banco?',
    ai_disclosure:'Respuestas generadas por un asistente de IA.',
    chiedi_placeholder:'pregunta a Matter Bench…',
    continua_free:'Continuar con el plan gratuito',
    continua_senza:'← Continuar sin registrarse',
    ct_idr:"Hidratación (baker's %)",
    ct_acido:'ácido %',
    ct_acqua_g:'agua g',
    ct_acqua_pre:'Agua pre-dilución',
    ct_add:'+ añadir ingrediente',
    ct_batch:'Lote',
    ct_bevanda_g:'bebida g',
    ct_bot:'bot. ml',
    ct_botg:'Embotellado',
    ct_botg_s:'agua ahora',
    ct_bq_serv:'porciones',
    ct_bq_vol:'volumen ml',
    ct_cookie_no:'Solo esenciales',
    ct_cookie_ok:'Aceptar',
    ct_dose_ey:'dosis g',
    ct_dose_ratio:'dosis g',
    ct_drink:'El cóctel',
    ct_drinkcost_label:'coste total orientativo · fuente ISMEA',
    ct_drinkcost_note:'Precios de mercado orientativos. Para coste real usa Cifra.',
    ct_drinkcost_title:'Drink cost orientativo',
    ct_extra:'extra %',
    ct_extra_lbl:'extra',
    ct_farina:'harina g',
    ct_flavor_btn:'Buscar',
    ct_flavor_placeholder:'ej. limón, café, mantequilla…',
    ct_foodcost_label:'coste total orientativo · fuente ISMEA',
    ct_foodcost_note:'Precios de mercado orientativos. Para coste real usa Cifra.',
    ct_foodcost_title:'Food cost orientativo',
    ct_hint_dil:'Punto de partida. Para calibrar: pesa el cóctel antes y después.',
    ct_ice:'Con hielo',
    ct_ice_s:'agua después',
    ct_idr_out:'Hidratación',
    ct_include:'incluye',
    ct_ing:'ingrediente',
    ct_mesc:'Mezclado',
    ct_par:'Equilibrador de acidez',
    ct_par_hint:'Lleva cualquier zumo al 6% como el lima.',
    ct_perporz:'Por porciones',
    ct_pervol:'Por volumen',
    ct_ph:'pH masa madre',
    ct_q10:'Q10 — tiempo de fermentación',
    ct_q10_caldo:'más cálido — fermentación más rápida',
    ct_q10_freddo:'más frío — fermentación más lenta',
    ct_q10_out:'Tiempo estimado',
    ct_quad_empty_sub:'Usa los calculadores y guarda tus medidas físicas.',
    ct_quad_empty_title:'Sin experimentos guardados',
    ct_quad_title:'Cuaderno',
    ct_ratio:'ratio 1:',
    ct_salva_btn:'+ Guardar en cuaderno',
    ct_salva_confirm:'Guardar',
    ct_salva_nome:'Nombre del experimento',
    ct_salva_note:'Notas (opcional)',
    ct_shak:'Agitado',
    ct_sic_aw:'Aw',
    ct_sic_cold:'Cadena de frío — riesgo zona de peligro',
    ct_sic_cold_disc:'Límite de seguridad: máx. 2 horas acumuladas en zona de peligro.',
    ct_sic_cold_hint:'Tiempo acumulado en zona de peligro (4°C–60°C).',
    ct_sic_cold_t:'Temperatura °C',
    ct_sic_cold_time:'Tiempo (min)',
    ct_sic_disc_uk:'This tool provides indicative estimates only.',
    ct_sic_past:'Pasteurización — reducción logarítmica',
    ct_sic_past_hint:'Tiempo necesario para reducir la carga bacteriana.',
    ct_sic_past_t:'Temperatura °C',
    ct_sic_past_time:'Tiempo (min)',
    ct_sic_ph:'pH',
    ct_sic_shelf:'Vida útil orientativa',
    ct_sic_shelf_disc:'Estimación orientativa — no sustituye pruebas microbiológicas.',
    ct_sic_shelf_hint:'Estimación basada en Aw, pH y temperatura de conservación.',
    ct_sic_temp:'T conserv. °C',
    ct_sour:'Sour',
    ct_succo:'zumo ml',
    ct_syr1:'Almíbar 1:1 (50 Brix)',
    ct_syr2:'Almíbar 2:1 (65 Brix)',
    ct_tab_sic:'Seguridad',
    ct_target:'objetivo %',
    ct_tds:'TDS %',
    ct_tecnica:'Técnica',
    ct_totale:'Total',
    disc_bakery:'Panadería',
    disc_caffetteria:'Café',
    domande_esaurite:'Has usado las 5 preguntas gratuitas de hoy.',
    fenomeno_giorno:'fenómeno del día',
    il_percorso:'Tu recorrido',
    indietro:'← Atrás',
    les_caricamento:'cargando…',
    les_errore:'Error al cargar — inténtalo de nuevo.',
    les_fenomeno:'Fenómeno',
    mappa_caricamento:'Cargando…',
    mappa_errore:'Error al cargar el mapa. Inténtalo de nuevo.',
    mappa_nessun_fen:'No se encontraron fenómenos para esta disciplina.',
    mappa_percorso:'Tu recorrido — ',
    mappa_scegli:'Elige una disciplina en Descubrir para ver tu recorrido.',
    num_bersaglio:'número objetivo',
    onb_complete_btn:'Ir al Mapa',
    onb_complete_sub:'Completaste la lección. Ve al Mapa para ver tu recorrido.',
    onb_complete_title:'Excelente trabajo.',
    onb_nudge_sub:'Selecciona tu disciplina abajo para comenzar.',
    onb_ovl_cta:'Empezar',
    onb_ovl_title:'Cómo funciona Matter Bench',
    onb_s1_sub:'Bar, Panadería, Cocina, Café — cada disciplina tiene sus fenómenos.',
    onb_s1_title:'Elige tu disciplina',
    onb_s2_sub:'Cada lección tiene un número objetivo — el parámetro físico que mides en el trabajo.',
    onb_s2_title:'Estudia el fenómeno',
    onb_s3_sub:'Haz una pregunta real. Respondo con números, no con opiniones.',
    onb_s3_title:'Pregunta a Matter Bench',
    passa_pro:'Pasar a Pro',
    perche_insieme:'Por qué funcionan juntos',
    ponte_cifra:'El puente hacia Cifra',
    principi_trasv:'Principios transversales',
    principio_del_giorno:'Principio del día',
    pro_desc:'Con Matter Pro continúas sin límites — lecciones, preguntas y calidad profesional.',
    prova:'Prueba:',
    registrati:'Registrarse',
    salvato:'✓ Guardado',
    scegli:'Elige tu disciplina',
    scegli_disc_mappa:'Elige una disciplina en Descubrir para ver tu recorrido.',
    sup_invia:'Enviar solicitud',
    sup_placeholder:'Ej. No puedo abrir la lección…',
    sup_sub:'Describe el problema. Te responderemos enseguida.',
    sup_titolo:'¿Necesitas ayuda?',
    vai_mappa:'Ir al Mapa →',
    vedi_mappa:'Ver el principio en el Mapa →'
  }
};

function _L(o){ return o[_lang] || o.it; }
function _t(k){ var v=(_strings[_lang]||_strings.it)[k]; return (v!==undefined&&v!==null)?v:k; }

function applicaStringheUI(){
  const s=id=>{ const el=document.getElementById(id); if(el) return el; };
  const st=(id,txt)=>{ const el=s(id); if(el) el.textContent=txt; };
  const sth=(id,html)=>{ const el=s(id); if(el) el.innerHTML=html; };
  // payoff e lang btn
  sth('payoff-text',_t('payoff'));
  // Aggiorna keyword discipline e database numbers con la lingua corrente
  const _dkw = ['bar','bakery','cucina','caffe','pasticceria','gelateria','vino','birra'];
  _dkw.forEach(d => { const el = s('disc-kw-'+d); if(el) el.textContent = _t('disc_kw_'+d)||''; });
  const _dbn = s('db-numbers-text');
  if(_dbn) _dbn.textContent = _t('db_numbers')||'';
  document.getElementById('lang-btn').textContent=_lang.toUpperCase();
  // tab labels — Scopri · Atlante · Chiedi · Quaderno (allineate ai contenuti)
  document.querySelectorAll('.tab-label').forEach((el,i)=>{
    const keys=['scopri','tab_atlante','tab_chiedi','tab_quaderno'];
    if(keys[i]) el.textContent=_t(keys[i]);
  });
  // scopri
  st('scopri-cta',_t('studia'));
  const noL=document.querySelector('.no-login'); if(noL){ var _nl=_t('nologin'); noL.textContent=_nl; noL.style.display=_nl?'':'none'; }
  document.querySelectorAll('.sec-label').forEach(el=>{
    if(el.textContent.includes('Scegli la tua')||el.textContent.includes('Choose your'))
      el.textContent=_t('scegli');
  });
  // AI Act disclosure badge
  st('ai-disclosure-bar', _t('ai_disclosure'));
  // chiedi
  const qIn=document.getElementById('q'); if(qIn) qIn.placeholder=_t('chiedi_placeholder');
  // ask-btn usa solo l'icona freccia — nessun testo
  st('ct-chiedi-title',_t('chiedi_title'));
  st('ct-chiedi-sub',_t('chiedi_sub'));
  st('sup-titolo',_t('sup_titolo'));
  st('sup-sub',_t('sup_sub'));
  st('sup-btn-inv',_t('sup_invia'));
  const supTxt=document.getElementById('sup-testo');
  if(supTxt) supTxt.placeholder=_t('sup_placeholder');
  // nomi discipline
  ['bar','bakery','cucina','pasticceria','gelateria','vino','birra'].forEach(d=>{
    const el=document.getElementById('disc-'+d+'-nome');
    if(el) el.textContent=_t('disc_'+d);
  });
  const caffe=document.getElementById('disc-caffe-nome');
  if(caffe) caffe.textContent=_t('disc_caffetteria');
  st('subtab-chat',_t('chiedi_al_grafo'));
  st('subtab-calc',_t('calcola'));
  // lezione
  st('les-btn-prec',_t('indietro'));
  // mappa hardcoded
  st('ct-princ-trasv',_t('principi_trasv'));
  st('ct-perche-ins',_t('perche_insieme'));
  st('ct-ponte-cifra',_t('ponte_cifra'));
  // calcolatori — diluizione
  st('ct-drink',_t('ct_drink'));
  st('ct-ing',_t('ct_ing'));
  st('ct-add',_t('ct_add'));
  st('ct-tecnica',_t('ct_tecnica'));
  st('ct-mesc',_t('ct_mesc'));
  st('ct-shak',_t('ct_shak'));
  st('ct-hint-dil',_t('ct_hint_dil'));
  // batch
  st('ct-batch',_t('ct_batch'));
  st('ct-perporz',_t('ct_perporz'));
  st('ct-pervol',_t('ct_pervol'));
  st('ct-extra',_t('ct_extra'));
  st('ct-bot',_t('ct_bot'));
  st('ct-ice',_t('ct_ice'));
  st('ct-ice-s',_t('ct_ice_s'));
  st('ct-botg',_t('ct_botg'));
  st('ct-botg-s',_t('ct_botg_s'));
  // aggiorna label batch dinamica se visibile
  const bqLab=document.getElementById('bq-lab');
  if(bqLab) bqLab.textContent = document.getElementById('bm-serv')?.getAttribute('aria-pressed')==='true'
    ? _t('ct_bq_serv') : _t('ct_bq_vol');
  // bilanciamento
  st('ct-sour',_t('ct_sour'));
  const syr1=document.getElementById('ct-syr1'); if(syr1) syr1.textContent=_t('ct_syr1');
  const syr2=document.getElementById('ct-syr2'); if(syr2) syr2.textContent=_t('ct_syr2');
  st('ct-par',_t('ct_par'));
  st('ct-par-hint',_t('ct_par_hint'));
  st('ct-succo',_t('ct_succo'));
  st('ct-acido',_t('ct_acido'));
  st('ct-target',_t('ct_target'));
  // bakery / caffè
  st('ct-idr',_t('ct_idr'));
  st('ct-q10',_t('ct_q10'));
  st('ct-ph',_t('ct_ph'));
  st('ct-farina',_t('ct_farina'));
  st('ct-acqua-g',_t('ct_acqua_g'));
  st('ct-dose-ey',_t('ct_dose_ey'));
  st('ct-bevanda-g',_t('ct_bevanda_g'));
  st('ct-tds',_t('ct_tds'));
  st('ct-dose-ratio',_t('ct_dose_ratio'));
  st('ct-ratio',_t('ct_ratio'));
  // cookie banner
  st('ct-cookie-ok',_t('ct_cookie_ok'));
  st('ct-cookie-no',_t('ct_cookie_no'));
  const cTxt=document.getElementById('ct-cookie-txt');
  if(cTxt) cTxt.childNodes[0].textContent=_t('ct_cookie_txt')+' ';
  // paywall
  document.querySelectorAll('.paywall-sheet h3').forEach(el=>el.textContent=_t('domande_esaurite'));
  document.querySelectorAll('.paywall-sheet p').forEach(el=>el.textContent=_t('pro_desc'));
  const pwCta=document.querySelector('.pw-cta'); if(pwCta) pwCta.textContent=_t('passa_pro');
  const pwSkip=document.querySelector('.pw-skip'); if(pwSkip) pwSkip.textContent=_t('continua_free');
  // auth
  st('auth-tab-login',_t('accedi'));
  st('auth-tab-reg',_t('registrati'));
  const authSkip=document.querySelector('.auth-skip a'); if(authSkip) authSkip.textContent=_t('continua_senza');
  // onboarding
  st('onb-ovl-title',_t('onb_ovl_title'));
  st('onb-s1-title',_t('onb_s1_title'));
  st('onb-s1-sub',_t('onb_s1_sub'));
  st('onb-s2-title',_t('onb_s2_title'));
  st('onb-s2-sub',_t('onb_s2_sub'));
  st('onb-s3-title',_t('onb_s3_title'));
  st('onb-s3-sub',_t('onb_s3_sub'));
  st('onb-ovl-cta',_t('onb_ovl_cta'));
  st('onb-nudge-title',_t('onb_nudge_title'));
  st('onb-nudge-sub',_t('onb_nudge_sub'));
  st('onb-complete-title',_t('onb_complete_title'));
  st('onb-complete-sub',_t('onb_complete_sub'));
  st('onb-complete-btn',_t('onb_complete_btn'));
  st('ct-disc-sicurezza',_t('ct_disc_sicurezza'));
  st('ct-disc-sicurezza-sub',_t('ct_disc_sicurezza_sub'));
  // sicurezza calcolatori
  st('ctab-sic',_t('ct_tab_sic'));
  st('ct-sic-shelf',_t('ct_sic_shelf'));
  st('ct-sic-shelf-hint',_t('ct_sic_shelf_hint'));
  st('ct-sic-aw',_t('ct_sic_aw'));
  st('ct-sic-ph',_t('ct_sic_ph'));
  st('ct-sic-temp',_t('ct_sic_temp'));
  const shelfDisc=document.getElementById('ct-sic-shelf-disc');
  if(shelfDisc) shelfDisc.textContent = _lang==='en' ? _t('ct_sic_disc_uk') : _t('ct_sic_shelf_disc');
  st('ct-sic-past',_t('ct_sic_past'));
  st('ct-sic-past-hint',_t('ct_sic_past_hint'));
  st('ct-sic-past-t',_t('ct_sic_past_t'));
  st('ct-sic-past-time',_t('ct_sic_past_time'));
  st('ct-sic-cold',_t('ct_sic_cold'));
  st('ct-sic-cold-hint',_t('ct_sic_cold_hint'));
  st('ct-sic-cold-t',_t('ct_sic_cold_t'));
  st('ct-sic-cold-time',_t('ct_sic_cold_time'));
  const coldDisc=document.getElementById('ct-sic-cold-disc'); if(coldDisc) coldDisc.textContent=_t('ct_sic_cold_disc');
  st('ct-sic-gate-title',_t('ct_sic_gate_title'));
  st('ct-sic-gate-desc',_t('ct_sic_gate_desc'));
  st('ct-sic-gate-btn',_t('ct_sic_gate_btn'));
  // drink cost / food cost
  st('ct-drinkcost-title',_t('ct_drinkcost_title'));
  st('ct-drinkcost-label',_t('ct_drinkcost_label'));
  const dcNote=document.getElementById('ct-drinkcost-note'); if(dcNote) dcNote.textContent=_t('ct_drinkcost_note');
  st('ct-foodcost-title',_t('ct_foodcost_title'));
  st('ct-foodcost-label',_t('ct_foodcost_label'));
  const fcNote=document.getElementById('ct-foodcost-note'); if(fcNote) fcNote.textContent=_t('ct_foodcost_note');
}
/* ── CALCOLATORI SICUREZZA ALIMENTARE ─────────────────── */

function calcShelfLife(){
  const aw = parseFloat(document.getElementById('sic-aw').value)||0;
  const ph = parseFloat(document.getElementById('sic-ph').value)||0;
  const t  = parseFloat(document.getElementById('sic-temp').value)||4;
  const out = document.getElementById('sic-shelf-out');

  // Modello semplificato Hurdle Technology
  // ogni barriera riduce la crescita — combinazione moltiplicativa
  let score = 0;
  let flag = '';

  // fattore Aw
  if(aw < 0.60) score += 4;
  else if(aw < 0.85) score += 3;
  else if(aw < 0.93) score += 2;
  else if(aw < 0.97) score += 1;
  else score += 0;

  // fattore pH
  if(ph < 3.5) score += 4;
  else if(ph < 4.0) score += 3;
  else if(ph < 4.6) score += 2;
  else if(ph < 5.5) score += 1;
  else score += 0;

  // fattore temperatura
  if(t <= 2) score += 3;
  else if(t <= 4) score += 2;
  else if(t <= 8) score += 1;
  else if(t > 60) score += 2; // caldo stabile
  else { score += 0; flag = '⚠️ zona pericolo'; }

  // stima giorni
  const giorni = [1, 2, 4, 7, 14, 30, 90, 180][Math.min(score, 7)];
  const livello = score >= 6 ? 'stabile' : score >= 4 ? 'buono' : score >= 2 ? 'limitato' : 'critico';
  const col = score >= 4 ? 'var(--s700)' : score >= 2 ? 'var(--e700)' : '#c0392b';

  out.innerHTML = `<span style="font-family:var(--mono);font-size:18px;font-weight:600;color:${col}">
    ~${giorni} giorn${giorni===1?'o':'i'}</span>
    <span style="font-size:12px;color:var(--ink-muted);margin-left:8px">${livello}${flag?' · '+flag:''}</span>`;
}

function calcPastorizzazione(){
  const T = parseFloat(document.getElementById('sic-past-t').value)||60;
  const t = parseFloat(document.getElementById('sic-past-time').value)||30;
  const out = document.getElementById('sic-past-out');

  // D-value per Salmonella (riferimento più comune): D70 = 0.1 min, z = 5.6°C
  const D_ref = 0.1; // min a 70°C
  const T_ref = 70;
  const z = 5.6;

  const D_T = D_ref * Math.pow(10, (T_ref - T) / z);
  const log_rid = t / D_T;
  const conf = log_rid >= 7 ? 'sterilizzazione commerciale' :
               log_rid >= 5 ? 'pastorizzazione alta (5 log)' :
               log_rid >= 3 ? 'pastorizzazione base (3 log)' : 'riduzione insufficiente';
  const col = log_rid >= 5 ? 'var(--s700)' : log_rid >= 3 ? 'var(--e700)' : '#c0392b';

  out.innerHTML = `<span style="font-family:var(--mono);font-size:18px;font-weight:600;color:${col}">
    ${log_rid.toFixed(1)} log</span>
    <span style="font-size:12px;color:var(--ink-muted);margin-left:8px">${conf}</span>
    <div style="font-size:11px;color:var(--ink-muted);margin-top:4px">D(${T}°C) = ${D_T.toFixed(2)} min (rif. Salmonella)</div>`;
}

function calcCatenaFreddo(){
  const T = parseFloat(document.getElementById('sic-cold-t').value)||20;
  const t = parseFloat(document.getElementById('sic-cold-time').value)||60;
  const out = document.getElementById('sic-cold-out');

  const inZona = T > 4 && T < 60;
  const ore = t / 60;

  if(!inZona){
    const msg = T <= 4 ? 'Temperatura sicura — sotto la zona pericolo.' : 'Sopra 60°C — zona di abbattimento batterico.';
    out.innerHTML = `<span style="font-size:13px;color:var(--s700)">${msg}</span>`;
    return;
  }

  // doubling time ~20 min a 37°C, Q10 ≈ 2 ogni 10°C
  const dt_37 = 20; // min
  const dt_T = dt_37 * Math.pow(2, (37 - T) / 10);
  const raddoppi = t / dt_T;
  const moltiplicatore = Math.pow(2, raddoppi);

  const rischio = ore >= 2 ? 'alto — scartare' : ore >= 1 ? 'moderato — consumare subito' : 'basso';
  const col = ore >= 2 ? '#c0392b' : ore >= 1 ? 'var(--e700)' : 'var(--s700)';

  out.innerHTML = `<span style="font-family:var(--mono);font-size:16px;font-weight:600;color:${col}">
    ×${moltiplicatore < 1000 ? moltiplicatore.toFixed(0) : '>1000'} batteri</span>
    <span style="font-size:12px;color:var(--ink-muted);margin-left:8px">rischio ${rischio}</span>
    <div style="font-size:11px;color:var(--ink-muted);margin-top:4px">${ore.toFixed(1)}h in zona pericolo · doubling time ~${dt_T.toFixed(0)} min a ${T}°C</div>`;
}

/* ── ONBOARDING OVERLAY ──────────────────────────────── */
function mostraOnbOverlay(){
  try{ if(localStorage.getItem('matter_onb_done')) return; }catch(e){}
  // nasconde il vecchio overlay HTML se presente, mostra il nuovo a 4 schermate
  var vecchio = document.getElementById('onb-overlay');
  if(vecchio) vecchio.classList.add('hidden');
  mostraOnb4();
}
function chiudiOnbOverlay(){
  const overlay = document.getElementById('onb-overlay');
  if(overlay) overlay.classList.add('hidden');
  try{ localStorage.setItem('matter_onb_done','1'); }catch(e){}
  if(typeof caricaHome === 'function') caricaHome();
}

/* ═══ ONBOARDING v2 — 4 schermate, la misura vera (spec congelata) ═══ */
var _onb4Station = null;
var ONB4_STATIONS = [
  { id:'bar', disc:'bar', t:'Dietro un bancone bar', d:'Cocktail, caffè, aperitivo',
    prob:'Il tuo Sour è mai cambiato senza cambiare ricetta?', probSub:'Lo stesso lime. La stessa dose. Perché oggi è diverso?',
    wowH:'Perché il Sour cambia', target:'1.2–1.5', unit:'% acidità titolabile', measUnit:'% acidità', measLab:'Acidità del tuo Sour',
    chat:[['Problema','Acidità fuori finestra.'],['Perché','Il pH e l\'acidità titolabile non sono la stessa misura. Il lime cambia di lotto in lotto.'],['__t__',''],['Azione','Misura una leva alla volta: prima l\'acido, poi lo zucchero.']] },
  { id:'forno', disc:'panificazione', t:'In un forno o pizzeria', d:'Impasti, pane, pizza',
    prob:'Perché due impasti identici lievitano in modo diverso?', probSub:'Stessa farina. Stessa acqua. Cambia una variabile nascosta.',
    wowH:'Perché la lievitazione cambia', target:'24', unit:'°C temperatura finale impasto', measUnit:'°C', measLab:'Temperatura del tuo impasto',
    chat:[['Problema','Temperatura finale impasto fuori target.'],['Perché','La fermentazione raddoppia ogni ~10°C. Bastano 2°C per cambiare i tempi.'],['__t__',''],['Azione','Calcola la temperatura dell\'acqua per centrare i 24°C.']] },
  { id:'cucina', disc:'cucina', t:'In cucina', d:'Piatti, salse, cotture',
    prob:'Perché una carbonara impazzisce?', probSub:'Non è la panna. È temperatura.',
    wowH:'Perché la carbonara impazzisce', target:'65', unit:'°C coagulazione ovoproteina', measUnit:'°C', measLab:'Temperatura della tua crema',
    chat:[['Problema','Il tuorlo coagula troppo presto.'],['Perché','L\'ovoproteina coagula a 65°C. Oltre, straccia: frittata, non crema.'],['__t__',''],['Azione','Manteca fuori fiamma, sotto i 65°C.']] },
  { id:'gelato', disc:'gelateria', t:'Gelateria / pasticceria', d:'Gelato, creme, dessert',
    prob:'Perché il gelato cristallizza?', probSub:'Non è il freezer. È acqua libera.',
    wowH:'Perché il gelato cristallizza', target:'70', unit:'PAC potere anticongelante', measUnit:'PAC', measLab:'PAC della tua base',
    chat:[['Problema','Cristalli di ghiaccio percepibili.'],['Perché','L\'acqua libera non legata cristallizza. Il PAC misura quanta ne resta mobile.'],['__t__',''],['Azione','Alza il PAC con destrosio: abbassi il punto di congelamento.']] },
  { id:'vino', disc:'vino', t:'Cantina / vino', d:'Vini e abbinamenti',
    prob:'Perché questo vino spegne il piatto?', probSub:'L\'acidità dialoga male col grasso.',
    wowH:'Perché il vino spegne il piatto', target:'6.5', unit:'g/L acidità totale', measUnit:'g/L', measLab:'Acidità del tuo vino',
    chat:[['Problema','Il vino non regge il grasso del piatto.'],['Perché','L\'acidità taglia il grasso. Sotto una soglia, il palato resta impastato.'],['__t__',''],['Azione','Cerca un\'acidità più alta, o alleggerisci il grasso.']] },
  { id:'locale', disc:'bar', t:'Gestisco un locale', d:'Menu, drink list, carta vini',
    prob:'La tua drink list e il tuo menu si parlano?', probSub:'Ingredienti specchio, ridondanze aromatiche.',
    wowH:'Se menu e drink list dialogano', target:'52', unit:'% asse aromatico dominante', measUnit:'%', measLab:'Peso dell\'asse dominante',
    chat:[['Problema','Ridondanza aromatica tra piatti e drink.'],['Perché','Se troppe voci battono sullo stesso asse, il palato satura.'],['__t__',''],['Azione','Bilancia gli assi: acido, dolce, amaro, grasso.']] }
];
function _onb4Ring(){return '<svg viewBox="0 0 14 14" fill="none" style="width:14px;height:14px"><circle cx="7" cy="7" r="5.6" stroke="#241109" stroke-width="1.2"/><circle cx="7" cy="7" r="2" fill="#241109"/><path d="M7 0v2.2M7 11.8V14M0 7h2.2M11.8 7H14" stroke="#241109" stroke-width="1.2"/></svg>';}
function mostraOnb4(){
  var o = document.getElementById('onb4');
  if(!o){
    o = document.createElement('div'); o.id='onb4'; o.className='onb4';
    document.body.appendChild(o);
  }
  o.innerHTML =
    '<div class="onb4-in">'
    + '<div class="onb4-prog"><div class="seg on" id="onb4-s0"></div><div class="seg" id="onb4-s1"></div><div class="seg" id="onb4-s2"></div></div>'
    + '<button class="onb4-skip" onclick="chiudiOnb4()">Salta →</button>'
    // schermata 0
    + '<div class="onb4-screen active" id="onb4-sc0">'
    +   '<div class="onb4-eye">Numeri. Non opinioni.</div>'
    +   '<div class="onb4-h">Dove lavori ogni giorno?</div>'
    +   '<div class="onb4-sub">Personalizziamo Matter sul tuo banco. Puoi cambiarlo quando vuoi.</div>'
    +   '<div class="onb4-opts">'+ONB4_STATIONS.map(function(s,i){return '<button class="onb4-opt" onclick="onb4Pick('+i+')"><span class="tx"><span class="t">'+s.t+'</span><span class="d">'+s.d+'</span></span></button>';}).join('')+'</div>'
    +   '<div class="onb4-micro">Niente email adesso. Prima ti mostriamo perché serve.</div>'
    + '</div>'
    // schermata 1 — problema
    + '<div class="onb4-screen" id="onb4-sc1"><div class="onb4-eye">Il problema</div><div class="onb4-probq" id="onb4-q"></div><div class="onb4-probsub" id="onb4-qsub"></div><button class="onb4-btn" onclick="onb4Go(2)">Scoprilo</button></div>'
    // schermata 2 — wow
    + '<div class="onb4-screen" id="onb4-sc2"><div class="onb4-eye">La risposta</div><div class="onb4-h" id="onb4-wowh" style="font-size:22px;margin-bottom:14px"></div><div class="onb4-chat" id="onb4-chat"></div><button class="onb4-btn" onclick="onb4Go(3)">Ora provalo tu →</button></div>'
    // schermata 3 — misura
    + '<div class="onb4-screen" id="onb4-sc3"><div class="onb4-eye">La tua prima misura</div><div class="onb4-h" style="font-size:23px">Inserisci il tuo valore.</div><div class="onb4-sub">Come faresti al banco adesso. Se non ce l\'hai sottomano, puoi entrare e misurare dopo.</div>'
    +   '<div class="onb4-meas"><div class="onb4-meas-lab" id="onb4-mlab">La tua misura</div><div class="onb4-field"><input type="text" inputmode="decimal" id="onb4-input" oninput="onb4Check()"><span class="u" id="onb4-munit"></span></div><div class="onb4-hint" id="onb4-hint"></div><div class="onb4-res" id="onb4-res"><div class="onb4-res-s" id="onb4-scarto"></div><div class="onb4-res-t" id="onb4-rtxt"></div></div></div>'
    +   '<button class="onb4-btn" id="onb4-enter" onclick="chiudiOnb4()">Entra in Matter →</button>'
    + '</div>'
    + '</div>';
  o.classList.add('show');
}
function onb4Pick(i){
  _onb4Station = ONB4_STATIONS[i];
  var s = _onb4Station;
  document.getElementById('onb4-q').textContent = s.prob;
  document.getElementById('onb4-qsub').textContent = s.probSub;
  document.getElementById('onb4-wowh').textContent = s.wowH;
  document.getElementById('onb4-chat').innerHTML = s.chat.map(function(row){
    if(row[0]==='__t__') return '<div class="onb4-target"><div class="onb4-target-lab">'+_onb4Ring()+' Bersaglio</div><div class="onb4-target-v">'+s.target+'</div><div class="onb4-target-u">'+s.unit+'</div></div>';
    return '<div class="onb4-crow"><div class="onb4-ck">'+row[0]+'</div><div class="onb4-cv">'+row[1]+'</div></div>';
  }).join('');
  document.getElementById('onb4-munit').textContent = s.measUnit;
  document.getElementById('onb4-mlab').textContent = s.measLab;
  document.getElementById('onb4-hint').innerHTML = 'Bersaglio: <b>'+s.target+' '+s.measUnit.replace(/^[^ ]* /,'')+'</b>';
  document.getElementById('onb4-input').placeholder = String(s.target).split(/[–-]/)[0];
  setTimeout(function(){ onb4Go(1); }, 160);
}
function onb4Go(n){
  var scr = document.querySelectorAll('.onb4-screen');
  for(var i=0;i<scr.length;i++) scr[i].classList.remove('active');
  document.getElementById('onb4-sc'+n).classList.add('active');
  var map={0:0,1:0,2:1,3:2}, cur=map[n];
  ['onb4-s0','onb4-s1','onb4-s2'].forEach(function(id,i){
    var el=document.getElementById(id); if(!el) return;
    el.classList.toggle('done', i<cur); el.classList.toggle('on', i===cur);
  });
}
function onb4Check(){
  var s=_onb4Station; if(!s) return;
  var v=parseFloat((document.getElementById('onb4-input').value||'').replace(',','.'));
  var res=document.getElementById('onb4-res');
  if(isNaN(v)){ res.classList.remove('show'); return; }
  var nums=String(s.target).split(/[–-]/).map(function(x){return parseFloat(x);});
  var lo=nums[0], hi=nums[1]||nums[0], scarto, txt;
  if(v<lo){ scarto='−'+(lo-v).toFixed(1); txt='Sei sotto la finestra. Manca poco per centrare il bersaglio.'; }
  else if(v>hi){ scarto='+'+(v-hi).toFixed(1); txt='Sei sopra la finestra. Basta poco per rientrare.'; }
  else { scarto='In finestra'; txt='Sei nel bersaglio. Questo è il valore che rende il risultato ripetibile.'; }
  document.getElementById('onb4-scarto').textContent=scarto;
  document.getElementById('onb4-rtxt').textContent=txt;
  res.classList.add('show');
}
function chiudiOnb4(){
  try{ localStorage.setItem('matter_onb_done','1'); if(_onb4Station) localStorage.setItem('matter_station', _onb4Station.disc); }catch(e){}
  var o=document.getElementById('onb4'); if(o) o.classList.remove('show');
  if(_onb4Station){ Matter.disciplina = _onb4Station.disc; Matter.step = 0; }
  if(typeof switchTab==='function') switchTab('scopri');
  if(typeof caricaHome==='function') caricaHome();
  // #7 associazione Bench=banco, una volta sola (solo IT)
  try{
    if((typeof _lang==='undefined'||_lang==='it') && !localStorage.getItem('matter_bench_spiegato')){
      localStorage.setItem('matter_bench_spiegato','1');
      setTimeout(function(){ if(typeof _toast==='function') _toast('Bench è il banco di lavoro del professionista. Matter Bench è il tuo banco di prova scientifico.'); }, 900);
    }
  }catch(e){}
}

// ── ONBOARDING PROFILAZIONE: mestiere → primo numero → lezione ──
let _onbMestiere = null;
async function onbScegliMestiere(disc, label){
  _onbMestiere = disc;
  Matter.disciplina = disc;
  document.getElementById('onb-f2-ey').textContent = label;
  // carico il primo fenomeno della disciplina per mostrare il primo numero
  try{
    const r = await fetch('/mappa/'+disc, { headers: _statoHeaders() });
    const j = await r.json();
    const primo = (j.fenomeni||[])[0];
    if(primo){
      document.getElementById('onb-pn-fen').textContent = primo.nome || '';
      const eroe = (primo.target||'').split(/\s*[·;]\s*/)[0].trim();
      document.getElementById('onb-pn-target').textContent = eroe || primo.target || '';
      _onbPrimoFen = primo;
    }
  }catch(e){ /* se fallisce, passo comunque alla fase 2 */ }
  document.getElementById('onb-fase-1').style.display='none';
  document.getElementById('onb-fase-2').style.display='block';
}
let _onbPrimoFen = null;
function onbVaiAllaLezione(){
  localStorage.setItem('matter_onb_done','1');
  const overlay = document.getElementById('onb-overlay');
  if(overlay) overlay.classList.add('hidden');
  // porto l'utente nella lezione della sua disciplina, al primo fenomeno
  if(_onbMestiere){ selezionaDisciplina(_onbMestiere); }
  else if(typeof caricaHome === 'function'){ caricaHome(); }
}

/* ── FLAVOR NETWORK MAPPA ─────────────────────────────── */
const FLAVOR_FREE = 3;
const QUAD_FREE = 3;

function _oggiKeyFlavor(){ return 'mf_'+new Date().toISOString().slice(0,10); }
function _getFlavorUse(){ return parseInt(localStorage.getItem(_oggiKeyFlavor())||'0',10); }
function _incFlavorUse(){ localStorage.setItem(_oggiKeyFlavor(), _getFlavorUse()+1); }

async function cercaFlavorMappa(){
  const q = document.getElementById('flavor-query').value.trim();
  if(!q) return;
  const res = document.getElementById('flavor-results-mappa');
  res.innerHTML = `<div style="color:var(--ink-muted);font-size:12px;padding:8px 0">${_t('caricamento')}</div>`;
  const ing = q.toLowerCase().replace(/\s+/g,'_');
  try {
    const r = await fetch('/v1/abbina/'+encodeURIComponent(ing));
    const j = await r.json();
    if(!j.abbinamenti || !j.abbinamenti.length){
      res.innerHTML=`<div style="color:var(--ink-muted);font-size:12px;padding:8px 0">Nessun abbinamento trovato per <b>${esc(q)}</b>.</div>`;
      return;
    }
    _incFlavorUse();
    caricaComposti(ing);
    const usate = _getFlavorUse();
    const isPro = _isPro();
    const tutti = j.abbinamenti;
    const visibili = isPro ? tutti : tutti.slice(0, FLAVOR_FREE);
    const nascosti = isPro ? [] : tutti.slice(FLAVOR_FREE);
    const _ingFlavor = ing; // ingrediente cercato

    let html = visibili.map(a=>`
      <div class="flavor-result-item" style="align-items:center">
        <span class="flavor-result-name">${esc(a.ingrediente.replace(/_/g,' '))}</span>
        <div style="display:flex;align-items:center;gap:6px">
          <span class="flavor-result-why">${esc(a.composto||'')} · ${a.overlap||''}</span>
          <button onclick="feedbackAbb('${esc(a.ingrediente)}','${esc(_ingFlavor)}',1,this)" title="Mi piace" style="background:none;border:none;cursor:pointer;font-size:14px;padding:2px;opacity:.5" class="fb-btn"><i class="ph ph-thumbs-up"></i></button>
          <button onclick="feedbackAbb('${esc(a.ingrediente)}','${esc(_ingFlavor)}',-1,this)" title="Non mi piace" style="background:none;border:none;cursor:pointer;font-size:14px;padding:2px;opacity:.5" class="fb-btn"><i class="ph ph-thumbs-down"></i></button>
        </div>
      </div>`).join('');

    if(nascosti.length){
      html += nascosti.map(a=>`
        <div class="flavor-result-item cap-blur">
          <span class="flavor-result-name">${esc(a.ingrediente.replace(/_/g,' '))}</span>
          <span class="flavor-result-why">${esc(a.composto||'')} · ${a.overlap||''}</span>
        </div>`).join('');
      html += `<div class="cap-lock">
        <svg viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/></svg>
        <span class="cap-lock-txt">${FLAVOR_FREE} abbinamenti liberi per ricerca. Vedi tutto con Pro.</span>
        <span class="cap-lock-cta" onclick="vaiAPro()">Passa a Pro →</span>
      </div>`;
    }
    res.innerHTML = html;

    // ── abbinamento per contrasto (fisico-percettivo) ────────
    const resC = document.getElementById('contrasto-results-mappa');
    if(resC){
      resC.innerHTML=`<div style="color:var(--ink-muted);font-size:12px;padding:4px 0">${_t('caricamento')}</div>`;
      try{
        const rc = await fetch('/v1/contrasto/'+encodeURIComponent(ing));
        const jc = await rc.json();
        if(jc.contrasti && jc.contrasti.length){
          resC.innerHTML = '<div style="font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--teal);margin:10px 0 6px">per contrasto</div>' +
            jc.contrasti.map(c=>`
              <div class="flavor-result-item">
                <span class="flavor-result-name" style="color:var(--teal)">${esc(c.ingrediente.replace(/_/g,' '))}</span>
                <span class="flavor-result-why" style="color:var(--teal);opacity:.8">${esc(c.meccanismo.replace(/_/g,' '))}</span>
              </div>
              <div style="font-size:11px;color:var(--ink-muted);padding:0 0 6px 0;line-height:1.4">${esc(c.perche)}</div>
            `).join('');
        } else {
          resC.innerHTML='';
        }
      }catch(e){ resC.innerHTML=''; }
    }
  } catch(e){
    res.innerHTML=`<div style="color:var(--e700);font-size:12px;padding:8px 0">Errore. Riprova.</div>`;
  }
}

/* ── COMPOSTI AROMATICI ────────────────────────────────── */
async function caricaComposti(ingrediente) {
  const section = document.getElementById('composti-section');
  const list = document.getElementById('composti-list');
  if (!section || !list) return;
  try {
    const r = await fetch('/v1/composti/' + encodeURIComponent(ingrediente));
    const data = await r.json();
    if (!data.composti || !data.composti.length) {
      section.style.display = 'none';
      return;
    }
    list.innerHTML = data.composti.map(c =>
      `<div style="background:rgba(44,110,99,0.08);border:1px solid rgba(44,110,99,0.2);border-radius:4px;padding:6px 10px;min-width:80px;max-width:160px">
        <div style="font-family:var(--mono);font-size:10px;font-weight:500;color:var(--teal);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(c.nome)}</div>
        <div style="font-family:var(--sans);font-size:11px;color:var(--ink-muted);margin-top:2px;font-style:italic;line-height:1.3">${esc(c.aroma)}</div>
      </div>`
    ).join('');
    section.style.display = 'block';
  } catch(e) {
    if(section) section.style.display = 'none';
  }
}


/* ── SSO CIFRA ─────────────────────────────────────────── */
async function importaCifra(ricetta_id) {
  const token = localStorage.getItem('matter_token');
  const email = localStorage.getItem('matter_email');
  if (!token || !email) {
    alert('Devi essere loggato per importare in Cifra.');
    switchTab('auth');
    return;
  }
  try {
    const r = await fetch('/v1/token/generate', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email: email, ricetta_id: ricetta_id || null })
    });
    const d = await r.json();
    if (d.deep_link) {
      window.open(d.deep_link, '_blank');
    } else {
      alert(_L({it:'Errore nella generazione del link: ',en:'Error generating link: ',es:'Error al generar el enlace: '}) + (d.errore || _L({it:'sconosciuto',en:'unknown',es:'desconocido'})));
    }
  } catch(e) {
    alert('Errore di connessione: ' + e.message);
  }
}

/* ── STRUMENTI DI MISURA ────────────────────────────────── */
async function caricaStrumenti(disciplina) {
  const list = document.getElementById('strumenti-list');
  if(!list) return;
  if(!disciplina) disciplina = 'bar';  // Parte A: mostra sempre qualcosa (default bar)
  try {
    const disc_norm = disciplina.toLowerCase().replace('caffetteria','caffe').replace('panificazione','panificazione');
    const r = await fetch('/v1/strumenti/' + encodeURIComponent(disc_norm));
    const j = await r.json();
    const items = j.strumenti || [];
    if(!items.length) { list.innerHTML = '<div style="color:var(--ink-muted);font-size:13px">Nessuno strumento per questa disciplina.</div>'; return; }
    list.innerHTML = items.map(s => `
      <a class="strum-card" href="${esc(s.amazon)}" target="_blank" rel="noopener sponsored">
        <div class="strum-card-head">
          <div class="strum-card-nome">${esc(s.nome)}</div>
          <span class="strum-card-vedi">Vedi <i class="ph ph-arrow-up-right"></i></span>
        </div>
        <div class="strum-card-meta"><span class="strum-card-mis">${esc(s.misura)}</span><span class="strum-card-sep">·</span><span>${esc(s.target)}</span><span class="strum-card-sep">·</span><span class="strum-card-prezzo">${esc(s.prezzo_approx||'')}</span></div>
        ${s.uso ? `<div class="strum-card-uso">${esc(s.uso)}</div>` : ''}
      </a>`).join('');
  } catch(e) {
    list.innerHTML = '<div style="color:var(--ink-muted);font-size:13px">Errore caricamento strumenti.</div>';
  }
}

/* ── SOMMELIER DIGITALE ─────────────────────────────────── */
async function caricaProfiloSensoriale() {
  const div = document.getElementById('profilo-sensoriale');
  if(!div) return;
  div.style.display = 'block';
  div.innerHTML = '<div style="color:var(--ink-muted);font-size:13px">Caricamento...</div>';
  try {
    const token = localStorage.getItem('matter_token') || '';
    if(!token) { div.innerHTML = '<div style="color:var(--ink-muted);font-size:13px">Accedi per vedere il tuo profilo sensoriale.</div>'; return; }
    const r = await fetch('/v1/profilo-sensoriale', {headers:{'Authorization':'Bearer '+token}});
    if(!r.ok){ div.innerHTML = '<div style="color:var(--ink-muted);font-size:13px">Fai qualche valutazione sugli abbinamenti per costruire il tuo profilo.</div>'; return; }
    const j = await r.json();
    if(j.errore) { div.innerHTML = '<div style="color:var(--ink-muted);font-size:13px">Fai qualche valutazione sugli abbinamenti per costruire il tuo profilo.</div>'; return; }
    // il profilo ha le dimensioni sensoriali (escludo le chiavi interne che iniziano con _)
    const profilo = j.profilo || {};
    const dim = {};
    Object.entries(profilo).forEach(([k,v]) => { if(!k.startsWith('_') && typeof v === 'number') dim[k]=v; });
    if(Object.keys(dim).length === 0){
      div.innerHTML = '<div style="color:var(--ink-muted);font-size:13px">Il tuo profilo si costruisce man mano che valuti gli abbinamenti con 👍 e 👎.</div>';
      return;
    }
    const html = Object.entries(dim).map(([k,v]) => `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <div style="font-family:var(--mono);font-size:10px;color:var(--ink-muted);width:82px;text-transform:uppercase">${esc(k)}</div>
        <div style="flex:1;background:var(--border);height:8px">
          <div style="background:var(--accent);width:${Math.round((v/10)*100)}%;height:8px"></div>
        </div>
        <div style="font-family:var(--mono);font-size:10px;color:var(--accent);width:26px;text-align:right">${Number(v).toFixed(1)}</div>
      </div>`).join('');
    div.innerHTML = html;
  } catch(e) {
    div.innerHTML = '<div style="color:var(--ink-muted);font-size:13px">Il profilo non è disponibile ora. Riprova tra poco.</div>';
  }
}

/* ── FINE STRUMENTI E SOMMELIER ─────────────────────────── */

/* ── AZIONI RISPOSTA (copia, PDF) ───────────────────────── */
function copiaRisposta(btn) {
  const card = btn.closest('.scheda');
  const domanda = card.querySelector('.s-q b')?.textContent || '';
  const risposta = card.querySelector('.s-body')?.textContent || '';
  const testo = `${domanda}\n\n${risposta}`;
  navigator.clipboard.writeText(testo).then(() => {
    btn.textContent = '✓ Copiato';
    setTimeout(() => btn.innerHTML = '<i class=\'ph ph-copy\'></i> Copia', 2000);
  }).catch(() => {
    btn.textContent = '✗ Errore';
    setTimeout(() => btn.innerHTML = '<i class=\'ph ph-copy\'></i> Copia', 2000);
  });
}

function scaricaPDF(btn) {
  const card = btn.closest('.scheda') || btn.closest('.vista-body') || btn.closest('[class*=risultato]') || document;
  const domanda = card.querySelector('.s-q b')?.textContent || card.querySelector('h2,h3,.vista-titolo')?.textContent || 'Risposta';
  // il risultato: prova .s-body, poi altri contenitori di contenuto, mai solo la domanda
  let risposta = card.querySelector('.s-body')?.textContent
    || card.querySelector('.risultato,.vista-risultato,.s-answer')?.textContent
    || '';
  if(!risposta.trim()){
    // ultimo fallback: tutto il testo della card meno la domanda
    const tutto = (card.textContent||'').replace(domanda,'').trim();
    risposta = tutto;
  }
  const fenchips = Array.from(card.querySelectorAll('.fenchip')).map(f => f.textContent).join(', ');
  const oggi = new Date().toLocaleDateString('it-IT');
  
  // Genera HTML del PDF
  const html = `<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>${domanda.substring(0,60)}</title>
<style>
  body{font-family:Georgia,serif;max-width:600px;margin:40px auto;color:#2a2a2a;line-height:1.6}
  .logo{font-family:'Arial',sans-serif;font-size:22px;font-weight:700;color:#245979;margin-bottom:4px}
  .payoff{font-family:'Courier New',monospace;font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:#9a9090;margin-bottom:32px}
  .domanda{font-size:18px;font-weight:700;color:#2a2a2a;margin-bottom:8px}
  .fenomeni{font-family:'Courier New',monospace;font-size:10px;color:#245979;letter-spacing:.1em;text-transform:uppercase;margin-bottom:20px}
  .risposta{font-size:14px;line-height:1.8;color:#333;margin-bottom:32px}
  .footer{font-family:'Courier New',monospace;font-size:9px;color:#9a9090;border-top:1px solid #eee;padding-top:12px}
</style>
</head>
<body>
<div class="logo">Matter Bench</div>
<div class="payoff">Science & Craft</div>
<div class="domanda">${domanda}</div>
${fenchips ? `<div class="fenomeni">Fenomeni: ${fenchips}</div>` : ''}
<div class="risposta">${risposta.replace(/\n/g,'<br>')}</div>
<div class="footer">Generato da Matter Bench · ${oggi} · matter-lab.com<br>Risposta generata da AI su base scientifica — verifica con fonti professionali.</div>
</body>
</html>`;

  // Apri finestra di stampa
  const w = window.open('', '_blank');
  w.document.write(html);
  w.document.close();
  w.focus();
  setTimeout(() => w.print(), 500);
}
/* ── FINE AZIONI RISPOSTA ───────────────────────────────── */
/* ── DRINK COST (bar) e FOOD COST (bakery) ────────────── */
async function _calcolaCosto(ingredienti, cardId, rowsId, totalId){
  const card = document.getElementById(cardId);
  const rows = document.getElementById(rowsId);
  const totalNum = document.getElementById(totalId);
  if(!ingredienti || !ingredienti.length){ if(card) card.style.display='none'; return; }
  if(card) card.style.display='block';
  if(rows) rows.innerHTML='';
  let totale = 0;
  for(const ing of ingredienti){
    if(!ing.n || !ing.n.trim()) continue;
    try {
      const r = await fetch('/prezzi_mercato/'+encodeURIComponent(ing.n.toLowerCase()));
      const j = await r.json();
      const prezzo = j.risultati?.[0]?.prezzo || null;
      if(prezzo && ing.vol){
        const costo = parseFloat(prezzo) * ing.vol / 1000;
        totale += costo;
        if(rows) rows.innerHTML += `<div class="foodcost-row"><span>${esc(ing.n)}</span><span style="font-family:var(--mono);color:var(--e700)">€${costo.toFixed(2)}</span></div>`;
      } else {
        if(rows) rows.innerHTML += `<div class="foodcost-row"><span>${esc(ing.n)}</span><span style="font-family:var(--mono);color:var(--ink-muted)">—</span></div>`;
      }
    } catch(e){
      if(rows) rows.innerHTML += `<div class="foodcost-row"><span>${esc(ing.n)}</span><span style="font-family:var(--mono);color:var(--ink-muted)">—</span></div>`;
    }
  }
  if(totalNum) totalNum.textContent = totale > 0 ? `€${totale.toFixed(2)}` : '—';
}

async function aggiornDrinkCost(ingredienti){
  const salvaBtnEl = document.getElementById('salva-btn');
  if(salvaBtnEl) salvaBtnEl.style.display = localStorage.getItem('matter_token') ? 'block' : 'none';
  const card = document.getElementById('drinkcost-card');
  const rows = document.getElementById('drinkcost-rows');
  const totalNum = document.getElementById('drinkcost-total-num');
  var validi = (ingredienti||[]).filter(function(x){ return x.n && x.n.trim() && x.vol; });
  if(!validi.length){ if(card) card.style.display='none'; return; }
  if(card) card.style.display='block';
  if(rows) rows.innerHTML='<div class="foodcost-row"><span>Calcolo…</span></div>';
  try{
    var pv = parseFloat((document.getElementById('dc-prezzo')||{}).value||'0')||0;
    var r = await fetch('/v1/drink-cost', {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}),
      body:JSON.stringify({nome:'Drink', ingredienti:validi.map(function(x){return {nome:x.n, ml:x.vol};}), prezzo_vendita:pv})});
    var j = await r.json();
    // righe per voce
    if(rows){
      var voci = j.voci || [];
      rows.innerHTML = voci.map(function(v){
        var costo = (v.costo!=null)? '€'+Number(v.costo).toFixed(2) : '—';
        return '<div class="foodcost-row"><span>'+esc(v.nome||'')+'</span><span style="font-family:var(--mono);color:var(--e700)">'+costo+'</span></div>';
      }).join('');
      // riga giudizio + percentuale se c'è prezzo
      if(j.drink_cost_percentuale!=null && pv>0){
        rows.innerHTML += '<div class="foodcost-row dc-giudizio"><span>Drink cost '+j.drink_cost_percentuale+'%</span><span class="dc-verdetto dc-'+(j.giudizio||'').replace(/\s/g,'')+'">'+esc(j.giudizio||'')+'</span></div>';
      }
    }
    if(totalNum) totalNum.textContent = (j.costo_ingredienti!=null) ? '€'+Number(j.costo_ingredienti).toFixed(2) : '—';
  }catch(e){
    if(rows) rows.innerHTML='<div class="foodcost-row"><span>Costo non disponibile</span><span>—</span></div>';
    if(totalNum) totalNum.textContent='—';
  }
}

function aggiornFoodCostBak(ingredienti){
  // bakery — usa foodcost-card-bak
  _calcolaCosto(ingredienti, 'foodcost-card-bak', 'foodcost-rows-bak', 'foodcost-total-bak');
}

/* ── QUADERNO ─────────────────────────────────────────── */
function apriFormSalva(){
  document.getElementById('salva-form').classList.toggle('open');
}

async function salvaEsperimento(){
  const token = localStorage.getItem('matter_token');
  if(!token){ switchTab('auth'); return; }
  if(!_isPro()){
    try {
      const rc = await fetch('/v1/quaderno',{headers:{'Authorization':'Bearer '+token}});
      const jc = await rc.json();
      if((jc.esperimenti||[]).length >= QUAD_FREE){ apriPaywall(); return; }
    } catch(e){}
  }
  const nome = document.getElementById('salva-nome').value.trim();
  if(!nome){ document.getElementById('salva-nome').focus(); return; }
  const note = document.getElementById('salva-note').value.trim();
  const abvEl = document.querySelector('.readout-num');
  const abv = abvEl ? parseFloat(abvEl.textContent) || null : null;
  try {
    const r = await fetch('/v1/quaderno', {
      method:'POST',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},
      body: JSON.stringify({nome, note, disciplina: Matter.disciplina||'bar', abv, area_mercato:'it'})
    });
    const j = await r.json();
    if(j.id){
      document.getElementById('salva-form').classList.remove('open');
      document.getElementById('salva-nome').value='';
      document.getElementById('salva-note').value='';
      const btn = document.getElementById('salva-btn');
      if(btn){ const orig=btn.textContent; btn.textContent=_t('salvato'); setTimeout(()=>{btn.textContent=orig;},2000); }
      caricaQuaderno();
    }
  } catch(e){}
}

// ── QUADERNO: toggle Misure / Menù ──
function switchQuaderno(vista){
  if(vista==='menu'){ var _o=document.getElementById('onb-overlay'); if(_o) _o.classList.add('hidden'); }
  document.getElementById('quad-pane-misure').style.display = vista==='misure'?'':'none';
  document.getElementById('quad-pane-menu').style.display = vista==='menu'?'':'none';
  var pr=document.getElementById('quad-pane-ricette'); if(pr) pr.style.display = vista==='ricette'?'':'none';
  var pp=document.getElementById('quad-pane-palestra'); if(pp) pp.style.display = vista==='palestra'?'':'none';
  document.getElementById('qtg-misure').classList.toggle('active', vista==='misure');
  document.getElementById('qtg-menu').classList.toggle('active', vista==='menu');
  var tr=document.getElementById('qtg-ricette'); if(tr) tr.classList.toggle('active', vista==='ricette');
  var tp=document.getElementById('qtg-palestra'); if(tp) tp.classList.toggle('active', vista==='palestra');
  if(vista==='menu') caricaMenuSalvati();
  if(vista==='ricette') caricaLeMieRicette();
  if(vista==='misure') caricaStoricoMisure();
  if(vista==='palestra') caricaPalestra();
}

// ═══ PALESTRA — quiz "Livello di Competenza del Banco" (P6) ═══
var _palQuiz=[]; var _palIdx=0; var _palRisposto=false;
async function caricaPalestra(){
  try{
    var rp=await fetch('/v1/quiz/progressi', {headers:_statoHeaders()});
    var jp=await rp.json();
    var tot=jp.totale_superati||0;
    var su148=Math.min(100, Math.round((tot/148)*100));
    var fill=document.getElementById('pal-barra-fill'); if(fill) fill.style.width=su148+'%';
    var cnt=document.getElementById('pal-count'); if(cnt) cnt.textContent=tot+'/148 dominati';
  }catch(e){}
  var body=document.getElementById('pal-body');
  if(body) body.innerHTML='<div class="calc-loading">Carico le domande…</div>';
  try{
    var r=await fetch('/v1/quiz?limit=10', {headers:_statoHeaders()});
    var j=await r.json();
    _palQuiz=j.quiz||[]; _palIdx=0; _palRisposto=false;
    if(!_palQuiz.length){ if(body) body.innerHTML='<div class="quad-empty"><b>Ancora nessuna domanda</b><span>Le domande arrivano man mano. Torna tra poco.</span></div>'; return; }
    _renderQuiz();
  }catch(e){ if(body) body.innerHTML='<div class="quad-empty"><b>Errore</b><span>Riprova.</span></div>'; }
}
function _renderQuiz(){
  var body=document.getElementById('pal-body'); if(!body) return;
  if(_palIdx>=_palQuiz.length){
    body.innerHTML='<div class="pal-fine"><b>Set completato!</b><button class="calc-go" onclick="caricaPalestra()">Altre domande</button></div>';
    return;
  }
  var q=_palQuiz[_palIdx]; var e=_escV;
  _palRisposto=false;
  body.innerHTML=
    '<div class="pal-quiz">'
    + '<div class="pal-meta"><span class="pal-tipo">'+e(q.tipo||'')+'</span><span class="pal-diff">'+e(q.difficolta||'')+'</span></div>'
    + '<div class="pal-domanda">'+e(q.domanda||'')+'</div>'
    + '<div class="pal-opzioni" id="pal-opzioni">'
    +   (q.opzioni||[]).map(function(op,i){ return '<button class="pal-opz" data-op="'+e(op)+'" onclick="_rispondiQuiz(this,\''+e(String(q.id))+'\')">'+e(op)+'</button>'; }).join('')
    + '</div>'
    + '<div id="pal-esito"></div>'
    + '</div>';
}
async function _rispondiQuiz(btn, quizId){
  if(_palRisposto) return; _palRisposto=true;
  var risposta=btn.getAttribute('data-op');
  document.querySelectorAll('.pal-opz').forEach(function(b){ b.disabled=true; });
  try{
    var r=await fetch('/v1/quiz/rispondi', {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}), body:JSON.stringify({quiz_id:quizId, risposta:risposta})});
    var j=await r.json();
    var e=_escV;
    document.querySelectorAll('.pal-opz').forEach(function(b){
      var op=b.getAttribute('data-op');
      if(op===j.risposta_corretta) b.classList.add('giusta');
      else if(b===btn) b.classList.add('sbagliata');
    });
    var esito=document.getElementById('pal-esito');
    if(esito){
      esito.innerHTML='<div class="pal-verdetto '+(j.superato?'ok':'no')+'">'+(j.superato?'✓ Esatto':'✗ Non è corretta')+'</div>'
        + (j.insight?'<div class="pal-insight">'+e(j.insight)+'</div>':'')
        + '<button class="calc-go" onclick="_palProssima()">Prossima →</button>';
    }
  }catch(e){ _toast('Errore, riprova'); _palRisposto=false; document.querySelectorAll('.pal-opz').forEach(function(b){ b.disabled=false; }); }
}
function _palProssima(){ _palIdx++; if(_palIdx>=_palQuiz.length){ caricaPalestra(); } else { _renderQuiz(); } }

// #1 fascia insight-trend del Quaderno (organizer)
async function _caricaInsightQuaderno(){
  var header=document.getElementById('misure-header');
  var old=document.getElementById('quad-insight'); if(old) old.remove();
  try{
    var r=await fetch('/v1/quaderno/insight', {headers:_statoHeaders()});
    var j=await r.json();
    var ins=(j.insight||[]).slice(0,5);
    if(!ins.length) return;
    // ordino: trend prima (più urgenti), stabilità dopo
    ins.sort(function(a,b){ return (a.tipo==='trend'?0:1)-(b.tipo==='trend'?0:1); });
    var e=_escV;
    var box=document.createElement('div'); box.id='quad-insight'; box.className='quad-insight';
    box.innerHTML=ins.map(function(x){
      var cls = x.tipo==='trend' ? 'ins-trend' : 'ins-stabile';
      var ico = x.tipo==='trend' ? '📈' : '✓';
      return '<div class="quad-ins '+cls+'"><span class="quad-ins-ico">'+ico+'</span><span class="quad-ins-txt">'+e(x.testo||'')+'</span></div>';
    }).join('');
    var pane=document.getElementById('quad-pane-misure');
    if(pane) pane.insertBefore(box, pane.firstChild);
  }catch(e){}
}
// ═══ STORICO MISURE — "Le mie misure" (cuore della retention) ═══
async function caricaStoricoMisure(){
  _caricaInsightQuaderno();
  var list=document.getElementById('misure-list');
  var empty=document.getElementById('quad-misure-empty');
  var header=document.getElementById('misure-header');
  if(!list) return;
  list.innerHTML='<div class="quad-loading">Carico le tue misure…</div>';
  try{
    var r=await fetch('/v1/misure/storico', {headers:_statoHeaders()});
    var j=await r.json();
    var fen=j.fenomeni||[];
    if(header){ document.getElementById('misure-tot-n').textContent = j.totale_misure||0; header.style.display = fen.length?'':'none'; }
    if(!fen.length){ list.innerHTML=''; if(empty) empty.style.display=''; return; }
    if(empty) empty.style.display='none';
    list.innerHTML=fen.map(function(f){
      var e=_escV;
      return '<div class="misura-card" onclick="apriStoricoFenomeno(\''+e(String(f.fenomeno)).replace(/'/g,"\\'")+'\')">'
        + '<div class="misura-card-main"><div class="misura-card-nome">'+e(f.fenomeno)+'</div>'
        + '<div class="misura-card-meta">'+(f.n_misure||0)+' misure</div></div>'
        + '<div class="misura-card-val">'+e(String(f.ultimo_valore||''))+(f.unita?'<span class="misura-card-u">'+e(f.unita)+'</span>':'')+'</div>'
        + '</div>';
    }).join('');
  }catch(e){
    list.innerHTML='<div class="quad-empty"><b>Non riesco a caricare le misure</b><span>Riprova tra poco.</span></div>';
  }
}
async function apriStoricoFenomeno(fenomeno){
  _apriVista(fenomeno, '<div class="quad-loading">Carico lo storico…</div>');
  try{
    var r=await fetch('/v1/misure/storico?fenomeno='+encodeURIComponent(fenomeno), {headers:_statoHeaders()});
    var j=await r.json();
    var e=_escV;
    var serie=j.serie||[];
    var ev=j.evoluzione;
    var html='';
    if(ev && ev.da!=null && ev.a!=null){
      html+='<div class="ev-box"><div class="ev-lab">La tua evoluzione</div><div class="ev-val">'+e(String(ev.da))+(ev.unita?e(ev.unita):'')+' <span class="ev-arr">→</span> '+e(String(ev.a))+(ev.unita?e(ev.unita):'')+'</div><div class="ev-sub">'+(ev.n_misure||serie.length)+' misure nel tempo</div></div>';
    }
    html+='<div class="serie-lab">Tutte le misure</div>';
    html+=serie.map(function(m){
      var data='';
      try{ var d=new Date(m.data); data=d.toLocaleDateString('it-IT',{day:'2-digit',month:'short'}); }catch(x){}
      return '<div class="serie-row"><div class="serie-val">'+e(String(m.valore))+(m.unita?e(m.unita):'')+'</div>'
        + '<div class="serie-info">'+(m.bersaglio?'<span class="serie-bers">bersaglio '+e(m.bersaglio)+'</span>':'')+(m.nota?'<span class="serie-nota">'+e(m.nota)+'</span>':'')+'</div>'
        + '<div class="serie-data">'+data+'</div></div>';
    }).join('');
    var body=document.getElementById('vista-body'); if(body) body.innerHTML=html;
  }catch(e){
    var body=document.getElementById('vista-body'); if(body) body.innerHTML='<div class="quad-empty"><b>Errore</b><span>Riprova.</span></div>';
  }
}
// Misura rapida dal modulo home (rituale quotidiano) — riusa il form salva-misura
function apriMisuraRapida(){
  _salvaMisuraCtx = {fenomeno:'', bersaglio:'', unita:''};
  var e=_escV;
  _apriVista('Misura adesso',
    '<div class="sm-intro">Registra una misura che hai fatto al banco. La ritrovi nel Quaderno con la sua evoluzione nel tempo.</div>'
    + '<div class="sm-field"><label>Cosa hai misurato</label><input type="text" id="sm-fenomeno" placeholder="es. Temperatura impasto"></div>'
    + '<div class="sm-field"><label>Il valore</label><div class="sm-val-row"><input type="text" inputmode="decimal" id="sm-valore" placeholder="es. 24"><input type="text" id="sm-unita" class="sm-u-input" placeholder="°C" maxlength="6"></div></div>'
    + '<div class="sm-field"><label>Nota (facoltativa)</label><input type="text" id="sm-nota" placeholder="es. impasto brioche"></div>'
    + '<button class="rg-btn rg-btn-salva" style="width:100%" onclick="_salvaMisuraRapida()">Salva nel Quaderno</button>');
  setTimeout(function(){ var i=document.getElementById('sm-fenomeno'); if(i) i.focus(); }, 200);
}
async function _salvaMisuraRapida(){
  var fenomeno=(document.getElementById('sm-fenomeno')||{}).value||'';
  var valore=(document.getElementById('sm-valore')||{}).value||'';
  var unita=(document.getElementById('sm-unita')||{}).value||'';
  var nota=(document.getElementById('sm-nota')||{}).value||'';
  if(!fenomeno.trim()){ _toast('Scrivi cosa hai misurato'); return; }
  if(!valore.trim()){ _toast('Inserisci il valore'); return; }
  try{
    var r=await fetch('/v1/misure/salva', {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}),
      body:JSON.stringify({fenomeno:fenomeno.trim(), valore:valore.trim(), unita:unita.trim(), nota:nota.trim()})});
    var j=await r.json();
    if(j && j.ok){ _toast('✓ Misura salvata nel Quaderno'); chiudiVista(); if(typeof caricaHome==='function') caricaHome(); }
    else { _toast('Non riuscita, riprova'); }
  }catch(e){ _toast('Non riuscita, riprova'); }
}
// Misura rapida dal Mirino (con fenomeno noto)
function apriSalvaMisura(fenomeno, bersaglio, unita){
  _salvaMisuraCtx = {fenomeno:fenomeno||'', bersaglio:bersaglio||'', unita:unita||''};
  var e=_escV;
  _apriVista('Salva la tua misura',
    '<div class="sm-intro">Hai misurato <b>'+e(fenomeno||'un valore')+'</b>'+(bersaglio?' (bersaglio '+e(bersaglio)+')':'')+'. Salva quello che hai letto: vedrai come cambia nel tempo.</div>'
    + '<div class="sm-field"><label>Il valore che hai misurato</label><div class="sm-val-row"><input type="text" inputmode="decimal" id="sm-valore" placeholder="es. 24"><span class="sm-u">'+e(unita||'')+'</span></div></div>'
    + '<div class="sm-field"><label>Nota (facoltativa)</label><input type="text" id="sm-nota" placeholder="es. impasto brioche"></div>'
    + '<button class="rg-btn rg-btn-salva" style="width:100%" onclick="_salvaMisura()">Salva nel Quaderno</button>');
  setTimeout(function(){ var i=document.getElementById('sm-valore'); if(i) i.focus(); }, 200);
}
var _salvaMisuraCtx = {};
async function _salvaMisura(){
  var valore=(document.getElementById('sm-valore')||{}).value||'';
  var nota=(document.getElementById('sm-nota')||{}).value||'';
  if(!valore.trim()){ _toast('Inserisci il valore misurato'); return; }
  var ctx=_salvaMisuraCtx||{};
  try{
    var r=await fetch('/v1/misure/salva', {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}),
      body:JSON.stringify({fenomeno:ctx.fenomeno||'Misura', valore:valore.trim(), unita:ctx.unita||'', bersaglio:ctx.bersaglio||'', nota:nota.trim()})});
    var j=await r.json();
    if(j && j.ok){ _toast('✓ Misura salvata nel Quaderno'); chiudiVista(); }
    else { _toast('Non riuscita, riprova'); }
  }catch(e){ _toast('Non riuscita, riprova'); }
}

// Carica "Le mie ricette" salvate (FLUSSO 1)
async function caricaLeMieRicette(){
  var list=document.getElementById('quad-ricette-list');
  var empty=document.getElementById('quad-ricette-empty');
  if(!list) return;
  list.innerHTML='<div class="quad-loading">Carico le tue ricette…</div>';
  try{
    var r=await fetch('/v1/ricette/le-mie', {headers: _statoHeaders()});
    var j=await r.json();
    var ricette=j.ricette||[];
    if(!ricette.length){ list.innerHTML=''; if(empty) empty.style.display=''; return; }
    if(empty) empty.style.display='none';
    list.innerHTML=ricette.map(function(r){
      var d=r.dati||{};
      var nIng=(d.ingredienti||[]).length;
      return '<div class="quad-ric-card" onclick=\'riapriRicettaSalvata('+JSON.stringify(JSON.stringify(r)).replace(/'/g,"&#39;")+')\'>'
        +'<div class="quad-ric-nome">'+_esc(r.nome||d.nome||'Ricetta')+'</div>'
        +'<div class="quad-ric-meta">'+(nIng?nIng+' ingredienti':'')+(d.disciplina?' · '+_esc(d.disciplina):'')+'</div>'
        +'<button class="quad-ric-rimuovi" onclick=\'event.stopPropagation();rimuoviRicettaSalvata("'+_esc(r.ricetta_id)+'")\'>Rimuovi</button>'
        +'</div>';
    }).join('');
  }catch(e){
    list.innerHTML='<div class="quad-empty"><b>Non riesco a caricare le ricette</b><span>Riprova tra poco.</span></div>';
  }
}
function riapriRicettaSalvata(rjson){
  try{
    var r=(typeof rjson==='string')?JSON.parse(rjson):rjson;
    var dati=r.dati||r;
    if(typeof mostraRicettaGen==='function'){ mostraRicettaGen(dati, r.ricetta_id); return; }
    // fallback: mostro nella lista ricette di Scopri
    switchTab('scopri');
    if(typeof _renderRicette==='function'){
      _renderRicette([dati]);
      var el=document.getElementById('ricette-list');
      if(el) el.scrollIntoView({behavior:'smooth'});
    }
  }catch(e){ console.warn('riapri ricetta', e); }
}
async function rimuoviRicettaSalvata(id){
  if(!id) return;
  try{
    await fetch('/v1/ricette/rimuovi', {method:'POST', headers: _statoHeaders({'Content-Type':'application/json'}), body: JSON.stringify({ricetta_id:id})});
    caricaLeMieRicette();
  }catch(e){ console.warn('rimuovi ricetta', e); }
}

/* ═══ SCHEDA RICETTA GENERATA con azioni (Salva / Chiedi / Food Cost) ═══
   Regola d'oro: nessun vicolo cieco. Ogni ricetta offre almeno queste 3 azioni. */
var _ricettaGenCorrente = null;
var _ctxChat = null;  // contesto ricetta/menu per la chat (FLUSSO 2)

// FLUSSO 3 — riconosce se l'utente vuole CREARE una ricetta (non fare una domanda scientifica)
// ═══ P0.3 — Schermata CREA: i 3 modi di creare, come card grandi (non un tutorial) ═══
function apriCrea(){
  var html=
    '<div class="crea-intro">Tre modi per creare. Scegli da dove parti.</div>'
    + '<button class="crea-card" onclick="_creaDaIngredienti()">'
    +   '<div class="crea-card-ico"><svg viewBox="0 0 24 24" fill="none" width="26" height="26"><path d="M4 7h16M4 12h16M4 17h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></div>'
    +   '<div class="crea-card-txt"><div class="crea-card-t">Da ingredienti</div><div class="crea-card-d">Scrivi cosa hai, ti do la ricetta coi numeri</div></div>'
    +   '<span class="crea-card-arr">→</span></button>'
    + '<button class="crea-card" onclick="chiudiVista();setTimeout(function(){apriFlavour();},120)">'
    +   '<div class="crea-card-ico"><svg viewBox="0 0 24 24" fill="none" width="26" height="26"><circle cx="7" cy="7" r="3" stroke="currentColor" stroke-width="2"/><circle cx="17" cy="17" r="3" stroke="currentColor" stroke-width="2"/><path d="M9.5 9.5l5 5" stroke="currentColor" stroke-width="2"/></svg></div>'
    +   '<div class="crea-card-txt"><div class="crea-card-t">Da abbinamento</div><div class="crea-card-d">Composti aromatici condivisi e affinità molecolare</div></div>'
    +   '<span class="crea-card-arr">→</span></button>'
    + '<button class="crea-card" onclick="chiudiVista();setTimeout(function(){apriMenuBuilder();},120)">'
    +   '<div class="crea-card-ico"><svg viewBox="0 0 24 24" fill="none" width="26" height="26"><rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" stroke-width="2"/><path d="M8 9h8M8 13h8M8 17h5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></div>'
    +   '<div class="crea-card-txt"><div class="crea-card-t">Da menu</div><div class="crea-card-d">Costruisci un menu completo dai tuoi ingredienti</div></div>'
    +   '<span class="crea-card-arr">→</span></button>'
    + '<button class="crea-card" onclick="chiudiVista();setTimeout(function(){creaMenuDaFoto();},120)">'
    +   '<div class="crea-card-ico"><svg viewBox="0 0 24 24" fill="none" width="26" height="26"><rect x="3" y="6" width="18" height="14" rx="2" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="13" r="4" stroke="currentColor" stroke-width="2"/><path d="M8 6l1.5-2h5L16 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></div>'
    +   '<div class="crea-card-txt"><div class="crea-card-t">Da foto</div><div class="crea-card-d">Fotografa gli ingredienti, Matter li riconosce e trova gli abbinamenti</div></div>'
    +   '<span class="crea-card-arr">→</span></button>';
  _apriVista('Crea', html);
}
function _creaDaIngredienti(){
  var html=
    '<div class="crea-intro">Scrivi gli ingredienti o il piatto che vuoi. Ti do la ricetta con dosi, procedimento e numeri-bersaglio.</div>'
    + '<div class="crea-input-wrap">'
    +   '<textarea class="crea-input" id="crea-ing-input" placeholder="es. branzino, finocchio e arancia — oppure: una carbonara"></textarea>'
    +   '<button class="rg-btn rg-btn-salva" style="width:100%;margin-top:12px" onclick="_creaGenera()">Genera la ricetta →</button>'
    + '</div>';
  _apriVista('Da ingredienti', html);
  setTimeout(function(){ var i=document.getElementById('crea-ing-input'); if(i) i.focus(); }, 200);
}
function _creaGenera(){
  var v=(document.getElementById('crea-ing-input')||{}).value||'';
  if(!v.trim()) return;
  generaRicettaDaTesto(v.trim());
}

// ═══ COMMUNITY — "Vetrina del Banco" (feed sola lettura, contatto fuori app) ═══
let _vetrinaOffset = 0;
let _vetrinaBusy = false;
async function apriVetrina(){
  _vetrinaOffset = 0;
  _apriVista('Vetrina del Banco',
    '<div class="vetr-intro">Ricette vere da chi sta al banco. Clona quelle che ti servono, connettiti con chi le ha fatte.</div>'
    + '<div class="vetr-feed" id="vetr-feed"></div>'
    + '<button class="vetr-more" id="vetr-more" onclick="_vetrinaCarica()" style="display:none">Carica altre</button>');
  _vetrinaCarica();
}
async function _vetrinaCarica(){
  if(_vetrinaBusy) return; _vetrinaBusy=true;
  var feed=document.getElementById('vetr-feed');
  var more=document.getElementById('vetr-more');
  if(_vetrinaOffset===0 && feed){ feed.innerHTML='<div class="vetr-loading">Carico la vetrina…</div>'; }
  if(more && _vetrinaOffset>0){ more.textContent='Caricamento…'; more.disabled=true; }
  try{
    var lang=(typeof _lang!=='undefined'?_lang:'it');
    var r=await fetch('/v1/community/feed?lingua='+lang+'&offset='+_vetrinaOffset);
    var j=await r.json();
    var ricette=j.ricette||[];
    if(_vetrinaOffset===0){ feed.innerHTML=''; }
    if(!ricette.length && _vetrinaOffset===0){
      feed.innerHTML='<div class="vetr-empty"><b>La vetrina è ancora vuota</b><span>Pubblica tu la prima ricetta dal Quaderno.</span></div>';
      if(more) more.style.display='none';
      _vetrinaBusy=false; return;
    }
    feed.insertAdjacentHTML('beforeend', ricette.map(_vetrinaCard).join(''));
    _vetrinaOffset += ricette.length;
    // tre stati del bottone
    if(more){
      more.disabled=false;
      if(ricette.length>=10){
        more.textContent='Carica altre'; more.style.display='';
      } else {
        // feed finito
        more.textContent='Hai visto tutte le ricette ('+_vetrinaOffset+')';
        more.style.display='';
        more.disabled=true;
        more.classList.add('vetr-more-fine');
      }
    }
  }catch(e){
    if(feed && _vetrinaOffset===0) feed.innerHTML='<div class="vetr-empty"><b>Non riesco a caricare la vetrina</b><span>Riprova tra poco.</span></div>';
    if(more){ more.textContent='Riprova'; more.disabled=false; }
  }
  _vetrinaBusy=false;
}
function _vetrinaCard(r){
  var e=_escV;
  var d=r.dati||{};
  var nIng=(d.ingredienti||[]).length;
  var autore = r.dal_team ? 'Team Matter Bench' : (r.autore||'Anonimo');
  var teamBadge = r.dal_team ? '<span class="vetr-team">Team Matter Bench</span>' : '';
  var post = r.postazione ? '<span class="vetr-post">'+e(r.postazione)+'</span>' : '';
  var rid = e(String(r.id));
  var dev = e(String(r.autore_device||''));
  return '<div class="vetr-card">'
    + '<div class="vetr-card-head"><div class="vetr-card-nome">'+e(r.nome||'Ricetta')+'</div>'+teamBadge+'</div>'
    + '<div class="vetr-card-meta">'+e(autore)+(post?' · ':'')+post+(nIng?' · '+nIng+' ingredienti':'')+'</div>'
    + '<div class="vetr-card-actions">'
    +   '<button class="vetr-btn vetr-btn-clona" onclick="_vetrinaClona(\''+rid+'\',this)">Clona nel Quaderno</button>'
    + (r.dal_team ? '' : '<button class="vetr-btn vetr-btn-connetti" onclick="_vetrinaConnetti(\''+dev+'\')">Connetti</button>')
    + '</div></div>';
}
async function _vetrinaClona(id, btn){
  if(btn){ btn.disabled=true; btn.textContent='Clono…'; }
  try{
    var r=await fetch('/v1/community/clona', {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}), body:JSON.stringify({id_pubblica:id})});
    var j=await r.json();
    if(btn){ btn.textContent = (j&&j.ok!==false) ? '✓ Nel tuo Quaderno' : 'Riprova'; btn.classList.add('fatto'); }
  }catch(e){ if(btn){ btn.disabled=false; btn.textContent='Riprova'; } }
}
async function _vetrinaConnetti(dev){
  if(!dev) return;
  try{
    var r=await fetch('/v1/community/profilo?device_id='+encodeURIComponent(dev));
    var j=await r.json();
    if(!j || j.trovato===false || !j.contatto_link){
      _apriVista('Connetti', '<div class="vetr-empty"><b>Contatto non disponibile</b><span>Questo autore non ha ancora impostato un modo per essere contattato.</span></div>');
      return;
    }
    var e=_escV;
    var tipo = (j.contatto_link.indexOf('wa.me')>=0||j.contatto_link.indexOf('whatsapp')>=0)?'WhatsApp'
             : (j.contatto_link.indexOf('t.me')>=0)?'Telegram'
             : (j.contatto_link.indexOf('linkedin')>=0)?'LinkedIn'
             : (j.contatto_link.indexOf('instagram')>=0)?'Instagram':'il contatto';
    _apriVista('Connetti con '+(j.nome||'autore'),
      '<div class="vetr-profilo">'
      + '<div class="vetr-prof-nome">'+e(j.nome||'Autore')+'</div>'
      + (j.postazione?'<div class="vetr-prof-post">'+e(j.postazione)+'</div>':'')
      + '<a class="vetr-prof-cta" href="'+e(j.contatto_link)+'" target="_blank" rel="noopener">Scrivi su '+tipo+' →</a>'
      + '<div class="vetr-prof-nota">Il contatto avviene fuori da Matter. Ti apriamo '+tipo+'.</div>'
      + '</div>');
  }catch(e){}
}
// Pubblica una ricetta nella Vetrina (dalla scheda ricetta o dal Quaderno)
async function pubblicaInVetrina(dati, ricettaId){
  var prof = _getProfiloLocale();
  if(!prof.nome || !prof.postazione){ apriProfiloMio(dati, ricettaId); return; }
  try{
    var lang=(typeof _lang!=='undefined'?_lang:'it');
    var r=await fetch('/v1/community/pubblica', {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}),
      body:JSON.stringify({nome:dati.nome, dati:dati, autore_nome:prof.nome, autore_postazione:prof.postazione, ricetta_id:ricettaId||'', lingua:lang})});
    var j=await r.json();
    _toast(j&&j.ok!==false ? '✓ Pubblicata nella Vetrina del Banco' : 'Non riuscita, riprova');
  }catch(e){ _toast('Non riuscita, riprova'); }
}
function _getProfiloLocale(){
  try{ return JSON.parse(localStorage.getItem('matter_profilo')||'{}'); }catch(e){ return {}; }
}
function apriProfiloMio(datiPost, ridPost){
  var prof=_getProfiloLocale();
  var e=_escV;
  var html=
    '<div class="vetr-intro">Come ti vedono gli altri professionisti nella Vetrina. Il contatto è un link esterno (WhatsApp, Telegram, LinkedIn, Instagram): le conversazioni avvengono fuori da Matter.</div>'
    + '<div class="prof-field"><label>Nome</label><input type="text" id="prof-nome" value="'+e(prof.nome||'')+'" placeholder="Come ti chiami"></div>'
    + '<div class="prof-field"><label>Postazione</label><input type="text" id="prof-post" value="'+e(prof.postazione||'')+'" placeholder="es. barman, pizzaiolo, pastry chef"></div>'
    + '<div class="prof-field"><label>Tipo di contatto</label><select id="prof-ctipo">'
    +   '<option value="whatsapp">WhatsApp</option><option value="telegram">Telegram</option><option value="linkedin">LinkedIn</option><option value="instagram">Instagram</option>'
    + '</select></div>'
    + '<div class="prof-field"><label>Contatto</label><input type="text" id="prof-cval" value="'+e(prof.contatto_valore||'')+'" placeholder="numero, @username o URL"></div>'
    + '<button class="rg-btn rg-btn-salva" style="width:100%" onclick="_salvaProfilo('+(datiPost?'true':'false')+')">Salva profilo'+(datiPost?' e pubblica':'')+'</button>';
  _apriVista('Il tuo profilo', html);
  if(prof.contatto_tipo){ setTimeout(function(){ var s=document.getElementById('prof-ctipo'); if(s) s.value=prof.contatto_tipo; }, 100); }
  _profiloPendingPost = datiPost ? {dati:datiPost, rid:ridPost} : null;
}
let _profiloPendingPost = null;
async function _salvaProfilo(poi){
  var nome=(document.getElementById('prof-nome')||{}).value||'';
  var post=(document.getElementById('prof-post')||{}).value||'';
  var ctipo=(document.getElementById('prof-ctipo')||{}).value||'whatsapp';
  var cval=(document.getElementById('prof-cval')||{}).value||'';
  if(!nome.trim()||!post.trim()){ _toast('Inserisci nome e postazione'); return; }
  var prof={nome:nome.trim(), postazione:post.trim(), contatto_tipo:ctipo, contatto_valore:cval.trim()};
  localStorage.setItem('matter_profilo', JSON.stringify(prof));
  try{
    await fetch('/v1/community/profilo', {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}),
      body:JSON.stringify(prof)});
  }catch(e){}
  _toast('✓ Profilo salvato');
  if(poi && _profiloPendingPost){
    var pp=_profiloPendingPost; _profiloPendingPost=null;
    pubblicaInVetrina(pp.dati, pp.rid);
  } else { chiudiVista(); }
}
function _toast(msg){
  var t=document.getElementById('mf-toast');
  if(!t){ t=document.createElement('div'); t.id='mf-toast'; t.className='mf-toast'; document.body.appendChild(t); }
  t.textContent=msg; t.classList.add('show');
  setTimeout(function(){ t.classList.remove('show'); }, 2600);
}

// REGOLA 1 — dal pulsante nella chat: genera la scheda ricetta vera (il Lab crea)
async function _generaDaChat(richiesta){
  var disc = localStorage.getItem('matter_station') || 'cucina';
  aggiungiThinking(); setBusy(true);
  try{
    var r=await fetch('/v1/genera-ricetta',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({richiesta:richiesta, disciplina:disc})});
    var j=await r.json();
    rimuoviThinking(); setBusy(false);
    if(j && (j.nome||j.ingredienti)){ mostraRicettaGen(j); }
  }catch(e){ rimuoviThinking(); setBusy(false); }
}
function _isIntentoRicetta(q){
  var s=(q||'').toLowerCase().trim();
  // "fammi/crea/prepara/facciamo/dammi/inventa una ricetta [con/di/per] ..."
  return /\b(fammi|crea|creami|prepara|preparami|facciamo|fai|dammi|inventa|proponimi|suggerisci|voglio|vorrei)\b[^.?!]*\bricett[ae]\b/.test(s)
      || /\bricetta (con|di|per|a base di)\b/.test(s)
      || /^(una |un )?(ricetta|piatto|cocktail)\b.*\b(con|di|a base di)\b/.test(s);
}
async function generaRicettaDaTesto(q){
  if(!_isPro()){ const usate=_getDomande(); if(usate>=FREE_LIMIT){ apriPaywall(); return; } }
  _apriVista('Creo la ricetta…', '<div class="calc-loading" style="padding:40px;text-align:center">Sto creando la ricetta…</div>');
  var disc = localStorage.getItem('matter_station') || 'cucina';
  try{
    var r=await fetch('/v1/genera-ricetta',{method:'POST',headers:_statoHeaders({'Content-Type':'application/json'}),
      body:JSON.stringify({richiesta:q, disciplina:disc})});
    var j=await r.json();
    _incDomande();
    if(j && j.errore==='non_trovata'){
      var bd=document.getElementById('vista-body'); if(bd) bd.innerHTML='<div class="quad-empty"><b>Piatto non trovato</b><span>'+_escV(j.messaggio||'Prova un nome classico o cerca nel Ricettario.')+'</span></div>';
      return;
    }
    if(j && (j.nome || j.ingredienti)){ mostraRicettaGen(j); }
    else { var bd2=document.getElementById('vista-body'); if(bd2) bd2.innerHTML='<div class="quad-empty"><b>Non riesco a creare la ricetta</b><span>Riprova, o chiedila all\'Assistente.</span></div>'; }
  }catch(e){
    var bd3=document.getElementById('vista-body'); if(bd3) bd3.innerHTML='<div class="quad-empty"><b>Errore di rete</b><span>Riprova.</span></div>';
  }
}
// versione della chat che bypassa il riconoscimento intento (per il fallback)
function chiediTestoRaw(q){
  aggiungiThinking(); setBusy(true);
  const history=_chatHistory.slice(-_HISTORY_MAX);
  const _tok=localStorage.getItem('matter_token')||'';
  fetch('/chiedi',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({domanda:q, history, token:_tok, contesto:_ctxChat||null})})
    .then(r=>r.json()).then(j=>{
      _incDomande(); rimuoviThinking(); setBusy(false);
      if(typeof renderRisp==='function' && j) renderRisp(j, q);
    }).catch(()=>{ rimuoviThinking(); setBusy(false); });
}
function mostraRicettaGen(dati, ricettaIdSalvata){
  _ricettaGenCorrente = dati;
  var e=_escV;
  var ing=(dati.ingredienti||[]).map(function(x){
    if(typeof x==='string') return '<li>'+e(x)+'</li>';
    var q=(x.quantita!=null?x.quantita:'')+(x.unita?' '+x.unita:'');
    return '<li><span class="rg-ing-n">'+e(x.nome||'')+'</span>'+(q?'<span class="rg-ing-q">'+e(q)+'</span>':'')+'</li>';
  }).join('');
  var proc=(dati.procedimento||[]).map(function(p,i){
    var t=(typeof p==='string')?p:(p.testo||'');
    var n=(typeof p==='object'&&p.n)?p.n:(i+1);
    return '<div class="rg-step"><span class="rg-step-n">'+e(String(n))+'</span><span class="rg-step-t">'+e(t)+'</span></div>';
  }).join('');
  var numeri=(dati.numeri && Object.keys(dati.numeri).length)
    ? '<div class="rg-numeri"><div class="rg-numeri-lab">Numeri bersaglio</div>'+Object.entries(dati.numeri).map(function(kv){return '<div class="rg-num-row"><span class="rg-num-k">'+e(kv[0])+'</span><span class="rg-num-v">'+e(kv[1])+'</span></div>';}).join('')+'</div>'
    : '';
  var critico=dati.punto_critico?'<div class="rg-critico"><span class="rg-critico-lab">Qui sbagliano quasi tutti</span> '+e(dati.punto_critico)+'</div>':'';
  var salvato = !!ricettaIdSalvata;
  if(salvato){ _ricettaGenCorrente._ricetta_id = ricettaIdSalvata; }
  // A4: se il backend ha tenuto il piatto fedele (fusione assurda richiesta), mostro la nota
  var notaContratto = dati._nota_contratto || (dati.ricetta && dati.ricetta._nota_contratto) || '';
  var boxContratto = (dati.corretta_da_contratto && notaContratto)
    ? '<div class="rg-contratto"><div class="rg-contratto-ico">✓</div><div class="rg-contratto-txt">'+e(notaContratto)+'</div></div>'
    : '';
  var html=
    '<div class="rg-scheda">'
    + boxContratto
    + (ing?'<div class="rg-sec"><div class="rg-sec-lab">Ingredienti</div><ul class="rg-ing">'+ing+'</ul></div>':'')
    + numeri
    + (proc?'<div class="rg-sec"><div class="rg-sec-lab">Procedimento</div>'+proc+'</div>':'')
    + critico
    + '<div class="rg-azioni">'
    +   '<button class="rg-btn rg-btn-salva'+(salvato?' fatto':'')+'" id="rg-btn-salva" onclick="salvaRicettaGen(this)">'+(salvato?'✓ Salvata':'Salva nel Quaderno')+'</button>'
    +   '<button class="rg-btn rg-btn-chiedi" onclick="chiediSuRicetta()">Chiedi su questa ricetta</button>'
    +   '<button class="rg-btn rg-btn-cost" onclick="foodCostRicetta()">Food Cost</button>'
    +   '<button class="rg-btn rg-btn-vetrina" onclick="pubblicaInVetrina(_ricettaGenCorrente, _ricettaGenCorrente&&_ricettaGenCorrente._ricetta_id)">Pubblica nella Vetrina del Banco</button>'
    + '</div>'
    + '<div class="rg-continua"><button class="rg-cont-btn" onclick="_ricettaFenomeni()">Vedi fenomeni attivi</button><button class="rg-cont-btn" onclick="_ricettaInMenu()">Apri in Menu Lab</button></div>'
    + '</div>';
  _apriVista(dati.nome || 'Ricetta', html);
  // #4 immagine ricetta (foto o blueprint della famiglia) above the fold
  if(ricettaIdSalvata){ _caricaImmagineRicetta(ricettaIdSalvata); }
}
var _BLUEPRINT_FAMIGLIE=['acidita','affumicatura','coagulazione','conservazione','cristallizzazione','diluizione','distillazione','emulsione','estrazione','fermentazione','gas','gelificazione','impasto','osmosi','ossidazione','reazione-termica'];
async function _caricaImmagineRicetta(id){
  try{
    var r=await fetch('/v1/ricetta/'+encodeURIComponent(id)+'/immagine', {headers:_statoHeaders()});
    var j=await r.json();
    var box=document.createElement('div'); box.className='rg-immagine';
    if(j.tipo==='foto' && j.url){
      box.innerHTML='<img src="'+_escV(j.url)+'" alt="" loading="lazy">'+(j.autore?'<span class="rg-img-credito">foto: '+_escV(j.autore)+'</span>':'');
    } else if(j.tipo==='blueprint' && j.famiglia && _BLUEPRINT_FAMIGLIE.indexOf(j.famiglia)>=0){
      box.innerHTML='<img src="/static/blueprints/'+_escV(j.famiglia)+'.svg" alt="Blueprint '+_escV(j.famiglia)+'" loading="lazy"><span class="rg-img-fam">'+_escV(j.famiglia)+'</span>';
    } else { return; }
    var sch=document.querySelector('#vista-body .rg-scheda') || document.querySelector('.rg-scheda');
    if(sch) sch.insertBefore(box, sch.firstChild);
  }catch(e){}
}
async function salvaRicettaGen(btn){
  var d=_ricettaGenCorrente; if(!d) return;
  if(d._ricetta_id){ btn.textContent='✓ Già salvata'; return; }
  btn.disabled=true; btn.textContent='Salvo…';
  try{
    var r=await fetch('/v1/ricette/salva', {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}), body:JSON.stringify({nome:d.nome||'Ricetta', dati:d})});
    var j=await r.json();
    if(j && j.ok){ d._ricetta_id=j.ricetta_id; btn.textContent='✓ Salvata nel Quaderno'; btn.disabled=false; btn.classList.add('fatto'); }
    else { btn.textContent='Riprova'; btn.disabled=false; }
  }catch(e){ btn.textContent='Riprova'; btn.disabled=false; }
}
function _ricettaFenomeni(){
  var d=_ricettaGenCorrente; if(!d) return;
  var fen=(d.fenomeni||[]);
  if(fen.length){ var f=fen[0]; var id=(typeof f==='object'?f.id:f); chiudiVista(); apriNodo(id, (typeof f==='object'?f.nome:'')||''); }
  else { _toast('Nessun fenomeno collegato a questa ricetta'); }
}
function _ricettaInMenu(){
  chiudiVista();
  if(typeof apriMenuBuilder==='function') apriMenuBuilder();
}
function chiediSuRicetta(){
  var d=_ricettaGenCorrente; if(!d) return;
  _ctxChat = {tipo:'ricetta', nome:d.nome, ingredienti:(d.ingredienti||[]).map(function(x){return typeof x==='string'?x:x.nome;}), fenomeni:d.fenomeni||[], punto_critico:d.punto_critico||''};
  chiudiVista();
  switchTab('chiedi');
  var inp=document.getElementById('ask-input');
  if(inp){ inp.placeholder='Chiedi su "'+(d.nome||'questa ricetta')+'"…'; inp.focus(); }
  var banner=document.getElementById('chat-ctx-banner');
  if(banner){ banner.textContent='Stai chiedendo su: '+(d.nome||'ricetta'); banner.style.display='block'; }
}
async function foodCostRicetta(){
  var d=_ricettaGenCorrente; if(!d) return;
  // l'endpoint lavora dagli ingredienti: non serve salvare prima
  var ingredienti=(d.ingredienti||[]).map(function(x){
    if(typeof x==='string') return {nome:x, quantita:'', unita:''};
    return {nome:(x.nome||''), quantita:String(x.quantita!=null?x.quantita:''), unita:(x.unita||'')};
  }).filter(function(x){return x.nome;});
  if(!ingredienti.length){ alert('Questa ricetta non ha ingredienti con dosi da calcolare.'); return; }
  var porzioni = d.porzioni || 4;
  _fcIngredienti = ingredienti; _fcPorzioni = porzioni;
  _mostraFoodCostPanel(null, true); // loading
  try{
    var r=await fetch('/v1/ricette/food-cost',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ingredienti:ingredienti, porzioni:porzioni})});
    var j=await r.json();
    _mostraFoodCostPanel(j, false);
  }catch(e){
    _mostraFoodCostPanel({errore:true}, false);
  }
}
var _fcIngredienti=[], _fcPorzioni=4;
async function _fcConPrezzo(){
  var prezzo=parseFloat((document.getElementById('fc-prezzo-input').value||'').replace(',','.'));
  if(isNaN(prezzo)) return;
  try{
    var r=await fetch('/v1/ricette/food-cost',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ingredienti:_fcIngredienti, porzioni:_fcPorzioni, prezzo_vendita:prezzo})});
    var j=await r.json();
    var box=document.getElementById('fc-pct-esito');
    if(box && j.food_cost_pct!=null){
      var pct=j.food_cost_pct;
      var col = pct<=30 ? 'var(--teal,#12545D)' : (pct<=38 ? 'var(--terra,#C77B3F)' : '#B23B3B');
      box.innerHTML='<div class="fc-pct-val" style="color:'+col+'">'+pct+'%</div><div class="fc-pct-lab">food cost sul tuo prezzo di '+prezzo+'€</div>';
      box.style.display='block';
    }
  }catch(e){}
}
function _mostraFoodCostPanel(j, loading){
  var e=_escV;
  var html;
  if(loading){
    html='<div class="fc-loading">Calcolo il food cost…</div>';
  } else if(!j || j.errore){
    html='<div class="fc-loading">Non riesco a calcolare il costo ora. Riprova.</div>';
  } else {
    var dett=(j.dettaglio||[]).map(function(x){
      var q=(x.quantita_g!=null?x.quantita_g+'g':(x.quantita||''));
      return '<div class="fc-row"><span class="fc-row-n">'+e(x.ingrediente||x.nome||'')+'</span><span class="fc-row-q">'+e(String(q))+'</span><span class="fc-row-c">'+e(String(x.costo_porzione_eur!=null?x.costo_porzione_eur+' €':''))+'</span></div>';
    }).join('');
    var sugg=j.prezzi_vendita_suggeriti||{};
    var suggRows=Object.keys(sugg).map(function(k){
      var lab=k.replace('fc_','food cost ').replace('pct','%');
      return '<div class="fc-sugg-row"><span class="fc-sugg-lab">'+e(lab)+'</span><span class="fc-sugg-v">'+e(String(sugg[k]))+' €</span></div>';
    }).join('');
    html=
      '<div class="fc-hero"><div class="fc-hero-lab">costo per porzione</div><div class="fc-hero-val">'+e(String(j.costo_per_porzione_eur!=null?j.costo_per_porzione_eur:'—'))+' €</div><div class="fc-hero-sub">costo totale '+e(String(j.costo_totale_eur))+' € · '+e(String(j.porzioni||_fcPorzioni))+' porzioni</div></div>'
      + (dett?'<div class="fc-sec"><div class="fc-sec-lab">Dettaglio per porzione</div>'+dett+'</div>':'')
      + (suggRows?'<div class="fc-sec"><div class="fc-sec-lab">Prezzi di vendita suggeriti</div>'+suggRows+'</div>':'')
      + '<div class="fc-sec"><div class="fc-sec-lab">Il tuo prezzo di vendita</div><div class="fc-prezzo-row"><input type="text" inputmode="decimal" id="fc-prezzo-input" placeholder="es. 12" oninput="_fcConPrezzo()"><span class="fc-prezzo-u">€</span></div><div class="fc-pct-esito" id="fc-pct-esito" style="display:none"></div></div>'
      + '<div class="fc-nota">'+e(j.nota||'Prezzi orientativi ISMEA — per il costo reale coi tuoi fornitori usa Cifra.')+'</div>';
  }
  _apriVista('Food Cost' + (_ricettaGenCorrente&&_ricettaGenCorrente.nome?' · '+_ricettaGenCorrente.nome:''), html);
}

function caricaMenuSalvati(){
  // v1: i menù stanno in localStorage (poi sync backend/Cifra in v2)
  const list = document.getElementById('menu-list');
  let menus = [];
  try { menus = JSON.parse(localStorage.getItem('matter_menus')||'[]'); } catch(e){}
  if(!menus.length){ list.innerHTML=''; return; }
  list.innerHTML = '<div class="menu-list-lab">I tuoi menù</div>' + menus.map((m,i)=>
    `<div class="menu-card" onclick="apriMenu(${i})">
      <div class="menu-card-nome">${_esc(m.nome||'Drink list')}</div>
      <div class="menu-card-meta">${(m.voci||[]).length} voci · ${m.tipo||'drink list'}</div>
    </div>`).join('');
}

// ══════════ BUILDER CREA MENÙ (Drink List v1) ══════════
let _mbStep = 1;
let _mbVoci = [];      // voci selezionate per il menù
let _mbTemplate = 'editorial';

// categoria di menù scelta (drink_list, pizzeria, ristorante, carta_vini, carta_birre)
let _mbCategoria = 'drink_list';
let _mbCategoriaLabel = 'Drink list';
const _MB_CAT_CFG = {
  drink_list:  {label:'Drink list',        disc:'bar',    min:8,  max:12, targetGuida:'diluizione 20-28%', unita:'drink'},
  pizzeria:    {label:'Menù pizzeria',      disc:'bakery', min:6,  max:14, targetGuida:'idratazione 60-65%', unita:'pizze'},
  ristorante:  {label:'Menù ristorante',    disc:'cucina', min:8,  max:20, targetGuida:'cuore 52-58°C',      unita:'piatti'},
  carta_vini:  {label:'Carta dei vini',     disc:'cucina', min:10, max:40, targetGuida:'servizio 8-18°C',    unita:'etichette'},
  carta_birre: {label:'Carta delle birre',  disc:'bar',    min:6,  max:20, targetGuida:'servizio 4-8°C',     unita:'birre'},
};
function mbScegliCategoria(cat, label){
  _mbCategoria = cat;
  _mbCategoriaLabel = label;
  document.getElementById('mm-title').textContent = label;
  document.getElementById('mm-cat-lab').textContent = label;
  var _onb=document.getElementById('onb-overlay'); if(_onb) _onb.classList.add('hidden');
  // carta vini: passa dalla FILOSOFIA (brief → filo conduttore → crea)
  if(cat==='carta_vini'){ apriCartaFilosofia(); return; }
  // carta birre: dritto al builder
  if(cat==='carta_birre'){ creaMenu(); return; }
  document.getElementById('menu-modo').classList.remove('hidden');
}
function chiudiModo(){ document.getElementById('menu-modo').classList.add('hidden'); }

function creaMenu(){
  var _onb=document.getElementById('onb-overlay'); if(_onb) _onb.classList.add('hidden');
  _mbStep = 1; _mbVoci = []; _mbTemplate = 'editorial';
  document.getElementById('mb-nome').value = '';
  document.getElementById('mb-locale').value = '';
  _mbMostraStep(1);
  document.getElementById('menu-builder').classList.remove('hidden');
}
function chiudiBuilder(){ document.getElementById('menu-builder').classList.add('hidden'); }

// ══════════ MENÙ DA FOTO INGREDIENTI (feature killer) — Step 1 ══════════
let _mfFiles = [];       // File scelti
let _mfIngredienti = []; // ingredienti riconosciuti/confermati

function creaMenuDaFoto(){
  // la carta vini/birre non parte dalle foto ingredienti
  if(_mbCategoria==='carta_vini' || _mbCategoria==='carta_birre'){ creaMenu(); return; }
  var _onb=document.getElementById('onb-overlay'); if(_onb) _onb.classList.add('hidden');
  _mfFiles = []; _mfIngredienti = [];
  document.getElementById('mf-thumbs').innerHTML = '';
  document.getElementById('mf-analizza').style.display = 'none';
  _mfMostraFase('foto');
  document.getElementById('menu-foto').classList.remove('hidden');
}
function chiudiMenuFoto(){ document.getElementById('menu-foto').classList.add('hidden'); }
function _mfMostraFase(f){
  ['foto','loading','valida','proposte','lab'].forEach(x=>{
    var el=document.getElementById('mf-fase-'+x);
    if(!el) return;
    if(x===f){
      el.style.display='block';
      // transizione d'entrata: la fase non appare di colpo, entra con un lieve scorrimento
      el.classList.remove('mf-fase-enter');
      void el.offsetWidth; // reflow per riavviare l'animazione
      el.classList.add('mf-fase-enter');
    } else {
      el.style.display='none';
      el.classList.remove('mf-fase-enter');
    }
  });
  // titolo dinamico dell'header per fase (bug: prima restava "Parti dagli ingredienti")
  var titoli = {
    foto:_L({it:'Parti dagli ingredienti',en:'Start from ingredients',es:'Empieza por los ingredientes'}),
    loading:'Sto leggendo il banco…',
    valida:'Conferma cosa hai',
    proposte:'Piatti realizzabili',
    lab:_L({it:'Dai i numeri a questa voce',en:'Give this item its numbers',es:'Dale los números a este elemento'})
  };
  var t = document.getElementById('mf-title');
  if(t && titoli[f]) t.textContent = titoli[f];
  // filo narrativo: evidenzio lo step corrente e quelli superati
  var filo = document.getElementById('mf-filo');
  if(filo){
    var ordine = ['foto','valida','proposte','lab'];
    // durante il loading tengo evidenziato lo step di destinazione logico
    var fase = (f==='loading') ? 'valida' : f;
    var idx = ordine.indexOf(fase);
    filo.querySelectorAll('.mf-filo-step').forEach(function(s){
      var si = ordine.indexOf(s.getAttribute('data-fase'));
      s.classList.toggle('done', si < idx);
      s.classList.toggle('active', si === idx);
    });
  }
}

function mfFileScelti(ev){
  const nuovi = Array.from(ev.target.files||[]).slice(0, 6 - _mfFiles.length);
  _mfFiles = _mfFiles.concat(nuovi).slice(0,6);
  const cont = document.getElementById('mf-thumbs');
  cont.innerHTML = _mfFiles.map((f,i)=>{
    const url = URL.createObjectURL(f);
    return `<div class="mf-thumb"><img src="${url}"><button onclick="mfRimuoviFoto(${i})">×</button></div>`;
  }).join('');
  document.getElementById('mf-analizza').style.display = _mfFiles.length?'block':'none';
}
function mfRimuoviFoto(i){ _mfFiles.splice(i,1); mfFileScelti({target:{files:[]}}); }

// ── SCANNER CODICE A BARRE (prodotti confezionati via Open Food Facts) ──
var _mfBarcodeStream = null, _mfBarcodeLoop = null, _mfBarcodeDetector = null;
async function mfApriBarcode(){
  var ov = document.getElementById('mf-scanner');
  var stato = document.getElementById('mf-scanner-stato');
  ov.classList.remove('hidden');
  // se il browser non supporta BarcodeDetector, resta solo l'inserimento manuale
  if(!('BarcodeDetector' in window)){
    stato.textContent = _L({it:'Fotocamera non disponibile su questo browser — digita il codice qui sotto.',en:'Camera not available on this browser — type the code below.',es:'Cámara no disponible en este navegador — escribe el código abajo.'});
    var v = document.getElementById('mf-scanner-video'); if(v) v.style.display='none';
    document.getElementById('mf-barcode-input').focus();
    return;
  }
  try{
    _mfBarcodeDetector = new BarcodeDetector({formats:['ean_13','ean_8','upc_a','upc_e','code_128']});
    _mfBarcodeStream = await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}});
    var video = document.getElementById('mf-scanner-video');
    video.srcObject = _mfBarcodeStream; await video.play();
    stato.textContent = _L({it:'Inquadra il codice a barre del prodotto',en:'Point the camera at the product barcode',es:'Enfoca el código de barras del producto'});
    _mfBarcodeScanLoop(video);
  }catch(e){
    stato.textContent = _L({it:'Non riesco ad aprire la fotocamera — digita il codice qui sotto.',en:'Cannot open the camera — type the code below.',es:'No puedo abrir la cámara — escribe el código abajo.'});
    document.getElementById('mf-barcode-input').focus();
  }
}
async function _mfBarcodeScanLoop(video){
  if(!_mfBarcodeDetector || !video) return;
  try{
    var codes = await _mfBarcodeDetector.detect(video);
    if(codes && codes.length){
      var raw = (codes[0].rawValue||'').replace(/\D/g,'');
      if(raw.length>=8){ mfChiudiBarcode(); _mfBarcodeCerca(raw); return; }
    }
  }catch(e){}
  _mfBarcodeLoop = requestAnimationFrame(function(){ _mfBarcodeScanLoop(video); });
}
function mfChiudiBarcode(){
  if(_mfBarcodeLoop){ cancelAnimationFrame(_mfBarcodeLoop); _mfBarcodeLoop=null; }
  if(_mfBarcodeStream){ _mfBarcodeStream.getTracks().forEach(function(t){t.stop();}); _mfBarcodeStream=null; }
  var ov=document.getElementById('mf-scanner'); if(ov) ov.classList.add('hidden');
}
function mfBarcodeManuale(){
  var v = (document.getElementById('mf-barcode-input').value||'').replace(/\D/g,'');
  if(v.length<8){ document.getElementById('mf-scanner-stato').textContent='Servono almeno 8 cifre.'; return; }
  mfChiudiBarcode(); _mfBarcodeCerca(v);
}
async function _mfBarcodeCerca(codice){
  var stato = document.getElementById('mf-scanner-stato');
  try{
    var r = await fetch('/v1/menu/barcode/'+encodeURIComponent(codice));
    var j = await r.json();
    if(!j.trovato){
      _mfToast(_L({it:'Prodotto non trovato. Puoi inserirlo a mano tra gli ingredienti.',en:'Product not found. You can add it manually to the ingredients.',es:'Producto no encontrado. Puedes añadirlo a mano entre los ingredientes.'}));
      return;
    }
    // aggiungo il prodotto come ingrediente "confezionato" alla lista validata
    _mfIngredienti = _mfIngredienti || [];
    _mfIngredienti.push({ nome: j.nome, categoria: 'confezionato', sel: true, _barcode: codice, _allergeni: j.allergeni||[] });
    _mfToast('✓ "'+j.nome+'" aggiunto'+(j.allergeni&&j.allergeni.length?' · allergeni: '+j.allergeni.join(', '):''));
    // se sono ancora nella fase foto, porto l'utente alla validazione per confermare
    if(typeof _mfRenderValida==='function'){ _mfRenderValida(); _mfMostraFase('valida'); }
  }catch(e){
    _mfToast('Open Food Facts non raggiungibile. Riprova o inserisci a mano.');
  }
}
function _mfToast(msg){
  var t = document.getElementById('mf-toast');
  if(!t){ t=document.createElement('div'); t.id='mf-toast'; t.className='mf-toast'; document.body.appendChild(t); }
  t.textContent = msg; t.classList.add('show');
  clearTimeout(t._h); t._h = setTimeout(function(){ t.classList.remove('show'); }, 3200);
}

async function mfAnalizza(){
  if(!_mfFiles.length) return;
  _mfMostraFase('loading');
  _mfTeatro();
  const b64s = await Promise.all(_mfFiles.map(f=>new Promise(res=>{
    const r=new FileReader(); r.onload=()=>res(r.result); r.readAsDataURL(f);
  })));
  try{
    const tok = localStorage.getItem('matter_token')||'';
    const r = await fetch('/v1/menu/riconosci-ingredienti', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({immagini_b64: b64s, token: tok})
    });
    const j = await r.json();
    // A5: nuovo contratto — stato, sicuri, da_confermare, puoi_inserire_a_mano
    _mfDaConfermare = (j.da_confermare||[]).map(x=>({nome:(typeof x==='string'?x:x.nome), sel:false}));
    var sicuri = j.sicuri || j.ingredienti || [];  // fallback al vecchio campo
    _mfIngredienti = sicuri.map(x=>({nome:(typeof x==='string'?x:x.nome), categoria:(typeof x==='object'?x.categoria:'')||'', sel:true}));
    _mfMessaggio = j.messaggio || '';
    _mfRenderValida();
    _mfMostraFase('valida');
  }catch(e){
    // mai vicolo cieco: mostro comunque la fase valida col campo a mano
    _mfIngredienti = []; _mfDaConfermare = [];
    _mfMessaggio = 'Non sono riuscito a leggere le foto. Aggiungi gli ingredienti a mano qui sotto.';
    _mfRenderValida();
    _mfMostraFase('valida');
  }
}
var _mfDaConfermare = [];
var _mfMessaggio = '';

function _mfTeatro(){
  const steps = _L({it:['Riconosco gli ingredienti','Controllo le corrispondenze','Cerco connessioni aromatiche','Cerco tecniche applicabili','Preparo le combinazioni'],en:['Recognizing ingredients','Checking matches','Finding aroma connections','Finding applicable techniques','Preparing combinations'],es:['Reconociendo ingredientes','Comprobando coincidencias','Buscando conexiones aromáticas','Buscando técnicas aplicables','Preparando combinaciones']});
  const cont = document.getElementById('mf-load-steps');
  cont.innerHTML = '';
  steps.forEach((s,i)=> setTimeout(()=>{
    if(document.getElementById('mf-fase-loading').style.display==='none') return;
    cont.innerHTML += `<div class="mf-load-step">✓ ${s}</div>`;
  }, i*700));
}

function _mfRenderValida(){
  const cont = document.getElementById('mf-ingredienti');
  var html='';
  // messaggio (fallback / nessun riconoscimento)
  if(_mfMessaggio){ html += '<div class="mf-msg">'+_esc(_mfMessaggio)+'</div>'; }
  // ingredienti sicuri (confermati)
  if(_mfIngredienti.length){
    html += '<div class="mf-sez-lab">Riconosciuti</div>';
    html += _mfIngredienti.map((ing,i)=>
      '<div class="mf-ing '+(ing.sel?'sel':'off')+'" onclick="mfToggleIng('+i+')">'
      + '<span class="mf-ing-nome">'+_esc(ing.nome)+'</span>'
      + (ing.categoria?'<span class="mf-ing-cat">'+_esc(ing.categoria)+'</span>':'')
      + '<span class="mf-ing-x">'+(ing.sel?'✓':'+')+'</span></div>').join('');
  }
  // da confermare: chip "Vedo X, è corretto?" (tap = conferma, mai tastiera)
  if(_mfDaConfermare.length){
    html += '<div class="mf-sez-lab mf-sez-conferma">Vedo questi, sono corretti?</div>';
    html += '<div class="mf-chips">'
      + _mfDaConfermare.map((c,i)=>
          '<span class="mf-chip '+(c.sel?'sel':'')+'" onclick="mfConfermaChip('+i+')">'
          + _esc(c.nome)+' <span class="mf-chip-ico">'+(c.sel?'✓':'+')+'</span></span>').join('')
      + '</div>';
  }
  if(!_mfIngredienti.length && !_mfDaConfermare.length && !_mfMessaggio){
    html = '<div class="mb-vuoto">Non ho riconosciuto ingredienti. Aggiungili a mano qui sotto.</div>';
  }
  cont.innerHTML = html;
}
function mfConfermaChip(i){
  // tap su un chip "da confermare" → lo promuove a ingrediente confermato
  var c = _mfDaConfermare[i]; if(!c) return;
  _mfIngredienti.push({nome:c.nome, categoria:'', sel:true});
  _mfDaConfermare.splice(i,1);
  _mfRenderValida();
}
function mfToggleIng(i){ _mfIngredienti[i].sel = !_mfIngredienti[i].sel; _mfRenderValida(); }
function mfAggiungiIng(){
  const nome = prompt('Nome dell\'ingrediente:');
  if(!nome||!nome.trim()) return;
  _mfIngredienti.push({nome:nome.trim(), categoria:'', sel:true});
  _mfRenderValida();
}
async function mfConferma(){
  const confermati = _mfIngredienti.filter(x=>x.sel).map(x=>x.nome);
  if(!confermati.length){ alert(_L({it:'Conferma almeno un ingrediente.',en:'Confirm at least one ingredient.',es:'Confirma al menos un ingrediente.'})); return; }
  _mfMostraFase('loading');
  document.getElementById('mf-load-steps').innerHTML = '<div class="mf-load-step">✓ Costruisco voci di menu realizzabili coi tuoi ingredienti</div>';
  try{
    const r = await fetch('/v1/menu/costruisci', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ingredienti: confermati, disciplina: (localStorage.getItem('matter_station')||'cucina')})
    });
    const j = await r.json();
    _mfProposte = j.voci || [];
    _mfRenderProposte(j);
    _mfMostraFase('proposte');
  }catch(e){
    alert('Non sono riuscito a costruire le voci. Riprova.');
    _mfMostraFase('valida');
  }
}

let _mfProposte = [];
function _mfRenderProposte(j){
  const cont = document.getElementById('mf-proposte');
  if(!_mfProposte.length){
    cont.innerHTML = '<div class="mb-vuoto">Non ho trovato voci realizzabili con questi ingredienti. Puoi comunque creare voci manualmente dal builder.</div>';
    return;
  }
  cont.innerHTML = _mfProposte.map((v,i)=>{
    const ing = (v.ingredienti||[]).join(' · ');
    const fen = (v.fenomeni||[]).map(f=>`<span class="mf-piatto-fen">${_esc(f)}</span>`).join('');
    const prontaBadge = v.pronta
      ? '<span class="mf-badge molecole">ricetta completa</span>'
      : '<span class="mf-badge esplora">ricetta in arrivo</span>';
    return `<div class="mf-piatto">
      <div class="mf-piatto-head">
        <div class="mf-piatto-nome">${_esc(v.piatto||'Piatto')}</div>
        ${v.tecnica?`<div class="mf-piatto-tecnica">${_esc(v.tecnica)}</div>`:''}
      </div>
      <div class="mf-piatto-ing">${_esc(ing)}</div>
      ${v.perche?`<div class="mf-piatto-perche"><span class="mf-piatto-perche-lab">Perché</span> ${_esc(v.perche)}</div>`:''}
      ${fen?`<div class="mf-piatto-fenomeni">${fen}</div>`:''}
      <div class="mf-piatto-foot">
        ${prontaBadge}
        <button class="mf-prop-btn" onclick="mfVaiAlLaboratorio(${i})">Porta al laboratorio →</button>
      </div>
    </div>`;
  }).join('');
}

// Mini-grafo delle connessioni: gli ingredienti come nodi, le relazioni come linee che si disegnano.
// Mostra che Matter TROVA una relazione, non la inventa. Solo i nodi della proposta, non un grafo caotico.
function _mfGrafoConnessioni(ingredienti, esplorativa){
  var n = ingredienti.length;
  if(n < 2) return '';
  var W = 260, H = 64, r = 5;
  var cx = W/2, cy = H/2;
  // dispongo i nodi in orizzontale, equidistanti
  var pts = [];
  for(var k=0;k<n;k++){
    var x = (n===1) ? cx : (30 + k*(W-60)/(n-1));
    pts.push({x:x, y:cy});
  }
  var col = esplorativa ? 'var(--ink-muted)' : 'var(--target-green)';
  var svg = '<svg class="mf-grafo" viewBox="0 0 '+W+' '+H+'" width="100%" height="'+H+'" aria-hidden="true">';
  // linee tra nodi consecutivi (e per il triangolo, chiudo il cerchio)
  var links = [];
  for(var a=0;a<n;a++) for(var b=a+1;b<n;b++) links.push([a,b]);
  links.forEach(function(pair){
    var p1=pts[pair[0]], p2=pts[pair[1]];
    var len = Math.hypot(p2.x-p1.x, p2.y-p1.y);
    svg += '<line class="mf-grafo-link" x1="'+p1.x+'" y1="'+p1.y+'" x2="'+p2.x+'" y2="'+p2.y+'" '
        + 'stroke="'+col+'" stroke-width="1.5" stroke-dasharray="'+len+'" stroke-dashoffset="'+len+'"/>';
  });
  pts.forEach(function(pt){
    svg += '<circle class="mf-grafo-nodo" cx="'+pt.x+'" cy="'+pt.y+'" r="'+r+'" fill="'+col+'"/>';
  });
  svg += '</svg>';
  return svg;
}
function mfVaiAlLaboratorio(i){
  const p = _mfProposte[i];
  _mfPropCorrente = p;
  document.getElementById('mf-lab-ing').textContent = p.ingredienti.join(' · ');
  document.getElementById('mf-lab-nome').value = '';
  document.getElementById('mf-lab-nome').placeholder = 'Trovo un nome…';
  _mfSuggerisciNome(p);
  document.getElementById('mf-lab-stato').textContent = '';
  document.getElementById('mf-lab-stato').className = 'mf-lab-stato';
  // carico le tecniche pertinenti alla disciplina dell'utente
  _mfTecnicaScelta = null;
  _mfCaricaTecniche();
  // Mirino in stato NEUTRO finché l'utente non sceglie una tecnica
  // (bug: prima mostrava il target di categoria — es. "cuore 52-58°C" — anche su card diverse)
  var box = document.getElementById('mf-lab-mirino');
  renderMirinoNeutro(box);
  _mfMostraFase('lab');
}
let _mfPropCorrente = null;

async function _mfSuggerisciNome(p){
  var campo = document.getElementById('mf-lab-nome');
  // le voci dal nuovo endpoint /costruisci hanno già un nome piatto: usalo subito
  if(p && p.piatto && !campo.value.trim()){
    campo.value = p.piatto;
    campo.placeholder = _L({it:'Dai un nome alla voce',en:'Name this item',es:'Dale un nombre al elemento'});
    var h = document.getElementById('mf-nome-hint');
    if(h) h.style.display = 'block';
    return;
  }
  var cfg = _MB_CAT_CFG[_mbCategoria] || _MB_CAT_CFG.drink_list;
  try{
    var r = await fetch('/v1/menu/naming', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ingredienti:p.ingredienti, disciplina:cfg.disc, tecnica:(_mfTecnicaScelta?_mfTecnicaScelta.nome:'')})});
    var j = await r.json();
    // pre-compilo SOLO se l'utente non ha già scritto qualcosa
    if(j.nome && !campo.value.trim()){
      campo.value = j.nome;
      campo.placeholder = _L({it:'Dai un nome alla voce',en:'Name this item',es:'Dale un nombre al elemento'});
      // segnale discreto che è un suggerimento
      var hint = document.getElementById('mf-nome-hint');
      if(hint) hint.style.display = 'block';
    } else {
      campo.placeholder = _L({it:'Dai un nome alla voce (es. Strawberry Sour)',en:'Name this item (e.g. Strawberry Sour)',es:'Dale un nombre (ej. Strawberry Sour)'});
    }
  }catch(e){
    campo.placeholder = _L({it:'Dai un nome alla voce (es. Strawberry Sour)',en:'Name this item (e.g. Strawberry Sour)',es:'Dale un nombre (ej. Strawberry Sour)'});
  }
}

async function _mfCaricaTecniche(){
  var cont = document.getElementById('mf-lab-tecniche');
  if(!cont) return;
  var cfg = _MB_CAT_CFG[_mbCategoria] || _MB_CAT_CFG.drink_list;
  var disc = cfg.disc;
  cont.innerHTML = '<div class="mf-tec-lab">Carico le tecniche…</div>';
  try{
    var r = await fetch('/v1/menu/tecniche', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({disciplina: disc})});
    var j = await r.json();
    var tecniche = (j.tecniche||[]).slice(0,8);
    if(!tecniche.length){ cont.innerHTML=''; return; }
    _mfTecniche = tecniche;
    cont.innerHTML = '<div class="mf-tec-lab">Tecniche che puoi usare — tocca per tarare il Mirino sul suo numero</div>' +
      tecniche.map(function(t,idx){
        return '<button class="mf-tec" onclick="mfScegliTecnica('+idx+')">'+
          '<span class="mf-tec-nome">'+_esc(t.nome)+'</span>'+
          '<span class="mf-tec-num">'+_esc((t.numeri||'').split('·')[0].trim())+'</span></button>';
      }).join('');
  }catch(e){ cont.innerHTML=''; }
}
let _mfTecniche = [];
function mfScegliTecnica(idx){
  var t = _mfTecniche[idx];
  if(!t) return;
  // taro il Mirino sul numero-bersaglio della tecnica scelta
  var box = document.getElementById('mf-lab-mirino');
  renderMirino(box, _mfPropCorrente.ingredienti.join(' · '), t.numeri);
  document.querySelectorAll('.mf-tec').forEach(function(b,i){ b.classList.toggle('active', i===idx); });
  _mfTecnicaScelta = t;
}
let _mfTecnicaScelta = null;

function mfValidaVoce(){
  // controllo se il mirino è stato misurato (feedback presente)
  var box = document.getElementById('mf-lab-mirino');
  var misurato = box && box.querySelector('.mirino-feedback');
  var st = document.getElementById('mf-lab-stato');
  if(misurato){
    st.textContent = '✓ Voce verificata al banco';
    st.className = 'mf-lab-stato ok';
    _mfVoceValidata = true;
  } else {
    st.textContent = _L({it:'Misura la diluizione col Mirino per verificare la voce (oppure aggiungila come non verificata).',en:'Measure dilution with the Mirino to verify the item (or add it as unverified).',es:'Mide la dilución con el Mirino para verificar el elemento (o añádelo como no verificado).'});
    st.className = 'mf-lab-stato warn';
  }
}
let _mfVoceValidata = false;

function mfAggiungiAlMenu(){
  var nome = document.getElementById('mf-lab-nome').value.trim();
  if(!nome){ document.getElementById('mf-lab-nome').focus(); return; }
  var p = _mfPropCorrente;
  // creo/aggiorno un menù "da foto" in localStorage con questa voce
  var cfg = _MB_CAT_CFG[_mbCategoria] || _MB_CAT_CFG.drink_list;
  var voce = {
    _src: 'foto'+Date.now(),
    nome: nome,
    target: _mfTecnicaScelta ? _mfTecnicaScelta.numeri : (_mfVoceValidata ? cfg.targetGuida : ''),
    tecnica: _mfTecnicaScelta ? _mfTecnicaScelta.nome : '',
    ingredienti: p.ingredienti,
    stato: _mfVoceValidata ? 'verified' : 'unverified'
  };
  // aggiungo al "menù in costruzione" foto (bozza in memoria + persistito)
  _mfVociMenu = _mfVociMenu || [];
  _mfVociMenu.push(voce);
  _mfVoceValidata = false;
  _mfTecnicaScelta = null;
  // feedback e torno alle proposte per aggiungere altre voci
  var st = document.getElementById('mf-lab-stato');
  st.textContent = '✓ "'+nome+'" aggiunta al menù ('+_mfVociMenu.length+' voci). Scegli un\'altra combinazione o finalizza.';
  st.className = 'mf-lab-stato ok';
  // conferma visiva sul bottone stesso (chiude il ciclo: l'azione ha prodotto qualcosa)
  var btn = document.querySelector('.mf-lab-add');
  if(btn){
    var testoOrig = btn.textContent;
    btn.textContent = '✓ Aggiunto al menù';
    btn.classList.add('mf-add-done');
    setTimeout(function(){ btn.textContent = testoOrig; btn.classList.remove('mf-add-done'); }, 800);
  }
  setTimeout(function(){ _mfMostraFase('proposte'); _mfAggiornaFinalizza(); }, 900);
}
let _mfVociMenu = [];

function _mfAggiornaFinalizza(){
  var bar = document.getElementById('mf-finalizza-bar');
  if(!bar) return;
  if(_mfVociMenu.length){
    bar.style.display = 'flex';
    document.getElementById('mf-finalizza-count').textContent = _mfVociMenu.length + (_mfVociMenu.length===1?' voce':' voci');
  } else bar.style.display = 'none';
}

function mfFinalizzaMenu(){
  if(!_mfVociMenu.length) return;
  // passo le voci al builder Crea Menù (step grafica): riuso _mbVoci + builder step 3
  _mbVoci = _mfVociMenu.map(function(v){ return {_src:v._src, nome:v.nome, target:v.target, stato:v.stato, ingredienti:v.ingredienti, tecnica:v.tecnica}; });
  // PRIMA della grafica: mostro il profilo del menù (schermata "IL TUO MENÙ")
  _mostraProfiloMenu();
}

// Analizza il menù costruito: voci, ingredienti totali/riutilizzati, basi condivise, allergeni.
function _analizzaProfiloMenu(voci){
  var conteggio = {};       // ingrediente → in quante voci compare
  var totVoci = voci.length;
  var verificate = 0;
  voci.forEach(function(v){
    if(v.stato==='verified') verificate++;
    var visti = {};
    (v.ingredienti||[]).forEach(function(ing){
      var k = (ing||'').toLowerCase().trim(); if(!k||visti[k]) return; visti[k]=1;
      conteggio[k] = (conteggio[k]||0)+1;
    });
  });
  var tuttiIng = Object.keys(conteggio);
  // ingredienti riutilizzati = presenti in 2+ voci (basi condivise, meno scarti)
  var riutilizzati = tuttiIng.filter(function(k){ return conteggio[k]>=2; })
                             .sort(function(a,b){ return conteggio[b]-conteggio[a]; });
  var allerg = (typeof allergeniMenu==='function') ? allergeniMenu(voci) : [];
  return {
    totVoci: totVoci,
    verificate: verificate,
    totIngredienti: tuttiIng.length,
    riutilizzati: riutilizzati,   // array di nomi
    conteggio: conteggio,
    allergeni: allerg
  };
}

function _mostraProfiloMenu(){
  var voci = _mbVoci || [];
  var pr = _analizzaProfiloMenu(voci);
  _trackFunnel('photo_menu', {voci: pr.totVoci, ingredienti: pr.totIngredienti});
  if(!window._ahaTracked){ window._ahaTracked=true; _trackFunnel('activation', {via:'foto_menu'}); }
  var ov = document.getElementById('menu-profilo');
  // costruisco l'overlay una volta sola
  if(!ov){
    ov = document.createElement('div');
    ov.id = 'menu-profilo';
    ov.className = 'menu-profilo-ov hidden';
    document.body.appendChild(ov);
  }
  // riepilogo ingredienti riutilizzati (le "basi condivise": efficienza, meno scarti)
  var basiHtml = pr.riutilizzati.length
    ? '<div class="mp-basi-lista">' + pr.riutilizzati.slice(0,8).map(function(k){
        return '<span class="mp-base">'+_esc(k)+' <b>×'+pr.conteggio[k]+'</b></span>';
      }).join('') + '</div>'
    : '<div class="mp-basi-vuoto">Nessun ingrediente condiviso tra le voci — ogni preparazione è indipendente.</div>';
  var allergHtml = pr.allergeni.length
    ? '<div class="mp-allerg-lista">' + pr.allergeni.map(function(a){
        return '<span class="mp-allerg">'+(typeof numeroAllergene==='function'?numeroAllergene(a)+' · ':'')+_esc(a)+'</span>';
      }).join('') + '</div>'
    : '<div class="mp-basi-vuoto">Nessun allergene rilevato automaticamente.</div>';

  ov.innerHTML =
    '<div class="mp-box">'
    + '<div class="mp-head">'
    +   '<div class="mp-eyebrow">Il tuo menù</div>'
    +   '<button class="mp-close" onclick="chiudiProfiloMenu()">✕</button>'
    + '</div>'
    + '<div class="mp-title">Ecco cosa hai costruito</div>'
    // tre numeri-chiave
    + '<div class="mp-stats">'
    +   '<div class="mp-stat"><div class="mp-stat-n">'+pr.totVoci+'</div><div class="mp-stat-l">'+(pr.totVoci===1?'voce':'voci')+'</div></div>'
    +   '<div class="mp-stat"><div class="mp-stat-n">'+pr.totIngredienti+'</div><div class="mp-stat-l">ingredienti</div></div>'
    +   '<div class="mp-stat"><div class="mp-stat-n">'+pr.verificate+'</div><div class="mp-stat-l">verificate</div></div>'
    + '</div>'
    // basi condivise
    + '<div class="mp-sez-lab">Basi condivise</div>'
    + '<div class="mp-sez-sub">Ingredienti usati in più preparazioni: meno acquisti, meno scarti.</div>'
    + basiHtml
    // allergeni
    + '<div class="mp-sez-lab">Allergeni del menù</div>'
    + allergHtml
    // food cost — gancio Cifra (bloccato)
    + '<div class="mp-cifra">'
    +   '<div class="mp-cifra-row"><span class="mp-cifra-lab">Food cost del menù</span><span class="mp-cifra-lock">🔒 Cifra</span></div>'
    +   '<div class="mp-cifra-sub">Sai se ci guadagni? Calcola food cost e margini con Cifra.</div>'
    + '</div>'
    // azioni
    + '<button class="mp-cta" onclick="_profiloVaiGrafica()">Crea la carta grafica →</button>'
    + '<button class="mp-cta-sec" onclick="chiudiProfiloMenu()">Torna al laboratorio</button>'
    + '</div>';
  ov.classList.remove('hidden');
}
function chiudiProfiloMenu(){ var ov=document.getElementById('menu-profilo'); if(ov) ov.classList.add('hidden'); }
function _profiloVaiGrafica(){
  chiudiProfiloMenu();
  var cfg = _MB_CAT_CFG[_mbCategoria] || _MB_CAT_CFG.drink_list;
  document.getElementById('mb-nome').value = cfg.label;
  chiudiMenuFoto();
  _mbTemplate = 'editorial';
  document.getElementById('menu-builder').classList.remove('hidden');
  _mbMostraStep(3); // le voci ci sono già
}


function _mbMostraStep(n){
  _mbStep = n;
  [1,2,3].forEach(s=> document.getElementById('mb-step-'+s).style.display = s===n?'block':'none');
  const cfg = _MB_CAT_CFG[_mbCategoria] || _MB_CAT_CFG.drink_list;
  const titoli = {1:_L({it:'Nuovo · ',en:'New · ',es:'Nuevo · '})+cfg.label, 2:_L({it:'Componi la carta',en:'Build the menu',es:'Compón la carta'}), 3:_L({it:'Stile della carta',en:'Menu style',es:'Estilo de la carta'})};
  document.getElementById('mb-step-title').textContent = titoli[n];
  document.getElementById('mb-next').style.display = n<3 ? '' : 'none';
  if(n===2) _mbCaricaValidati();
}

function mbAvanti(){
  if(_mbStep===1){
    const nome = document.getElementById('mb-nome').value.trim();
    if(!nome){ document.getElementById('mb-nome').focus(); return; }
    _mbMostraStep(2);
  } else if(_mbStep===2){
    if(!_mbVoci.length){ alert(_L({it:'Aggiungi almeno una voce alla carta.',en:'Add at least one item to the menu.',es:'Añade al menos un elemento a la carta.'})); return; }
    _mbMostraStep(3);
  }
}

// carica gli esperimenti validati dal Quaderno (le misure salvate)
function _mbCaricaValidati(){
  const cont = document.getElementById('mb-validati');
  let misure = [];
  try { misure = JSON.parse(localStorage.getItem('matter_quaderno')||'[]'); } catch(e){}
  // trasformo le misure salvate in voci candidate; ognuna ha uno stato di validazione
  if(!misure.length){
    cont.innerHTML = '<div class="mb-vuoto">Non hai ancora esperimenti salvati nel Quaderno. Puoi aggiungere voci manualmente qui sotto — appariranno come <b>non verificate</b> finché non le misuri.</div>';
    _mbAggiornaEquilibrio(); return;
  }
  cont.innerHTML = '<div class="mb-val-lab">Dai tuoi esperimenti validati</div>' + misure.map((m,i)=>{
    const nome = m.nome || m.fenomeno || ('Preparazione '+(i+1));
    const target = m.target || m.valore || '';
    const inMenu = _mbVoci.some(v=>v._src==='quad'+i);
    return `<div class="mb-vcand ${inMenu?'sel':''}" onclick="mbToggleVoce('quad${i}','${_esc(nome).replace(/'/g,"")}','${_esc(target).replace(/'/g,"")}',true)">
      <div class="mb-vcand-info"><span class="mb-vcand-nome">${_esc(nome)}</span>
      ${target?`<span class="mb-vcand-tgt">${_esc(target)}</span>`:''}</div>
      <div class="mb-vcand-stato verified">✓ verificato</div>
      <div class="mb-vcand-check">${inMenu?'✓':'+'}</div>
    </div>`;
  }).join('');
  _mbAggiornaEquilibrio();
}

function mbToggleVoce(src, nome, target, verificato){
  const idx = _mbVoci.findIndex(v=>v._src===src);
  if(idx>=0) _mbVoci.splice(idx,1);
  else _mbVoci.push({_src:src, nome, target, stato: verificato?'verified':'unverified'});
  _mbCaricaValidati();
}

function mbAggiungiManuale(){
  const nome = prompt('Nome della voce (es. Negroni Sbagliato):');
  if(!nome||!nome.trim()) return;
  _mbVoci.push({_src:'man'+Date.now(), nome:nome.trim(), target:'', stato:'unverified'});
  _mbCaricaValidati();
}

// EQUILIBRIO DELLA CARTA (il valore di Matter, non un generatore qualunque)
function _mbAggiornaEquilibrio(){
  const box = document.getElementById('mb-equilibrio');
  const n = _mbVoci.length;
  const verif = _mbVoci.filter(v=>v.stato==='verified').length;
  if(!n){ box.innerHTML=''; return; }
  const cfg = _MB_CAT_CFG[_mbCategoria] || _MB_CAT_CFG.drink_list;
  let msg = '';
  if(n < cfg.min) msg = `Hai <b>${n}</b> ${n===1?'voce':'voci'}. Per ${cfg.label.toLowerCase()} equilibrata te ne servono <b>${cfg.min}-${cfg.max}</b>.`;
  else if(n <= cfg.max) msg = `<b>${n} voci</b> — una carta ben dimensionata.`;
  else msg = `<b>${n} voci</b> — carta ampia. Valuta se snellire per non confondere il cliente.`;
  const nonVerif = n - verif;
  box.innerHTML = `<div class="mb-eq-riga">${msg}</div>` +
    (nonVerif>0 ? `<div class="mb-eq-warn">⚠ ${nonVerif} ${nonVerif===1?'voce non verificata':'voci non verificate'} al banco. Puoi pubblicarle, ma senza il sigillo “verificato da Matter”.</div>` : `<div class="mb-eq-ok">✓ Tutte le voci sono verificate al banco.</div>`);
}

function mbScegliTemplate(t){
  _mbTemplate = t;
  document.querySelectorAll('.mb-tpl').forEach(b=> b.classList.toggle('active', b.dataset.tpl===t));
}

function mbGenera(){
  const nome = document.getElementById('mb-nome').value.trim();
  const locale = document.getElementById('mb-locale').value.trim();
  const menu = {nome, locale, tipo:_mbCategoriaLabel, categoria:_mbCategoria, template:_mbTemplate, voci:_mbVoci, creato: Date.now()};
  // salvo in localStorage (v1)
  let menus = [];
  try { menus = JSON.parse(localStorage.getItem('matter_menus')||'[]'); } catch(e){}
  menus.unshift(menu);
  localStorage.setItem('matter_menus', JSON.stringify(menus));
  chiudiBuilder();
  apriAnteprima(menu);
}

function apriMenu(i){
  let menus=[]; try{ menus=JSON.parse(localStorage.getItem('matter_menus')||'[]'); }catch(e){}
  if(menus[i]) apriAnteprima(menus[i]);
}

// ANTEPRIMA GRAFICA del menù + export (Pro)
function apriAnteprima(menu){
  const ov = document.getElementById('menu-anteprima');
  const tpl = menu.template || 'editorial';
  const voci = menu.voci || [];
  _maMenuCorrente = menu;
  // VISTA CLIENTE: elegante, solo nome + ingredienti descrittivi
  const corpoCliente = voci.map(v=>{
    const sigillo = v.stato==='verified' ? '<span class="ma-verif">✓</span>' : '';
    const ingr = (v.ingredienti && v.ingredienti.length) ? v.ingredienti.join(' · ') : '';
    return `<div class="ma-voce"><div class="ma-voce-nome">${_esc(v.nome)}${sigillo}</div>${ingr?`<div class="ma-voce-desc">${_esc(ingr)}</div>`:''}</div>`;
  }).join('');
  document.getElementById('ma-render').className = 'ma-render tpl-'+tpl;
  // blocco allergeni (Reg. UE 1169/2011): derivato dagli ingredienti, con avviso di verifica
  var allMenu = (typeof allergeniMenu==='function') ? allergeniMenu(voci) : [];
  var bloccoAllergeni = allMenu.length
    ? `<div class="ma-allergeni">
         <div class="ma-allergeni-tit">Allergeni presenti nel menù</div>
         <div class="ma-allergeni-lista">${allMenu.map(function(a){return '<span class="ma-allerg">'+numeroAllergene(a)+' · '+_esc(a)+'</span>';}).join('')}</div>
         <div class="ma-allergeni-avviso">Rilevati automaticamente dagli ingredienti. Verifica sempre la composizione effettiva e le informazioni del fornitore (contaminazioni, sostituzioni, ingredienti composti).</div>
       </div>`
    : '';
  document.getElementById('ma-render').innerHTML =
    `<div class="ma-head"><div class="ma-locale">${_esc(menu.locale||'Il tuo locale')}</div>
     <div class="ma-nome">${_esc(menu.nome||'Drink List')}</div></div>
     <div class="ma-voci">${corpoCliente}</div>
     ${bloccoAllergeni}
     <div class="ma-foot">Verificato da Matter</div>`;
  // VISTA STAFF: scheda di linea coi numeri-bersaglio
  const corpoStaff = voci.map(v=>{
    const ingr = (v.ingredienti && v.ingredienti.length) ? v.ingredienti.join(' · ') : '—';
    const tgt = v.target ? `<div class="mas-voce-target">TARGET · ${_esc(v.target)}</div>` : '';
    const stato = v.stato==='verified' ? '<span class="mas-verif">✓ verificato al banco</span>' : '<span class="mas-nonverif">da verificare</span>';
    var av = (typeof derivaAllergeni==='function') ? derivaAllergeni(v.ingredienti||[]).allergeni : [];
    const allerg = av.length ? `<div class="mas-voce-allerg">Allergeni: ${av.map(function(a){return numeroAllergene(a)+' '+_esc(a);}).join(' · ')}</div>` : '';
    return `<div class="mas-voce">
      <div class="mas-voce-nome">${_esc(v.nome)} ${stato}</div>
      <div class="mas-voce-ing">${_esc(ingr)}</div>
      ${tgt}
      ${allerg}
    </div>`;
  }).join('');
  document.getElementById('mas-render').innerHTML =
    `<div class="mas-head"><div class="mas-locale">${_esc(menu.locale||'Il tuo locale')} · scheda di linea</div>
     <div class="mas-nome">${_esc(menu.nome||'Drink List')}</div></div>
     <div class="mas-voci">${corpoStaff}</div>
     <div class="mas-foot">Scheda operativa — i numeri che lo staff deve colpire · Matter</div>`;
  _maSwitchVista('cliente');
  ov.classList.remove('hidden');
}
let _maMenuCorrente = null;
function _maSwitchVista(v){
  document.getElementById('ma-render').style.display = v==='cliente'?'block':'none';
  document.getElementById('mas-render').style.display = v==='staff'?'block':'none';
  var tc=document.getElementById('ma-tg-cliente'), ts=document.getElementById('ma-tg-staff');
  if(tc) tc.classList.toggle('active', v==='cliente');
  if(ts) ts.classList.toggle('active', v==='staff');
  document.body.setAttribute('data-print-vista', v);
}
function chiudiAnteprima(){ document.getElementById('menu-anteprima').classList.add('hidden'); caricaMenuSalvati(); }

// Applica il brand del ristoratore all'anteprima (colore accento, font, footer)
function _maApplicaBrand(){
  var render = document.getElementById('ma-render');
  if(!render) return;
  var accent = (document.getElementById('ma-brand-accent')||{}).value || '#245979';
  var font = (document.getElementById('ma-brand-font')||{}).value || 'serif';
  var footer = (document.getElementById('ma-brand-footer')||{}).value || '';
  render.style.setProperty('--ma-accent', accent);
  render.setAttribute('data-font', font);
  // salvo le scelte brand sul menu corrente, per l'export
  if(_maMenuCorrente){
    _maMenuCorrente.brand = {accent:accent, font:font, footer:footer};
  }
  // footer live
  var fEl = render.querySelector('.ma-brand-footer-live');
  if(footer){
    if(!fEl){ fEl=document.createElement('div'); fEl.className='ma-brand-footer-live'; render.appendChild(fEl); }
    fEl.textContent = footer;
  } else if(fEl){ fEl.remove(); }
}

// ── MOTORE ALLERGENI (Reg. UE 1169/2011) ──────────────────────────────
// Deriva i 14 allergeni obbligatori dagli ingredienti del menù. Deterministico, zero AI.
// Mappa ingrediente(IT, lowercase, senza accenti) → allergene UE. Match su parola intera/inclusione.
var _ALLERGENI_MAP = {
  // Glutine
  'glutine':'Glutine','farina':'Glutine','frumento':'Glutine','grano':'Glutine','pane':'Glutine','pasta':'Glutine',
  'orzo':'Glutine','segale':'Glutine','avena':'Glutine','farro':'Glutine','couscous':'Glutine','bulgur':'Glutine',
  'pangrattato':'Glutine','birra':'Glutine','malto':'Glutine','seitan':'Glutine','biscotto':'Glutine','impasto':'Glutine',
  // Crostacei
  'gambero':'Crostacei','gamberi':'Crostacei','gamberetto':'Crostacei','scampo':'Crostacei','scampi':'Crostacei',
  'aragosta':'Crostacei','granchio':'Crostacei','astice':'Crostacei','mazzancolla':'Crostacei','crostacei':'Crostacei',
  // Uova
  'uovo':'Uova','uova':'Uova','tuorlo':'Uova','albume':'Uova','maionese':'Uova','frittata':'Uova','meringa':'Uova',
  // Pesce
  'pesce':'Pesce','tonno':'Pesce','salmone':'Pesce','acciuga':'Pesce','acciughe':'Pesce','alice':'Pesce','alici':'Pesce',
  'baccala':'Pesce','merluzzo':'Pesce','branzino':'Pesce','orata':'Pesce','sgombro':'Pesce','colatura':'Pesce','bottarga':'Pesce',
  // Arachidi
  'arachide':'Arachidi','arachidi':'Arachidi','burro di arachidi':'Arachidi','noccioline':'Arachidi',
  // Soia
  'soia':'Soia','tofu':'Soia','edamame':'Soia','tempeh':'Soia','salsa di soia':'Soia','miso':'Soia',
  // Latte
  'latte':'Latte','burro':'Latte','panna':'Latte','formaggio':'Latte','mozzarella':'Latte','parmigiano':'Latte',
  'pecorino':'Latte','ricotta':'Latte','mascarpone':'Latte','yogurt':'Latte','gorgonzola':'Latte','stracciatella':'Latte',
  'grana':'Latte','provola':'Latte','scamorza':'Latte','fontina':'Latte','caciocavallo':'Latte','gelato':'Latte','besciamella':'Latte',
  // Frutta a guscio
  'mandorla':'Frutta a guscio','mandorle':'Frutta a guscio','nocciola':'Frutta a guscio','nocciole':'Frutta a guscio',
  'noce':'Frutta a guscio','noci':'Frutta a guscio','pistacchio':'Frutta a guscio','pistacchi':'Frutta a guscio',
  'anacardo':'Frutta a guscio','anacardi':'Frutta a guscio','pinoli':'Frutta a guscio','pinolo':'Frutta a guscio','noce pecan':'Frutta a guscio',
  // Sedano
  'sedano':'Sedano',
  // Senape
  'senape':'Senape','mostarda':'Senape',
  // Sesamo
  'sesamo':'Sesamo','tahina':'Sesamo','tahini':'Sesamo','gomasio':'Sesamo',
  // Solfiti
  'vino':'Solfiti','aceto':'Solfiti','aceto balsamico':'Solfiti','frutta secca':'Solfiti',
  // Lupini
  'lupini':'Lupini','lupino':'Lupini',
  // Molluschi
  'cozza':'Molluschi','cozze':'Molluschi','vongola':'Molluschi','vongole':'Molluschi','calamaro':'Molluschi','calamari':'Molluschi',
  'polpo':'Molluschi','seppia':'Molluschi','seppie':'Molluschi','ostrica':'Molluschi','ostriche':'Molluschi','totano':'Molluschi','moscardino':'Molluschi',
};
var _ALLERGENI_ORDINE = ['Glutine','Crostacei','Uova','Pesce','Arachidi','Soia','Latte','Frutta a guscio','Sedano','Senape','Sesamo','Solfiti','Lupini','Molluschi'];

function _normAllerg(s){
  return (s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim();
}
// Deriva gli allergeni da una lista di ingredienti (stringhe). Ritorna {allergeni:[], perIngrediente:{}}
function derivaAllergeni(ingredienti){
  var trovati = [];
  var perIng = {};
  (ingredienti||[]).forEach(function(ing){
    var n = _normAllerg(ing);
    if(!n) return;
    for(var chiave in _ALLERGENI_MAP){
      // match se la chiave è parola intera o compare nell'ingrediente
      var re = new RegExp('(^|\\s|\\b)'+chiave.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(s|\\b|\\s|$)');
      if(n===chiave || re.test(n) || n.indexOf(chiave)>=0){
        var a = _ALLERGENI_MAP[chiave];
        if(trovati.indexOf(a)<0) trovati.push(a);
        (perIng[ing] = perIng[ing]||[]).push(a);
      }
    }
  });
  // ordino secondo la lista UE
  trovati.sort(function(a,b){ return _ALLERGENI_ORDINE.indexOf(a)-_ALLERGENI_ORDINE.indexOf(b); });
  return {allergeni:trovati, perIngrediente:perIng};
}
// Riepilogo allergeni per l'intero menù (tutte le voci)
function allergeniMenu(voci){
  var tutti = [];
  (voci||[]).forEach(function(v){
    var r = derivaAllergeni(v.ingredienti||[]);
    r.allergeni.forEach(function(a){ if(tutti.indexOf(a)<0) tutti.push(a); });
  });
  tutti.sort(function(a,b){ return _ALLERGENI_ORDINE.indexOf(a)-_ALLERGENI_ORDINE.indexOf(b); });
  return tutti;
}
// Numero UE dell'allergene (1-14) per la convenzione "Allergeni: 1 · 3 · 7"
function numeroAllergene(nome){ return _ALLERGENI_ORDINE.indexOf(nome)+1; }

async function esportaMenu(){
  const piano = localStorage.getItem('matter_piano');
  if(piano!=='pro'){
    if(typeof mostraPopupPro==='function'){ mostraPopupPro('menu_export'); return; }
  }
  var menu = _maMenuCorrente || {};
  var voci = (menu.voci||[]).map(function(v){
    return {nome:v.nome||'', prezzo:v.prezzo||'', descrizione:(v.ingredienti&&v.ingredienti.length)?v.ingredienti.join(' \u00b7 '):(v.descrizione||''), sezione:v.sezione||''};
  });
  _apriVista('Il tuo menu \u00e8 pronto', '<div class="quad-loading">Preparo PDF e QR\u2026</div>');
  try{
    var accent=(document.getElementById('ma-brand-accent')||{}).value||'#245979';
    var r=await fetch('/v1/menu/crea', {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}),
      body:JSON.stringify(Object.assign({titolo:menu.nome||'Menu', locale:menu.locale||'', lingua:(typeof _lang!=='undefined'?_lang:'it'), voci:voci},
        window._filosofiaCorrente ? {tipo_menu:'wine', filosofia:window._filosofiaCorrente.filosofia_riassunto, tema_grafico:window._filosofiaCorrente.tema_grafico} : {}))});
    var j=await r.json();
    if(!j || !j.id){ var bd=document.getElementById('vista-body'); if(bd) bd.innerHTML='<div class="quad-empty"><b>Non riesco a creare il menu</b><span>Riprova tra poco.</span></div>'; return; }
    _mostraMenuPronto(j.id, accent.replace('#',''));
  }catch(e){
    var bd2=document.getElementById('vista-body'); if(bd2) bd2.innerHTML='<div class="quad-empty"><b>Errore</b><span>Riprova.</span></div>';
  }
}
function _mostraMenuPronto(id, accent){
  var base='/v1/menu/'+encodeURIComponent(id);
  var pdfUrl=base+'/pdf?accent='+encodeURIComponent(accent||'245979');
  if(window._filosofiaCorrente && window._filosofiaCorrente.tema_grafico){ pdfUrl += '&tema='+encodeURIComponent(window._filosofiaCorrente.tema_grafico); }
  var qrUrl=base+'/qr';
  var html=
    '<div class="mp-intro">Il tuo menu \u00e8 salvato. Tre modi per usarlo al banco.</div>'
    + '<a class="mp-btn mp-btn-pdf" href="'+pdfUrl+'" target="_blank" rel="noopener" download>Scarica il PDF</a>'
    + '<a class="mp-btn mp-btn-qr" href="'+qrUrl+'" target="_blank" rel="noopener" download>Scarica il QR</a>'
    + '<div class="mp-guide">'
    +   '<div class="mp-guide-row"><span class="mp-guide-ico">\ud83d\udcc4</span><div><b>Stampa il PDF</b> e mettilo sui tavoli.</div></div>'
    +   '<div class="mp-guide-row"><span class="mp-guide-ico">\u25a6</span><div><b>Stampa il QR</b>, mettilo sul tavolo: i clienti lo inquadrano e vedono il menu.</div></div>'
    +   '<div class="mp-guide-row"><span class="mp-guide-ico">\ud83d\udd17</span><div><b>Il menu \u00e8 anche online</b>, condividi il link.</div></div>'
    + '</div>';
  var bd=document.getElementById('vista-body'); if(bd) bd.innerHTML=html;
}

async function caricaQuaderno(){
  const token = localStorage.getItem('matter_token');
  const empty = document.getElementById('quad-empty');
  const list = document.getElementById('quad-list');
  if(!token){
    if(empty) empty.style.display='none';
    if(list) list.innerHTML = `
      <div class="quad-empty-wrap">
        <!-- anteprima sfocata di un quaderno già compilato: l'utente desidera possederlo -->
        <div class="quad-preview" aria-hidden="true">
          <div class="quad-prev-row"><span class="qp-date">24/08 · 18:40</span><span class="qp-name">Batch Negrono ×12</span><span class="qp-val">dil 22% <b>OK</b></span></div>
          <div class="quad-prev-row"><span class="qp-date">24/08 · 11:05</span><span class="qp-name">Pasta madre rinfresco</span><span class="qp-val">pH 3.8 <b>OK</b></span></div>
          <div class="quad-prev-row"><span class="qp-date">23/08 · 22:10</span><span class="qp-name">Sour bilanciato</span><span class="qp-val">acidità 1.3% <b>OK</b></span></div>
          <div class="quad-prev-row"><span class="qp-date">23/08 · 16:30</span><span class="qp-name">Focaccia 80%</span><span class="qp-val">idr 80% <b>OK</b></span></div>
          <div class="quad-prev-row"><span class="qp-date">22/08 · 09:15</span><span class="qp-name">Espresso dial-in</span><span class="qp-val">TDS 9.2% <b>OK</b></span></div>
        </div>
        <div class="quad-hero quad-hero-over">
          <div class="quad-hero-icon"><i class="ph ph-notebook"></i></div>
          <div class="quad-hero-title">Costruisci il tuo metodo</div>
          <div class="quad-hero-sub">Ogni misura che salvi — diluizioni, pH, idratazione, food cost — diventa il tuo archivio operativo. Non stai imparando: stai costruendo il tuo modo di lavorare.</div>
          <button class="quad-hero-btn" onclick="apriAccount()"><i class="ph ph-plus"></i> Salva la tua prima misura</button>
          <div class="quad-hero-note">Gratis. Nessuna carta richiesta.</div>
        </div>
      </div>`;
    return;
  }
  try {
    const r = await fetch('/v1/quaderno',{headers:{'Authorization':'Bearer '+token}});
    const j = await r.json();
    const esps = j.esperimenti || [];
    if(!esps.length){ if(empty) empty.style.display='block'; if(list) list.innerHTML=''; return; }
    if(empty) empty.style.display='none';
    const isPro = _isPro();
    const visibili = isPro ? esps : esps.slice(0, QUAD_FREE);
    const nascosti = isPro ? [] : esps.slice(QUAD_FREE);
    let html = visibili.map(e=>{
      const chips=[];
      if(e.abv) chips.push(`ABV ${parseFloat(e.abv).toFixed(1)}%`);
      if(e.ph) chips.push(`pH ${e.ph}`);
      if(e.idratazione) chips.push(`Idr ${e.idratazione}%`);
      const ts=e.ts?new Date(e.ts).toLocaleDateString('it-IT',{day:'numeric',month:'short'}):'';
      return `<div class="quad-item"><div class="quad-item-name">${esc(e.nome)}</div>
        <div class="quad-item-meta">${e.disciplina?`<span>${esc(e.disciplina)}</span>`:''}
        ${chips.map(c=>`<span class="quad-item-chip">${c}</span>`).join('')}
        ${ts?`<span>${ts}</span>`:''}</div></div>`;
    }).join('');
    if(nascosti.length){
      html += nascosti.map(e=>`<div class="quad-item cap-blur">
        <div class="quad-item-name">${esc(e.nome)}</div>
        <div class="quad-item-meta">${e.disciplina?`<span>${esc(e.disciplina)}</span>`:''}</div>
      </div>`).join('');
      html += `<div class="cap-lock">
        <svg viewBox="0 0 24 24" style="width:15px;height:15px;stroke:var(--e700);fill:none;stroke-width:2;flex-shrink:0"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/></svg>
        <span class="cap-lock-txt">${QUAD_FREE} esperimenti gratuiti. Salva senza limite con Pro.</span>
        <span class="cap-lock-cta" onclick="vaiAPro()">Passa a Pro →</span>
      </div>`;
    }
    if(list) list.innerHTML = html;
  } catch(e){ if(empty) empty.style.display='block'; }
}

/* ── LOGIN TOPBAR ─────────────────────────────────────── */
function apriAccount(){
  const token = localStorage.getItem('matter_token');
  if(token){
    const menu = document.getElementById('account-menu');
    const emailEl = document.getElementById('account-menu-email');
    const email = localStorage.getItem('matter_email') || '';
    if(emailEl) emailEl.textContent = email;
    if(menu){
      const isOpen = menu.style.display !== 'none';
      menu.style.display = isOpen ? 'none' : 'block';
      if(!isOpen){
        // chiudi cliccando fuori
        setTimeout(()=>document.addEventListener('click', chiudiAccountMenu, {once:true}), 50);
      }
    }
  } else {
    switchTab('auth');
  }
}
function chiudiAccountMenu(){
  const menu = document.getElementById('account-menu');
  if(menu) menu.style.display = 'none';
}
function doLogout(){
  localStorage.removeItem('matter_token');
  localStorage.removeItem('matter_email');
  localStorage.removeItem('matter_piano');
  chiudiAccountMenu();
  aggiornaTopbarLogin();
  switchTab('scopri');
}
function aggiornaTopbarLogin(){
  const btn=document.getElementById('login-topbar-btn'); if(!btn) return;
  const token=localStorage.getItem('matter_token');
  const email=localStorage.getItem('matter_email')||'';
  if(token){ btn.textContent=email?email.split('@')[0]:'•'; btn.classList.add('logged'); }
  else { btn.textContent=_t('accedi'); btn.classList.remove('logged'); }
}

async function cercaAbbinamenti(ingrediente){
  switchTab('chiedi');
  const ing = (ingrediente||'').toLowerCase().replace(/[\s/]+/g,'_');
  try {
    const r = await fetch('/v1/abbina/'+encodeURIComponent(ing));
    const j = await r.json();
    const card = document.createElement('div'); card.className='scheda';
    if(!j.abbinamenti || !j.abbinamenti.length){
      card.innerHTML=`<div class="s-body" style="color:var(--ink-muted)">Nessun abbinamento trovato per ${esc(ingrediente)}.</div>`;
    } else {
      const items = j.abbinamenti.map(a=>
        `<div style="padding:6px 0;border-bottom:1px solid var(--border);font-size:13px">
          <b style="color:var(--flavor)">${esc((a.ingrediente||'').replace(/_/g,' '))}</b>
          <span style="color:var(--ink-muted);font-size:12px"> — ${esc(a.composto||'')} (${a.overlap||''})</span>
        </div>`).join('');
      card.innerHTML=`<div class="s-q" style="color:var(--flavor)"><i class="ph ph-leaf"></i> perché funzionano insieme — ${esc(ingrediente)}</div>
        <div style="padding:8px 14px">${items}</div>
        <div style="font-family:var(--mono);font-size:10px;color:var(--ink-muted);padding:6px 14px">${esc(j.nota||'')}</div>`;
    }
    document.getElementById('schede').prepend(card);
  } catch(e){ _logErr('flavor', e); }
}

/* ── FEEDBACK ─────────────────────────────────────────── */
async function inviaFeedback(logId, voto, btn){
  try {
    await fetch('/v1/feedback', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({log_id:logId, voto:voto})
    });
    btn.closest('.s-feedback').innerHTML='<span style="color:var(--s500);font-size:12px">Grazie per il feedback.</span>';
  } catch(e){}
}

/* ── TEST KT (TE3) ────────────────────────────────────── */
async function testaKT(){
  // (rimossa: funzione di test manuale usata solo in sviluppo)
}

/* ===== blocco 5 (da index.html) ===== */
/* ── SUPPORTO ──────────────────────────────────────────── */
function aprireSupporto(){
  document.getElementById('sup-modal').classList.add('show');
  setTimeout(()=>document.getElementById('sup-testo').focus(),100);
}
function chiudiSupporto(){
  document.getElementById('sup-modal').classList.remove('show');
  document.getElementById('sup-testo').value='';
  const fb=document.getElementById('sup-fb');
  fb.style.display='none'; fb.textContent='';
}
async function inviaSupporto(){
  const testo=document.getElementById('sup-testo').value.trim();
  if(!testo) return;
  const btn=document.getElementById('sup-btn-inv');
  btn.disabled=true; btn.textContent='Invio…';
  const fb=document.getElementById('sup-fb');
  try{
    const tok=localStorage.getItem('matter_token')||'';
    const r=await fetch('/v1/supporto',{
      method:'POST',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+tok},
      body:JSON.stringify({testo})
    });
    const d=await r.json();
    fb.textContent=d.risposta||'Richiesta inviata. Ti risponderemo via email.';
    fb.style.color='var(--teal)'; fb.style.display='block';
    document.getElementById('sup-testo').value='';
    setTimeout(chiudiSupporto,5000);
  }catch(e){
    fb.textContent='Errore di rete. Scrivi a supporto@matter.app';
    fb.style.color='var(--e700)'; fb.style.display='block';
  }finally{
    btn.disabled=false; btn.textContent='Invia richiesta';
  }
}

/* ── RESET PASSWORD ──────────────────────────────────────────── */
function mostraResetForm(){
  ['auth-panel-login','auth-panel-reg'].forEach(id=>{
    const el=document.getElementById(id); if(el) el.style.display='none';
  });
  const rp=document.getElementById('auth-panel-reset');
  if(rp) rp.style.display='block';
}
async function doResetRichiesta(){
  const email=(document.getElementById('reset-email').value||'').trim();
  const msg=document.getElementById('reset-msg');
  const btn=document.getElementById('reset-btn');
  if(!email){msg.textContent='Inserisci la tua email.';return;}
  btn.disabled=true; btn.textContent='Invio…';
  try{
    const r=await fetch('/v1/auth/reset-richiesta',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});
    const d=await r.json();
    msg.textContent=d.messaggio||'Controlla la tua email.';
    msg.style.color='var(--teal)';
  }catch(e){msg.textContent='Errore di rete.';}
  finally{btn.disabled=false;btn.textContent='Invia link di reset';}
}
async function doResetConferma(){
  const pw=(document.getElementById('nuova-pw').value||'').trim();
  const msg=document.getElementById('nuova-pw-msg');
  const tok=new URLSearchParams(location.search).get('reset')||'';
  if(!pw||pw.length<8){msg.textContent='Password minimo 8 caratteri.';return;}
  try{
    const r=await fetch('/v1/auth/reset-conferma',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({token:tok,password:pw})});
    const d=await r.json();
    if(d.ok){
      msg.textContent=d.messaggio||'Password aggiornata!';
      msg.style.color='var(--teal)';
      history.replaceState({},'','/app');
      setTimeout(()=>switchAuthTab('login'),2000);
    }else{
      msg.textContent=d.errore||'Errore.';
      msg.style.color='var(--e700)';
    }
  }catch(e){msg.textContent='Errore di rete.';}
}

// ── TRIAL FUNCTIONS ─────────────────────────────────────────
function mostraNotificaTrial(rimaste){
  const old=document.querySelector('.trial-banner');if(old)old.remove();
  const b=document.createElement('div');b.className='trial-banner';
  var _tb={'it':`Hai ancora ${rimaste} chat di prova. Passa a Pro per continuare.`,'en':`You have ${rimaste} free chats left. Upgrade to Pro to continue.`,'es':`Te quedan ${rimaste} chats gratuitos. Actualiza a Pro para continuar.`};
  b.textContent=_tb[_lang]||_tb['it'];
  document.body.appendChild(b);
  setTimeout(()=>{if(b.parentNode)b.remove();},5000);
}
// gestisce feature col formato "icona␣␣testo" (EN/ES) o solo "testo" (IT) — evita undefined
function _pwFeatIcon(s){ s=String(s||''); var i=s.indexOf('  '); return i>0 ? s.slice(0,i).trim() : '·'; }
function _pwFeatText(s){ s=String(s||''); var i=s.indexOf('  '); return i>0 ? s.slice(i+2).trim() : s.trim(); }
function mostraPopupPro(motivo){
  _trackFunnel('paywall_hit', {motivo: motivo||'?'});
  const old=document.querySelector('.trial-popup-overlay');if(old)old.remove();
  // Mostra popup solo nella tab Chiedi per motivazioni chat
  if(motivo === 'ultima_chat' || motivo === 'esaurito') {
    const chiediScreen=document.getElementById('screen-chiedi');
    if(!chiediScreen||!chiediScreen.classList.contains('active')) return;
  }

  // Contenuti per lingua e motivo
  const _COPY = {
    it: {
      badge: 'Matter Pro',
      icon_chat: '',
      icon_lesson: '',
      title_esaurito: 'Capire la scienza è gratis.',
      title_ultimo: 'Ultimo assaggio gratuito',
      title_lezione: 'Fenomeno riservato a Pro',
      title_lezione_locked: 'Fenomeno riservato a Pro',
      sub_esaurito: 'Il metodo operativo per non sbagliare il servizio è Pro: tutti gli errori da banco, tutte le tecniche, gli esperimenti guidati.',
      sub_ultimo: 'Ancora una risposta e poi dovrai scegliere.',
      sub_lezione: 'I fenomeni avanzati sono disponibili con il piano Pro.',
      feat1: 'Analisi operative dei tuoi problemi',
      feat2: 'Foto di impasti e preparazioni',
      feat3: 'Risposte a voce, mani libere',
      feat4: 'Ragionamento sui tuoi valori reali',
      price: '€19,99',
      period: '/mese · Disdici quando vuoi',
      cta: 'Continua con Matter →',
      skip_esaurito: 'L\'Atlante, il Mirino e i Calcolatori restano gratuiti.',
      skip_altro: 'Continua in free',
    },
    en: {
      badge: 'Matter Bench Pro',
      icon_chat: '',
      icon_lesson: '',
      title_esaurito: 'You\'ve used all 5 free chats',
      title_ultimo: 'Last free chat',
      title_lezione: 'Advanced phenomenon — Pro only',
      title_lezione_locked: 'Advanced phenomenon — Pro only',
      sub_esaurito: 'Keep using the science of your craft without limits.',
      sub_ultimo: 'One more answer, then you\'ll need to choose.',
      sub_lezione: 'Advanced phenomena are available with the Pro plan.',
      feat1: '∞  Unlimited chats with real numbers',
      feat2: 'All phenomena, all disciplines',
      feat3: '⊞  6 calculators, no limits',
      feat4: 'Full Flavor Network',
      price: '€19.99',
      period: '/month · Cancel anytime',
      cta: 'Upgrade to Pro',
      skip_esaurito: 'Back to home',
      skip_altro: 'Continue free',
    },
    es: {
      badge: 'Matter Bench Pro',
      icon_chat: '',
      icon_lesson: '',
      title_esaurito: 'Has usado los 5 chats gratuitos',
      title_ultimo: 'Último chat gratuito',
      title_lezione: 'Fenómeno avanzado — solo Pro',
      title_lezione_locked: 'Fenómeno avanzado — solo Pro',
      sub_esaurito: 'Sigue usando la ciencia de tu oficio sin límites.',
      sub_ultimo: 'Una respuesta más y tendrás que elegir.',
      sub_lezione: 'Los fenómenos avanzados están disponibles con el plan Pro.',
      feat1: '∞  Chats ilimitados con números reales',
      feat2: 'Todos los fenómenos, todas las disciplinas',
      feat3: '⊞  6 calculadoras sin restricciones',
      feat4: 'Flavor Network completo',
      price: '€19,99',
      period: '/mes · Cancela cuando quieras',
      cta: 'Pasarse a Pro',
      skip_esaurito: 'Volver al inicio',
      skip_otro: 'Continuar gratis',
    }
  };

  const C = _COPY[_lang] || _COPY['it'];
  const isChat = motivo === 'esaurito' || motivo === 'ultima_chat';
  const isLesson = motivo === 'lezione' || motivo === 'lezione_locked';

  const titolo = motivo === 'esaurito' ? C.title_esaurito
    : motivo === 'ultima_chat' ? C.title_ultimo
    : motivo === 'lezione' ? C.title_lezione
    : C.title_lezione_locked;

  const sub = motivo === 'esaurito' ? C.sub_esaurito
    : motivo === 'ultima_chat' ? C.sub_ultimo
    : C.sub_lezione;

  const skipLabel = motivo === 'esaurito'
    ? (C.skip_esaurito || 'Torna alla home')
    : (C.skip_altro || C.skip_otro || 'Continua in free');

  const overlay = document.createElement('div');
  overlay.className = 'trial-popup-overlay';
  overlay.innerHTML = `
    <div class="trial-popup" onclick="event.stopPropagation()">
      <div class="trial-popup-badge">${C.badge}</div>
      <div class="trial-popup-icon">${isChat ? C.icon_chat : C.icon_lesson}</div>
      <h3>${titolo}</h3>
      <p class="trial-popup-sub">${sub}</p>
      <div class="trial-popup-features">
        <div class="trial-popup-feat"><span class="trial-popup-feat-icon">${_pwFeatIcon(C.feat1)}</span><span class="trial-popup-feat-text">${_pwFeatText(C.feat1)}</span></div>
        <div class="trial-popup-feat"><span class="trial-popup-feat-icon">${_pwFeatIcon(C.feat2)}</span><span class="trial-popup-feat-text">${_pwFeatText(C.feat2)}</span></div>
        <div class="trial-popup-feat"><span class="trial-popup-feat-icon">${_pwFeatIcon(C.feat3)}</span><span class="trial-popup-feat-text">${_pwFeatText(C.feat3)}</span></div>
        <div class="trial-popup-feat"><span class="trial-popup-feat-icon">${_pwFeatIcon(C.feat4)}</span><span class="trial-popup-feat-text">${_pwFeatText(C.feat4)}</span></div>
      </div>
      <div class="trial-popup-price">${C.price}</div>
      <div class="trial-popup-price-note">${C.period}</div>
      <div class="trial-popup-founding" id="pw-founding">Silent Launch — solo per i primi 100 professionisti:<br><b>Founding Member 99 € il primo anno</b></div>
      <button class="trial-popup-cta" onclick="document.querySelector('.trial-popup-overlay').remove();apriPrezzi()">${C.cta}</button>
      <button class="trial-popup-skip" onclick="${motivo === 'esaurito' ? "document.querySelector('.trial-popup-overlay').remove();switchTab('scopri')" : "document.querySelector('.trial-popup-overlay').remove()"}">${skipLabel}</button>
    </div>`;

  document.body.appendChild(overlay);
  overlay.addEventListener('click', e => { if(e.target === overlay) overlay.remove(); });
  _caricaPostiFounding();
}
// ═══ PAGINA PREZZI — 3 piani (R2). Bottoni pronti, si collegano a Stripe coi price ID ═══
async function apriPrezzi(){
  _apriVista('Matter Pro',
    '<div class="prezzi-intro">Il numero-bersaglio esatto è il valore. Con Pro lo vedi nitido, sempre.</div>'
    + '<div class="prezzi-grid" id="prezzi-grid">'
    +   '<div class="prezzo-card">'
    +     '<div class="prezzo-nome">Mensile</div>'
    +     '<div class="prezzo-val">19,99 €<span class="prezzo-per">/mese</span></div>'
    +     '<button class="prezzo-btn" onclick="_vaiCheckout(\'mensile\')">Scegli mensile</button>'
    +   '</div>'
    +   '<div class="prezzo-card">'
    +     '<div class="prezzo-nome">Annuale</div>'
    +     '<div class="prezzo-val">149 €<span class="prezzo-per">/anno</span></div>'
    +     '<div class="prezzo-badge-save">~37% di sconto</div>'
    +     '<button class="prezzo-btn" onclick="_vaiCheckout(\'annuale\')">Scegli annuale</button>'
    +   '</div>'
    +   '<div class="prezzo-card prezzo-card-founding">'
    +     '<div class="prezzo-badge-founding">Silent Launch</div>'
    +     '<div class="prezzo-nome">Founding Member</div>'
    +     '<div class="prezzo-val">99 €<span class="prezzo-per">il primo anno</span></div>'
    +     '<div class="prezzo-founding-nota" id="prezzi-founding-count">100 posti</div>'
    +     '<button class="prezzo-btn prezzo-btn-founding" onclick="_vaiCheckout(\'founding\')">Diventa Founding</button>'
    +   '</div>'
    + '</div>'
    + '<div class="prezzi-free-nota">Il piano gratuito resta: fenomeno del giorno, 5 chat, ricette in lettura.</div>');
  // carico i posti reali per la card founding
  try{
    var r=await fetch('/v1/founding/posti'); var j=await r.json();
    var el=document.getElementById('prezzi-founding-count');
    if(el){
      if(j.esauriti){ el.textContent='Posti esauriti'; var fb=document.querySelector('.prezzo-btn-founding'); if(fb){fb.disabled=true;fb.textContent='Esauriti';} }
      else { el.textContent='Rimasti: '+(j.rimasti!=null?j.rimasti:100)+'/'+(j.totali!=null?j.totali:100); }
    }
  }catch(e){}
}
function _vaiCheckout(piano){
  // Stripe non ancora attivo (post-P.IVA): i price ID arriveranno. Per ora avvia il flusso login/checkout.
  if(!localStorage.getItem('matter_token')){
    chiudiVista(); switchTab('auth'); if(typeof switchAuthTab==='function') switchAuthTab('reg');
    _toast('Registrati per continuare — il pagamento sarà attivo a breve');
    return;
  }
  var _tk=localStorage.getItem('matter_token')||'';
  fetch('/v1/stripe/checkout',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+_tk},
    body:JSON.stringify({piano:piano, token:_tk})})
    .then(r=>r.json()).then(j=>{
      if(j.url) window.location.href=j.url;
      else if(j.checkout_url) window.location.href=j.checkout_url;
      else _toast('Il pagamento sarà attivo a breve');
    }).catch(()=>_toast('Il pagamento sarà attivo a breve'));
}
// Contatore posti Founding reali (R1)
async function _caricaPostiFounding(){
  var el=document.getElementById('pw-founding');
  if(!el) return;
  try{
    var r=await fetch('/v1/founding/posti');
    var j=await r.json();
    if(j.esauriti){
      el.innerHTML='<b>Posti Founding esauriti</b><br>Pro a 19,99 €/mese o 149 €/anno.';
      return;
    }
    var rimasti = (j.rimasti!=null)?j.rimasti:100;
    var totali = (j.totali!=null)?j.totali:100;
    el.innerHTML='Silent Launch — solo per i primi '+totali+' professionisti:<br><b>Founding Member 99 € il primo anno</b><br><span class="pw-founding-count">Rimasti: '+rimasti+'/'+totali+'</span>';
  }catch(e){}
}


  // Registra Service Worker PWA
  if('serviceWorker' in navigator){
    window.addEventListener('load', ()=>{
      navigator.serviceWorker.register('/sw.js', {scope:'/'})
        .then(r=>console.log('[SW] registrato:', r.scope))
        .catch(e=>console.log('[SW] errore:', e));
    });
  }


// ── CALCOLA COSTO ─────────────────────────────────────────────
function mostraCostoBtn(){
  const btn=document.getElementById('costo-btn');
  if(btn) btn.style.display='inline-flex';
}
async function calcolaCosto(){
  const tok=localStorage.getItem('matter_token')||'';
  // Raccoglie ingredienti dalla scheda attuale (dal DOM o dal motore)
  const ingredienti=_ultimi_ingredienti||[];
  if(!ingredienti.length){
    alert(_L({it:'Salva prima la ricetta nel quaderno per calcolare il costo.',en:'Save the recipe to the notebook first to calculate the cost.',es:'Guarda primero la receta en el cuaderno para calcular el coste.'}));
    return;
  }
  try{
    const r=await fetch('/v1/quaderno/0/costo',{
      method:'POST',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+tok},
      body:JSON.stringify({ingredienti})
    });
    const j=await r.json();
    if(j.costo_totale_eur!==undefined){
      const fc=j.food_cost_pct?` (food cost ${j.food_cost_pct}%)`:'';
      const suggeriti=j.prezzi_vendita_suggeriti||{};
      const msg=[
        `Costo ingredienti: €${j.costo_totale_eur.toFixed(2)}${fc}`,
        ``,
        `Prezzo vendita suggerito:`,
        `  Food cost 25%: €${suggeriti.fc_25pct||'—'}`,
        `  Food cost 30%: €${suggeriti.fc_30pct||'—'}`,
        `  Food cost 33%: €${suggeriti.fc_33pct||'—'}`,
        ``,
        `Fonte: ${j.fonte||'Matter Bench / ISMEA orientativo'}`
      ].join('\n');
      alert(msg);
    }
  }catch(e){
    alert('Errore nel calcolo costo: '+e.message);
  }
}
let _ultimi_ingredienti=[];


// ── PILL CHAT BILINGUE ──────────────────────────────────────
var _PILLS = {
  it: [
    {q: 'a che temperatura coagula il tuorlo?', l: 'A che temperatura coagula il tuorlo? →'},
    {q: 'quanta acidità ci vuole in un sour?', l: 'Quanta acidità in un sour? →'},
    {q: 'a che temperatura estraggo l\'espresso?', l: 'A che temperatura estraggo l\'espresso? →'},
    {q: 'quanto lievito madre per un kg di farina?', l: 'Quanto lievito madre per 1 kg di farina? →'},
  ],
  en: [
    {q: 'my espresso tastes different every morning with the same recipe — why?', l: 'Espresso never the same →'},
    {q: 'my bread crust is pale even at high temperature — what am I missing?', l: 'Pale crust at high heat →'},
    {q: 'my ganache splits every time I reheat it — how do I fix it?', l: 'Ganache keeps splitting →'},
    {q: 'how do I measure water activity to predict shelf life?', l: 'Shelf life & water activity →'},
  ],
  es: [
    {q: '¿por qué mi espresso sabe diferente cada mañana con la misma receta?', l: 'El espresso nunca es igual →'},
    {q: '¿por qué mi pan no sube en el horno aunque la masa fermenta bien?', l: 'El pan no sube en el horno →'},
    {q: '¿cómo controlo la fermentación cuando hace mucho calor?', l: 'Fermentación fuera de control →'},
    {q: '¿cómo mido el pH de una masa o de un cóctel?', l: 'Cómo mido el pH →'},
  ]
};
function aggiornaPills() {
  var lang = _lang || 'it';
  var pills = _PILLS[lang] || _PILLS.it;
  ['pill1','pill2','pill3','pill4'].forEach(function(id, i) {
    var el = document.getElementById(id);
    if (el && pills[i]) {
      el.textContent = pills[i].l;
      el.dataset.q = pills[i].q;
    }
  });
}
function chiediPill(i) {
  var lang = _lang || 'it';
  var pills = _PILLS[lang] || _PILLS.it;
  if (pills[i]) chiediTesto(pills[i].q);
}
// Aggiorna le pill quando cambia la lingua
var _origSetLang = typeof setLang === 'function' ? setLang : null;


// ── FOTOCAMERA (Vision) ────────────────────────────────────────
// ── AGGANCIO AL LOOP dalla foto ──────────────────────────────
// ── STRUMENTO per misurare il numero-bersaglio del fenomeno (Parte B) ──
async function _caricaStrumentoPerFenomeno(disc, fenNome, target){
  var box = document.getElementById('les-strumento-box');
  var cont = document.getElementById('les-strumento-content');
  if(!box || !cont) return;
  try {
    var dnorm = _normDisc(disc);
    var r = await fetch('/v1/strumenti/' + encodeURIComponent(dnorm));
    var j = await r.json();
    var items = j.strumenti || [];
    if(!items.length){ box.style.display='none'; return; }
    // scelgo lo strumento più pertinente: matching parole tra misura/target strumento e fenomeno/target
    var testo = ((fenNome||'') + ' ' + (target||'')).toLowerCase();
    var best = null, bestScore = 0;
    items.forEach(function(s){
      var chiavi = ((s.misura||'') + ' ' + (s.target||'') + ' ' + (s.nome||'')).toLowerCase();
      var score = 0;
      // parole chiave sensoriali comuni
      ['ph','brix','°c','temperatura','abv','alcol','grammi','peso','bar','tds','densità','so2','umidità','aw','acidità'].forEach(function(k){
        if(testo.indexOf(k)>=0 && chiavi.indexOf(k)>=0) score += 2;
      });
      if(score > bestScore){ bestScore = score; best = s; }
    });
    if(!best){ best = items[0]; } // fallback: il primo strumento della disciplina
    cont.innerHTML =
      '<a class="les-strum-card" href="'+esc(best.amazon)+'" target="_blank" rel="noopener sponsored">'
      +'<div class="les-strum-info">'
      +'<span class="les-strum-nome">'+esc(best.nome)+'</span>'
      +'<span class="les-strum-meta">'+esc(best.misura)+' · '+esc(best.prezzo_approx||'')+'</span>'
      +'</div>'
      +'<span class="les-strum-cta">Vedi <i class="ph ph-arrow-up-right"></i></span>'
      +'</a>';
    box.style.display = '';
  } catch(e){ box.style.display='none'; }
}
function _normDisc(d){
  var m = {bar:'bar',bakery:'panificazione',panificazione:'panificazione',cucina:'cucina',
    caffetteria:'caffe',caffe:'caffe',pasticceria:'pasticceria',gelateria:'gelateria',
    vino:'vino',birra:'birra'};
  return m[(d||'').toLowerCase()] || (d||'').toLowerCase();
}

async function _fotoAscolta(btn, testo){
  if(!testo) return;
  // se sta già suonando, ferma
  if(window._fotoAudio && !window._fotoAudio.paused){
    window._fotoAudio.pause(); window._fotoAudio = null;
    btn.innerHTML = '<i class="ph ph-speaker-high"></i> Ascolta'; return;
  }
  var orig = btn.innerHTML;
  btn.innerHTML = '<i class="ph ph-circle-notch ph-spin"></i> …';
  btn.disabled = true;
  try {
    var r = await fetch('/v1/tts', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({testo: testo, lang: _lang||'it', voce:'onyx'})});
    if(!r.ok){ throw new Error('tts '+r.status); }
    var blob = await r.blob();
    var url = URL.createObjectURL(blob);
    var audio = new Audio(url);
    window._fotoAudio = audio;
    btn.innerHTML = '<i class="ph ph-pause"></i> Pausa';
    btn.disabled = false;
    audio.onended = function(){ btn.innerHTML = '<i class="ph ph-speaker-high"></i> Ascolta'; window._fotoAudio=null; };
    audio.play();
  } catch(e){
    btn.innerHTML = orig; btn.disabled = false;
    // fallo silenzioso: l'audio è un di più, non deve rompere l'esperienza
  }
}
async function _fotoStudiaFenomeno(fenId){
  // apre la scheda del fenomeno via /nodo (ha già target + scheda)
  if(!fenId) return;
  try {
    const r = await fetch('/nodo', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({id: fenId, lang: _lang||'it'})});
    const j = await r.json();
    const disc = j.disciplina || (j.nodo && j.nodo.disciplina);
    if(disc){ switchTab('lezione'); setTimeout(function(){ _caricaLezionePerId(disc, fenId); }, 150); return; }
  } catch(e){}
  // fallback: porta alla chat con domanda pronta sul fenomeno
  switchTab('chiedi');
  setTimeout(function(){ var q=document.getElementById('q'); if(q){ q.value='Spiegami il fenomeno e il suo numero bersaglio'; q.focus(); } }, 300);
}
function _fotoVaiFlavor(nome){
  switchTab('mappa');
  setTimeout(function(){
    if(typeof switchMappaTab==='function') switchMappaTab('flavor');
    setTimeout(function(){
      var inp=document.getElementById('flavor-input');
      if(inp){ inp.value=nome; if(typeof cercaFlavor==='function') cercaFlavor(); }
    }, 300);
  }, 200);
}

// ── APPROFONDISCI NELLA CHAT col contesto della scheda ──────────
// ══════════ MIRINO OPERATIVO — il loop VEDI→MISURA→CONFRONTA→DECIDI→RIMISURA ══════════
// Estrae il range numerico da un target testuale. Scansiona TUTTI i pezzi
// (eroe + condizioni) finché trova un numero utile. "pH · 3.7-3.9" o "pH 3.7-3.9" funzionano.
function _parseRange(target){
  if(!target) return null;
  var pezzi = target.split(/\s*[·;]\s*/).map(function(s){return s.trim();}).filter(Boolean);
  // provo ogni pezzo: prima chi ha un range esplicito, poi soglie, poi valore singolo
  function tenta(txt){
    // range "a-b"
    var m = txt.match(/(-?\d+(?:[.,]\d+)?)\s*[-–—]\s*(-?\d+(?:[.,]\d+)?)/);
    if(m){
      var lo=parseFloat(m[1].replace(',','.')), hi=parseFloat(m[2].replace(',','.'));
      // etichetta = testo prima del numero (es. "pH", "burro")
      var lab = txt.slice(0, m.index).replace(/[:=]/g,'').trim();
      return {min:Math.min(lo,hi), max:Math.max(lo,hi), raw:txt, etichetta:lab};
    }
    // soglia "<1" ">35" "≥9"
    var s = txt.match(/([<>≤≥]=?)\s*(-?\d+(?:[.,]\d+)?)/);
    if(s){
      var v=parseFloat(s[2].replace(',','.')), op=s[1];
      var lab2 = txt.slice(0, s.index).replace(/[:=]/g,'').trim();
      if(op.indexOf('>')>=0||op.indexOf('≥')>=0) return {min:v, max:v+Math.max(v*0.5,1), raw:txt, soglia:'min', etichetta:lab2};
      if(op.indexOf('<')>=0||op.indexOf('≤')>=0) return {min:Math.max(0,v-Math.max(v*0.5,1)), max:v, raw:txt, soglia:'max', etichetta:lab2};
    }
    return null;
  }
  // 1) cerco un range/soglia esplicito in qualsiasi pezzo
  for(var i=0;i<pezzi.length;i++){ var r=tenta(pezzi[i]); if(r) return r; }
  // 2) fallback: primo pezzo con un numero singolo → range ±10%
  for(var j=0;j<pezzi.length;j++){
    var u=pezzi[j].match(/(-?\d+(?:[.,]\d+)?)/);
    if(u){ var vv=parseFloat(u[1].replace(',','.'));
      var lab3=pezzi[j].slice(0,u.index).replace(/[:=]/g,'').trim();
      return {min:vv*0.9, max:vv*1.1, raw:pezzi[j], singolo:vv, etichetta:lab3}; }
  }
  return null; // nessun numero: fenomeno qualitativo
}

// Stato NEUTRO del Mirino: nessuna tecnica scelta ancora → invito, non un target finto
function renderMirinoNeutro(box){
  if(!box) return;
  box.style.display='';
  box._range = null;
  box.innerHTML = '<div class="mirino-neutro">'
    + '<div class="mirino-neutro-ico">◎</div>'
    + '<div class="mirino-neutro-txt">Scegli una tecnica per vedere il numero da colpire</div>'
    + '</div>';
}

// Costruisce il Mirino in STATO 1 (solo target, invito a misurare)
function renderMirino(box, fenomeno, target, azioneFn){
  if(!box) return;
  var r = _parseRange(target);
  if(!r){ box.style.display='none'; return; } // niente numero → niente mirino
  box.style.display='';
  box._range = r; box._fenomeno = fenomeno; box._azioneFn = azioneFn||null;
  var span = r.max - r.min;
  // scala: estendo il range su ciascun lato per mostrare anche valori fuori
  var margine = Math.max(span*0.9, span>0?span:1);
  var loScale = r.min - margine, hiScale = r.max + margine;
  box._scale = {lo:loScale, hi:hiScale};
  // percentuali zona target sulla barra
  var pTargetLo = ((r.min - loScale)/(hiScale-loScale))*100;
  var pTargetHi = ((r.max - loScale)/(hiScale-loScale))*100;
  var pCentro = (pTargetLo+pTargetHi)/2;
  box.innerHTML =
    '<div class="mirino-head"><span class="mirino-lab">target</span>'+
    '<span class="mirino-target">'+_esc(r.raw)+'</span></div>'+
    '<div class="mirino-track-wrap">'+
      '<div class="mirino-track">'+
        '<div class="mirino-zone mzone-low" style="width:'+pTargetLo+'%"></div>'+
        '<div class="mirino-zone mzone-target" style="width:'+(pTargetHi-pTargetLo)+'%"></div>'+
        '<div class="mirino-zone mzone-high" style="width:'+(100-pTargetHi)+'%"></div>'+
      '</div>'+
      '<div class="mirino-target-lab" style="left:'+pCentro+'%">zona target</div>'+
    '</div>'+
    '<div class="mirino-scale"><span>'+_fmtN(loScale)+'</span><span>'+_fmtN(r.min)+'</span><span>'+_fmtN(r.max)+'</span><span>'+_fmtN(hiScale)+'</span></div>'+
    '<div class="mirino-input-row">'+
      '<span class="mirino-input-lab">Misura il tuo valore</span>'+
      '<input class="mirino-input" type="text" inputmode="decimal" placeholder="—" id="mirino-val-'+box.id+'">'+
      '<button class="mirino-confronta" onclick="confrontaMirino(\''+box.id+'\')">Confronta</button>'+
    '</div>';
}

function _fmtN(n){
  if(Math.abs(n)>=100) return Math.round(n).toString();
  if(Math.abs(n)>=10) return (Math.round(n*10)/10).toString().replace('.',',');
  return (Math.round(n*100)/100).toString().replace('.',',');
}

// STATO 2: l'utente ha inserito il valore → scarto + azione + rimisura
function confrontaMirino(boxId){
  var box = document.getElementById(boxId); if(!box||!box._range) return;
  var inp = document.getElementById('mirino-val-'+boxId);
  var val = parseFloat((inp.value||'').replace(',','.'));
  if(isNaN(val)) { inp.focus(); return; }
  // Aha Moment: primo uso reale del Mirino (una volta per sessione)
  if(!window._ahaTracked){ window._ahaTracked=true; _trackFunnel('activation', {via:'mirino'}); }
  var r = box._range, sc = box._scale;
  var dentro = val >= r.min && val <= r.max;
  var pCursore = Math.max(0, Math.min(100, ((val - sc.lo)/(sc.hi-sc.lo))*100));
  // scarto
  var scarto = dentro ? 0 : (val < r.min ? val-r.min : val-r.max);
  var scartoTxt = dentro ? 'nel range · nella zona target'
    : (scarto>0?'+':'')+_fmtN(scarto)+' fuori target';
  // azione (delega al chiamante se fornita, altrimenti generica per direzione)
  var azione;
  if(box._azioneFn) azione = box._azioneFn(val, r, dentro);
  else if(dentro) azione = 'Sei nel range. Puoi procedere.';
  else if(val < r.min) azione = 'Il valore è sotto il target. Interviene secondo la tecnica del fenomeno e rimisura.';
  else azione = 'Il valore è sopra il target. Interviene secondo la tecnica del fenomeno e rimisura.';
  // aggiungo il cursore sulla barra — animato: nasce da sinistra e scorre alla misura
  var track = box.querySelector('.mirino-track-wrap');
  var old = box.querySelector('.mirino-cursor'); if(old) old.remove();
  var cur = document.createElement('div');
  cur.className='mirino-cursor'; cur.style.left='0%';
  cur.innerHTML='<span class="mirino-cursor-val">'+_fmtN(val)+'</span>';
  track.appendChild(cur);
  // forzo un reflow poi animo verso la posizione reale (transizione via CSS)
  void cur.offsetWidth;
  cur.style.left=pCursore+'%';
  // se dentro il target, la zona verde fa un glow sobrio a fine corsa
  if(dentro){
    var zt = box.querySelector('.mzone-target');
    if(zt){
      setTimeout(function(){
        zt.classList.add('mzone-hit');
        setTimeout(function(){ zt.classList.remove('mzone-hit'); }, 900);
      }, 380); // dopo che il cursore è arrivato
    }
  }
  // feedback block
  var fb = box.querySelector('.mirino-feedback'); if(fb) fb.remove();
  var div = document.createElement('div');
  div.className='mirino-feedback';
  // disclaimer HACCP: SOLO sui parametri critici di sicurezza alimentare (non su tutto)
  var haccp = _isParametroCritico(box._fenomeno) ?
    '<div class="mirino-haccp">I valori sono modelli predittivi a scopo analitico. '
    + 'L\'operatore è l\'unico responsabile del rispetto dei protocolli HACCP e della '
    + 'validazione ufficiale della stabilità microbiologica degli alimenti somministrati.</div>' : '';
  div.innerHTML =
    '<div class="mirino-scarto '+(dentro?'dentro':'fuori')+'">'+_esc(scartoTxt)+'</div>'+
    '<div class="mirino-azione-lab">cosa fare</div>'+
    '<div class="mirino-azione">'+_esc(azione)+'</div>'+
    haccp+
    '<button class="mirino-rimisura" onclick="resetMirino(\''+box.id+'\')">Rimisura</button>';
  box.appendChild(div);
  // nascondo la riga input (è stata "consumata")
  var ir = box.querySelector('.mirino-input-row'); if(ir) ir.style.display='none';
}

// Riconosce se un fenomeno tocca la SICUREZZA ALIMENTARE (→ serve disclaimer HACCP).
// Deterministico: match su parole-chiave nel nome del fenomeno/tecnica. Conservativo:
// nel dubbio su parametri di conservazione/microbiologia, meglio mostrarlo.
function _isParametroCritico(fenomeno){
  var n = (fenomeno||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  var critici = [
    'fermentazion','fermentat','abbattiment','abbattut','conservazion','conserva',
    'sottovuoto','sotto vuoto','pastorizzazion','pastorizz','sterilizzazion',
    'botulin','clostridium','salmonell','listeria','patogen','microbiolog','carica batterica',
    'temperatura a cuore','cuore del','catena del freddo','abbattitore',
    'ph', 'attivita dell\'acqua','attivita acqua','aw','water activity',
    'marinatur','salamoia','curing','stagionatur','essiccazion','affumicatur',
    'lievito madre','pasta madre','kombucha','koji','miso','garum','lacto'
  ];
  return critici.some(function(k){ return n.indexOf(k)>=0; });
}

function resetMirino(boxId){
  var box=document.getElementById(boxId); if(!box) return;
  renderMirino(box, box._fenomeno, box._range.raw, box._azioneFn);
}

// ── RENDER TARGET: eroe primario + parametri secondari (result first) ──
function _renderTarget(box, target, mostraLabel){
  if(!box) return;
  if(!target){ box.style.display='none'; return; }
  box.style.display='';
  // Architettura "bersaglio a contratto": il primo pezzo e' un NUMERO vero (finestra
  // operativa misurabile) oppure una FRASE-bersaglio (stato da riconoscere). Il display
  // si adatta: mai una frase resa come numero-eroe gigante.
  var parti = target.split(/\s*[·;]\s*/).map(function(s){return s.trim();}).filter(Boolean);
  var primo = parti[0] || target;
  var resto = parti.slice(1);
  var haNumero = /\d/.test(primo) && primo.length <= 32;
  var html = '';
  var free = (typeof _isPro==='function') && !_isPro();
  if(haNumero){
    if(mostraLabel !== false) html += '<div class="target-lab">finestra operativa</div>';
    // La scienza è gratis: il numero è sempre nitido (la leva Pro è sul metodo, non sul numero)
    html += '<div class="target-eroe">' + _esc(primo) + '</div>';
    if(resto.length){
      html += '<div class="target-cond-lab">condizioni</div><div class="target-grid">';
      resto.forEach(function(p){ html += '<div class="target-cond">' + _esc(p) + '</div>'; });
      html += '</div>';
    }
  } else {
    if(mostraLabel !== false) html += '<div class="target-lab">bersaglio</div>';
    html += '<div class="target-frase">' + _esc(primo) + '</div>';
    if(resto.length){
      html += '<div class="target-nota">' + _esc(resto.join(' · ')) + '</div>';
    }
  }
  box.innerHTML = html;
}
function _esc(s){ var d=document.createElement('div'); d.textContent=s; return d.innerHTML; }

// ── FORMATTA LA SCHEDA: spezza il muro + evidenzia i valori ──────
function _formattaScheda(el, testo){
  if(!el) return;
  testo = (testo || '').trim();
  if(!testo){ el.textContent = 'Scheda in aggiornamento.'; return; }
  var reNB = /\s*Numero bersaglio\s*:\s*/i;
  if(reNB.test(testo)){ testo = testo.split(reNB)[0].trim(); }
  var frasi = testo.replace(/([.!?])\s+(?=[A-ZÀ-Ù])/g, '$1|SPLIT|').split('|SPLIT|');
  function evidenzia(s){
    var d = document.createElement('div'); d.textContent = s; s = d.innerHTML;
    s = s.replace(/(\b\d+[.,]?\d*\s?(?:°C|°|%|g\/L|mg\/L|g\b|ml\b|bar\b|µm|Brix|Plato|ABV|Aw|kg\b|h\b|min\b)|\bpH\s?\d+[.,]?\d*(?:-\d+[.,]?\d*)?)/gi,
      '<span class="sch-num">$1</span>');
    return s;
  }
  var html = ''; var buf = [];
  frasi.forEach(function(f, i){
    buf.push(f.trim());
    if(buf.length >= 2 || i === frasi.length - 1){
      html += '<p class="sch-p">' + evidenzia(buf.join(' ')) + '</p>';
      buf = [];
    }
  });
  el.innerHTML = html;
}

function _approfondisciInChat(){
  // prende il fenomeno della lezione corrente e apre la chat già contestualizzata
  var nome = (document.getElementById('les-nome')?.textContent || '').trim();
  var disc = (Matter && Matter.disciplina) ? Matter.disciplina : '';
  if(!nome || nome === '—'){ switchTab('chiedi'); return; }
  // salvo il contesto: la chat lo antepone al prompt così risponde informata
  window._chatContesto = {
    fenomeno: nome,
    disciplina: disc,
    scheda: (document.getElementById('les-scheda')?.textContent || '').slice(0, 600),
    target: (document.getElementById('les-target')?.textContent || '')
  };
  switchTab('chiedi');
  setTimeout(function(){
    var q = document.getElementById('q');
    if(q){
      q.value = nome + ' — nel mio caso specifico: ';
      q.focus();
      // porta il cursore in fondo
      q.setSelectionRange(q.value.length, q.value.length);
    }
    // mostro un indicatore che la chat sa di cosa stiamo parlando
    var badge = document.getElementById('chat-contesto-badge');
    if(badge){
      badge.textContent = 'Contesto: ' + nome;
      badge.style.display = 'inline-flex';
    }
  }, 300);
}

async function inviaFoto(input){
  if(!input||!input.files||!input.files[0]) return;
  var file = input.files[0];
  var tok = localStorage.getItem('matter_token')||'';
  var previewUrl = URL.createObjectURL(file);
  // card con preview + skeleton
  var card = document.createElement('div');
  card.className = 'scheda';
  card.innerHTML =
    '<div class="s-q"><i class="ph ph-camera"></i> '+(_t('foto_analisi_titolo')||'Analisi immagine')+'</div>'
    +'<img src="'+previewUrl+'" style="max-width:100%;max-height:200px;border-radius:10px;margin:8px 0;object-fit:cover">'
    +'<div class="s-body foto-loading"><span class="foto-load-fase" id="foto-load-fase">Riconosco gli ingredienti…</span></div>';
  var schede = document.getElementById('schede');
  if(schede){ schede.prepend(card); schede.scrollTop=0; }
  // TEATRO del caricamento: fasi che avanzano mentre l'AI lavora
  var _fasi = (_lang==='en')
    ? ['Recognizing ingredients…','Searching the phenomena…','Finding the target numbers…','Almost there…']
    : (_lang==='es')
    ? ['Reconozco los ingredientes…','Busco los fenómenos…','Encuentro los números objetivo…','Casi listo…']
    : ['Riconosco gli ingredienti…','Cerco i fenomeni collegati…','Trovo i numeri-bersaglio…','Ci siamo quasi…'];
  var _fi = 0;
  var _faseEl = card.querySelector('#foto-load-fase');
  var _teatro = setInterval(function(){
    _fi++;
    if(_fi < _fasi.length && _faseEl){ _faseEl.textContent = _fasi[_fi]; }
  }, 1400);
  try {
    var fd = new FormData();
    fd.append('immagine', file);
    var _ftok = localStorage.getItem('matter_token')||'';
    if(_ftok) fd.append('token', _ftok);
    var r = await fetch('/v1/foto-analisi?lang='+(_lang||'it'), {
      method:'POST', body:fd
    });
    clearInterval(_teatro);
    if(r.status===402){
      // foto è funzione Pro: mostra il paywall invece dell'errore
      card.remove();
      if(typeof mostraPopupPro==='function') mostraPopupPro('foto');
      else if(typeof apriPaywall==='function') apriPaywall();
      input.value=''; return;
    }
    var j = await r.json();
    var body = card.querySelector('.s-body');
    body.className = 's-body';
    if(j.errore){
      body.textContent = j.errore;
    } else {
      // build rich output
      var html = '';
      // ingredienti trovati — cliccabili → flavor network
      if(j.ingredienti_riconosciuti && j.ingredienti_riconosciuti.length>0){
        html += '<div class="s-block s-block-scient" style="margin-bottom:8px">'
          +'<span class="s-label">Riconosciuti</span><div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:4px">';
        j.ingredienti_riconosciuti.forEach(function(i){
          var nome = (i.nodo_nome||'').replace(/'/g,"\\'");
          html += '<button class="foto-chip" onclick="_fotoVaiFlavor(\''+nome+'\')">'
            +esc(i.nodo_nome)+' <i class="ph ph-arrow-right"></i></button>';
        });
        html += '</div></div>';
      }
      if(j.ingredienti_sconosciuti && j.ingredienti_sconosciuti.length>0){
        html += '<div style="font-size:11px;color:var(--muted);margin-bottom:6px">Non trovati nel grafo: '
          +j.ingredienti_sconosciuti.join(', ')+'</div>';
      }
      // abbinamenti aromatici
      if(j.abbinamenti && j.abbinamenti.length>0){
        html += '<div class="s-block" style="margin-bottom:8px">'
          +'<span class="s-label">Abbinamenti aromatici</span>';
        j.abbinamenti.forEach(function(a){
          html += '<div style="font-size:12px;padding:2px 0"><i class=\'ph ph-link\' style=\'color:var(--flavor)\'></i> <b>'+esc(a.a)+'</b> + <b>'+esc(a.b)+'</b> — '+esc(a.perche)+'</div>';
        });
        html += '</div>';
      }
      // fenomeni — CLICCABILI → studia la lezione (aggancio al loop)
      if(j.fenomeni && j.fenomeni.length>0){
        html += '<div class="s-block" style="margin-bottom:8px">'
          +'<span class="s-label">Studia il fenomeno</span>';
        j.fenomeni.forEach(function(f){
          var fid = (f.id||'').replace(/'/g,"\\'");
          html += '<button class="foto-fen" onclick="_fotoStudiaFenomeno(\''+fid+'\')">'
            +'<i class=\'ph ph-flask\' style=\'color:var(--accent)\'></i> <b>'+esc(f.nome)+'</b>'
            +(f.target?' · <span style="color:var(--accent);font-family:var(--mono);font-size:11px">'+esc(f.target)+'</span>':'')
            +' <i class="ph ph-arrow-right" style="margin-left:auto"></i></button>';
        });
        html += '</div>';
      }
      // output scientifico
      if(j.output_scientifico){
        var _txtAudio = (j.output_scientifico||'').replace(/'/g,"\\'").replace(/\n/g,' ');
        html += '<div class="s-block s-block-action" style="margin-top:8px">'
          +'<div style="display:flex;align-items:center;justify-content:space-between;gap:8px">'
          +'<span class="s-label">Analisi</span>'
          +'<button class="foto-audio-btn" onclick="_fotoAscolta(this,\''+_txtAudio+'\')"><i class="ph ph-speaker-high"></i> Ascolta</button>'
          +'</div>'
          +'<p style="margin:4px 0 0;font-size:13px;line-height:1.5">'+esc(j.output_scientifico)+'</p></div>';
      }
      // AGGANCIO AL LOOP — prossimi passi
      if(j.ingredienti_riconosciuti && j.ingredienti_riconosciuti.length>0){
        html += '<div class="foto-loop">'
          +'<span class="foto-loop-lab">Continua nel laboratorio</span>'
          +'<button class="foto-loop-btn" onclick="switchTab(\'chiedi\');setTimeout(function(){var q=document.getElementById(\'q\');if(q){q.value=\''
          + (j.ingredienti_riconosciuti[0].nodo_nome||'').replace(/'/g,"\\'")
          +' — come lo lavoro?\';q.focus();}},300)"><i class="ph ph-chat-circle"></i> Chiedi come lavorarlo</button>'
          +'<button class="foto-loop-btn" onclick="switchTab(\'mappa\');setTimeout(function(){if(typeof switchMappaTab===\'function\')switchMappaTab(\'ricette\');},300)"><i class="ph ph-cards"></i> Ricette che lo usano</button>'
          +'</div>';
      }
      // coverage
      if(j.meta){
        html += '<div style="font-size:10px;color:var(--muted);margin-top:8px;text-align:right">'
          +'Copertura grafo: '+j.meta.coverage+' ('+j.meta.trovati_grafo+'/'+j.meta.totale_visione+')</div>';
      }
      body.innerHTML = html || '<div style="color:var(--ink-muted);font-size:13px;text-align:center;padding:8px 0"><i class="ph ph-camera-slash" style="font-size:22px;display:block;margin-bottom:6px"></i>Nessun ingrediente riconoscibile — prova con una foto più nitida.</div>';
    }
  } catch(e){
    clearInterval(_teatro);
    var b = card.querySelector('.s-body');
    if(b) b.textContent = 'Errore di rete: '+e.message;
  }
  input.value = '';
}

// ── MICROFONO (Whisper STT) ─────────────────────────────────────
var _mediaRec = null, _audioChunks = [];
async function toggleMic(){
  var btn = document.getElementById('btn-mic');
  if(_mediaRec && _mediaRec.state==='recording'){
    _mediaRec.stop();
    if(btn){ btn.classList.remove('recording'); btn.title='Parla al banco'; }
    return;
  }
  try {
    var stream = await navigator.mediaDevices.getUserMedia({audio:true});
    _audioChunks = [];
    _mediaRec = new MediaRecorder(stream, {mimeType:'audio/webm'});
    _mediaRec.ondataavailable = function(e){ if(e.data.size>0) _audioChunks.push(e.data); };
    _mediaRec.onstop = async function(){
      stream.getTracks().forEach(function(t){t.stop();});
      if(btn) btn.classList.add('processing');
      var blob = new Blob(_audioChunks, {type:'audio/webm'});
      await inviaAudio(blob);
      if(btn) btn.classList.remove('processing');
    };
    _mediaRec.start();
    if(btn){ btn.classList.add('recording'); btn.title='Tocca per fermare'; }
  } catch(e){ alert('Microfono non disponibile: '+e.message); }
}
async function inviaAudio(blob){
  var tok = localStorage.getItem('matter_token')||'';
  try {
    var fd = new FormData();
    fd.append('audio', blob, 'audio.webm');
    var r = await fetch('/v1/stt?lang='+(_lang||'it'), {
      method:'POST', headers:{'X-Token':tok}, body:fd
    });
    var j = await r.json();
    if(j.trascrizione){
      var q = document.getElementById('q');
      if(q){ q.value=j.trascrizione; q.focus(); setTimeout(function(){invia();},800); }
    } else if(j.errore && j.errore.indexOf('Pro')>=0){
      if(typeof mostraPopupPro==='function') mostraPopupPro('stt');
    } else {
      alert(j.errore||'Trascrizione non riuscita.');
    }
  } catch(e){ alert('Errore: '+e.message); }
}

// rileva ?reset=TOKEN nell'URL e mostra la schermata nuova password
(function(){
  const tok=new URLSearchParams(location.search).get('reset');
  if(tok){
    switchTab('auth');
    ['auth-panel-login','auth-panel-reg','auth-panel-reset'].forEach(id=>{
      const el=document.getElementById(id); if(el) el.style.display='none';
    });
    const np=document.getElementById('auth-panel-nuova-pw');
    if(np) np.style.display='block';
  }
})();

// rileva ?verifica=TOKEN nell'URL → attiva account automaticamente
(function(){
  const tok=new URLSearchParams(location.search).get('verifica');
  if(!tok) return;
  // Mostra messaggio di attesa
  document.addEventListener('DOMContentLoaded',()=>{
    switchTab('auth');
  });
  fetch('/v1/auth/verifica-email',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({token:tok})
  })
  .then(r=>r.json())
  .then(j=>{
    if(j.ok && j.token){
      // Account attivato — salva sessione e vai all'app
      localStorage.setItem('ml_token', j.token);
      localStorage.setItem('ml_piano', j.piano||'free');
      // Pulisce il token dall'URL
      history.replaceState({},'','/app');
      // Mostra messaggio di benvenuto e ricarica
      alert('Email confermata! Benvenuto in Matter Bench.');
      location.reload();
    } else {
      alert(j.errore||'Link non valido o scaduto. Prova a registrarti di nuovo.');
      history.replaceState({},'','/app');
    }
  })
  .catch(()=>{
    alert('Errore di rete. Riprova.');
  });
})();

// ═══ SCAVA — motore della longevità reso visibile ═══
// A fine scheda, quattro porte per andare più a fondo nel fenomeno.
// Mostra SOLO le porte che hanno dati reali (niente vicoli ciechi).
function renderScava(scava, nomeFen){
  var box = document.getElementById('les-scava-box');
  if(!box) return;
  if(!scava){ box.style.display='none'; return; }
  var porte = [];
  // 1. ERRORI — il cuore della ritenzione (l'utente col problema risale al fenomeno)
  if(scava.errori && scava.errori.length){
    porte.push({
      cls:'scava-errori', ico:'⚠',
      tit: _L({it:'Vedi gli errori', en:'See the errors', es:'Ver los errores'}),
      sub: scava.errori.length + ' ' + (scava.errori.length===1?
        _L({it:'errore tipico',en:'typical error',es:'error típico'}):
        _L({it:'errori tipici',en:'typical errors',es:'errores típicos'})),
      dett: scava.errori.map(function(e){
        return '<div class="scava-item"><b>'+_esc(e.nome)+'</b>'+
               (e.sintomo?'<span>'+_esc(e.sintomo)+'</span>':'')+'</div>';
      }).join('')
    });
  }
  // 2. CONNESSIONI trasversali — la scoperta cross-disciplina (il "pozzo")
  if(scava.connessioni && scava.connessioni.length){
    porte.push({
      cls:'scava-conn', ico:'⇄',
      tit: _L({it:'Scopri una connessione', en:'Discover a connection', es:'Descubre una conexión'}),
      sub: scava.connessioni.length + ' ' +
        _L({it:'ponte tra discipline',en:'cross-discipline bridge',es:'puente entre disciplinas'}) +
        (scava.connessioni.length>1?'i':''),
      dett: scava.connessioni.map(function(c){
        return '<div class="scava-item"><b>'+_esc(c.nome)+
               (c.dominio?' <span class="scava-dom">'+_esc(c.dominio)+'</span>':'')+'</b>'+
               (c.legame?'<span>'+_esc(c.legame)+'</span>':'')+'</div>';
      }).join('')
    });
  }
  // 3. TECNICHE — come si realizza (con la nota: effetto sul numero)
  if(scava.tecniche && scava.tecniche.length){
    porte.push({
      cls:'scava-tec', ico:'⚙',
      tit: _L({it:'Vedi le tecniche', en:'See the techniques', es:'Ver las técnicas'}),
      sub: scava.tecniche.length + ' ' + (scava.tecniche.length===1?
        _L({it:'tecnica',en:'technique',es:'técnica'}):
        _L({it:'tecniche',en:'techniques',es:'técnicas'})),
      dett: scava.tecniche.map(function(t){
        return '<div class="scava-item"><b>'+_esc(t.nome)+'</b>'+
               (t.nota?'<span>'+_esc(t.nota)+'</span>':'')+'</div>';
      }).join('')
    });
  }
  // 4. STRUMENTI — con cosa si misura
  if(scava.strumenti && scava.strumenti.length){
    porte.push({
      cls:'scava-strum', ico:'◎',
      tit: _L({it:'Come si misura', en:'How to measure', es:'Cómo se mide'}),
      sub: scava.strumenti.map(function(s){return s.nome;}).join(' · '),
      dett: ''
    });
  }
  if(!porte.length){ box.style.display='none'; return; }
  var html = '<div class="scava-titolo">'+
    _L({it:'Scava più a fondo',en:'Dig deeper',es:'Excava más'})+'</div>'+
    '<div class="scava-porte">';
  porte.forEach(function(p, i){
    html += '<button class="scava-porta '+p.cls+'" onclick="toggleScavaPorta('+i+')">'+
      '<span class="scava-ico">'+p.ico+'</span>'+
      '<span class="scava-txt"><span class="scava-porta-tit">'+_esc(p.tit)+'</span>'+
      '<span class="scava-porta-sub">'+_esc(p.sub)+'</span></span>'+
      (p.dett?'<span class="scava-freccia">›</span>':'')+
      '</button>'+
      (p.dett?'<div class="scava-dett" id="scava-dett-'+i+'" style="display:none">'+p.dett+'</div>':'');
  });
  html += '</div>';
  box.innerHTML = html;
  box.style.display = 'block';
}

function toggleScavaPorta(i){
  var d = document.getElementById('scava-dett-'+i);
  if(!d) return;
  var aperto = d.style.display !== 'none';
  d.style.display = aperto ? 'none' : 'block';
}

/* ═══════════════════════════════════════════════════════════════════
   MATTER · VISTE INTEGRATE v1 — Flavour Network · Ponti · Menu Builder
   Overlay a schermo pieno dentro l'app (pattern come onb-overlay).
   Cablate agli endpoint reali (same-origin: nessun problema CORS).
   Accesso: funzioni apriFlavour() / apriPonti() / apriMenuBuilder()
   richiamabili da pulsanti in Scopri e Lab.
   ═══════════════════════════════════════════════════════════════════ */

// helper condivisi
function _escV(s){return (s==null?'':String(s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function _vistaLang(){ return (typeof _lang!=='undefined' && _lang) ? _lang : 'it'; }

// crea (una volta) il contenitore overlay generico per le viste
function _ensureVistaOverlay(){
  let o = document.getElementById('vista-overlay');
  if(!o){
    o = document.createElement('div');
    o.id = 'vista-overlay';
    o.className = 'vista-overlay hidden';
    o.innerHTML = '<div class="vista-topbar"><button class="vista-close" onclick="chiudiVista()" aria-label="Chiudi">‹ Indietro</button><span class="vista-title" id="vista-title"></span></div><div class="vista-body" id="vista-body"></div>';
    document.body.appendChild(o);
  }
  return o;
}
function chiudiVista(){
  const o = document.getElementById('vista-overlay');
  if(o) o.classList.add('hidden');
}
function _apriVista(titolo, htmlIniziale){
  const o = _ensureVistaOverlay();
  document.getElementById('vista-title').textContent = titolo;
  document.getElementById('vista-body').innerHTML = htmlIniziale;
  o.classList.remove('hidden');
  document.getElementById('vista-body').scrollTop = 0;
}

/* ─── mirini svg riusabili ─── */
function _mirinoSorpresa(){return '<svg viewBox="0 0 38 38" fill="none"><circle class="vm-pulse" cx="19" cy="19" r="15" stroke="#131C21" stroke-width="1.5"/><circle cx="19" cy="19" r="8" stroke="#131C21" stroke-width="1.2"/><circle cx="19" cy="19" r="3" fill="#245979"/><path d="M19 2v6M19 30v6M2 19h6M30 19h6" stroke="#131C21" stroke-width="1.5"/></svg>';}
function _mirinoClassico(){return '<svg viewBox="0 0 38 38" fill="none"><circle cx="19" cy="19" r="12" stroke="#12545D" stroke-width="1"/><circle cx="19" cy="19" r="2.5" fill="#12545D"/></svg>';}
function _mirinoPonte(){return '<svg viewBox="0 0 36 36" fill="none"><circle cx="18" cy="18" r="11" stroke="#12545D" stroke-width="1"/><circle cx="18" cy="18" r="2.4" fill="#245979"/><path d="M18 3v5M18 28v5M3 18h5M28 18h5" stroke="#12545D" stroke-width="1"/></svg>';}

/* ═══════════════ 1. FLAVOUR NETWORK ═══════════════ */
function apriFlavour(ingredienteIniziale){
  _apriVista('Flavour Network',
    '<div class="fnv-head"><div class="fnv-h">Cosa dialoga con cosa.</div>'+
    '<div class="fnv-sub">Non opinioni: composti aromatici condivisi.</div>'+
    '<div class="fnv-search"><input id="fnv-input" placeholder="fragola, lime, pomodoro…" '+
    'onkeydown="if(event.key===\'Enter\')caricaFlavour()"><button onclick="caricaFlavour()">Cerca</button></div>'+
    '<div class="fnv-chips">'+['fragola','pomodoro','lime','cioccolato','basilico'].map(c=>'<span class="fnv-chip" onclick="caricaFlavour(\''+c+'\')">'+c+'</span>').join('')+'</div>'+
    '</div><div id="fnv-out"></div>');
  caricaFlavour(ingredienteIniziale || 'fragola');
}
async function caricaFlavour(term){
  const inp = document.getElementById('fnv-input') || document.getElementById('flavor-query');
  const q = (term || (inp?inp.value:'') || '').trim();
  if(!q) return;
  if(inp) inp.value = q;
  // feedback netto: evidenzio la chip attiva
  document.querySelectorAll('.fnv-chip').forEach(function(c){ c.classList.toggle('attiva', c.textContent.trim().toLowerCase()===q.toLowerCase()); });
  const out = document.getElementById('fnv-out');
  if(!out) return;
  out.innerHTML = '<div class="vista-loading">Leggo il grafo dei composti…</div>';
  try{
    const r = await fetch('/v1/abbina/'+encodeURIComponent(q)+'?lang='+_vistaLang());
    const d = await r.json();
    if(!d.abbinamenti || !d.abbinamenti.length){ out.innerHTML = '<div class="vista-empty">Nessun dato per questo ingrediente.</div>'; return; }
    const sorpr = d.abbinamenti.filter(a=>a.sorprendente);
    const classici = d.abbinamenti.filter(a=>!a.sorprendente);
    let h = '<div class="fnv-center"><div class="fnv-center-lab">◉ Ingrediente</div><div class="fnv-center-name">'+_escV(d.ingrediente||q)+'</div>'+(d.nota?'<div class="fnv-center-nota">'+_escV(d.nota)+'</div>':'')+'</div>';
    if(sorpr.length){
      h += '<div class="fnv-sec-h"><span class="t">Sorprendenti</span><span class="rule"></span><span class="cnt">'+sorpr.length+'</span></div>';
      h += sorpr.map((a,i)=>_flavourNode(a,'s'+i,true,d.ingrediente||q)).join('');
    }
    if(classici.length){
      h += '<div class="fnv-sec-h"><span class="t">'+(sorpr.length?'Classici':'Abbinamenti')+'</span><span class="rule"></span><span class="cnt">'+classici.length+'</span></div>';
      h += classici.map((a,i)=>_flavourNode(a,'c'+i,false,d.ingrediente||q)).join('');
    }
    out.innerHTML = h;
  }catch(e){ out.innerHTML = '<div class="vista-empty">Errore di rete. Riprova.</div>'; }
}
function _flavourNode(a,key,surprise,centro){
  const n = Math.round(a.overlap||0);
  // TUTTI i nodi (classici e sorprendenti) hanno il dettaglio espandibile con il bottone "Crea ricetta"
  const perche = surprise
    ? (_escV(centro)+' e '+_escV(a.ingrediente)+' condividono <b>'+n+' composti aromatici</b>. '+_escV(a.perche||'')+' Non è un\'opinione: è chimica.')
    : (_escV(centro)+' e '+_escV(a.ingrediente)+' condividono <b>'+n+' composti aromatici</b>. '+_escV(a.perche||'Un abbinamento classico, confermato dalla chimica.'));
  const det = '<div class="fnv-detail" id="fnv-det-'+key+'"><div class="fnv-detail-why">'+perche+'</div><button class="fnv-cta" onclick="event.stopPropagation();_flavourCrea(\''+_escV(centro)+'\',\''+_escV(a.ingrediente)+'\')">Crea una ricetta con questo abbinamento →</button></div>';
  return '<div class="fnv-node'+(surprise?' surprise':'')+'" onclick="_flavourToggle(\''+key+'\')">'+
    '<div class="fnv-mirino">'+(surprise?_mirinoSorpresa():_mirinoClassico())+'</div>'+
    '<div class="fnv-node-body"><div class="fnv-node-name">'+_escV(a.ingrediente)+'</div>'+
    '<div class="fnv-node-why">'+(surprise?'Sorprendente — tocca per il perché':'Tocca per il perché')+'</div></div>'+
    '<div class="fnv-node-n">'+n+'<span class="u">composti</span></div></div>'+det;
}
function _flavourToggle(key){ const d=document.getElementById('fnv-det-'+key); if(d) d.classList.toggle('show'); }
async function _flavourCrea(a,b){
  // tocca abbinamento → ricetta in vista dedicata (NON chat)
  _apriVista('Creo la ricetta…', '<div class="calc-loading" style="padding:40px;text-align:center">Sto creando la ricetta con '+_escV(a)+' e '+_escV(b)+'…</div>');
  var disc = localStorage.getItem('matter_station') || 'cucina';
  try{
    var r=await fetch('/v1/genera-ricetta',{method:'POST',headers:_statoHeaders({'Content-Type':'application/json'}),
      body:JSON.stringify({richiesta: a+' e '+b, disciplina:disc})});
    var j=await r.json();
    if(j && j.errore==='non_trovata'){
      var bd=document.getElementById('vista-body'); if(bd) bd.innerHTML='<div class="quad-empty"><b>Non riesco a creare questo piatto</b><span>'+_escV(j.messaggio||'Prova un altro abbinamento.')+'</span></div>';
      return;
    }
    if(j && (j.nome||j.ingredienti)){ mostraRicettaGen(j); }
    else { var bd2=document.getElementById('vista-body'); if(bd2) bd2.innerHTML='<div class="quad-empty"><b>Non riesco a creare la ricetta ora</b><span>Riprova tra poco.</span></div>'; }
  }catch(e){ var bd3=document.getElementById('vista-body'); if(bd3) bd3.innerHTML='<div class="quad-empty"><b>Errore di rete</b><span>Riprova.</span></div>'; }
}

/* ═══════════════ 2. PONTI TRA DISCIPLINE ═══════════════ */
let _pontiTab = 'vino';
function apriPonti(){
  _apriVista('Ponti tra discipline',
    '<div class="ptv-head"><div class="ptv-h">Il piatto non è mai solo.</div>'+
    '<div class="ptv-sub">Cosa dialoga col tuo piatto — e perché.</div>'+
    '<div class="ptv-field"><input id="ptv-input" placeholder="brasato, pizza, pesce…" onkeydown="if(event.key===\'Enter\')caricaPonti()"></div>'+
    '<div class="ptv-tabs">'+
      '<div class="ptv-tab on" data-t="vino" onclick="_pontiSetTab(\'vino\')">Vino</div>'+
      '<div class="ptv-tab" data-t="birra" onclick="_pontiSetTab(\'birra\')">Birra</div>'+
      '<div class="ptv-tab" data-t="dolce" onclick="_pontiSetTab(\'dolce\')">Dolce</div>'+
    '</div><button class="ptv-go" onclick="caricaPonti()">Trova il dialogo</button></div><div id="ptv-out"></div>');
  _pontiTab = 'vino';
}
function _pontiSetTab(t){
  _pontiTab = t;
  document.querySelectorAll('.ptv-tab').forEach(x=>x.classList.toggle('on', x.dataset.t===t));
}
async function caricaPonti(){
  const inp = document.getElementById('ptv-input');
  const q = (inp?inp.value:'').trim();
  if(!q) return;
  const out = document.getElementById('ptv-out');
  out.innerHTML = '<div class="vista-loading">Cerco il dialogo…</div>';
  const urls = {
    vino: '/v1/vino-per-piatto?piatto='+encodeURIComponent(q)+'&lang='+_vistaLang(),
    birra:'/v1/birra-per-piatto?piatto='+encodeURIComponent(q)+'&lang='+_vistaLang(),
    dolce:'/v1/dolce-per-menu?menu='+encodeURIComponent(q)+'&lang='+_vistaLang()
  };
  try{
    const r = await fetch(urls[_pontiTab]);
    const d = await r.json();
    if(_pontiTab==='vino') out.innerHTML = _pontiVino(d);
    else if(_pontiTab==='birra') out.innerHTML = _pontiBirra(d);
    else out.innerHTML = _pontiDolce(d);
  }catch(e){ out.innerHTML = '<div class="vista-empty">Nessun dialogo trovato.</div>'; }
}
function _pontiNota(txt){ return txt ? '<div class="ptv-nota"><div class="ptv-nota-lab">◉ Il principio</div><div class="ptv-nota-txt">'+_escV(txt)+'</div></div>' : ''; }
function _pontiVino(d){
  if(!d.suggerimenti||!d.suggerimenti.length) return '<div class="vista-empty">Nessun vino in dialogo.</div>';
  return _pontiNota(d.nota) + d.suggerimenti.map(cat=>
    '<div class="ptv-cat"><div class="ptv-cat-name">'+_escV(cat.categoria)+'</div>'+
    (cat.descrizione?'<div class="ptv-cat-desc">'+_escV(cat.descrizione)+'</div>':'')+
    (cat.vini_consigliati||[]).map(v=>'<div class="ptv-item"><div class="ptv-item-mirino">'+_mirinoPonte()+'</div><div class="ptv-item-body"><div class="ptv-item-name">'+_escV(v.nome)+(v.territorio?' <span class="ptv-item-terr">'+_escV(v.territorio)+'</span>':'')+'</div>'+(v.perche?'<div class="ptv-item-why">'+_escV(v.perche)+'</div>':'')+'</div></div>').join('')+
    '</div>').join('');
}
function _pontiBirra(d){
  if(!d.birre_in_dialogo||!d.birre_in_dialogo.length) return '<div class="vista-empty">Nessuna birra in dialogo.</div>';
  return _pontiNota(d.nota) + d.birre_in_dialogo.map(b=>
    '<div class="ptv-item"><div class="ptv-item-mirino">'+_mirinoPonte()+'</div><div class="ptv-item-body"><div class="ptv-item-name">'+_escV(b.categoria)+'</div>'+
    (b.perche?'<div class="ptv-item-why">'+_escV(b.perche)+'</div>':'')+
    (b.profilo?'<div class="ptv-item-profilo">Profilo: '+_escV(b.profilo)+'</div>':'')+
    (b.abbina?'<div class="ptv-item-profilo">Va con: '+_escV(b.abbina)+'</div>':'')+'</div></div>').join('');
}
function _pontiDolce(d){
  const dc = d.dessert_consigliato;
  if(!dc) return '<div class="vista-empty">Nessun dessert consigliato.</div>';
  return '<div class="ptv-dessert"><div class="ptv-dessert-tipo">'+_escV(dc.tipo||'Dessert consigliato')+'</div>'+
    (dc.perche?'<div class="ptv-dessert-why">'+_escV(dc.perche)+'</div>':'')+
    (dc.esempi&&dc.esempi.length?'<div class="ptv-dessert-lab">Esempi</div>'+dc.esempi.map(e=>'<div class="ptv-dessert-item"><span class="b"></span>'+_escV(e)+'</div>').join(''):'')+'</div>';
}

/* ═══════════════ 3. MENU BUILDER ═══════════════ */
let _menuIngredienti = [];
// ═══ RICETTARIO DEI PROFESSIONISTI — le 454 ricette certificate (separato dal Quaderno) ═══
var _ricettarioDisc = null;
async function apriRicettario(){
  _apriVista('Ricettario dei Professionisti',
    '<div class="ric-search"><input type="text" id="ricp-q" placeholder="Cerca tra le 454 ricette certificate…" onkeydown="if(event.key===\'Enter\')_ricettarioCerca()"><button onclick="_ricettarioCerca()">Cerca</button></div>'
    + '<div class="ric-disc-chips" id="ricp-chips"></div>'
    + '<div id="ricp-out"><div class="calc-loading">Carico il ricettario…</div></div>');
  try{
    var r=await fetch('/v1/ricettario/discipline');
    var j=await r.json();
    _ricettarioDisc=j.discipline||[];
    var e=_escV;
    var chips=document.getElementById('ricp-chips');
    if(chips){
      chips.innerHTML=(j.discipline||[]).map(function(d){
        return '<span class="ric-disc-chip" onclick="_ricettarioDisciplina(\''+e(d.disciplina)+'\',this)">'+e(d.disciplina)+' <span class="ric-disc-n">'+d.n+'</span></span>';
      }).join('');
    }
    // carico la prima disciplina di default
    if((j.discipline||[]).length){ _ricettarioDisciplina(j.discipline[0].disciplina, null); }
  }catch(e){ var o=document.getElementById('ricp-out'); if(o) o.innerHTML='<div class="vista-empty">Errore di rete.</div>'; }
}
async function _ricettarioDisciplina(disc, chip){
  document.querySelectorAll('.ric-disc-chip').forEach(function(c){ c.classList.remove('on'); });
  if(chip) chip.classList.add('on');
  else { var first=document.querySelector('.ric-disc-chip'); if(first) first.classList.add('on'); }
  _ricettarioCarica('disciplina='+encodeURIComponent(disc));
}
function _ricettarioCerca(){
  var q=(document.getElementById('ricp-q')||{}).value||'';
  if(!q.trim()){ return; }
  document.querySelectorAll('.ric-disc-chip').forEach(function(c){ c.classList.remove('on'); });
  _ricettarioCarica('q='+encodeURIComponent(q.trim()));
}
async function _ricettarioCarica(query){
  var out=document.getElementById('ricp-out'); if(out) out.innerHTML='<div class="calc-loading">Carico…</div>';
  try{
    var r=await fetch('/v1/ricettario/canonico?'+query+'&limit=30');
    var j=await r.json();
    var ric=j.ricette||[];
    var e=_escV;
    if(!ric.length){ out.innerHTML='<div class="vista-empty">Nessuna ricetta trovata.</div>'; return; }
    out.innerHTML='<div class="ricp-griglia">'+ric.map(function(x){
      var img='';
      if(x.immagine){
        if(x.immagine.tipo==='foto' && x.immagine.url){ img='<img src="'+e(x.immagine.url)+'" alt="" loading="lazy">'; }
        else if(x.immagine.tipo==='blueprint' && x.immagine.famiglia){ img='<img src="/static/blueprints/'+e(x.immagine.famiglia)+'.svg" alt="" loading="lazy">'; }
      }
      return '<div class="ricp-card" onclick="_ricettarioApri(\''+e(x.id)+'\',\''+e(String(x.nome)).replace(/'/g,"\\'")+'\')">'
        + '<div class="ricp-img">'+img+(x.certificata?'<span class="ricp-cert">✓ Lab</span>':'')+'</div>'
        + '<div class="ricp-nome">'+e(x.nome||'')+'</div>'
        + (x.fenomeno?'<div class="ricp-fen">'+e(x.fenomeno)+'</div>':'')
        + '</div>';
    }).join('')+'</div>';
  }catch(e){ if(out) out.innerHTML='<div class="vista-empty">Errore.</div>'; }
}
function _ricettarioApri(id, nome){
  // apre la scheda scientifica della ricetta canonica
  if(typeof apriNodo==='function' && id){ chiudiVista(); apriNodo(id, nome||''); }
}
// ═══ RIUSO SCARTI / cross-utilization (#2) ═══
// ═══ DOVE LO COMPRO — rendering multi-store (Amazon + Special Ingredients) ═══
async function _doveComprare(ingrediente, el){
  if(!ingrediente) return;
  var esistente = el && el.parentElement ? el.parentElement.querySelector('.store-box') : null;
  if(esistente){ esistente.remove(); return; }
  var box=document.createElement('div'); box.className='store-box'; box.innerHTML='<div class="store-loading">Cerco…</div>';
  if(el && el.parentElement) el.parentElement.appendChild(box);
  try{
    var lang=(typeof _lang!=='undefined'?_lang:'it');
    var r=await fetch('/v1/prodotto?q='+encodeURIComponent(ingrediente)+'&lang='+lang);
    var j=await r.json();
    var e=_escV;
    var stores=j.stores||[];
    if(!stores.length){ box.innerHTML='<div class="store-vuoto">Nessun negozio trovato.</div>'; return; }
    var html=stores.map(function(s){
      return '<a class="store-btn'+(/special/i.test(s.store||'')?' store-special':'')+'" href="'+e(s.url||'#')+'" target="_blank" rel="noopener sponsored">'
        + '<span class="store-nome">Compra su '+e(s.store||'')+'</span>'
        + (s.nota?'<span class="store-nota">'+e(s.nota)+'</span>':'')
        + '</a>';
    }).join('');
    if(j.disclosure){ html+='<div class="store-disclosure">'+e(j.disclosure)+'</div>'; }
    box.innerHTML=html;
  }catch(e){ box.innerHTML='<div class="store-vuoto">Non riesco a cercare ora.</div>'; }
}
async function apriScarti(){
  _apriVista('Recupera gli scarti',
    '<div class="cf-intro">Ogni scarto è un ingrediente che non hai ancora usato. Matter Bench ti dice come riusarlo e per quanti giorni.</div>'
    + '<div id="scarti-out"><div class="calc-loading">Carico la libreria…</div></div>');
  try{
    var r=await fetch('/v1/scarti/libreria');
    var j=await r.json();
    // j può essere {scarti:[...]} o un dict
    var lista = j.scarti || (Array.isArray(j)?j:Object.values(j));
    if(!Array.isArray(lista)){ lista=Object.values(j); }
    var e=_escV;
    var out=document.getElementById('scarti-out');
    if(!lista.length){ out.innerHTML='<div class="vista-empty">Libreria non disponibile.</div>'; return; }
    out.innerHTML=lista.map(function(s){
      var riusi=(s.riusi||[]).map(function(r){ return '<span class="scarto-riuso">'+e(r)+'</span>'; }).join('');
      return '<div class="scarto-card">'
        + '<div class="scarto-nome">'+e(s.scarto||'')+'</div>'
        + (s.nasce_da?'<div class="scarto-nasce">da '+e(s.nasce_da)+'</div>':'')
        + '<div class="scarto-riusi">'+riusi+'</div>'
        + '<div class="scarto-foot">'
        +   (s.shelf_giorni?'<span class="scarto-shelf">entro '+e(String(s.shelf_giorni))+' giorni</span>':'')
        +   '<span class="scarto-compra" onclick="_doveComprare(\''+e(String(s.scarto||'')).replace(/'/g,"\\'")+'\',this)">Dove lo compro</span>'
        +   (s.fenomeno_id?'<span class="scarto-link" onclick="chiudiVista();apriNodo(\''+e(s.fenomeno_id)+'\',\'\')">la scienza →</span>':'')
        + '</div>'
        + '</div>';
    }).join('');
  }catch(e){ var o=document.getElementById('scarti-out'); if(o) o.innerHTML='<div class="vista-empty">Errore di rete.</div>'; }
}
// ═══ CARTA VINI — flusso filosofia (brief → filo conduttore → crea) ═══
var _cartaFilosofia = null;
function apriCartaFilosofia(){
  _apriVista('La tua carta dei vini',
    '<div class="cf-intro">Prima dei vini, il <b>filo conduttore</b>. Raccontami il locale: Matter Bench costruisce la filosofia che tiene insieme la carta.</div>'
    + '<div class="calc-form">'
    + '<div class="calc-field"><label>Che locale è (vibe)</label><input type="text" id="cf-vibe" placeholder="es. bistrot di mare, osteria moderna…"></div>'
    + '<div class="calc-field"><label>Territorio</label><input type="text" id="cf-terr" placeholder="es. Costiera Amalfitana, Langhe…"></div>'
    + '<div class="calc-field"><label>Filo conduttore</label><input type="text" id="cf-filo" placeholder="es. agrumi e affumicato, montagna e selvaggina…"></div>'
    + '<div class="calc-field"><label>Tema grafico del PDF</label><select id="cf-tema" class="calc-select">'
    +   '<option value="enoteca-classica">Enoteca classica (elegante)</option>'
    +   '<option value="minimal-blueprint">Minimal blueprint (tecnico)</option>'
    +   '<option value="gastro-bistrot">Gastro bistrot (moderno)</option>'
    + '</select></div>'
    + '<button class="calc-go" onclick="_generaFilosofia()">Genera il filo conduttore</button>'
    + '</div><div id="cf-out"></div>');
}
async function _generaFilosofia(){
  var vibe=(document.getElementById('cf-vibe')||{}).value||'';
  var terr=(document.getElementById('cf-terr')||{}).value||'';
  var filo=(document.getElementById('cf-filo')||{}).value||'';
  var tema=(document.getElementById('cf-tema')||{}).value||'enoteca-classica';
  if(!vibe.trim() && !terr.trim()){ _toast('Dimmi almeno il vibe o il territorio'); return; }
  var out=document.getElementById('cf-out'); if(out) out.innerHTML='<div class="calc-loading">Costruisco la filosofia…</div>';
  try{
    var r=await fetch('/v1/menu/filosofia', {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}),
      body:JSON.stringify({vibe:vibe.trim(), territorio:terr.trim(), filo_conduttore:filo.trim(), tipo_menu:'wine', stagione:'', fascia_prezzo:'media'})});
    var j=await r.json();
    var e=_escV;
    _cartaFilosofia = {filosofia_riassunto:j.filosofia_riassunto||'', regola_di_coerenza:j.regola_di_coerenza||'', tema_grafico:tema, macro:j.macro_ingredienti_target||[]};
    var macro=(j.macro_ingredienti_target||[]).map(function(m){ return '<span class="cf-macro">'+e(m)+'</span>'; }).join('');
    if(out) out.innerHTML=
      '<div class="cf-filosofia">'
      + '<div class="cf-fil-lab">Il filo conduttore</div>'
      + '<div class="cf-fil-testo">'+e(j.filosofia_riassunto||'')+'</div>'
      + (j.regola_di_coerenza?'<div class="cf-regola"><span class="cf-regola-lab">Regola di coerenza</span>'+e(j.regola_di_coerenza)+'</div>':'')
      + (macro?'<div class="cf-macro-wrap">'+macro+'</div>':'')
      + '<button class="calc-go" onclick="_cartaProsegui()">Aggiungi i vini →</button>'
      + '</div>';
  }catch(e){ if(out) out.innerHTML='<div class="calc-err">Errore. Riprova.</div>'; }
}
function _cartaProsegui(){
  // porta al builder normale, con la filosofia salvata (usata in creaMenu/esporta)
  _mbCategoria='carta_vini';
  window._filosofiaCorrente = _cartaFilosofia;
  creaMenu();
}
function apriMenuBuilder(){
  _menuIngredienti = [];
  _apriVista('Menu Lab',
    '<div class="mbv-head"><div class="mbv-h">Costruisci per composti.</div>'+
    '<div class="mbv-sub">Aggiungi ingredienti: Matter trova le combinazioni che dialogano, dal grafo aromatico reale.</div>'+
    '<div class="mbv-add"><input id="mbv-input" placeholder="aggiungi un ingrediente…" onkeydown="if(event.key===\'Enter\')mbAdd()"><button onclick="mbAdd()">+</button></div>'+
    '<div class="mbv-chips" id="mbv-chips"></div>'+
    '<button class="mbv-go" id="mbv-go" onclick="mbProposte()" disabled>Trova le combinazioni</button></div>'+
    '<div id="mbv-out"></div>');
  _mbRenderChips();
}
function mbAdd(ing){
  const inp = document.getElementById('mbv-input');
  const v = (ing || (inp?inp.value:'') || '').trim().toLowerCase();
  if(!v) return;
  if(!_menuIngredienti.includes(v)) _menuIngredienti.push(v);
  if(inp) inp.value = '';
  _mbRenderChips();
}
function mbRemove(i){ _menuIngredienti.splice(i,1); _mbRenderChips(); }
function _mbRenderChips(){
  const box = document.getElementById('mbv-chips');
  if(!box) return;
  box.innerHTML = _menuIngredienti.map((x,i)=>'<span class="mbv-chip">'+_escV(x)+'<button onclick="mbRemove('+i+')" aria-label="Rimuovi">×</button></span>').join('')
    || '<span class="mbv-chip-hint">Aggiungi almeno 2 ingredienti.</span>';
  const go = document.getElementById('mbv-go');
  if(go){
    go.disabled = _menuIngredienti.length < 2;
    // messaggio chiaro sul bottone: fa capire perché è disabilitato
    if(_menuIngredienti.length===0){ go.textContent='Aggiungi 2 ingredienti'; }
    else if(_menuIngredienti.length===1){ go.textContent='Aggiungine ancora 1'; }
    else { go.textContent='Trova le combinazioni ('+_menuIngredienti.length+')'; }
  }
}
async function mbProposte(){
  const out = document.getElementById('mbv-out');
  out.innerHTML = '<div class="vista-loading">Cerco le combinazioni nel grafo…</div>';
  try{
    const r = await fetch('/v1/menu/proposte', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ ingredienti:_menuIngredienti, tipo:'piatto', lang:_vistaLang() })
    });
    const d = await r.json();
    if(!d.proposte || !d.proposte.length){ out.innerHTML = '<div class="vista-empty">Nessuna combinazione forte tra questi ingredienti. Prova ad aggiungerne altri.</div>'; return; }
    let h = (d.fonte?'<div class="mbv-fonte">'+_escV(d.fonte)+'</div>':'');
    h += d.proposte.map(p=>{
      const ings = (p.ingredienti||[]).map(x=>'<span class="mbv-pill">'+_escV(x)+'</span>').join('');
      const conn = p.connessioni || (p.proof&&p.proof.connessioni_aromatiche) || 0;
      // A6: badge robustezza (forte/media/da esplorare)
      var rob='';
      if(p.robustezza){
        var rc = /forte/i.test(p.robustezza)?'forte':(/media/i.test(p.robustezza)?'media':'esplorare');
        rob = '<span class="mbv-rob mbv-rob-'+rc+'"><span class="mbv-rob-dot"></span>'+_escV(p.robustezza)+'</span>';
      }
      return '<div class="mbv-prop"><div class="mbv-prop-top"><span class="mbv-prop-tipo">'+_escV(p.tipo||'combinazione')+'</span>'+rob+
        '<span class="mbv-prop-conn">'+conn+'<span class="u">connessioni</span></span></div>'+
        '<div class="mbv-prop-ings">'+ings+'</div>'+
        '<button class="mbv-prop-cta" onclick="_mbCreaRicetta(\''+_escV((p.ingredienti||[]).join(', '))+'\')">Crea un piatto →</button></div>';
    }).join('');
    out.innerHTML = h;
  }catch(e){ out.innerHTML = '<div class="vista-empty">Errore di rete. Riprova.</div>'; }
}
function _mbCreaRicetta(ings){
  chiudiVista();
  if(typeof switchTab==='function') switchTab('chiedi');
  const ask = document.getElementById('ask-input');
  if(ask){ ask.value = 'Crea un piatto con '+ings; if(typeof inviaDomanda==='function') inviaDomanda(); }
}

/* ═══════════════ 4. STRUMENTI DI MISURA ═══════════════ */
// ═══ CALCOLATORI 2.0 — scalatore impasto · conversione teglie · food cost piatto ═══
// ═══ TECNICHE AVANZATE DI LABORATORIO (punto 7) — leva Pro, contenuto premium ═══
async function apriAvanzate(){
  _apriVista('Tecniche Avanzate',
    '<div class="avz-intro">I fenomeni che un professionista esperto non trova altrove. Fat washing, koji, nixtamalizzazione, wok hei, tandoor…</div>'
    + '<div id="avz-out"><div class="calc-loading">Carico le tecniche…</div></div>');
  try{
    var r=await fetch('/fenomeni-avanzati?lang='+_vistaLang());
    var j=await r.json();
    var fen=j.fenomeni||[];
    var out=document.getElementById('avz-out');
    if(!fen.length){ out.innerHTML='<div class="vista-empty">Nessuna tecnica disponibile.</div>'; return; }
    // raggruppo per dominio
    var perDom={};
    fen.forEach(function(f){ var d=f.dominio||'altro'; (perDom[d]=perDom[d]||[]).push(f); });
    var html='<div class="avz-count">'+fen.length+' tecniche avanzate</div>';
    Object.keys(perDom).forEach(function(dom){
      html+='<div class="avz-dom-lab">'+_escV(dom)+'</div>';
      html+=perDom[dom].map(function(f){
        return '<div class="avz-card" onclick="chiudiVista();apriNodo(\''+_escV(f.id)+'\',\''+_escV(f.nome).replace(/'/g,"\\'")+'\')">'
          + '<div class="avz-card-main"><div class="avz-card-nome">'+_escV(f.nome)+'</div>'
          + (f.sommario?'<div class="avz-card-sum">'+_escV(f.sommario)+'</div>':'')+'</div>'
          + '<span class="avz-card-arr">→</span></div>';
      }).join('');
    });
    out.innerHTML=html;
  }catch(e){
    var o=document.getElementById('avz-out'); if(o) o.innerHTML='<div class="vista-empty">Errore di rete. Riprova.</div>';
  }
}
function apriCalcolatori(){
  _apriVista('Calcolatori',
    '<div class="calc-intro">Strumenti del banco. Ogni risultato ti dice cosa significa e cosa fare.</div>'
    + '<div class="calc-menu">'
    +   '<button class="calc-menu-btn on" onclick="_calcTab(\'impasto\',this)">Scalatore impasto</button>'
    +   '<button class="calc-menu-btn" onclick="_calcTab(\'teglie\',this)">Conversione teglie</button>'
    +   '<button class="calc-menu-btn" onclick="_calcTab(\'foodcost\',this)">Food cost piatto</button>'
    +   '<button class="calc-menu-btn" onclick="_calcTab(\'calo\',this)">Resa / calo peso</button>'
    +   '<button class="calc-menu-btn" onclick="_calcTab(\'vino\',this)">Temperatura vino</button>'
    +   '<button class="calc-menu-btn" onclick="_calcTab(\'brix\',this)">Brix → ABV</button>'
    + '</div>'
    + '<div id="calc-body"></div>');
  _calcRenderImpasto();
}
function _calcTab(which, btn){
  document.querySelectorAll('.calc-menu-btn').forEach(function(b){ b.classList.remove('on'); });
  if(btn) btn.classList.add('on');
  if(which==='impasto') _calcRenderImpasto();
  else if(which==='teglie') _calcRenderTeglie();
  else if(which==='vino') _calcRenderVino();
  else if(which==='calo') _calcRenderCalo();
  else if(which==='brix') _calcRenderBrix();
  else _calcRenderFoodCost();
}
function _calcBody(html){ var b=document.getElementById('calc-body'); if(b) b.innerHTML=html; }
// risultato comune: interpretazione (carta) + leva (teal) + link fenomeno
function _calcRisultato(numeroHtml, j, bersaglio){
  var h = '<div class="calc-mirino calc-mirino-anim">'+numeroHtml+'</div>';
  // #3 MIRINO-SISTEMA: il backend manda i campi bersaglio → ago su TUTTI i calcolatori col range
  if(!bersaglio && j && j.valore_corrente!=null && j.scala_min!=null && j.scala_max!=null){
    bersaglio = {
      valore: j.valore_corrente, min: j.scala_min, max: j.scala_max,
      bersaglio_min: j.bersaglio_min, bersaglio_max: j.bersaglio_max,
      unita: j.unita_mirino||'', dentro: j.dentro_bersaglio
    };
  }
  if(bersaglio && bersaglio.valore!=null){
    h += _barraMirino(bersaglio);
  }
  if(j.interpretazione){ h += '<div class="calc-interp">'+_escV(j.interpretazione)+'</div>'; }
  if(j.leva_azione){ h += '<div class="calc-leva"><span class="calc-leva-lab">Cosa fare</span>'+_escV(j.leva_azione)+'</div>'; }
  if(j.fenomeno_id){ h += '<button class="calc-fen-link" onclick="apriNodo(\''+_escV(j.fenomeno_id)+'\',\'\')">Studia il fenomeno →</button>'; }
  return h;
}
// barra graduata orizzontale con l'ago-Mirino che scorre fino al valore
function _barraMirino(b){
  var min=b.min, max=b.max, val=b.valore;
  var lo=b.bersaglio_min, hi=b.bersaglio_max;
  var pos=Math.max(0, Math.min(100, ((val-min)/(max-min))*100));
  // uso dentro_bersaglio del backend se presente, altrimenti calcolo
  var centrato = (typeof b.dentro==='boolean') ? b.dentro : ((lo!=null && hi!=null) ? (val>=lo && val<=hi) : false);
  // zona bersaglio evidenziata
  var zonaL = (lo!=null) ? Math.max(0,((lo-min)/(max-min))*100) : 0;
  var zonaW = (lo!=null && hi!=null) ? Math.min(100-zonaL, ((hi-lo)/(max-min))*100) : 0;
  var id='mir-'+Math.random().toString(36).slice(2,7);
  var html='<div class="mirino-barra '+(centrato?'centrato':'fuori')+'">'
    + '<div class="mirino-track">'
    +   (zonaW>0?'<div class="mirino-zona" style="left:'+zonaL+'%;width:'+zonaW+'%"></div>':'')
    +   '<div class="mirino-ago" id="'+id+'" style="left:0%">'
    +     '<svg viewBox="0 0 24 24" width="28" height="28"><circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="2"/>'
    +     '<line x1="12" y1="1" x2="12" y2="4" stroke="currentColor" stroke-width="2"/><line x1="12" y1="20" x2="12" y2="23" stroke="currentColor" stroke-width="2"/>'
    +     '<line x1="1" y1="12" x2="4" y2="12" stroke="currentColor" stroke-width="2"/><line x1="20" y1="12" x2="23" y2="12" stroke="currentColor" stroke-width="2"/>'
    +     '<circle cx="12" cy="12" r="3" fill="currentColor"/></svg>'
    +   '</div>'
    + '</div>'
    + '<div class="mirino-scala"><span>'+_escV(String(min))+(b.unita||'')+'</span><span>'+_escV(String(max))+(b.unita||'')+'</span></div>'
    + (centrato?'<div class="mirino-verdetto centrato">◎ Bersaglio centrato</div>':'<div class="mirino-verdetto fuori">Fuori dal bersaglio</div>')
    + '</div>';
  // animo l'ago dopo il render (transizione cubica 0.6s)
  setTimeout(function(){ var a=document.getElementById(id); if(a) a.style.left=pos+'%'; }, 80);
  return html;
}
// --- Scalatore impasto ---
function _calcRenderImpasto(){
  _calcBody(
    '<div class="calc-form">'
    + '<div class="calc-field"><label>Peso totale impasto (g)</label><input type="number" inputmode="numeric" id="ci-peso" placeholder="1000"></div>'
    + '<div class="calc-perc-lab">Percentuali del panettiere (farina = 100)</div>'
    + '<div class="calc-perc-grid">'
    +   '<div class="calc-perc"><span>Farina</span><input type="number" id="ci-farina" value="100" readonly></div>'
    +   '<div class="calc-perc"><span>Acqua</span><input type="number" inputmode="decimal" id="ci-acqua" placeholder="70"></div>'
    +   '<div class="calc-perc"><span>Sale</span><input type="number" inputmode="decimal" id="ci-sale" placeholder="2"></div>'
    +   '<div class="calc-perc"><span>Lievito</span><input type="number" inputmode="decimal" id="ci-lievito" placeholder="1"></div>'
    + '</div>'
    + '<button class="calc-go" onclick="_calcImpasto()">Calcola le grammature</button>'
    + '</div><div id="ci-out"></div>');
}
async function _calcImpasto(){
  var peso=parseFloat((document.getElementById('ci-peso')||{}).value||'0')||0;
  if(peso<=0){ _toast('Inserisci il peso totale'); return; }
  var perc={farina:100};
  ['acqua','sale','lievito'].forEach(function(k){ var v=parseFloat((document.getElementById('ci-'+k)||{}).value||'0'); if(v>0) perc[k]=v; });
  var out=document.getElementById('ci-out'); if(out) out.innerHTML='<div class="calc-loading">Calcolo…</div>';
  try{
    var r=await fetch('/calcola',{method:'POST',headers:_statoHeaders({'Content-Type':'application/json'}),body:JSON.stringify({calcolo:'scalatore_impasto',parametri:{peso_totale_g:peso,percentuali:perc}})});
    var j=await r.json();
    var g=j.grammature||{};
    var righe=Object.keys(g).map(function(k){ return '<div class="calc-riga"><span>'+_escV(k)+'</span><b>'+_escV(String(g[k]))+' g</b></div>'; }).join('');
    var num='<div class="calc-grammature">'+righe+'</div>';
    if(out) out.innerHTML=_calcRisultato(num, j);
  }catch(e){ if(out) out.innerHTML='<div class="calc-err">Errore. Riprova.</div>'; }
}
// --- Conversione teglie ---
function _calcRenderTeglie(){
  _calcBody(
    '<div class="calc-form">'
    + '<div class="calc-teglie-row"><div class="calc-field"><label>Teglia di partenza (cm)</label><div class="calc-dim"><input type="number" inputmode="numeric" id="ct-b1" placeholder="20"><span>×</span><input type="number" inputmode="numeric" id="ct-a1" placeholder="20"></div></div></div>'
    + '<div class="calc-teglie-row"><div class="calc-field"><label>Teglia di arrivo (cm)</label><div class="calc-dim"><input type="number" inputmode="numeric" id="ct-b2" placeholder="30"><span>×</span><input type="number" inputmode="numeric" id="ct-a2" placeholder="40"></div></div></div>'
    + '<button class="calc-go" onclick="_calcTeglie()">Calcola il coefficiente</button>'
    + '</div><div id="ct-out"></div>');
}
async function _calcTeglie(){
  var b1=parseFloat((document.getElementById('ct-b1')||{}).value||'0'),a1=parseFloat((document.getElementById('ct-a1')||{}).value||'0');
  var b2=parseFloat((document.getElementById('ct-b2')||{}).value||'0'),a2=parseFloat((document.getElementById('ct-a2')||{}).value||'0');
  if(b1<=0||a1<=0||b2<=0||a2<=0){ _toast('Inserisci tutte le dimensioni'); return; }
  var out=document.getElementById('ct-out'); if(out) out.innerHTML='<div class="calc-loading">Calcolo…</div>';
  try{
    var r=await fetch('/calcola',{method:'POST',headers:_statoHeaders({'Content-Type':'application/json'}),body:JSON.stringify({calcolo:'conversione_teglie',parametri:{base1_cm:b1,alt1_cm:a1,base2_cm:b2,alt2_cm:a2}})});
    var j=await r.json();
    var num='<div class="calc-coef">×'+_escV(String(j.coefficiente||'?'))+'</div>';
    if(out) out.innerHTML=_calcRisultato(num, j);
  }catch(e){ if(out) out.innerHTML='<div class="calc-err">Errore. Riprova.</div>'; }
}
// --- Food cost piatto ---
var _fcpIng=[];
function _calcRenderFoodCost(){
  _calcBody(
    '<div class="calc-form">'
    + '<div class="calc-fcp-add"><input type="text" id="fcp-nome" placeholder="ingrediente"><input type="number" inputmode="numeric" id="fcp-g" placeholder="g" class="fcp-mini"><input type="number" inputmode="decimal" id="fcp-pk" placeholder="€/kg" class="fcp-mini"><button onclick="_fcpAdd()">+</button></div>'
    + '<div id="fcp-lista"></div>'
    + '<div class="calc-field"><label>Prezzo di vendita (€)</label><input type="number" inputmode="decimal" id="fcp-pv" placeholder="15"></div>'
    + '<button class="calc-go" onclick="_calcFoodCost()">Calcola il food cost</button>'
    + '</div><div id="fcp-out"></div>');
  _fcpRender();
}
function _fcpAdd(){
  var nome=(document.getElementById('fcp-nome')||{}).value||'';
  var g=parseFloat((document.getElementById('fcp-g')||{}).value||'0');
  var pk=parseFloat((document.getElementById('fcp-pk')||{}).value||'0');
  if(!nome.trim()||g<=0){ _toast('Nome e grammi obbligatori'); return; }
  _fcpIng.push({nome:nome.trim(), grammi:g, prezzo_kg:pk>0?pk:null});
  document.getElementById('fcp-nome').value=''; document.getElementById('fcp-g').value=''; document.getElementById('fcp-pk').value='';
  _fcpRender();
}
function _fcpRemove(i){ _fcpIng.splice(i,1); _fcpRender(); }
function _fcpRender(){
  var l=document.getElementById('fcp-lista'); if(!l) return;
  l.innerHTML=_fcpIng.map(function(x,i){
    var prezzo = x.prezzo_kg!=null ? (x.prezzo_kg+' €/kg') : '<span class="fcp-noprice" onclick="_fcpChiediPrezzo('+i+')">manca prezzo →</span>';
    return '<div class="calc-riga"><span>'+_escV(x.nome)+' · '+x.grammi+'g</span><span>'+prezzo+' <button class="fcp-x" onclick="_fcpRemove('+i+')">×</button></span></div>';
  }).join('');
}
function _fcpChiediPrezzo(i){
  var v=prompt('Prezzo al kg di '+_fcpIng[i].nome+' (€):');
  var p=parseFloat(v||'0'); if(p>0){ _fcpIng[i].prezzo_kg=p; _fcpRender(); }
}
async function _calcFoodCost(){
  if(!_fcpIng.length){ _toast('Aggiungi almeno un ingrediente'); return; }
  var pv=parseFloat((document.getElementById('fcp-pv')||{}).value||'0')||0;
  var out=document.getElementById('fcp-out'); if(out) out.innerHTML='<div class="calc-loading">Calcolo…</div>';
  try{
    var r=await fetch('/calcola',{method:'POST',headers:_statoHeaders({'Content-Type':'application/json'}),body:JSON.stringify({calcolo:'food_cost_piatto',parametri:{ingredienti:_fcpIng, prezzo_vendita:pv}})});
    var j=await r.json();
    var num='<div class="calc-fcp-num">€'+_escV(String(j.costo_totale||'?'))+(j.food_cost_perc!=null?'<span class="calc-fcp-pct">'+j.food_cost_perc+'%</span>':'')+'</div>';
    if(out) out.innerHTML=_calcRisultato(num, j);
  }catch(e){ if(out) out.innerHTML='<div class="calc-err">Errore. Riprova.</div>'; }
}
// --- Temperatura servizio vino (P4) ---
function _calcRenderVino(){
  var tipi=[['rosso_strutturato','Rosso strutturato'],['rosso_giovane','Rosso giovane'],['bianco','Bianco'],['rosato','Rosato'],['bollicina','Bollicina'],['dolce','Dolce']];
  _calcBody(
    '<div class="calc-form">'
    + '<div class="calc-field"><label>Tipo di vino</label><select id="cv-tipo" class="calc-select">'
    +   tipi.map(function(t){return '<option value="'+t[0]+'">'+t[1]+'</option>';}).join('')+'</select></div>'
    + '<div class="calc-field"><label>Temperatura attuale (°C)</label><input type="number" inputmode="numeric" id="cv-temp" placeholder="22"></div>'
    + '<div class="calc-field"><label>Metodo</label><select id="cv-metodo" class="calc-select"><option value="frigo">Frigo</option><option value="secchiello">Secchiello ghiaccio</option><option value="abbattitore">Abbattitore</option></select></div>'
    + '<button class="calc-go" onclick="_calcVino()">Quanto tempo serve</button>'
    + '</div><div id="cv-out"></div>');
}
async function _calcVino(){
  var tipo=(document.getElementById('cv-tipo')||{}).value||'rosso_strutturato';
  var temp=parseFloat((document.getElementById('cv-temp')||{}).value||'0')||0;
  var metodo=(document.getElementById('cv-metodo')||{}).value||'frigo';
  if(temp<=0){ _toast('Inserisci la temperatura attuale'); return; }
  var out=document.getElementById('cv-out'); if(out) out.innerHTML='<div class="calc-loading">Calcolo…</div>';
  try{
    var r=await fetch('/calcola',{method:'POST',headers:_statoHeaders({'Content-Type':'application/json'}),body:JSON.stringify({calcolo:'temperatura_servizio_vino',parametri:{tipo_vino:tipo,temp_attuale_c:temp,metodo:metodo}})});
    var j=await r.json();
    var num='<div class="calc-coef">'+_escV(String(j.minuti||'?'))+'<span class="calc-fcp-pct">min</span></div>';
    if(out) out.innerHTML=_calcRisultato(num, j);
  }catch(e){ if(out) out.innerHTML='<div class="calc-err">Errore. Riprova.</div>'; }
}
// --- Resa / calo peso (#3) — food cost dinamico crudo→finito ---
function _calcRenderCalo(){
  _calcBody(
    '<div class="calc-form">'
    + '<div class="calc-field"><label>Peso crudo (g)</label><input type="number" inputmode="numeric" id="rc-peso" placeholder="2000"></div>'
    + '<div class="calc-field"><label>Costo al kg (€)</label><input type="number" inputmode="decimal" id="rc-costo" placeholder="18"></div>'
    + '<div class="calc-field"><label>Calo in cottura (%)</label><input type="number" inputmode="decimal" id="rc-calo" placeholder="35"></div>'
    + '<button class="calc-go" onclick="_calcCalo()">Calcola il costo reale</button>'
    + '</div><div id="rc-out"></div>');
}
async function _calcCalo(){
  var peso=parseFloat((document.getElementById('rc-peso')||{}).value||'0')||0;
  var costo=parseFloat((document.getElementById('rc-costo')||{}).value||'0')||0;
  var calo=parseFloat((document.getElementById('rc-calo')||{}).value||'0')||0;
  if(peso<=0||costo<=0){ _toast('Inserisci peso e costo'); return; }
  var out=document.getElementById('rc-out'); if(out) out.innerHTML='<div class="calc-loading">Calcolo…</div>';
  try{
    var r=await fetch('/calcola',{method:'POST',headers:_statoHeaders({'Content-Type':'application/json'}),body:JSON.stringify({calcolo:'resa_calo_peso',parametri:{peso_crudo_g:peso,costo_kg:costo,calo_perc:calo}})});
    var j=await r.json();
    var e=_escV;
    // due numeri a confronto: crudo vs finito (il salto è il valore forte)
    var crudoKg=(j.costo_g_crudo!=null)?(j.costo_g_crudo*1000).toFixed(2):costo.toFixed(2);
    var finitoKg=(j.costo_g_finito!=null)?(j.costo_g_finito*1000).toFixed(2):'?';
    var num='<div class="calo-confronto">'
      + '<div class="calo-col"><div class="calo-lab">crudo</div><div class="calo-val">'+e(crudoKg)+'<span class="calo-u">€/kg</span></div></div>'
      + '<div class="calo-arr">→</div>'
      + '<div class="calo-col calo-finito"><div class="calo-lab">finito reale</div><div class="calo-val">'+e(finitoKg)+'<span class="calo-u">€/kg</span></div></div>'
      + '</div>';
    if(out) out.innerHTML=_calcRisultato(num, j);
  }catch(e){ if(out) out.innerHTML='<div class="calc-err">Errore. Riprova.</div>'; }
}
// --- Brix → ABV (P4) ---
function _calcRenderBrix(){
  _calcBody(
    '<div class="calc-form">'
    + '<div class="calc-field"><label>Gradi Brix (°Bx)</label><input type="number" inputmode="decimal" id="cb-brix" placeholder="22"></div>'
    + '<button class="calc-go" onclick="_calcBrix()">Grado alcolico potenziale</button>'
    + '</div><div id="cb-out"></div>');
}
async function _calcBrix(){
  var brix=parseFloat((document.getElementById('cb-brix')||{}).value||'0')||0;
  if(brix<=0){ _toast('Inserisci i gradi Brix'); return; }
  var out=document.getElementById('cb-out'); if(out) out.innerHTML='<div class="calc-loading">Calcolo…</div>';
  try{
    var r=await fetch('/calcola',{method:'POST',headers:_statoHeaders({'Content-Type':'application/json'}),body:JSON.stringify({calcolo:'brix_to_abv',parametri:{brix:brix}})});
    var j=await r.json();
    var num='<div class="calc-fcp-num">'+_escV(String(j.abv_potenziale_perc||'?'))+'<span class="calc-fcp-pct">% vol</span></div>';
    if(out) out.innerHTML=_calcRisultato(num, j);
  }catch(e){ if(out) out.innerHTML='<div class="calc-err">Errore. Riprova.</div>'; }
}
function apriStrumenti(disc){
  const d = disc || (typeof Matter!=='undefined' && Matter.disciplina) || 'bar';
  _apriVista('Strumenti di misura',
    '<div class="stv-head"><div class="stv-h">Gli strumenti del banco.</div>'+
    '<div class="stv-sub">Ogni numero-bersaglio ha lo strumento che lo misura. Cosa serve, quanto costa, dove prenderlo.</div>'+
    '<div class="stv-discs" id="stv-discs">'+
      ['bar','cucina','panificazione','pasticceria','gelateria','vino'].map(x=>'<span class="stv-disc'+(x===d?' on':'')+'" onclick="caricaStrumentiVista(\''+x+'\')">'+x+'</span>').join('')+
    '</div></div><div id="stv-out"></div>');
  caricaStrumentiVista(d);
}
async function caricaStrumentiVista(disc){
  document.querySelectorAll('.stv-disc').forEach(x=>x.classList.toggle('on', x.textContent===disc));
  const out = document.getElementById('stv-out');
  out.innerHTML = '<div class="vista-loading">Carico gli strumenti…</div>';
  try{
    const r = await fetch('/v1/strumenti/'+encodeURIComponent(disc)+'?lang='+_vistaLang());
    const d = await r.json();
    if(!d.strumenti || !d.strumenti.length){ out.innerHTML = '<div class="vista-empty">Nessuno strumento per questa disciplina.</div>'; return; }
    out.innerHTML = d.strumenti.map(s=>
      '<div class="stv-card"><div class="stv-card-top"><div class="stv-card-name">'+_escV(s.nome)+'</div>'+
      (s.prezzo_approx?'<div class="stv-card-price">'+_escV(s.prezzo_approx)+'</div>':'')+'</div>'+
      '<div class="stv-card-meta"><span class="stv-card-misura">'+_escV(s.misura||'')+'</span>'+
      (s.target?'<span class="stv-card-target">'+_escV(s.target)+'</span>':'')+'</div>'+
      (s.uso?'<div class="stv-card-uso">'+_escV(s.uso)+'</div>':'')+
      (s.amazon?'<a class="stv-card-cta" href="'+_escV(s.amazon)+'" target="_blank" rel="noopener">Cerca su Amazon →</a>':'')+
      '</div>').join('');
  }catch(e){ out.innerHTML = '<div class="vista-empty">Errore di rete. Riprova.</div>'; }
}

/* ═══════════════ 5. CREATIVITÀ BAR ═══════════════ */
function apriCreativita(){
  _apriVista('Creatività Bar',
    '<div class="cbv-head"><div class="cbv-h">Parti dal distillato.</div>'+
    '<div class="cbv-sub">Scegli uno spirito: Matter ti dà il carattere aromatico, con cosa dialoga e gli spunti per creare.</div>'+
    '<div class="cbv-chips">'+['gin','rum','whisky','tequila','vodka','mezcal','cognac'].map(s=>'<span class="cbv-chip" onclick="caricaCreativita(\''+s+'\')">'+s+'</span>').join('')+'</div>'+
    '</div><div id="cbv-out"></div>');
  caricaCreativita('gin');
}
async function caricaCreativita(spirito){
  document.querySelectorAll('.cbv-chip').forEach(x=>x.classList.toggle('on', x.textContent===spirito));
  const out = document.getElementById('cbv-out');
  out.innerHTML = '<div class="vista-loading">Leggo il profilo del distillato…</div>';
  try{
    const r = await fetch('/v1/creativita-bar/'+encodeURIComponent(spirito)+'?lang='+_vistaLang());
    const d = await r.json();
    let h = '<div class="cbv-center"><div class="cbv-center-lab">◉ Distillato</div><div class="cbv-center-name">'+_escV(d.distillato||spirito)+'</div>'+
      (d.carattere?'<div class="cbv-center-car">'+_escV(d.carattere)+'</div>':'')+'</div>';
    if(d.abbina_bar) h += '<div class="cbv-block"><div class="cbv-block-lab">Dialoga con</div><div class="cbv-block-txt">'+_escV(d.abbina_bar)+'</div></div>';
    if(d.spunti) h += '<div class="cbv-block cbv-spunti"><div class="cbv-block-lab">Spunti per creare</div><div class="cbv-block-txt">'+_escV(d.spunti)+'</div></div>';
    h += '<button class="cbv-cta" onclick="_creativitaCrea(\''+_escV(d.distillato||spirito)+'\')">Crea un cocktail con '+_escV(d.distillato||spirito)+' →</button>';
    out.innerHTML = h;
  }catch(e){ out.innerHTML = '<div class="vista-empty">Errore di rete. Riprova.</div>'; }
}
function _creativitaCrea(spirito){
  chiudiVista();
  if(typeof switchTab==='function') switchTab('chiedi');
  const ask = document.getElementById('ask-input');
  if(ask){ ask.value = 'Crea un cocktail con '+spirito; if(typeof inviaDomanda==='function') inviaDomanda(); }
}

// quando una misura viene salvata, se l'Atlante è la vista attiva, ricaricalo (Mirino in tempo reale)
window.addEventListener('measurement_saved', function(ev){
  try{
    var mappaAttiva = document.getElementById('screen-mappa') && document.getElementById('screen-mappa').classList.contains('active');
    if(mappaAttiva && typeof Matter!=='undefined' && Matter.disciplina && typeof caricaMappa==='function'){
      caricaMappa(Matter.disciplina);
    }
  }catch(e){}
});
