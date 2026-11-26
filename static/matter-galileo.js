// ═══ MATTER-GALILEO.js — l'AI dell'ecosistema (pulsante globale + sheet) ═══
(function(){
var _gBusy=false, _gAperto=false, _galStorico=[];
var _AUT={ alta:'Disponibile', normale:'Disponibile', bassa:'In esaurimento', esaurita:'Esaurita per oggi' };

// icona mirino-assistente (traguardo a parentesi + punto) come SVG inline: distinta dal crosshair della misura
var _SPARK='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9.2V6.9A.9.9 0 0 1 6.9 6H9.2"/><path d="M14.8 6h2.3a.9.9 0 0 1 .9.9V9.2"/><path d="M18 14.8v2.3a.9.9 0 0 1-.9.9H14.8"/><path d="M9.2 18H6.9a.9.9 0 0 1-.9-.9V14.8"/><circle cx="12" cy="12" r="1.75" fill="currentColor" stroke="none"/></svg>';

// escape sicuro: usa il globale se c'e', altrimenti un fallback locale (le pagine nuove non definiscono _escV)
var _escV = (typeof window!=='undefined' && typeof window._escV==='function') ? window._escV : function(s){
  return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});
};

// formattatore risposta: usa il globale se c'e' (home vecchia), altrimenti un fallback locale.
// NB: senza questo, sulle pagine nuove _formattaRispostaChat e' un identificatore non dichiarato
// e il riferimento diretto lancia ReferenceError dentro il .then -> cadeva nel catch ("Errore di rete").
var _fmt = (typeof window!=='undefined' && typeof window._formattaRispostaChat==='function') ? window._formattaRispostaChat : function(s){
  return String(s==null?'':s).split(/\n{2,}/).map(function(p){ return '<p>'+_escV(p).replace(/\n/g,'<br>')+'</p>'; }).join('');
};

// inietta il CSS del widget una sola volta (scoped a gal-*): funziona su qualsiasi pagina
function _galInjectCss(){
  if(document.getElementById('galileo-widget-css')) return;
  var l=document.createElement('link');
  l.id='galileo-widget-css'; l.rel='stylesheet'; l.href='/static/galileo-widget.css';
  document.head.appendChild(l);
}

// crea il pulsante globale persistente (basso a destra)
window._galileoInit = function(){
  _galInjectCss();
  if(document.getElementById('galileo-fab')) return;
  var fab=document.createElement('button');
  fab.id='galileo-fab'; fab.className='galileo-fab'; fab.setAttribute('aria-label','Chiedi a Matter');
  fab.innerHTML=_SPARK;
  fab.onclick=window.apriGalileo;
  document.body.appendChild(fab);
  setTimeout(function(){ window._aggiornaGalileoFab&&window._aggiornaGalileoFab(); }, 100);
};

