/* Matter — logica principale (estratta da index.html) */

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
    chiedi_al_grafo:'Preguntar a Matter Lab',
    calcola:'Calcular',
    onb_s1_title:'La física del oficio',
    onb_s1_sub:'Fenómenos físicos y químicos bajo cada gesto profesional.',
    onb_s2_title:'Números objetivo',
    onb_s2_sub:'Cada fenómeno tiene un número medible. Matter Lab te lo da.',
    onb_s3_title:'Preguntar a Matter Lab',
    onb_s3_sub:'Haz preguntas reales del trabajo diario.',
    auth_email:'Email',
    auth_pwd:'Contraseña',
    auth_login:'Iniciar sesión',
    auth_reg:'Crear cuenta',
    auth_reg_ok:'Cuenta creada. ¡Bienvenido a Matter Lab!',
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
    ct_cookie_txt:'Matter Lab usa cookies técnicas y registra las preguntas para mejorar el servicio.',
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
    chat_thinking:'consultando Matter Lab',
    chiedi_btn:'Preguntar',
    onb_nudge_title:'¿Listo en el banco?',
    ai_disclosure:'Respuestas generadas por un asistente de IA.',
    foto_analisi_titolo:'Análisis de foto',
    foto_analisi_loading:'Identificando ingredientes y botellas…',
    chiedi_placeholder:'pregunta a Matter Lab…',
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
    onb_ovl_title:'Cómo funciona Matter Lab',
    onb_s1_sub:'Bar, Panadería, Cocina, Café — cada disciplina tiene sus fenómenos.',
    onb_s1_title:'Elige tu disciplina',
    onb_s2_sub:'Cada lección tiene un número objetivo — el parámetro físico que mides en el trabajo.',
    onb_s2_title:'Estudia el fenómeno',
    onb_s3_sub:'Haz una pregunta real — un problema de tu trabajo. Respondo con números, no con opiniones.',
    onb_s3_title:'Pregunta a Matter Lab',
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
  el.innerHTML=ricette.map(r=>`
    <div class="ric-card" id="ric-${r.id}" onclick="toggleRicetta('${r.id}')">
      <div class="ric-disc">${r.disciplina}</div>
      <div class="ric-nome">${r.nome}</div>
      <div class="ric-desc">${r.descrizione||''}</div>
      <div class="ric-fenomeni">${(r.fenomeni||[]).map(f=>`<span class="ric-fen-tag">${f.replace('fen-','').replace(/-/g,' ')}</span>`).join('')}</div>
      <div class="ric-body">
        ${r.numeri && Object.keys(r.numeri).length ? `
        <div class="ric-numeri">
          <div class="ric-numeri-lab">Numeri bersaglio</div>
          ${Object.entries(r.numeri).map(([k,v])=>`<div class="ric-num-row"><span class="ric-num-k">${k}</span><span class="ric-num-v">${v}</span></div>`).join('')}
        </div>` : ''}
        ${r.punto_critico ? `
        <div class="ric-critico">
          <div class="ric-critico-lab">⚠ Punto critico</div>
          <div class="ric-critico-txt">${r.punto_critico}</div>
        </div>` : ''}
      </div>
      <div class="ric-toggle">Vedi dettagli ↓</div>
    </div>
  `).join('');
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
function switchTab(t){
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
    if(typeof switchMappaTab==='function') switchMappaTab('fenomeni');
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
    const u = new URLSearchParams(location.search).get('lang');
    if (u && ok.includes(u)) return u;
    const s = localStorage.getItem('matter_lang');
    if (s && ok.includes(s)) return s;
    const nav = (navigator.language || 'it').slice(0,2).toLowerCase();
    if (ok.includes(nav)) return nav;
  } catch(e){}
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

