// ═══ MATTER-PLANNER.js — Planner Menu (5ª porta: PROGETTARE) ═══
(function(){
var _pl = { giorni:30, slot:['primo','secondo','contorno'], no_ripeti:5, mese:(new Date().getMonth()+1), budget:null, escludi:[], lock:{}, step:1, risposta:null };
var _PORTATE = ['antipasto','primo','secondo','contorno','dolce','pane','drink'];
var _MESI = ['','Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno','Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre'];

window._plSetGiorni=function(n){ _pl.giorni=n; _plReRender(); };
window._plStep=function(n){ _pl.step=n; _plReRender(); };
window.apriPlanner = function(){ _pl.step=1; _pl.risposta=null; _apriVista('Planner Menu', _plRender()); };

function _plRender(){
  if(_pl.step===1) return _plStep1();
  if(_pl.step===2) return _plStep2();
  if(_pl.step===3) return _plStep3();
  return _plStep4();
}
function _plReRender(){ var b=document.getElementById('vista-body'); if(b){ b.innerHTML=_plRender(); b.scrollTop=0; } }
window._plReRender=_plReRender;

// ── SCHERMATA 1: OBIETTIVO ──
function _plStep1(){
  var e=_escV;
  var slotChips=_PORTATE.map(function(p){
    var on=_pl.slot.indexOf(p)>=0;
    return '<button class="pl-portata'+(on?' sel':'')+'" onclick="_plToggleSlot(\''+p+'\')">'+e(p)+'</button>';
  }).join('');
  return '<div class="pl-head"><span class="pl-num">1/4</span><span class="pl-eyebrow">— L\'OBIETTIVO</span></div>'
    + '<div class="pl-h">Cosa vuoi<br>progettare?</div>'
    + '<div class="pl-lab">PERIODO</div>'
    + '<div class="pl-btn-row">'
    +   '<button class="pl-btn'+(_pl.giorni===30?' sel':'')+'" onclick="_plSetGiorni(30)">30 giorni</button>'
    +   '<button class="pl-btn'+(_pl.giorni===60?' sel':'')+'" onclick="_plSetGiorni(60)">60 giorni</button>'
    + '</div>'
    + '<div class="pl-lab">PORTATE PER GIORNO <span class="pl-lab-sub">('+_pl.slot.length+' selezionate)</span></div>'
    + '<div class="pl-portate-grid">'+slotChips+'</div>'
    + '<div class="pl-lab">MESE DI PARTENZA (stagionalità)</div>'
    + '<select class="pl-select" id="pl-mese" onchange="_pl.mese=+this.value">'+_MESI.map(function(m,i){ return i?'<option value="'+i+'"'+(i===_pl.mese?' selected':'')+'>'+m+'</option>':''; }).join('')+'</select>'
    + '<button class="pl-avanti" onclick="_plVai2()">Avanti · Regole →</button>';
}
window._plToggleSlot=function(p){ var i=_pl.slot.indexOf(p); if(i>=0){ if(_pl.slot.length>1) _pl.slot.splice(i,1); } else _pl.slot.push(p); _plReRender(); };
window._plVai2=function(){ _pl.step=2; _plReRender(); };

// ── SCHERMATA 2: REGOLE ──
function _plStep2(){
  return '<div class="pl-head"><span class="pl-num">2/4</span><span class="pl-eyebrow">— LE REGOLE</span></div>'
    + '<div class="pl-h">Con quali<br>vincoli?</div>'
    + '<div class="pl-lab">NON RIPETERE UN PIATTO PER <span class="pl-lab-sub" id="pl-ripeti-v">'+_pl.no_ripeti+' giorni</span></div>'
    + '<input type="range" class="pl-range" min="1" max="14" value="'+_pl.no_ripeti+'" oninput="_pl.no_ripeti=+this.value;document.getElementById(\'pl-ripeti-v\').textContent=this.value+\' giorni\'">'
    + '<div class="pl-lab">FOOD COST TARGET €/GIORNO (opzionale)</div>'
    + '<div class="pl-inp-u"><input type="number" inputmode="decimal" id="pl-budget" placeholder="es. 6" value="'+(_pl.budget!=null?_pl.budget:'')+'"><span>€</span></div>'
    + '<div class="pl-lab">INGREDIENTI DA ESCLUDERE (opzionale)</div>'
    + '<input class="pl-inp" id="pl-escludi" placeholder="es. pesce, maiale (separati da virgola)" value="'+_escV(_pl.escludi.join(', '))+'">'
    + '<button class="pl-progetta" onclick="_plGenera()">Progetta il menu →</button>';
}
window._plGenera=function(){
  var bv=document.getElementById('pl-budget'); _pl.budget = bv&&bv.value?parseFloat(bv.value):null;
  var ev=document.getElementById('pl-escludi'); _pl.escludi = ev&&ev.value?ev.value.split(',').map(function(x){return x.trim();}).filter(Boolean):[];
  _pl.step=3;
  var b=document.getElementById('vista-body');
  if(b) b.innerHTML='<div class="pl-head pl-head3"><span class="pl-eyebrow">◎ IL CALENDARIO</span></div><div class="skel-card skeleton" style="height:300px;margin:16px"></div>';
  var body={ giorni:_pl.giorni, slot:_pl.slot, no_ripeti_giorni:_pl.no_ripeti, mese:_pl.mese };
  if(_pl.budget!=null) body.target_food_cost_giorno=_pl.budget;
  if(_pl.escludi.length) body.escludi_ingredienti=_pl.escludi;
  if(Object.keys(_pl.lock).length) body.lock=_pl.lock;
  fetch('/v1/planner/genera',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    .then(function(r){return r.json();})
    .then(function(j){ _pl.risposta=j; _plReRender(); })
    .catch(function(){ _pl.risposta={errore:true}; _plReRender(); });
};

// ── SCHERMATA 3: CALENDARIO ──
function _plStep3(){
  var e=_escV, d=_pl.risposta;
  if(!d || d.errore) return '<div class="pl-head pl-head3"><span class="pl-eyebrow">◎ IL CALENDARIO</span></div><div class="vista-empty">Errore nella generazione. <button class="pl-btn" onclick="_plStep(2)">Torna alle regole</button></div>';
  var cal=d.calendario||[];
  var giorni=cal.map(function(g){
    var fcGiorno=g.food_cost_giorno;
    if(fcGiorno==null){ fcGiorno=(g.slot_piatti||[]).reduce(function(s,sp){ return s+(sp.food_cost_teorico||0); },0); fcGiorno=Math.round(fcGiorno*10)/10; }
    var piatti=(g.slot_piatti||[]).map(function(sp){
      return '<div class="pl-piatto"><span class="pl-piatto-portata">'+e(sp.portata)+'</span><span class="pl-piatto-nome">'+e(sp.nome)+'</span><span class="pl-piatto-fc">'+(sp.food_cost_teorico!=null?'€'+sp.food_cost_teorico:'')+'</span></div>';
    }).join('');
    return '<div class="pl-giorno'+(g.sfora_budget?' sfora':'')+'">'
      + '<div class="pl-giorno-top"><span class="pl-giorno-n">Giorno '+g.giorno_index+'</span><span class="pl-giorno-fc'+(g.sfora_budget?' sfora':'')+'">€'+fcGiorno+'</span></div>'
      + piatti + '</div>';
  }).join('');
  return '<div class="pl-head pl-head3"><span class="pl-eyebrow">◎ IL CALENDARIO</span><span class="pl-ricetta-lab">'+_pl.giorni+' GIORNI</span></div>'
    + '<div class="pl-cal-sommario">'+_pl.slot.length+' portate/giorno · '+(_pl.budget!=null?'target €'+_pl.budget:'nessun budget')+'</div>'
    + '<div class="pl-cal">'+giorni+'</div>'
    + '<button class="pl-genera-btn" onclick="_plGenera()">↻ Rigenera</button>'
    + '<button class="pl-analisi-btn" onclick="_plStep(4)">Vedi l\'analisi →</button>';
}

// ── SCHERMATA 4: ANALISI ──
function _plStep4(){
  var e=_escV, d=_pl.risposta||{}, a=d.analisi||{};
  var righe=[
    ['Piatti totali', a.n_piatti_totali!=null?a.n_piatti_totali:'—', false],
    ['Piatti unici (varietà)', a.piatti_unici!=null?a.piatti_unici:'—', false],
    ['Food cost medio/giorno', a.food_cost_medio_giorno_eur!=null?'€'+a.food_cost_medio_giorno_eur:'—', true],
    ['Food cost totale periodo', a.food_cost_totale_periodo_eur!=null?'€'+a.food_cost_totale_periodo_eur:'—', true]
  ];
  var varieta = (a.piatti_unici && a.n_piatti_totali) ? Math.round(a.piatti_unici/a.n_piatti_totali*100) : null;
  return '<div class="pl-head pl-head3"><span class="pl-eyebrow">◎ L\'ANALISI</span></div>'
    + '<div class="pl-h">Il tuo menu<br>in numeri.</div>'
    + (varieta!=null?'<div class="pl-varieta"><div class="pl-varieta-n">'+varieta+'%</div><div class="pl-varieta-lab">varietà del menu — quanti piatti diversi sul totale</div></div>':'')
    + '<div class="pl-analisi-box">'+righe.map(function(r){ return '<div class="pl-an-row"><span class="pl-an-k">'+e(r[0])+'</span><span class="pl-an-v'+(r[2]?' evid':'')+'">'+e(String(r[1]))+'</span></div>'; }).join('')+'</div>'
    + '<button class="pl-genera-btn" onclick="_plStep(3)">← Torna al calendario</button>';
}
})();
