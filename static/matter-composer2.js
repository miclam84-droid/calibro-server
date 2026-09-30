// ═══ MATTER-COMPOSER2.js — Il Composer (board 5): "la materia è la risposta della simulazione" ═══
// SIMULA: cambia una variabile → la TIMELINE degli effetti si propaga nel tempo. Non testo: conseguenze.
(function(){
var _co={ ingredienti:[], variabile:'idratazione', da:65, a:75 };

window.apriComposer2 = function(){
  _apriVista('Composer', _cmpShell());
  _cmpRenderAbbinamenti();
};
function _cmpShell(){
  var e=_escV;
  return '<div id="cmp-host">'
    + '<div class="cmp-hero ds-grid-bg"><div class="ds-eyebrow">◎ IL LABORATORIO MENTALE</div>'
    +   '<div class="ds-display cmp-hero-t" style="color:#fff">Cosa succede<br>se cambio…</div>'
    +   '<div class="cmp-hero-sub">Simula una variabile. Vedi gli effetti propagarsi nel tempo.</div></div>'
    // SIMULA
    + '<div class="cmp-sez-lab">◎ SIMULA</div>'
    + '<div class="cmp-simula">'
    +   '<div class="cmp-var-row"><span class="cmp-var-nome" id="cmp-var-nome">Idratazione</span></div>'
    +   '<div class="cmp-slider-wrap">'
    +     '<div class="cmp-slider-cap"><span>da <b id="cmp-da">65</b>%</span><span>a <b id="cmp-a">75</b>%</span></div>'
    +     '<input type="range" id="cmp-slider" min="50" max="90" value="75" oninput="_cmpSliderMove(this.value)">'
    +   '</div>'
    +   '<button class="cmp-simula-btn" onclick="_cmpSimula()">▶ Simula la variazione</button>'
    + '</div>'
    + '<div id="cmp-timeline"></div>'
    // ABBINAMENTI
    + '<div class="cmp-sez-lab">◎ ABBINAMENTI GOVERNATI</div>'
    + '<div id="cmp-abbinamenti"><div class="vista-loading"></div></div>'
    + '</div>';
}
window._cmpSliderMove=function(v){ _co.a=parseInt(v,10); var a=document.getElementById('cmp-a'); if(a) a.textContent=v; };

window._cmpSimula=function(){
  var tl=document.getElementById('cmp-timeline'); if(tl) tl.innerHTML='<div class="vista-loading"></div>';
  fetch('/v1/composer/simula',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reagenti:['farina','acqua'], variabile:_co.variabile, da_valore:String(_co.da), a_valore:String(_co.a)})})
    .then(function(r){return r.json();}).then(function(d){ _cmpRenderTimeline(d); })
    .catch(function(){ var t=document.getElementById('cmp-timeline'); if(t) t.innerHTML='<div class="vista-empty">Errore nella simulazione.</div>'; });
};
function _cmpRenderTimeline(d){
  var e=_escV, box=document.getElementById('cmp-timeline'); if(!box) return;
  var tl=(d.effetti_timeline||[]);
  if(!tl.length){ box.innerHTML='<div class="cmp-vuoto">Nessun effetto simulato per questa variazione.</div>'; return; }
  var html='<div class="cmp-tl-head">'+e(d.variabile||'Variabile')+': <span class="ds-data">'+e(d.da||_co.da)+'</span> → <span class="ds-data" style="color:var(--ds-rame)">'+e(d.a||_co.a)+'</span></div>'
    + '<div class="cmp-tl">';
  tl.forEach(function(ef,i){
    var quando=(typeof ef==='object')?(ef.quando||('Fase '+(i+1))):'';
    var eff=(typeof ef==='object')?(ef.effetto||''):String(ef);
    var perche=(typeof ef==='object')?(ef.perche||''):'';
    html+='<div class="cmp-tl-nodo"><div class="cmp-tl-marker"></div><div class="cmp-tl-body">'
      + (quando?'<div class="cmp-tl-quando">'+e(quando)+'</div>':'')
      + '<div class="cmp-tl-effetto">'+e(eff)+'</div>'
      + (perche?'<div class="cmp-tl-perche">'+e(perche)+'</div>':'')
      + '</div></div>';
  });
  html+='</div>';
  // fenomeni attivati
  var fen=(d.fenomeni_attivati||[]);
  if(fen.length){ html+='<div class="cmp-fen-lab">Fenomeni attivati</div><div class="cmp-fen">'+fen.map(function(f){return '<span class="cmp-fen-chip">'+e(typeof f==='string'?f:(f.nome||''))+'</span>';}).join('')+'</div>'; }
  // avvertimenti (rischi)
  var avv=(d.avvertimenti||[]);
  if(avv.length){ html+='<div class="cmp-avv-lab">⚠ Attenzione</div>'+avv.map(function(a){return '<div class="cmp-avv">'+e(typeof a==='string'?a:(a.testo||''))+'</div>';}).join(''); }
  // salva come commit
  html+='<button class="cmp-commit" onclick="_cmpCommit()">◱ Salva questo esperimento nel Quaderno</button>';
  box.innerHTML=html;
}

function _cmpRenderAbbinamenti(){
  fetch('/v1/composer/prossimi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ingredienti:['pomodoro']})})
    .then(function(r){return r.json();}).then(function(d){
      var e=_escV, box=document.getElementById('cmp-abbinamenti'); if(!box) return;
      var trad=(d.suggeriti_tradizione||[]).slice(0,4);
      var scop=(d.suggeriti_analogia||[]).slice(0,3);
      var html='';
      if(trad.length){ html+='<div class="cmp-abb-grp"><div class="cmp-abb-grp-lab">Tradizione — fiducia alta</div>'+trad.map(function(x){return '<div class="cmp-abb cmp-abb-trad"><span class="cmp-abb-nome">'+e(x.nome)+'</span>'+(x.piatto?'<span class="cmp-abb-piatto">'+e(x.piatto)+'</span>':'')+'</div>';}).join('')+'</div>'; }
      if(scop.length){ html+='<div class="cmp-abb-grp"><div class="cmp-abb-grp-lab">Scoperta molecolare — fiducia dichiarata bassa</div>'+scop.map(function(x){return '<div class="cmp-abb cmp-abb-scop"><span class="cmp-abb-nome">'+e(x.nome)+'</span>'+(x.motivo?'<span class="cmp-abb-motivo">'+e(x.motivo)+'</span>':'')+'</div>';}).join('')+'</div>'; }
      box.innerHTML=html||'<div class="cmp-vuoto">Nessun abbinamento.</div>';
    }).catch(function(){ var b=document.getElementById('cmp-abbinamenti'); if(b) b.innerHTML=''; });
}
window._cmpCommit=function(){
  fetch('/v1/quaderno/esperimento',{method:'POST',headers:{'Content-Type':'application/json','X-Device-Id':(localStorage.getItem('matter_device_id')||'anon')},body:JSON.stringify({nome:'Simulazione '+_co.variabile+' '+_co.da+'→'+_co.a, parametri:{variabile:_co.variabile,da:_co.da,a:_co.a}, esito:'simulato'})})
    .then(function(r){return r.json();}).then(function(j){ if(typeof _toast==='function') _toast('◱ Esperimento salvato nel Quaderno'+(j.commit_n?' #'+j.commit_n:'')); }).catch(function(){ if(typeof _toast==='function') _toast('Errore nel salvataggio'); });
};
})();