function renderHome(j){
  const f = j.fenomeno || {};
  { const _h=document.getElementById('scopri-hero'); if(_h) _h.classList.remove('loading'); }
  document.getElementById('scopri-ey').textContent =
    'oggi al banco · ' + (f.dominio||'');
  document.getElementById('scopri-titolo').textContent = f.nome || '—';
    const _loop = document.getElementById('loop-guidato');
    const _loopFen = document.getElementById('loop-fen-nome');
    if(_loop) _loop.style.display='none';
    if(_loopFen) _loopFen.textContent = f.nome || 'Fenomeno';
  // il numero-bersaglio: TARGET primario (eroe) + condizioni secondarie
  const numBox = document.getElementById('scopri-num');
  if(f.target){
    _renderTarget(numBox, f.target);
    numBox.style.display='block';
  } else { numBox.style.display='none'; }
  // poi il PERCHÉ (descrizione), sotto il numero
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
      renderMirino(document.getElementById('les-mirino'), j.fenomeno.nome, j.fenomeno.target);
      datoBox.style.display = '';
      _caricaStrumentoPerFenomeno(disc, j.fenomeno.nome, j.fenomeno.target);
    } else {
      datoBox.style.display = 'none';
      var _mir=document.getElementById('les-mirino'); if(_mir) _mir.style.display='none';
      var sb=document.getElementById('les-strumento-box'); if(sb) sb.style.display='none';
    }
    // stepper a puntini: quanti fenomeni, dove sei, salto diretto
    renderLesDots(j.step, j.totale_passi);
    // principio
    const pb = document.getElementById('les-principio-box');
    if(j.principio){
      document.getElementById('les-principio-testo').textContent = j.principio.testo||'';
      pb.style.display='block';
    } else { pb.style.display='none'; }
    // quiz: caricato a parte (lazy), così la lezione appare subito.
    // La prima volta il server lo genera, poi è in cache e istantaneo.
    caricaQuizLezione(j.fenomeno.id);
    // bottoni nav
    document.getElementById('les-btn-prec').style.opacity = j.ha_precedente?'1':'0.4';
    document.getElementById('les-btn-succ').textContent =
      j.ha_successivo ? 'Avanti →' : 'Vai alla Mappa →';
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

function renderMappa(disc, fens){
  const label = document.getElementById('mappa-label');
  const cont = document.getElementById('mappa-percorso');
  label.textContent = _t('mappa_percorso') + disc;
  if(!fens.length){
    cont.innerHTML=`<div style="padding:14px;color:var(--ink-muted);font-size:13px">${_t('mappa_nessun_fen')}</div>`;
    return;
  }
  // il connettore verticale tra i nodi lo disegna il CSS (.p-step::after):
  // qui NON lo iniettiamo, per evitare la doppia linea.
  cont.innerHTML = fens.map((f,i)=>{
    const isFirst = i===0;
    const stato = f.stato||'libero';
    const nodeClass = stato==='completato'?'done':isFirst?'active':'lock';
    // il target diventa il NUMERO protagonista: estraggo solo l'eroe (primo pezzo)
    const targetEroe = (f.target||'').split(/\s*[·;]\s*/)[0].trim();
    const tagHtml = stato==='completato'
      ? '<span class="p-tag done">completato</span>'
      : isFirst ? '<span class="p-tag active">inizia da qui</span>'
      : '<span class="p-tag prolock">Pro</span>';
    const svgIcon = stato==='completato'
      ? '<svg viewBox="0 0 24 24"><path d="M5 12l5 5L20 6"/></svg>'
      : isFirst
      ? '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/></svg>'
      : '<svg viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/></svg>';
    const nodeStyle = stato==='lock'
      ? 'border:1px solid rgba(196,98,45,0.3);background:var(--surface);'
      : '';
    return `<div class="p-step ${stato==='completato'?'done':''}" style="cursor:pointer" onclick="vaiAStep(${i})">
      <div class="pnode ${nodeClass}" style="${nodeStyle}">${svgIcon}</div>
      <div class="p-info">
        <div class="p-name-row"><span class="p-name">${esc(f.nome)}</span>${tagHtml}</div>
        ${targetEroe?`<div class="p-target">${esc(targetEroe)}</div>`:''}
      </div>
    </div>`;
  }).join('');
}

