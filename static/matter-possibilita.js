// ═══ MATTER-POSSIBILITA.js — Il Grafo delle Possibilità V2 (Board #50) ═══
(function(){
var _RUOLO_LAB={ base:'Base', grasso:'Grasso', acido:'Acido', freschezza:'Freschezza', croccantezza:'Croccantezza', umami:'Umami', dolcezza:'Dolcezza', struttura:'Struttura', sapidita:'Sapidità', aroma:'Aroma' };

window.apriPossibilita = function(ingredienteIniziale){
  var e=_escV;
  _apriVista('Possibilità',
    '<div class="ps-hero"><div class="ps-hero-lab">ESPLORA · IL PIATTO CHE NASCE</div>'
    + '<div class="ps-hero-claim">Parti da un ingrediente.<br>Costruisci un piatto.</div>'
    + '<div class="ps-hero-sub">Non abbinamenti a caso: i ruoli dell\'ingrediente, e il piatto embrionale che può diventare.</div></div>'
    + '<div class="ps-field"><input id="ps-input" placeholder="pomodoro, guanciale, limone…" onkeydown="if(event.key===\'Enter\')caricaPossibilita()"><button class="ps-go" onclick="caricaPossibilita()">→</button></div>'
    + '<div class="ps-chips">'+['pomodoro','guanciale','limone','melanzana','cioccolato'].map(function(c){ return '<button class="ps-chip" onclick="_psCerca(\''+e(c)+'\')">'+e(c)+'</button>'; }).join('')+'</div>'
    + '<div id="ps-out"></div>');
  var inp=document.getElementById('ps-input');
  var start=ingredienteIniziale||'pomodoro';
  if(inp) inp.value=start;
  caricaPossibilita();
};
window._psCerca=function(ing){ var i=document.getElementById('ps-input'); if(i)i.value=ing; caricaPossibilita(); };

window.caricaPossibilita = function(){
  var inp=document.getElementById('ps-input'); var q=inp?inp.value.trim():'';
  if(!q) return;
  var out=document.getElementById('ps-out');
  if(out) out.innerHTML='<div class="vista-loading">Costruisco le possibilità…</div>';
  fetch('/v1/possibilita/'+encodeURIComponent(q)+'?contesto=piatto').then(function(r){return r.json();}).then(function(d){
    _psRender(d);
  }).catch(function(){ if(out) out.innerHTML='<div class="vista-empty">Errore di rete.</div>'; });
};

function _psRender(d){
  var e=_escV, out=document.getElementById('ps-out');
  if(!out) return;
  var centro=d.centro||'';
  // 1. FIRMA DI RUOLI
  var firma=(d.firma_ruoli||[]);
  var firmaHtml = firma.length ? '<div class="ps-sec-lab">Chi è '+e(centro)+'</div><div class="ps-firma">'
    + firma.map(function(r){ return '<div class="ps-ruolo"><div class="ps-ruolo-top"><span class="ps-ruolo-n">'+e(r.ruolo)+'</span><span class="ps-ruolo-f">'+(r.forza||'')+'</span></div>'+(r.desc?'<div class="ps-ruolo-d">'+e(r.desc)+'</div>':'')+'</div>'; }).join('')
    + '</div>' : '';
  // 2. IL BLUEPRINT (protagonista)
  var bp=d.blueprint||{};
  var bpKeys=Object.keys(bp);
  var bpHtml='';
  if(bpKeys.length){
    // base per prima, poi gli altri ruoli
    var ordine=['base'].concat(bpKeys.filter(function(k){return k!=='base';}));
    bpHtml='<div class="ps-sec-lab">◎ Il piatto che nasce</div><div class="ps-blueprint">'
      + ordine.filter(function(k){return bp[k];}).map(function(k){
          var isBase=(k==='base');
          return '<div class="ps-bp-riga'+(isBase?' ps-bp-base':'')+'"><span class="ps-bp-ruolo">'+e(_RUOLO_LAB[k]||k)+'</span><span class="ps-bp-ing">'+e(String(bp[k]).replace(/_/g,' '))+'</span></div>';
        }).join('')
      + '</div>';
  }
  // 3. EQUILIBRIO
  var prosp=d.prospettive||{};
  var eq=(prosp.equilibrio||[]);
  var eqHtml = eq.length ? '<div class="ps-sec-lab">Per bilanciare, aggiungi</div><div class="ps-equilibrio">'
    + eq.map(function(x){ return '<button class="ps-eq" onclick="_psCerca(\''+e(String(x.ingrediente)).replace(/'/g,"\\'")+'\')"><span class="ps-eq-ing">'+e(String(x.ingrediente).replace(/_/g,' '))+'</span><span class="ps-eq-ruolo">'+e(x.ruolo||'')+'</span></button>'; }).join('')
    + '</div>' : '';
  // Tradizione / Scoperta: solo se non vuote (nota onesta)
  var trad=(prosp.tradizione||[]);
  var scop=(prosp.scoperta||[]);
  var tradHtml = trad.length ? '<div class="ps-sec-lab">I classici</div><div class="ps-lista-sec">'+trad.map(function(x){ return '<button class="ps-eq" onclick="_psCerca(\''+e(String(x.ingrediente||x.nome)).replace(/'/g,"\\'")+'\')"><span class="ps-eq-ing">'+e(String(x.ingrediente||x.nome).replace(/_/g,' '))+'</span></button>'; }).join('')+'</div>' : '';
  var scopHtml = scop.length ? '<div class="ps-sec-lab">Sorprese molecolari</div><div class="ps-lista-sec">'+scop.map(function(x){ return '<button class="ps-eq" onclick="_psCerca(\''+e(String(x.ingrediente||x.nome)).replace(/'/g,"\\'")+'\')"><span class="ps-eq-ing">'+e(String(x.ingrediente||x.nome).replace(/_/g,' '))+'</span></button>'; }).join('')+'</div>' : '';
  // CTA composer (porta il blueprint nel Composer)
  var cta='<button class="ps-composer" onclick="_psAlComposer('+JSON.stringify(JSON.stringify(bp)).replace(/'/g,"&#39;")+')">Costruisci questo piatto nel Composer →</button>';
  out.innerHTML='<div class="ps-res-head"><span class="ps-res-nome">'+e(centro)+'</span></div>'
    + firmaHtml + bpHtml + eqHtml + tradHtml + scopHtml + cta;
}
window._psAlComposer=function(bpJson){
  var bp={}; try{ bp=JSON.parse(bpJson); }catch(e){}
  var ings=Object.keys(bp).map(function(k){ return bp[k]; }).filter(Boolean);
  chiudiVista&&chiudiVista();
  _caricaModulo('composer').then(function(){
    if(window.apriComposer) apriComposer();
    setTimeout(function(){ ings.forEach(function(ing){ if(window._coAggiungi) _coAggiungi(String(ing)); }); }, 500);
  });
};
})();
