// ═══ MATTER-COMPOSER.js — Il Composer (Laboratorio Ricette manipolabile) ═══
(function(){
var _co = { ingredienti:[], dati:null, loading:false };
// proprietà sensoriali principali da mostrare come barre (le più parlanti)
var _PROPS = [
  ['grasso','Grasso'], ['umami','Umami'], ['acido','Acido'], ['salato','Salato'],
  ['dolce','Dolce'], ['amaro','Amaro'], ['corposita','Corposità'], ['aroma_fresco','Aroma fresco'],
  ['aroma_caldo','Aroma caldo'], ['croccante','Croccante'], ['fermentato','Fermentato'], ['termico','Termico']
];

window.apriComposer = function(){ _co.ingredienti=[]; _co.dati=null; _apriVista('Composer', _coRender()); };

function _coRender(){
  var e=_escV;
  var chips = _co.ingredienti.length
    ? _co.ingredienti.map(function(ing,i){ return '<button class="co-chip" onclick="_coRimuovi('+i+')">'+e(ing)+'<span class="co-chip-x">×</span></button>'; }).join('')
    : '<div class="co-vuoto">Aggiungi un ingrediente per iniziare a costruire.</div>';
  var out = _co.dati ? _coProfilo(_co.dati) : '';
  return '<div class="co-hero"><div class="co-hero-lab">IL COMPOSER</div><div class="co-hero-claim">Costruisci una ricetta,<br>ingrediente per ingrediente.</div><div class="co-hero-sub">Aggiungi, togli, guarda l\'equilibrio cambiare in tempo reale. Non è una chat: è un laboratorio.</div></div>'
    + '<div class="co-add"><input id="co-input" placeholder="cerca un ingrediente (es. guanciale)" onkeydown="if(event.key===\'Enter\')_coAggiungiInput()"><button onclick="_coAggiungiInput()">+</button></div>'
    + '<div class="co-esempi-lab">Parti da un ingrediente</div>'
    + '<div class="co-esempi">'+['guanciale','pomodoro','cioccolato','gambero','fragola'].map(function(x){ return '<button class="co-esempio" onclick="_coAggiungi(\''+e(x)+'\')">'+e(x)+'</button>'; }).join('')+'</div>'
    + '<div class="co-esempi-lab">…oppure da un obiettivo</div>'
    + '<div class="co-esempi">'+['umami','freschezza','avvolgente','croccante','acidità'].map(function(x){ return '<button class="co-obiettivo" onclick="_coDaObiettivo(\''+e(x)+'\')">'+e(x)+'</button>'; }).join('')+'</div>'
    + '<div class="co-lab-ing">La tua ricetta</div>'
    + '<div class="co-chips" id="co-chips">'+chips+'</div>'
    + '<div id="co-out">'+out+'</div>';
}
function _coReRender(){ var b=document.getElementById('vista-body'); if(b){ b.innerHTML=_coRender(); b.scrollTop=b.scrollTop; } }

window._coAggiungiInput=function(){ var i=document.getElementById('co-input'); var v=i?i.value.trim():''; if(v) _coAggiungi(v); };
window._coAggiungi=function(ing){
  ing=ing.toLowerCase().trim();
  if(!ing || _co.ingredienti.indexOf(ing)>=0) return;
  _co.ingredienti.push(ing);
  _coCalcola();
};
window._coRimuovi=function(i){ _co.ingredienti.splice(i,1); if(_co.ingredienti.length) _coCalcola(); else { _co.dati=null; _coReRender(); } };

function _coCalcola(){
  _coReRender();
  var out=document.getElementById('co-out');
  if(out) out.innerHTML='<div class="vista-loading">Calcolo l\'equilibrio…</div>';
  fetch('/v1/composer/prossimi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ingredienti:_co.ingredienti})})
    .then(function(r){return r.json();})
    .then(function(j){ _co.dati=j; var o=document.getElementById('co-out'); if(o) o.innerHTML=_coProfilo(j); })
    .catch(function(){ var o=document.getElementById('co-out'); if(o) o.innerHTML='<div class="vista-empty">Errore di rete.</div>'; });
}

function _coProfilo(d){
  var e=_escV;
  var prof=d.profilo_sensoriale||{};
  // barre profilo sensoriale (il wow reattivo)
  var barre=_PROPS.filter(function(p){ return prof[p[0]]!=null; }).map(function(p){
    var v=prof[p[0]]||0, pct=Math.min(100, v*10);
    var forte=v>=5;
    return '<div class="co-bar-row"><span class="co-bar-lab">'+e(p[1])+'</span><div class="co-bar-track"><div class="co-bar-fill'+(forte?' forte':'')+'" style="width:'+pct+'%"></div></div><span class="co-bar-v">'+v+'</span></div>';
  }).join('');
  // alert contrasti
  var alerts='';
  var contr=d.contrasti_da_bilanciare||[];
  if(contr.length){
    alerts='<div class="co-alerts">'+contr.map(function(c){
      return '<div class="co-alert"><span class="co-alert-ico">⚠</span><span class="co-alert-txt"><b>'+e(c.proprieta||'')+'</b> — '+e(c.spiegazione||'')+'</span></div>';
    }).join('')+'</div>';
  }
  // suggeriti analogia
  var ana=d.suggeriti_analogia||[];
  var anaHtml = ana.length ? '<div class="co-sug-lab">Per analogia <span class="co-sug-sub">— stessi composti aromatici</span></div><div class="co-sug-grid">'
    + ana.slice(0,6).map(function(x){ return '<button class="co-sug co-sug-ana" onclick="_coAggiungi(\''+e(x.nome)+'\')"><span class="co-sug-nome">'+e(x.nome)+'</span><span class="co-sug-n">'+(x.composti_condivisi||'')+'</span></button>'; }).join('')
    + '</div>' : '';
  // suggeriti contrasto
  var con=d.suggeriti_contrasto||[];
  var conHtml = con.length ? '<div class="co-sug-lab">Per contrasto <span class="co-sug-sub">— bilanciano il piatto</span></div><div class="co-sug-list">'
    + con.slice(0,6).map(function(x){ return '<button class="co-sug-c" onclick="_coAggiungi(\''+e(x.nome)+'\')"><span class="co-sug-c-nome">'+e(x.nome)+'</span><span class="co-sug-c-motivo">'+e(x.motivo||'')+'</span></button>'; }).join('')
    + '</div>' : '';
  return '<div class="co-profilo"><div class="co-profilo-lab">◎ Profilo sensoriale</div>'+barre+'</div>'
    + alerts + anaHtml + conHtml
    + (_co.ingredienti.length>=2 ? '<button class="co-salva" onclick="_coDiagnosi()">Vedi la diagnosi della ricetta →</button>' : '');
}

window._coDaObiettivo=function(ob){
  var out=document.getElementById('co-out');
  if(out) out.innerHTML='<div class="vista-loading">Cerco l\'ingrediente-fulcro per "'+_escV(ob)+'"…</div>';
  fetch('/v1/composer/obiettivo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({obiettivo:ob})})
    .then(function(r){return r.json();})
    .then(function(j){
      var ful=(j.ingredienti_fulcro||[])[0];
      if(ful && ful.nome){ _coAggiungi(ful.nome); }
      else if(out){ out.innerHTML='<div class="vista-empty">Nessun ingrediente per questo obiettivo.</div>'; }
    }).catch(function(){ if(out) out.innerHTML='<div class="vista-empty">Errore di rete.</div>'; });
};
window._coDiagnosi=function(){
  var out=document.getElementById('co-out');
  fetch('/v1/composer/diagnosi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ingredienti:_co.ingredienti})})
    .then(function(r){return r.json();})
    .then(function(j){ _coMostraDiagnosi(j); })
    .catch(function(){});
};
function _coMostraDiagnosi(d){
  var e=_escV;
  var eq=(d.diagnosi_equilibrio||[]).map(function(x){ return '<li>'+e(x)+'</li>'; }).join('');
  var fen=(d.fenomeni_coinvolti||[]).map(function(x){ return '<span class="co-diag-fen">'+e(x)+'</span>'; }).join('');
  var note=(d.note_dominanti||[]).join(' · ');
  var html='<div class="co-diag"><div class="co-diag-lab">◎ DIAGNOSI DELLA RICETTA</div>'
    + (note?'<div class="co-diag-note">'+e(note)+'</div>':'')
    + (eq?'<ul class="co-diag-eq">'+eq+'</ul>':'')
    + (fen?'<div class="co-diag-fen-lab">Fenomeni coinvolti</div><div class="co-diag-fen-list">'+fen+'</div>':'')
    + '<button class="co-salva" onclick="_coSalva()">Salva nel Quaderno →</button></div>';
  var m=document.createElement('div'); m.className='co-diag-overlay'; m.innerHTML='<div class="co-diag-sheet">'+html+'<button class="co-diag-chiudi" onclick="this.closest(\'.co-diag-overlay\').remove()">Continua a costruire</button></div>';
  document.getElementById('vista-body').appendChild(m);
}
window._coSalva=function(){
  var nome = _co.ingredienti.join(' + ');
  _toast && _toast('✓ Ricetta "'+nome.slice(0,30)+'" salvata');
  // salvataggio reale via endpoint ricette se disponibile
  try{
    fetch('/v1/ricette/salva',{method:'POST',headers:_statoHeaders?_statoHeaders({'Content-Type':'application/json'}):{'Content-Type':'application/json'},body:JSON.stringify({nome:nome, dati:{ingredienti:_co.ingredienti, profilo:_co.dati?_co.dati.profilo_sensoriale:null, origine:'composer'}})});
  }catch(e){}
};
})();