async function caricaMappa(disc){
  // rientro: se già in cache, render immediato, zero placeholder = zero salto
  if(_mappaCache[disc]){ renderMappa(disc, _mappaCache[disc]); return; }
  const cont = document.getElementById('mappa-percorso');
  document.getElementById('mappa-label').textContent = _t('mappa_percorso') + disc;
  // altezza minima durante il load: le sezioni sotto non si spostano
  cont.innerHTML = `<div style="display:flex;flex-direction:column;gap:10px;padding:4px 0">`
    +['80%','65%','75%','55%'].map(w=>`<div class="skel" style="height:52px;border-radius:10px;width:${w}">&nbsp;</div>`).join('')
    +'</div>';
  try {
    const r = await fetch('/mappa/'+disc);
    if(!r.ok) throw new Error('server');
    const j = await r.json();
    const fens = j.fenomeni||[];
    _mappaCache[disc] = fens;
    renderMappa(disc, fens);
  } catch(e){
    cont.innerHTML=`<div style="padding:14px;color:var(--e700);font-size:13px">${_t('mappa_errore')}</div>`;
  }
}

function vaiAStep(idx){
  Matter.step = idx;
  switchTab('lezione');
}

/* ── CHAT / GRAFO ─────────────────────────────────────── */
const DOMCOL={bar:'#D3B566',cucina:'#E0AA76',bakery:'#2C6E63',caffetteria:'#9A5A28',fermentazione:'#8FBBB0',trasversale:'#6F6A60'};
let busy=false;
function setBusy(b){busy=b;document.getElementById('ask-btn').disabled=b;}
function invia(){const q=document.getElementById('q').value.trim();if(!q||busy)return;document.getElementById('q').value='';chiediTesto(q);}

// mini-history: ultimi 3 scambi in memoria (resettata al refresh, zero DB)
const _chatHistory=[];
const _HISTORY_MAX=3;

