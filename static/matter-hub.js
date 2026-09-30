// ═══ MATTER-HUB.js — Protocol Hub (board 2): "un ingrediente è un PORTALE, si entra da un VERBO" ═══
// ESPERIMENTI prima (cosa puoi FARE), identità dopo. Dalla materia alla teoria.
(function(){
var _DISC={cucina:'Cucina',bar:'Bar',panificazione:'Panificazione',pasticceria:'Pasticceria',caffetteria:'Caffetteria',gelateria:'Gelateria',birra:'Birra',vino:'Vino',trasversale:'Trasversale'};

window.apriHub = function(ingrediente){
  var e=_escV, ing=ingrediente||'pomodoro';
  _apriVista('Protocol Hub', '<div id="hub-host"><div class="vista-loading"></div></div>');
  var host=document.getElementById('hub-host');
  // carico esperimenti + varietà in parallelo
  Promise.all([
    fetch('/v1/ingrediente/'+encodeURIComponent(ing)+'/protocolli').then(function(r){return r.json();}).catch(function(){return{};}),
    fetch('/v1/ingrediente/'+encodeURIComponent(ing)+'/varieta').then(function(r){return r.json();}).catch(function(){return{};})
  ]).then(function(res){
    var esp=(res[0].esperimenti||[]), varieta=(res[1].varieta||[]);
    _hubRender(ing, esp, varieta);
  });
};

function _hubRender(ing, esp, varieta){
  var e=_escV, host=document.getElementById('hub-host'); if(!host) return;
  // 0 esperimenti: gestione elegante (non rotto)
  if(!esp.length){
    host.innerHTML='<div class="hub-vuoto ds-grid-bg"><div class="hub-vuoto-ico">◎</div><div class="hub-vuoto-t">'+e(_cap(ing))+'</div><div class="hub-vuoto-d">Matter non ha ancora esperimenti su questo ingrediente. Il patrimonio cresce — riprova o cercane un altro.</div><button class="hub-vuoto-cta" onclick="apriRicerca&&apriRicerca()">Cerca un altro ingrediente →</button></div>';
    return;
  }
  // 1. HERO materia (identità sintetica) — 30% strumento
  var html='<div class="hub-hero ds-grid-bg"><div class="ds-eyebrow">◎ IL PORTALE</div>'
    + '<div class="ds-display hub-hero-nome">'+e(_cap(ing))+'</div>'
    + '<div class="hub-hero-n"><span class="ds-data">'+esp.length+'</span> esperimenti · '+(varieta.length?('<span class="ds-data">'+varieta.length+'</span> varietà'):'materia viva')+'</div></div>';
  // 2. ESPERIMENTI — il cuore (cosa puoi FARE)
  html+='<div class="hub-sez-lab">◎ COSA PUOI FARE</div><div class="hub-esp-lista">';
  html+=esp.slice(0,12).map(function(p){
    var bers=(p.bersaglio&&p.bersaglio.valore)?('<span class="hub-esp-bers ds-data">'+e(p.bersaglio.valore)+(p.bersaglio.unita?' '+e(p.bersaglio.unita):'')+'</span>'):'';
    var fen=(p.fenomeni||[]).slice(0,2).map(e).join(' · ');
    return '<button class="hub-esp" onclick="_hubApriProt(\''+e(p.id)+'\')">'
      + '<div class="hub-esp-top"><span class="hub-esp-nome">'+e(p.nome)+'</span>'+bers+'</div>'
      + (p.variabile_critica?'<div class="hub-esp-var">leva: '+e(p.variabile_critica)+'</div>':'')
      + (fen?'<div class="hub-esp-fen">'+fen+'</div>':'')
      + '</button>';
  }).join('')+'</div>';
  // 3. VARIETÀ (carte materiche) — solo se ci sono (biodiversità)
  if(varieta.length){
    html+='<div class="hub-sez-lab">◎ LE VARIETÀ — differenze operative</div><div class="hub-var-lista">';
    html+=varieta.slice(0,8).map(function(v){
      var pr=v.proprieta||{};
      var barre=['acidita','zuccheri','acqua','struttura'].filter(function(k){return pr[k]!=null;}).map(function(k){
        var val=Math.max(0,Math.min(10,Number(pr[k])||0));
        return '<div class="hub-var-barra"><span class="hub-var-bk">'+k.slice(0,4)+'</span><div class="hub-var-bt"><div class="hub-var-bf" style="width:'+(val*10)+'%"></div></div></div>';
      }).join('');
      return '<div class="hub-var"><div class="hub-var-nome">'+e(v.nome)+'</div>'+(v.origine?'<div class="hub-var-orig">'+e(v.origine)+'</div>':'')+(barre?'<div class="hub-var-barre">'+barre+'</div>':'')+(v.note?'<div class="hub-var-note">'+e(v.note)+'</div>':'')+'</div>';
    }).join('')+'</div>';
  }
  // ricerca altro ingrediente
  html+='<div class="hub-cerca"><input id="hub-cerca-input" placeholder="Un altro ingrediente…" onkeydown="if(event.key===\'Enter\')_hubCerca()"><button onclick="_hubCerca()">→</button></div>';
  host.innerHTML=html;
}
function _cap(s){ s=String(s||''); return s.charAt(0).toUpperCase()+s.slice(1); }
window._hubApriProt=function(id){ if(typeof apriProtocollo==='function'){ apriProtocollo(id); } else if(typeof _caricaModulo==='function'){ _caricaModulo('protocollo').then(function(){ if(window.apriProtocollo) apriProtocollo(id); }); } };
window._hubCerca=function(){ var i=document.getElementById('hub-cerca-input'); var q=i?i.value.trim():''; if(q) apriHub(q); };
})();
