// ═══ MATTER-DIAGNOSI.js — La Diagnosi (board 6): "il luogo dove Matter dimostra di capire il mestiere" ═══
// Due tempi: SERVIZIO (20s: causa+patch, salva il banco) → COMPRENSIONE (il perché, espandibile).
// Triage, non chat. Chiede sensori (il corpo del cuoco), non numeri. Ranking, non certezze.
(function(){
var _PROB={alta:['Molto probabile','#9B3B2E'],media:['Possibile','#C77B3F'],bassa:['Meno probabile','#5A6C70']};

window.apriDiagnosi = function(sintomo){
  _apriVista('Diagnosi', _diagInput(sintomo||''));
  if(sintomo){ setTimeout(function(){ _diagCerca(sintomo); }, 100); }
};
function _diagInput(pre){
  var e=_escV;
  return '<div id="diag-host"><div class="diag-intro ds-grid-bg">'
    + '<div class="ds-eyebrow">◎ COSA NON FUNZIONA AL BANCO?</div>'
    + '<div class="diag-intro-t">Dimmi cosa vedi.<br>Matter risale alla causa.</div>'
    + '<div class="diag-intro-search"><input id="diag-input" placeholder="es. la carbonara è impazzita" value="'+e(pre)+'" onkeydown="if(event.key===\'Enter\')_diagVai()"><button onclick="_diagVai()">→</button></div>'
    + '<div class="diag-intro-hint">Descrivi il problema come lo diresti a un collega</div>'
    + '</div><div id="diag-esito"></div></div>';
}
window._diagVai=function(){ var i=document.getElementById('diag-input'); var q=i?i.value.trim():''; if(q) _diagCerca(q); };

function _diagCerca(sintomo){
  var box=document.getElementById('diag-esito'); if(box) box.innerHTML='<div class="vista-loading"></div>';
  fetch('/v1/diagnosi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sintomo:sintomo})})
    .then(function(r){return r.json();}).then(function(d){ _diagRender(d, sintomo); })
    .catch(function(){ var b=document.getElementById('diag-esito'); if(b) b.innerHTML='<div class="vista-empty">Errore. Riprova.</div>'; });
}

function _diagRender(d, sintomo){
  var e=_escV, box=document.getElementById('diag-esito'); if(!box) return;
  var cause=(d.cause||[]);
  if(!cause.length){ box.innerHTML='<div class="diag-vuoto">Non ho trovato una causa per "'+e(sintomo)+'". Prova a descrivere il sintomo in modo diverso, o chiedi a Matter.</div>'; return; }

  // ═══ TEMPO SERVIZIO (20s) — la causa probabile + fai questo adesso ═══
  var top=cause[0];
  var prob=_PROB[(top.probabilita||'media').toLowerCase()]||_PROB.media;
  var html='<div class="diag-servizio"><div class="diag-serv-lab">◎ FALLO ADESSO — SERVIZIO</div>'
    + '<div class="diag-causa-top"><span class="diag-prob" style="color:'+prob[1]+';border-color:'+prob[1]+'">'+prob[0]+'</span></div>'
    + '<div class="diag-causa-nome">'+e(top.causa)+'</div>'
    + (top.patch?'<div class="diag-patch"><span class="diag-patch-lab">→ La correzione</span><div class="diag-patch-txt">'+e(top.patch)+'</div></div>':'')
    + '</div>';

  // sensori da controllare (chip — "fammi vedere")
  var sens=(d.sensori_da_controllare||[]);
  if(sens.length){
    html+='<div class="diag-sez-lab">◎ CONTROLLA AL BANCO</div><div class="diag-sensori">'
      + sens.map(function(s){ var t=(typeof s==='object')?(s.domanda||s.sensore):s; var tp=(typeof s==='object')?(s.sensore||'vista'):'vista'; return window.dsSensore?dsSensore(tp,t):('<span class="ds-sensore">'+e(t)+'</span>'); }).join('')+'</div>';
  }

  // altre cause (ranking — "forse anche")
  if(cause.length>1){
    html+='<div class="diag-sez-lab">◎ OPPURE POTREBBE ESSERE</div><div class="diag-altre">'
      + cause.slice(1).map(function(c){
          var p=_PROB[(c.probabilita||'media').toLowerCase()]||_PROB.media;
          return '<div class="diag-altra"><div class="diag-altra-top"><span class="diag-altra-causa">'+e(c.causa)+'</span><span class="diag-altra-prob" style="color:'+p[1]+'">'+p[0]+'</span></div>'+(c.patch?'<div class="diag-altra-patch">'+e(c.patch)+'</div>':'')+'</div>';
        }).join('')+'</div>';
  }

  // ═══ TEMPO COMPRENSIONE (espandibile) — il perché ═══
  var caus=d.causalita_fenomeno||{};
  var hasCaus = caus && ((caus.acceleranti||[]).length || (caus.rallentanti||[]).length || (caus.conseguenze||[]).length);
  if(d.fenomeno || hasCaus){
    html+='<button class="diag-comprendi-toggle" onclick="_diagComprendi(this)">▼ Perché succede — capiscilo dopo il servizio</button>'
      + '<div class="diag-comprensione" style="display:none">'
      + (d.fenomeno?'<div class="diag-fenomeno"><span class="diag-fen-lab">Il fenomeno</span><span class="diag-fen-nome">'+e(d.fenomeno)+'</span></div>':'');
    if(hasCaus){
      html+='<div class="diag-catena">';
      (caus.acceleranti||[]).slice(0,4).forEach(function(a){ html+=_catenaRiga(a,'accelera','↑','#9B3B2E'); });
      (caus.rallentanti||[]).slice(0,4).forEach(function(a){ html+=_catenaRiga(a,'rallenta','↓','#3E5871'); });
      (caus.conseguenze||[]).slice(0,3).forEach(function(a){ html+=_catenaRiga(a,'porta a','→','#5A6C70'); });
      html+='</div>';
    }
    if(d.fonti_patrimonio){ html+='<div class="diag-fonti">Basato su '+d.fonti_patrimonio+' diagnosi verificate del patrimonio Matter</div>'; }
    html+='</div>';
  }
  box.innerHTML=html;
}
function _catenaRiga(a, verbo, freccia, col){
  var e=_escV;
  var fattore = (typeof a==='object')?(a.fattore||a.nome||''):a;
  var dir = (typeof a==='object'&&a.direzione)?a.direzione:'';
  return '<div class="diag-cat-riga"><span class="diag-cat-freccia" style="color:'+col+'">'+freccia+'</span><span class="diag-cat-verbo">'+verbo+'</span><span class="diag-cat-fattore">'+e(fattore)+(dir?' '+e(dir):'')+'</span></div>';
}
window._diagComprendi=function(btn){ var c=btn.nextElementSibling; if(c){ var vis=c.style.display!=='none'; c.style.display=vis?'none':'block'; btn.textContent=(vis?'▼':'▲')+' Perché succede'+(vis?' — capiscilo dopo il servizio':''); } };
})();
