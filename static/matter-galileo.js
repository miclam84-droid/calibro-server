// ═══ MATTER-GALILEO.js — l'AI dell'ecosistema (pulsante globale + sheet) ═══
(function(){
var _gBusy=false, _gAperto=false;
var _AUT={ alta:'Disponibile', normale:'Disponibile', bassa:'In esaurimento', esaurita:'Esaurita per oggi' };

// crea il pulsante globale persistente (basso a destra)
window._galileoInit = function(){
  if(document.getElementById('galileo-fab')) return;
  var fab=document.createElement('button');
  fab.id='galileo-fab'; fab.className='galileo-fab'; fab.setAttribute('aria-label','Galileo');
  fab.innerHTML='<i class="ph ph-sparkle" aria-hidden="true"></i>';
  fab.onclick=window.apriGalileo;
  document.body.appendChild(fab);
};

window.apriGalileo = function(){
  var e=_escV;
  if(document.getElementById('galileo-sheet-overlay')) return;
  var ov=document.createElement('div');
  ov.id='galileo-sheet-overlay'; ov.className='galileo-sheet-overlay';
  ov.innerHTML='<div class="galileo-sheet">'
    + '<div class="gal-top"><div class="gal-brand"><i class="ph ph-sparkle"></i> Galileo</div>'
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
  fetch('/v1/assistente/galileo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({domanda:q, account_id:acc})})
    .then(function(r){return r.json();})
    .then(function(j){
      _gBusy=false;
      if(j.autorizzato===false || j.energia==='esaurita'){
        risp.innerHTML='<div class="gal-esaurita">'+e(j.messaggio||'Autonomia esaurita per oggi. Torna domani.')+'</div>';
        var b=f.closest('.galileo-sheet').querySelector('.gal-bar input'); if(b){ b.disabled=true; b.placeholder='Autonomia esaurita per oggi'; }
        return;
      }
      var html=(_formattaRispostaChat?_formattaRispostaChat(j.risposta||''):e(j.risposta||''));
      // indicatore web
      if(j.web){ html+='<div class="gal-web">◉ cercato sul web</div>'; }
      risp.innerHTML=html;
      // trasferimento al dominio scientifico
      if(j.trasferimento_dominio){
        var td=j.trasferimento_dominio;
        var ctx=(td.contesto&&td.contesto.domanda)||q;
        risp.insertAdjacentHTML('beforeend','<div class="gal-dominio"><div class="gal-dominio-txt">'+e(td.testo||'Questa è una domanda scientifica del mestiere.')+'</div>'
          + '<button class="gal-dominio-btn" onclick="chiudiGalileo();switchTab(\'chiedi\');switchSubtab(\'chat\');setTimeout(function(){chiediTesto('+JSON.stringify(ctx).replace(/"/g,'&quot;')+')},300)">Apri in Chiedi a Matter →</button></div>');
      }
      risp.scrollIntoView({behavior:'smooth',block:'end'});
      // riconoscimento decisione strategica (dormiente)
      _galRiconosciDecisione(q, f);
    })
    .catch(function(){ _gBusy=false; risp.innerHTML='<div class="gal-esaurita">Errore di rete. Riprova.</div>'; });
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
        + '<div class="gal-cs-msg">'+e(j.messaggio||'Galileo potrà preparare business plan, bandi, finanziamenti e analisi usando il contesto del tuo lavoro.')+'</div></div>');
      f.lastChild.scrollIntoView({behavior:'smooth',block:'end'});
    }).catch(function(){});
};
})();