window.apriGalileo = function(){
  var e=_escV;
  if(document.getElementById('galileo-sheet-overlay')) return;
  _galStorico=[]; // ogni apertura del pannello = conversazione nuova
  var ov=document.createElement('div');
  ov.id='galileo-sheet-overlay'; ov.className='galileo-sheet-overlay';
  ov.innerHTML='<div class="galileo-sheet">'
    + '<div class="gal-top"><div class="gal-brand">'+_SPARK+' Chiedi a Matter</div>'
    +   '<button class="gal-chiudi" onclick="chiudiGalileo()" aria-label="Chiudi">✕</button></div>'
    + '<div class="gal-flusso" id="gal-flusso">'
    +   '<div class="gal-intro"><div class="gal-intro-lab">INCLUSO NELL\'ABBONAMENTO</div>'
    +     '<div class="gal-intro-h">Il tuo AI personale, incluso in Matter.</div>'
    +     '<div class="gal-intro-sub">Scrive, cerca, traduce, riassume, analizza documenti. Non solo la scienza del mestiere: anche il lavoro di ogni giorno.</div>'
    +     '<div class="gal-esempi">'+[
            'Scrivi una mail al fornitore per un ordine',
            'Cerca i prezzi del pesce oggi a Napoli',
            'Riassumi questo PDF',
            'Traduci il menu in inglese',
            'Aiutami a organizzare un evento'
          ].map(function(x){ return '<button class="gal-esempio" onclick="_galChiedi(\''+e(x).replace(/'/g,"\\'")+'\')">'+e(x)+'</button>'; }).join('')+'</div>'
    +   '</div>'
    + '</div>'
    + '<div class="gal-bar"><input id="gal-input" placeholder="Chiedi qualsiasi cosa…" onkeydown="if(event.key===\'Enter\')_galInvia()"><button onclick="_galInvia()" aria-label="Invia">↑</button></div>'
    + '</div>';
  document.body.appendChild(ov);
  _gAperto=true;
  setTimeout(function(){ ov.classList.add('on'); },10);
};
window.chiudiGalileo = function(){
  var ov=document.getElementById('galileo-sheet-overlay');
  if(ov){ ov.classList.remove('on'); setTimeout(function(){ ov.remove(); },250); }
  _gAperto=false;
};
window._galChiedi = function(q){ var i=document.getElementById('gal-input'); if(i) i.value=q; _galInvia(); };

// INTENT PRE-ROUTE (unificazione chat, slice 1 — una chat, comportamenti distinti):
// la SCIENZA è il DEFAULT (il fossato). Solo i segnali chiari di "generale/quotidiano"
// (web aggiornato, scrivere, tradurre, riassumere) vanno al modo generale; tutto il
// resto va al motore groundato /chiedi, lo STESSO della pagina. Così una domanda di
// scienza dalla porta fluttuante non ottiene più una risposta NON groundata (buco del
// fossato chiuso). Default-scienza = una classificazione incerta ricade sul groundato
// (sicuro), mai la scienza nel generale. I segnali sono scelti per NON comparire nelle
// domande di mestiere (niente "oggi/stasera" che appaiono anche al banco).
var _GAL_SEG_GENERALE = [
  'prezzo','prezzi','quanto costa','quanto costano','meteo','che tempo fa','previsioni del tempo',
  'news','notizie','ultime notizie','cerca online','cerca sul web','sul web','quotazion','cambio euro',
  'scrivi una mail','scrivi un\'email','scrivimi una mail','mail al','email al','scrivi un messaggio',
  'scrivi un post','scrivi una lettera','scrivi un testo','traduci','traducimi','traduzione di',
  'come si dice in','riassumi','riassunto','fai un riassunto','correggimi','correggi il testo',
  'lista della spesa','idee per un'
];
function _galIntentoGenerale(q){
  var s=(' '+(q||'').toLowerCase()+' ');
  for(var i=0;i<_GAL_SEG_GENERALE.length;i++){ if(s.indexOf(_GAL_SEG_GENERALE[i])!==-1) return true; }
  return false;
}

window._galInvia = function(){
  if(_gBusy) return;
  var inp=document.getElementById('gal-input'); var q=inp?inp.value.trim():'';
  if(!q) return;
  inp.value='';
  var f=document.getElementById('gal-flusso');
  var intro=f.querySelector('.gal-intro'); if(intro) intro.remove();
  var e=_escV;
  f.insertAdjacentHTML('beforeend','<div class="gal-msg gal-msg-u">'+e(q)+'</div>');
  var risp=document.createElement('div'); risp.className='gal-msg gal-msg-a'; risp.innerHTML='<span class="gal-typing">…</span>';
  f.appendChild(risp); risp.scrollIntoView({behavior:'smooth',block:'end'});
  _gBusy=true;
  var acc=(localStorage.getItem('matter_device_id')||localStorage.getItem('matter_token')||'anon');
  var lang=(window._lang||'it');
  if(_galIntentoGenerale(q)){
    fetch('/v1/assistente/galileo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({domanda:q, account_id:acc, storico:_galStorico})})
      .then(function(r){return r.json();})
      .then(function(j){ _galRenderGenerale(j,q,f,risp); })
      .catch(function(){ _gBusy=false; risp.innerHTML='<div class="gal-esaurita">Errore di rete. Riprova.</div>'; });
  } else {
    // SCIENZA/DEFAULT: stesso motore groundato della pagina (provenienza, non inventa).
    fetch('/chiedi',{method:'POST',headers:{'Content-Type':'application/json','X-Device-Id':acc},body:JSON.stringify({domanda:q, lang:lang, history:_galStorico})})
      .then(function(r){return r.json();})
      .then(function(j){ _galRenderScienza(j,q,f,risp); })
      .catch(function(){ _gBusy=false; risp.innerHTML='<div class="gal-esaurita">Errore di rete. Riprova.</div>'; });
  }
};

// render del MODO GENERALE (invariato): energia, indicatore web, trasferimento al dominio.
window._galRenderGenerale = function(j,q,f,risp){
  _gBusy=false;
  var e=_escV;
  if(j.autorizzato===false || j.energia==='esaurita'){
    risp.innerHTML='<div class="gal-esaurita">'+e(j.messaggio||'Autonomia esaurita per oggi. Torna domani.')+'</div>';
    var b=f.closest('.galileo-sheet').querySelector('.gal-bar input'); if(b){ b.disabled=true; b.placeholder='Autonomia esaurita per oggi'; }
    return;
  }
  var html=_fmt(j.risposta||'');
  if(j.web){ html+='<div class="gal-web">◉ cercato sul web</div>'; }
  risp.innerHTML=html;
  _galStorico.push({role:'user',content:q});
  _galStorico.push({role:'assistant',content:(j.risposta||'')});
  if(_galStorico.length>12) _galStorico=_galStorico.slice(-12);
  if(j.trasferimento_dominio){
    var td=j.trasferimento_dominio;
    var ctx=(td.contesto&&td.contesto.domanda)||q;
    risp.insertAdjacentHTML('beforeend','<div class="gal-dominio"><div class="gal-dominio-txt">'+e(td.testo||'Questa è una domanda scientifica del mestiere.')+'</div>'
      + '<button class="gal-dominio-btn" onclick="chiudiGalileo();switchTab(\'chiedi\');switchSubtab(\'chat\');setTimeout(function(){chiediTesto('+JSON.stringify(ctx).replace(/"/g,'&quot;')+')},300)">Apri in Chiedi a Matter →</button></div>');
  }
  risp.scrollIntoView({behavior:'smooth',block:'end'});
  _galRiconosciDecisione(q, f);
};

// render del MOTORE SCIENTIFICO groundato (/chiedi): testo + gestione gate/errore.
// Niente energia/web/trasferimento: qui siamo GIÀ nel dominio.
window._galRenderScienza = function(j,q,f,risp){
  _gBusy=false;
  var e=_escV;
  j = j || {};
  if(j.errore || (j.messaggio && !j.risposta)){
    risp.innerHTML='<div class="gal-esaurita">'+e(j.messaggio||j.errore||'Non riesco a rispondere ora.')+'</div>';
    return;
  }
  risp.innerHTML=_fmt(j.risposta||'');
  _galStorico.push({role:'user',content:q});
  _galStorico.push({role:'assistant',content:(j.risposta||'')});
  if(_galStorico.length>12) _galStorico=_galStorico.slice(-12);
  risp.scrollIntoView({behavior:'smooth',block:'end'});
};

function _galRiconosciDecisione(testo, f){
  fetch('/v1/galileo/riconosci-decisione',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({testo:testo})})
    .then(function(r){return r.json();})
    .then(function(j){
      if(!j.merita_decisione) return;
      var e=_escV;
      f.insertAdjacentHTML('beforeend','<div class="gal-decisione"><div class="gal-dec-fam">'+e(j.famiglia||'Decisione Strategica')+'</div>'
        + '<div class="gal-dec-prop">'+e(j.proposta||'Questa sembra una decisione importante per la tua attività.')+'</div>'
        + '<div class="gal-dec-btns"><button class="gal-dec-avvia" onclick="_galAvviaDecisione()">'+e(j.cta_continua||'Avvia una Decisione Strategica')+'</button>'
        + '<button class="gal-dec-resta" onclick="this.closest(\'.gal-decisione\').remove()">'+e(j.cta_resta||'Resta qui')+'</button></div></div>');
    }).catch(function(){});
}
window._galAvviaDecisione = function(){
  fetch('/v1/matter/galileo-run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})})
    .then(function(r){return r.json();})
    .then(function(j){
      var e=_escV, f=document.getElementById('gal-flusso');
      if(!f) return;
      f.insertAdjacentHTML('beforeend','<div class="gal-comingsoon"><div class="gal-cs-lab">◎ DECISIONI STRATEGICHE</div>'
        + '<div class="gal-cs-titolo">'+e(j.titolo||'In arrivo')+'</div>'
        + '<div class="gal-cs-msg">'+e(j.messaggio||'Matter potrà preparare business plan, bandi, finanziamenti e analisi usando il contesto del tuo lavoro.')+'</div></div>');
      f.lastChild.scrollIntoView({behavior:'smooth',block:'end'});
    }).catch(function(){});
};
})();
