// ═══ MATTER-SCIENZA.js — Schede Scienza (la scienza del mestiere navigabile) ═══
(function(){
var _CATLAB={ 'grande lievitato':'Grandi lievitati','lievitato':'Lievitati','base/sugo':'Basi e sughi','base/salsa':'Salse madri','emulsione':'Emulsioni','pasticceria':'Pasticceria','base/tecnica':'Basi e tecniche','tecnica':'Tecniche','bar':'Bar' };

window.apriSchedeScienza = function(){
  _apriVista('Schede Scienza',
    '<div class="sc-hero"><div class="sc-hero-lab">IMPARA · LA SCIENZA DEL MESTIERE</div>'
    + '<div class="sc-hero-claim">Non ricette. I numeri e i fenomeni dietro ogni preparazione madre.</div></div>'
    + '<div id="sc-lista"><div class="vista-loading">Carico le schede…</div></div>');
  fetch('/v1/schede-scienza').then(function(r){return r.json();}).then(function(d){
    var schede=d.schede||[];
    var cont=document.getElementById('sc-lista'); if(!cont) return;
    if(!schede.length){ cont.innerHTML='<div class="vista-empty">Nessuna scheda disponibile.</div>'; return; }
    // raggruppo per categoria
    var gruppi={};
    schede.forEach(function(s){ var c=s.categoria||'altro'; (gruppi[c]=gruppi[c]||[]).push(s); });
    var e=_escV, html='';
    Object.keys(gruppi).forEach(function(cat){
      html+='<div class="sc-cat-lab">'+e(_CATLAB[cat]||cat)+'</div><div class="sc-grid">';
      html+=gruppi[cat].map(function(s){
        return '<button class="sc-card" onclick="apriSchedaScienza(\''+e(s.slug)+'\')"><span class="sc-card-nome">'+e(s.nome||s.slug)+'</span><span class="sc-card-arr">→</span></button>';
      }).join('');
      html+='</div>';
    });
    cont.innerHTML=html;
  }).catch(function(){ var c=document.getElementById('sc-lista'); if(c) c.innerHTML='<div class="vista-empty">Errore di rete.</div>'; });
};

window.apriSchedaScienza = function(slug){
  _apriVista('Scheda', '<div class="vista-loading">Carico la scienza…</div>');
  fetch('/v1/scheda-scienza/'+encodeURIComponent(slug)).then(function(r){return r.json();}).then(function(d){
    if(d.errore || !d.nome){ var b=document.getElementById('vista-body'); if(b) b.innerHTML='<div class="vista-empty">Scheda non disponibile.</div>'; return; }
    _scRender(d);
  }).catch(function(){ var b=document.getElementById('vista-body'); if(b) b.innerHTML='<div class="vista-empty">Errore di rete.</div>'; });
};

function _scRender(d){
  var e=_escV;
  var sez=function(lab,val,cls){ if(!val) return ''; return '<div class="sc-sez'+(cls?' '+cls:'')+'"><div class="sc-sez-lab">'+e(lab)+'</div><div class="sc-sez-txt">'+e(val)+'</div></div>'; };
  var html='<div class="sc-scheda">'
    // header
    + '<div class="sc-sch-head"><div class="sc-sch-cat">'+e(_CATLAB[d.categoria]||d.categoria||'')+'</div><div class="sc-sch-nome">'+e(d.nome)+'</div></div>'
    // NUMERO BERSAGLIO in alto, grande, arancione (il dato che cercano per primo)
    + (d.numero_bersaglio?'<div class="sc-bersaglio"><div class="sc-bers-lab">◎ NUMERO BERSAGLIO</div><div class="sc-bers-val">'+e(d.numero_bersaglio)+'</div></div>':'')
    // blocchi
    + sez('Il fenomeno', d.fenomeno)
    + sez('Il principio', d.principio)
    + sez('Punto critico', d.punto_critico, 'critico')
    + sez('Segnale reale al banco', d.segnale_reale)
    + sez('La tecnica', d.tecnica)
    + sez('⚠ Errori comuni', d.errori_comuni, 'errori')
    // CTA context engine
    + '<button class="sc-chiedi" onclick=\'_chatConContesto("fenomeno",{nome:'+JSON.stringify(d.nome).replace(/'/g,"&#39;")+',fenomeno:'+JSON.stringify(d.nome).replace(/'/g,"&#39;")+',target:'+JSON.stringify(d.numero_bersaglio||"").replace(/'/g,"&#39;")+'})\'>Chiedi a Matter su questo →</button>'
    + '</div>';
  var b=document.getElementById('vista-body'); if(b) b.innerHTML=html;
}
})();
