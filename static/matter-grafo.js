// ═══ MATTER-GRAFO.js — Il Grafo Visuale navigabile (killer feature) ═══
(function(){
var _g = { centro:null, vista:'discipline', breadcrumb:[], dati:null };
var _VISTE = {
  sapori:     { lab:'Sapori',     ep:function(c){ return '/v1/flavour-network/'+encodeURIComponent(c); }, key:'nodi' },
  discipline: { lab:'Discipline', ep:function(c){ return '/v1/ponti/'+encodeURIComponent(c); }, key:'ponti' }
};

function _grNome(raw){
  var s=String(raw||'').replace(/_/g,' ').trim();
  if(!s) return '';
  return s.charAt(0).toUpperCase()+s.slice(1);
}
function _grDedup(nodi){
  var visti={}, out=[];
  nodi.forEach(function(n){
    var k=_grNome(n.nome).toLowerCase();
    if(!visti[k]){ visti[k]=1; out.push(n); }
  });
  return out;
}
function _grLabel(nome){
  var s=_grNome(nome);
  return s.length>12 ? s.slice(0,11)+'\u2026' : s;
}
window.apriGrafo = function(ingredienteIniziale){
  _g.centro = ingredienteIniziale||'pomodoro';
  _g.vista='discipline'; _g.breadcrumb=[_g.centro];
  _apriVista('Il Grafo', _grafoShell());
  _grafoCarica();
};

function _grafoShell(){
  var e=_escV;
  return '<div class="gr-toggle">'
    + Object.keys(_VISTE).map(function(k){ return '<button class="gr-tab'+(_g.vista===k?' on':'')+'" onclick="_grafoVista(\''+k+'\')">'+e(_VISTE[k].lab)+'</button>'; }).join('')
    + '</div>'
    + '<div class="gr-breadcrumb" id="gr-breadcrumb"></div>'
    + '<div class="gr-canvas-wrap"><div id="gr-canvas" class="gr-canvas"><div class="vista-loading">Carico il grafo…</div></div></div>'
    + '<div class="gr-hint">Tocca un nodo per esplorarlo · tocca il centro per aprirne la scheda</div>'
    + '<div id="gr-sheet"></div>';
}
window._grafoVista=function(v){ _g.vista=v; document.querySelectorAll('.gr-tab').forEach(function(b){ b.classList.toggle('on', b.textContent===_VISTE[v].lab); }); _grafoCarica(); };

function _grafoCarica(){
  _grafoBreadcrumb();
  var cv=document.getElementById('gr-canvas');
  if(cv) cv.innerHTML='<div class="vista-loading">…</div>';
  var V=_VISTE[_g.vista];
  fetch(V.ep(_g.centro)).then(function(r){return r.json();}).then(function(d){
    _g.dati=d; _grafoDisegna(d, V);
  }).catch(function(){ if(cv) cv.innerHTML='<div class="vista-empty">Errore di rete.</div>'; });
}

function _grafoDisegna(d, V){
  var e=_escV, cv=document.getElementById('gr-canvas');
  if(!cv) return;
  var nodi=[];
  if(_g.vista==='sapori'){
    var grezzi=(d.nodi||[]).map(function(n){ return {nome:n.nome, forza:n.forza||50, perche:n.perche}; });
    // deduplica per famiglia: max 2 per prefisso (evita 8 varianti d'aceto ripetitive)
    var perFam={}, filtrati=[];
    grezzi.forEach(function(n){
      var fam=String(n.nome).toLowerCase().split(/[ \-]/)[0];
      perFam[fam]=(perFam[fam]||0)+1;
      if(perFam[fam]<=2) filtrati.push(n);
    });
    nodi=_grDedup(filtrati).slice(0,14);
  }
  else { // discipline: appiattisco i ponti in nodi
    (d.ponti||[]).forEach(function(p){ (p.abbinati||[]).slice(0,3).forEach(function(a){ nodi.push({nome:a.ingrediente, forza:a.affinita||a.forza||60, disc:p.disciplina}); }); });
    nodi=_grDedup(nodi).slice(0,14);
  }
  if(!nodi.length){ cv.innerHTML='<div class="vista-empty">Nessuna connessione per "'+e(_g.centro)+'".</div>'; return; }
  var W=358, H=360, cx=W/2, cy=H/2, R=125;
  var svg='<svg class="gr-svg" viewBox="0 0 '+W+' '+H+'" xmlns="http://www.w3.org/2000/svg">';
  // archi (spessore = forza)
  nodi.forEach(function(n,i){
    var ang=(-90 + i*(360/nodi.length))*Math.PI/180;
    var x=cx+R*Math.cos(ang), y=cy+R*Math.sin(ang);
    var sw=1+(n.forza/100)*3.5;
    svg+='<line x1="'+cx+'" y1="'+cy+'" x2="'+x+'" y2="'+y+'" stroke="#c4c0b4" stroke-width="'+sw.toFixed(1)+'" class="gr-line" style="animation-delay:'+(i*0.04)+'s"/>';
  });
  // nodi esterni (tap = naviga N+1)
  nodi.forEach(function(n,i){
    var ang=(-90 + i*(360/nodi.length))*Math.PI/180;
    var x=cx+R*Math.cos(ang), y=cy+R*Math.sin(ang);
    var forte=n.forza>=75;
    svg+='<g class="gr-node" style="animation-delay:'+(i*0.04+0.1)+'s" onclick="_grafoNaviga(\''+e(String(n.nome)).replace(/'/g,"\\'")+'\')">';
    svg+='<circle cx="'+x+'" cy="'+y+'" r="20" fill="#fff" stroke="'+(forte?'#c77b3f':'#245979')+'" stroke-width="'+(forte?2:1.5)+'"/>';
    svg+='<text x="'+x+'" y="'+(y+3)+'" text-anchor="middle" font-family="Inter,sans-serif" font-size="8.5" fill="#141d22">'+e(_grLabel(n.nome))+'</text>';
    svg+='<text x="'+x+'" y="'+(y+13)+'" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="8" font-weight="700" fill="'+(forte?'#c77b3f':'#245979')+'">'+Math.round(n.forza)+'</text>';
    svg+='</g>';
  });
  // centro (tap = scheda portale)
  svg+='<g class="gr-centro" onclick="_grafoPortale(\''+e(String(_g.centro)).replace(/'/g,"\\'")+'\')">';
  svg+='<circle cx="'+cx+'" cy="'+cy+'" r="30" fill="#141d22" stroke="#c77b3f" stroke-width="2.5"/>';
  svg+='<text x="'+cx+'" y="'+(cy+4)+'" text-anchor="middle" font-family="Space Grotesk,sans-serif" font-weight="700" font-size="11" fill="#e8935a">'+e(_grLabel(_g.centro))+'</text>';
  svg+='</g></svg>';
  cv.innerHTML=svg;
}

window._grafoNaviga=function(nome){
  // N+1: il nodo toccato diventa il nuovo centro
  _g.centro=nome;
  if(_g.breadcrumb[_g.breadcrumb.length-1]!==nome) _g.breadcrumb.push(nome);
  if(_g.breadcrumb.length>5) _g.breadcrumb=_g.breadcrumb.slice(-5);
  _grafoCarica();
};

function _grafoBreadcrumb(){
  var e=_escV, bc=document.getElementById('gr-breadcrumb');
  if(!bc) return;
  bc.innerHTML=_g.breadcrumb.map(function(x,i){
    var last=i===_g.breadcrumb.length-1;
    return '<button class="gr-crumb'+(last?' on':'')+'" onclick="_grafoVaiA('+i+')">'+e(x)+'</button>'+(last?'':'<span class="gr-crumb-sep">›</span>');
  }).join('');
}
window._grafoVaiA=function(i){ _g.centro=_g.breadcrumb[i]; _g.breadcrumb=_g.breadcrumb.slice(0,i+1); _grafoCarica(); };

// PORTALE: bottom sheet con nodo-completo
window._grafoPortale=function(nome){
  var sheet=document.getElementById('gr-sheet');
  if(!sheet) return;
  sheet.innerHTML='<div class="gr-sheet-overlay"><div class="gr-sheet"><div class="vista-loading">Carico la scheda…</div></div></div>';
  // provo per id (se ho l'id) o per nome
  fetch('/v1/nodo-completo/'+encodeURIComponent(nome)).then(function(r){return r.json();}).then(function(d){
    if(d.errore || !d.nome){ // fallback: scheda ingrediente per nome
      fetch('/v1/ingrediente/'+encodeURIComponent(nome)).then(function(r){return r.json();}).then(_grafoRenderSheet).catch(function(){ sheet.innerHTML=''; });
      return;
    }
    _grafoRenderSheet(d);
  }).catch(function(){ sheet.innerHTML=''; });
};
function _grafoRenderSheet(d){
  var e=_escV, sheet=document.getElementById('gr-sheet');
  var props=d.proprieta_principali||{};
  var PLAB={grasso:'Grasso',umami:'Umami',acido:'Acido',salato:'Salato',dolce:'Dolce',amaro:'Amaro',corposita:'Corposità',aroma_fresco:'Aroma fresco',aroma_caldo:'Aroma caldo'};
  var barre=Object.keys(props).slice(0,6).map(function(k){ var v=props[k]||0; return '<div class="gr-pb"><span class="gr-pb-l">'+e(PLAB[k]||k)+'</span><div class="gr-pb-t"><div class="gr-pb-f'+(v>=5?' forte':'')+'" style="width:'+Math.min(100,v*10)+'%"></div></div></div>'; }).join('');
  var dial=(d.dialoga_con||[]).slice(0,6).map(function(x){ return '<span class="gr-tag">'+e(String(x).replace(/_/g,' '))+'</span>'; }).join('');
  var fen=(d.fenomeni||[]).slice(0,4).map(function(x){ return '<span class="gr-tag gr-tag-fen">'+e(typeof x==='string'?x:(x.nome||''))+'</span>'; }).join('');
  var h='<div class="gr-sheet-h"><div class="gr-sheet-nome">'+e(d.nome)+'</div>'+(d.categoria?'<div class="gr-sheet-cat">'+e(d.categoria)+'</div>':'')+'</div>';
  if(d.caratteristica) h+='<div class="gr-sheet-car">'+e(d.caratteristica)+'</div>';
  if(barre) h+='<div class="gr-sheet-lab">Profilo</div><div class="gr-sheet-prof">'+barre+'</div>';
  if(dial) h+='<div class="gr-sheet-lab">Dialoga con</div><div class="gr-tags">'+dial+'</div>';
  if(fen) h+='<div class="gr-sheet-lab">Fenomeni</div><div class="gr-tags">'+fen+'</div>';
  h+='<button class="gr-sheet-composer" onclick="chiudiVista();_caricaModulo(\'composer\').then(function(){apriComposer&&apriComposer();setTimeout(function(){_coAggiungi&&_coAggiungi(\''+e(String(d.nome)).replace(/'/g,"\\'")+'\')},400)})">Invia al Composer →</button>';
  h+='<button class="gr-sheet-chiedi" onclick=\'_chatConContesto("ingrediente",'+JSON.stringify({nome:d.nome, caratteristica:d.caratteristica||'', uso_tipico:d.uso_tipico||'', dialoga_con:d.dialoga_con||[], fenomeni:d.fenomeni||[]}).replace(/'/g,"&#39;")+')\'>Chiedi a Matter →</button>';
  sheet.innerHTML='<div class="gr-sheet-overlay" onclick="if(event.target===this)this.remove()"><div class="gr-sheet">'+h+'<button class="gr-sheet-chiudi" onclick="this.closest(\'.gr-sheet-overlay\').remove()">Chiudi</button></div></div>';
}
})();