function chiediTesto(q){
  if(busy)return;
  // paywall: controlla limite giornaliero (solo per utenti non Pro)
  if(!_isPro()){
    const usate=_getDomande();
    if(usate>=FREE_LIMIT){ apriPaywall(); return; }
  }
  const e=document.getElementById('empty-state');if(e)e.remove();
  switchTab('chiedi');switchSubtab('chat');
  aggiungiThinking();setBusy(true);
  // passa gli ultimi scambi per dare continuità alla conversazione
  const history=_chatHistory.slice(-_HISTORY_MAX);
  const _tok=localStorage.getItem('matter_token')||'';
  // se arrivo da una scheda lezione, passo il contesto così la chat risponde già informata
  const _ctx = window._chatContesto || null;
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
  fetch('/nodo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})})
    .then(r=>r.json()).then(j=>renderRisp(nome,j,true)).catch(()=>renderErr()).finally(()=>setBusy(false));
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
  const fens=(j.trovato||[]).map(f=>{
    const match=(j.connessi||[]).find(c=>c.nome===f);
    const fid=match?match.id:'';
    return `<span class="fenchip" style="cursor:pointer;text-decoration:underline dotted" onclick="${fid?`apriNodo('${fid}','${f.replace(/'/g,"\'")}')`:'switchTab(\"lezione\")'}" title="Esplora fenomeno">${esc(f)}</span>`;
  }).join('');
  const conns=(j.connessi||[]).map(c=>{
    const col=DOMCOL[c.dominio]||'#6F6A60';
    const tg=c.target?`<span class="tg">${esc(c.target)}</span>`:'';
    return `<span class="conn" onclick="apriNodo('${c.id}','${(c.nome||'').replace(/'/g,"\\'")}')"><span class="dot" style="background:${col}"></span>${esc(c.nome)}${tg}</span>`;
  }).join('');
  // FL4b: chip flavor dal primo fenomeno trovato
  const trovati = j.trovato || [];
  const flavorChip = trovati.length > 0
    ? `<div class="s-conn" style="border-top:1px solid var(--border)">
        <div class="s-conn-lab" style="color:var(--flavor)">cerca abbinamenti nella Mappa →</div>
        <div class="conns"><span class="conn" style="color:var(--flavor);border-color:var(--flavor-border)" onclick="switchTab('mappa')">
          <span class="dot" style="background:var(--flavor)"></span>Vai alla Mappa aromatica →
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
  const numBox = numBersaglio ? `<div class="s-num-box">
    <div class="s-num-label">numero bersaglio</div>
    <div class="s-num-val">${esc(numBersaglio)}</div>
  </div>` : '';
  
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
      if(!hasStructure) return '<div class="s-body">'+esc(r)+'</div>';
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
        const tagBg = isAct ? '#2C6E63' : '#8FBBB0';
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
    const col=DOMCOL[c.dominio]||'#6F6A60';
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
      } else if(j.token){localStorage.setItem('matter_token',j.token);localStorage.setItem('matter_email',email);aggiornaTopbarLogin();msg.className='auth-msg ok';msg.textContent=_t('auth_reg_ok');setTimeout(()=>switchTab('scopri'),900);}
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
    scopri:'Scopri', lezione:'Lezione', mappa:'Mappa', db_fenomeni:'Fenomeni',
    db_ingredienti:'Ingredienti',
    db_connessioni:'Connessioni aromatiche',
    db_calcolatori:'Calcolatori',
    chiedi:'Chiedi',
    studia:'Misura questo →', nologin:'',
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
    num_bersaglio:'numero bersaglio',
    indietro:'← Indietro', avanti:'Avanti →', vai_mappa:'Vai alla Mappa →',
    principio_del_giorno:'Principio del giorno',
    vedi_mappa:'Vedi il principio nella Mappa →',
    chiedi_placeholder:'chiedi a Matter Lab…',
    chiedi_btn:'Chiedi',
    onb_nudge_title:'Pronto al banco?',
    ai_disclosure:'Risposte generate da un assistente AI.',
    foto_analisi_titolo:'Analisi foto',
    foto_analisi_loading:'Riconosco ingredienti e bottiglie…',
    chiedi_title:'Chiedi a Matter Lab',
    chiedi_sub:'Un problema reale del tuo lavoro — rispondo con i numeri, non con le opinioni.',
    sup_titolo:'Hai bisogno di aiuto?',
    sup_sub:'Descrivi il problema. Ti risponderemo entro 24 ore via email.',
    sup_placeholder:'Es. Non riesco ad aprire la lezione…',
    sup_invia:'Invia richiesta',
    disc_bar:'Bar', disc_bakery:'Panificazione', disc_cucina:'Cucina',
    disc_caffetteria:'Caffè', disc_pasticceria:'Pasticceria',
    disc_gelateria:'Gelateria', disc_vino:'Vino', disc_birra:'Birra',
    chiedi_al_grafo:'Chiedi a Matter Lab',
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
    ct_cookie_txt:'Matter Lab usa cookie tecnici per funzionare e registra le domande per migliorare il servizio. Nessun cookie di profilazione. Le risposte sono generate da AI (Anthropic/Mistral).',
    // batch output
    ct_acqua_pre:'Acqua pre-diluizione',
    ct_totale:'Totale',
    ct_include:'include',
    ct_extra_lbl:'extra',
    // onboarding
    onb_ovl_title:'Come funziona Matter Lab',
    onb_s1_title:'Scegli la tua disciplina',
    onb_s1_sub:'Bar, Panificazione, Cucina, Caffetteria e altro — ogni disciplina ha le sue leggi fisiche.',
    onb_s2_title:'Studia il fenomeno',
    onb_s2_sub:'Ogni fenomeno ha un numero che puoi misurare. Quello che devi sapere quando qualcosa non torna.',
    onb_s3_title:'Chiedi a Matter Lab',
    onb_s3_sub:'Descrivi un problema del tuo lavoro. Ricevi numeri da misurare e azioni concrete — non consigli generici.',
    onb_ovl_cta:'Inizia',
    onb_nudge_sub:'Seleziona la tua disciplina qui sotto per la prima lezione',
    onb_complete_title:'Percorso completato.',
    onb_complete_sub:'Hai completato la lezione. Vai alla Mappa per vedere il tuo percorso.',
    onb_complete_btn:'Vai alla Mappa',
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
    chat_thinking:'consulto Matter Lab',
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
    ct_sic_gate_desc:'Shelf life orientativa, pastorizzazione e catena del freddo. Disponibile con Matter Lab Pro.',
    ct_sic_gate_btn:'Passa a Pro — €19,99/mese',
  },
  en:{
    payoff:'The science behind the craft',
    scopri:'Discover', lezione:'Lesson', mappa:'Map', db_fenomeni:'Phenomena',
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
    indietro:'← Back', avanti:'Next →', vai_mappa:'Go to Map →',
    principio_del_giorno:'Principle of the day',
    vedi_mappa:'See the principle in the Map →',
    chiedi_placeholder:'ask Matter Lab…',
    chiedi_btn:'Ask',
    onb_nudge_title:'Ready at the bench?',
    ai_disclosure:'Responses generated by an AI assistant.',
    foto_analisi_titolo:'Photo analysis',
    foto_analisi_loading:'Identifying ingredients and bottles…',
    chiedi_title:'Ask Matter Lab',
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
    chiedi_al_grafo:'Ask Matter Lab',
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
    ct_cookie_txt:'Matter Lab uses technical cookies and logs questions to improve the service. No profiling cookies. Responses are AI-generated (Anthropic/Mistral).',
    // batch output
    ct_acqua_pre:'Pre-dilution water',
    ct_totale:'Total',
    ct_include:'includes',
    ct_extra_lbl:'extra',
    // onboarding
    onb_ovl_title:'How Matter Lab works',
    onb_s1_title:'Choose your discipline',
    onb_s1_sub:'Bar, Bakery, Kitchen, Coffee — each discipline has its own path through physical phenomena.',
    onb_s2_title:'Study the phenomenon',
    onb_s2_sub:'Each lesson has a target number — the physical parameter that governs that gesture at the bench.',
    onb_s3_title:'Ask Matter Lab',
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
    chat_thinking:'asking Matter Lab',
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
    scopri:'Descubrir', lezione:'Lección', mappa:'Mapa', db_fenomeni:'Fenómenos',
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
    chiedi_title:'Preguntar a Matter Lab',
    disc_bar:'Bar', disc_cucina:'Cocina', disc_panificazione:'Panadería',
    disc_pasticceria:'Pastelería', disc_gelateria:'Heladería', disc_caffe:'Café',
    disc_vino:'Vino', disc_birra:'Cerveza', disc_sicurezza:'Seguridad alimentaria',
    chiedi_sub:'Un fenómeno físico para cada gesto profesional',
    chiedi_al_grafo:'Preguntar', calcola:'Calcular',
    auth_email:'Email', auth_pwd:'Contraseña',
    auth_login:'Iniciar sesión', auth_reg:'Crear cuenta',
    auth_reg_ok:'¡Cuenta creada. Bienvenido a Matter Lab!',
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
    ct_cookie_txt:'Matter Lab usa cookies técnicas para funcionar.',
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
    chat_thinking:'consultando Matter Lab',
    chiedi_btn:'Preguntar',
    onb_nudge_title:'¿Listo en el banco?',
    ai_disclosure:'Respuestas generadas por un asistente de IA.',
    chiedi_placeholder:'pregunta a Matter Lab…',
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
    onb_ovl_title:'Cómo funciona Matter Lab',
    onb_s1_sub:'Bar, Panadería, Cocina, Café — cada disciplina tiene sus fenómenos.',
    onb_s1_title:'Elige tu disciplina',
    onb_s2_sub:'Cada lección tiene un número objetivo — el parámetro físico que mides en el trabajo.',
    onb_s2_title:'Estudia el fenómeno',
    onb_s3_sub:'Haz una pregunta real. Respondo con números, no con opiniones.',
    onb_s3_title:'Pregunta a Matter Lab',
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
  // tab labels
  document.querySelectorAll('.tab-label').forEach((el,i)=>{
    const keys=['scopri','lezione','mappa','chiedi'];
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
  if(localStorage.getItem('matter_onb_done')) return;
  const overlay = document.getElementById('onb-overlay');
  if(overlay) overlay.classList.remove('hidden');
}
function chiudiOnbOverlay(){
  const overlay = document.getElementById('onb-overlay');
  if(overlay) overlay.classList.add('hidden');
  localStorage.setItem('matter_onb_done','1');
  // assicura che la home carichi dopo aver chiuso l'overlay
  if(typeof caricaHome === 'function') caricaHome();
}

// ── ONBOARDING PROFILAZIONE: mestiere → primo numero → lezione ──
let _onbMestiere = null;
async function onbScegliMestiere(disc, label){
  _onbMestiere = disc;
  Matter.disciplina = disc;
  document.getElementById('onb-f2-ey').textContent = label;
  // carico il primo fenomeno della disciplina per mostrare il primo numero
  try{
    const r = await fetch('/mappa/'+disc);
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
      alert('Errore nella generazione del link: ' + (d.errore || 'sconosciuto'));
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
  const card = btn.closest('.scheda');
  const domanda = card.querySelector('.s-q b')?.textContent || 'Risposta';
  const risposta = card.querySelector('.s-body')?.textContent || '';
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
  .logo{font-family:'Arial',sans-serif;font-size:22px;font-weight:700;color:#D3B566;margin-bottom:4px}
  .payoff{font-family:'Courier New',monospace;font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:#9a9090;margin-bottom:32px}
  .domanda{font-size:18px;font-weight:700;color:#2a2a2a;margin-bottom:8px}
  .fenomeni{font-family:'Courier New',monospace;font-size:10px;color:#D3B566;letter-spacing:.1em;text-transform:uppercase;margin-bottom:20px}
  .risposta{font-size:14px;line-height:1.8;color:#333;margin-bottom:32px}
  .footer{font-family:'Courier New',monospace;font-size:9px;color:#9a9090;border-top:1px solid #eee;padding-top:12px}
</style>
</head>
<body>
<div class="logo">Matter Lab</div>
<div class="payoff">Science & Craft</div>
<div class="domanda">${domanda}</div>
${fenchips ? `<div class="fenomeni">Fenomeni: ${fenchips}</div>` : ''}
<div class="risposta">${risposta.replace(/\n/g,'<br>')}</div>
<div class="footer">Generato da Matter Lab · ${oggi} · matter-lab.com<br>Risposta generata da AI su base scientifica — verifica con fonti professionali.</div>
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

function aggiornDrinkCost(ingredienti){
  // bar — usa drinkcost-card
  _calcolaCosto(ingredienti, 'drinkcost-card', 'drinkcost-rows', 'drinkcost-total-num');
  const salvaBtnEl = document.getElementById('salva-btn');
  if(salvaBtnEl) salvaBtnEl.style.display = localStorage.getItem('matter_token') ? 'block' : 'none';
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
  document.getElementById('quad-pane-misure').style.display = vista==='misure'?'':'none';
  document.getElementById('quad-pane-menu').style.display = vista==='menu'?'':'none';
  document.getElementById('qtg-misure').classList.toggle('active', vista==='misure');
  document.getElementById('qtg-menu').classList.toggle('active', vista==='menu');
  if(vista==='menu') caricaMenuSalvati();
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

function creaMenu(){
  _mbStep = 1; _mbVoci = []; _mbTemplate = 'editorial';
  document.getElementById('mb-nome').value = '';
  document.getElementById('mb-locale').value = '';
  _mbMostraStep(1);
  document.getElementById('menu-builder').classList.remove('hidden');
}
function chiudiBuilder(){ document.getElementById('menu-builder').classList.add('hidden'); }

function _mbMostraStep(n){
  _mbStep = n;
  [1,2,3].forEach(s=> document.getElementById('mb-step-'+s).style.display = s===n?'block':'none');
  const titoli = {1:'Nuova drink list', 2:'Componi la carta', 3:'Stile della carta'};
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
    if(!_mbVoci.length){ alert('Aggiungi almeno una voce alla carta.'); return; }
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
  let msg = '';
  if(n < 8) msg = `Hai <b>${n}</b> ${n===1?'voce':'voci'}. Per una drink list equilibrata te ne servono <b>8-12</b>.`;
  else if(n <= 12) msg = `<b>${n} voci</b> — una carta ben dimensionata.`;
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
  const menu = {nome, locale, tipo:'drink list', template:_mbTemplate, voci:_mbVoci, creato: Date.now()};
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
  const corpo = voci.map(v=>{
    const sigillo = v.stato==='verified' ? '<span class="ma-verif">✓</span>' : '';
    return `<div class="ma-voce"><div class="ma-voce-nome">${_esc(v.nome)}${sigillo}</div>${v.target?`<div class="ma-voce-tgt">${_esc(v.target)}</div>`:''}</div>`;
  }).join('');
  document.getElementById('ma-render').className = 'ma-render tpl-'+tpl;
  document.getElementById('ma-render').innerHTML =
    `<div class="ma-head"><div class="ma-locale">${_esc(menu.locale||'Il tuo locale')}</div>
     <div class="ma-nome">${_esc(menu.nome||'Drink List')}</div></div>
     <div class="ma-voci">${corpo}</div>
     <div class="ma-foot">Verificato da Matter</div>`;
  ov.classList.remove('hidden');
}
function chiudiAnteprima(){ document.getElementById('menu-anteprima').classList.add('hidden'); caricaMenuSalvati(); }

function esportaMenu(){
  // export PDF = Pro (paywall)
  const tok = localStorage.getItem('matter_token');
  const piano = localStorage.getItem('matter_piano');
  if(piano!=='pro'){
    if(typeof mostraPopupPro==='function'){ mostraPopupPro('menu_export'); }
    else alert('L\'esportazione del menù è una funzione Pro.');
    return;
  }
  // Pro: genero il PDF (v1: stampa del contenitore anteprima)
  window.print();
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
  } catch(e){ console.error('flavor',e); }
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
  console.group('TE3 — Validazione kT');
  const r1 = await fetch('/chiedi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({domanda:'i miei crauti non fermentano'})});
  const j1 = await r1.json();
  const kt1 = (j1.risposta||'').toLowerCase().includes('boltzmann');
  console.log('Test 1 (normale) — kT:', kt1, '(atteso: false)');
  const r2 = await fetch('/chiedi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({domanda:'perche la fermentazione accelera con il caldo?'})});
  const j2 = await r2.json();
  const kt2 = (j2.risposta||'').toLowerCase().includes('boltzmann')||(j2.trovato||[]).some(f=>f.toLowerCase().includes('principio'));
  console.log('Test 2 (perche) — kT:', kt2, '(atteso: true)');
  console.log(kt1===false && kt2===true ? '✓ kT VALIDATO' : '✗ VERIFICARE');
  console.groupEnd();
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
function mostraPopupPro(motivo){
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
      title_esaurito: 'Hai visto cosa può fare Matter.',
      title_ultimo: 'Ultimo assaggio gratuito',
      title_lezione: 'Fenomeno riservato a Pro',
      title_lezione_locked: 'Fenomeno riservato a Pro',
      sub_esaurito: 'Hai usato i tuoi 5 assaggi. Da qui Matter continua a lavorare con te.',
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
      badge: 'Matter Lab Pro',
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
      badge: 'Matter Lab Pro',
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
        <div class="trial-popup-feat"><span class="trial-popup-feat-icon">${C.feat1.split(' ')[0]}</span><span class="trial-popup-feat-text">${C.feat1.split('  ')[1]}</span></div>
        <div class="trial-popup-feat"><span class="trial-popup-feat-icon">${C.feat2.split(' ')[0]}</span><span class="trial-popup-feat-text">${C.feat2.split('  ')[1]}</span></div>
        <div class="trial-popup-feat"><span class="trial-popup-feat-icon">${C.feat3.split(' ')[0]}</span><span class="trial-popup-feat-text">${C.feat3.split('  ')[1]}</span></div>
        <div class="trial-popup-feat"><span class="trial-popup-feat-icon">${C.feat4.split(' ')[0]}</span><span class="trial-popup-feat-text">${C.feat4.split('  ')[1]}</span></div>
      </div>
      <div class="trial-popup-price">${C.price}</div>
      <div class="trial-popup-price-note">${C.period}</div>
      <button class="trial-popup-cta" onclick="document.querySelector('.trial-popup-overlay').remove();switchTab('auth')">${C.cta}</button>
      <button class="trial-popup-skip" onclick="${motivo === 'esaurito' ? "document.querySelector('.trial-popup-overlay').remove();switchTab('scopri')" : "document.querySelector('.trial-popup-overlay').remove()"}">${skipLabel}</button>
    </div>`;

  document.body.appendChild(overlay);
  overlay.addEventListener('click', e => { if(e.target === overlay) overlay.remove(); });
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
    alert('Salva prima la ricetta nel quaderno per calcolare il costo.');
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
        `Fonte: ${j.fonte||'Matter Lab / ISMEA orientativo'}`
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
    {q: 'uso sempre lo stesso lime ma il sour cambia ogni sera — perché?', l: 'Il sour non è mai uguale →'},
    {q: 'il mio impasto con lievito madre fermenta bene ma il pane non cresce in forno — cosa succede?', l: 'Il pane non cresce in forno →'},
    {q: 'd\'estate la fermentazione va troppo veloce e l\'impasto va oltre — come lo controllo?', l: 'Fermentazione fuori controllo →'},
    {q: 'come misuro il pH di un impasto o di un cocktail al banco?', l: 'Come misuro il pH →'},
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
  // aggiungo il cursore sulla barra
  var track = box.querySelector('.mirino-track-wrap');
  var old = box.querySelector('.mirino-cursor'); if(old) old.remove();
  var cur = document.createElement('div');
  cur.className='mirino-cursor'; cur.style.left=pCursore+'%';
  cur.innerHTML='<span class="mirino-cursor-val">'+_fmtN(val)+'</span>';
  track.appendChild(cur);
  // feedback block
  var fb = box.querySelector('.mirino-feedback'); if(fb) fb.remove();
  var div = document.createElement('div');
  div.className='mirino-feedback';
  div.innerHTML =
    '<div class="mirino-scarto '+(dentro?'dentro':'fuori')+'">'+_esc(scartoTxt)+'</div>'+
    '<div class="mirino-azione-lab">cosa fare</div>'+
    '<div class="mirino-azione">'+_esc(azione)+'</div>'+
    '<button class="mirino-rimisura" onclick="resetMirino(\''+box.id+'\')">Rimisura</button>';
  box.appendChild(div);
  // nascondo la riga input (è stata "consumata")
  var ir = box.querySelector('.mirino-input-row'); if(ir) ir.style.display='none';
}

function resetMirino(boxId){
  var box=document.getElementById(boxId); if(!box) return;
  renderMirino(box, box._fenomeno, box._range.raw, box._azioneFn);
}

// ── RENDER TARGET: eroe primario + parametri secondari (result first) ──
function _renderTarget(box, target, mostraLabel){
  if(!box) return;
  var parti = target.split(/\s*[·;]\s*/).map(function(s){return s.trim();}).filter(Boolean);
  var eroe = parti[0] || target;
  var params = parti.slice(1);
  var html = '';
  if(mostraLabel !== false) html += '<div class="target-lab">target</div>';
  html += '<div class="target-eroe">' + _esc(eroe) + '</div>';
  if(params.length){
    html += '<div class="target-cond-lab">condizioni</div><div class="target-grid">';
    params.forEach(function(p){
      html += '<div class="target-cond">' + _esc(p) + '</div>';
    });
    html += '</div>';
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
      alert('Email confermata! Benvenuto in Matter Lab.');
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
