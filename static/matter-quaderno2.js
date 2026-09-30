// ═══ MATTER-QUADERNO2.js — Il Quaderno (board 4): il FOSSATO. 2 memorie. ═══
// L1 COMMIT (cosa hai fatto, fattuale) + L2 MAESTRIA (come stai crescendo). La crescita è curva, non voto.
(function(){
function _dev(){ return localStorage.getItem('matter_device_id')||localStorage.getItem('matter_token')||'anon'; }
function _h(){ return {'X-Device-Id':_dev()}; }

window.apriQuaderno2 = function(){
  _apriVista('Quaderno', '<div id="qd-host"><div class="vista-loading"></div></div>');
  Promise.all([
    fetch('/v1/quaderno/esperimenti',{headers:_h()}).then(function(r){return r.json();}).catch(function(){return{esperimenti:[]}}),
    fetch('/v1/quaderno/maneggiare-la-materia',{headers:_h()}).then(function(r){return r.json();}).catch(function(){return{crescita:[]}})
  ]).then(function(res){ _qdRender(res[0].esperimenti||[], res[1]); });
};

function _qdRender(esp, mem){
  var e=_escV, host=document.getElementById('qd-host'); if(!host) return;
  var cresc=(mem&&mem.crescita)||[];

  // stato vuoto — dignitoso (il Quaderno è nuovo, si costruisce salvando)
  if(!esp.length && !cresc.length){
    host.innerHTML='<div class="qd-hero ds-grid-bg"><div class="ds-eyebrow">◎ IL TUO QUADERNO</div>'
      + '<div class="ds-display qd-hero-t">La tua memoria<br>del mestiere.</div></div>'
      + '<div class="qd-vuoto"><div class="qd-vuoto-ico">◱</div>'
      + '<div class="qd-vuoto-t">Il fossato si costruisce un esperimento alla volta</div>'
      + '<div class="qd-vuoto-d">Ogni esperimento che salvi diventa un commit. Col tempo, Matter impara come maneggi la materia: cosa ti riesce, dove cresci, i tuoi pattern. Questa memoria è tua e non si copia.</div>'
      + '<button class="qd-vuoto-cta" onclick="if(typeof apriComposer2===\'function\'){chiudiVista();apriComposer2()}">Simula il primo esperimento →</button></div>';
    return;
  }

  var html='<div class="qd-hero ds-grid-bg"><div class="ds-eyebrow">◎ IL TUO QUADERNO</div>'
    + '<div class="ds-display qd-hero-t" style="font-size:26px">La tua memoria del mestiere</div>'
    + '<div class="qd-hero-n"><span class="ds-data">'+esp.length+'</span> esperimenti registrati</div></div>';

  // L2 — PROFILO DI MAESTRIA (la crescita, curva non voto)
  if(cresc.length){
    html+='<div class="qd-sez-lab">◎ COME MANEGGI LA MATERIA</div><div class="qd-maestria">';
    html+=cresc.slice(0,8).map(function(m){
      var nome=m.esperimento||m.materia||m.fenomeno||'';
      var riusc=m.riusciti!=null?m.riusciti:0, tent=m.tentativi!=null?m.tentativi:0;
      var pct=tent>0?Math.round((riusc/tent)*100):0;
      var stato=m.stato||(pct>=75?'consolidato':(pct>=40?'in crescita':'agli inizi'));
      var col=stato==='consolidato'?'var(--ds-salvia)':(stato==='in crescita'?'var(--ds-rame)':'var(--ds-muted)');
      return '<div class="qd-mae"><div class="qd-mae-top"><span class="qd-mae-nome">'+e(nome)+'</span><span class="qd-mae-stato" style="color:'+col+'">'+e(stato)+'</span></div>'
        + '<div class="qd-mae-bar"><div class="qd-mae-fill" style="width:'+pct+'%;background:'+col+'"></div></div>'
        + '<div class="qd-mae-n">'+riusc+'/'+tent+' riusciti</div></div>';
    }).join('')+'</div>';
  }

  // L1 — I COMMIT (cronologia fattuale)
  if(esp.length){
    html+='<div class="qd-sez-lab">◎ GLI ESPERIMENTI — i tuoi commit</div><div class="qd-commit-lista">';
    html+=esp.slice(0,20).map(function(x){
      var esito=(x.esito||'').toLowerCase();
      var badgeCol=esito.indexOf('riusc')>=0?'var(--ds-salvia)':(esito.indexOf('roll')>=0||esito.indexOf('fall')>=0?'var(--ds-ossido)':'var(--ds-muted)');
      var cn=x.commit_n!=null?('#'+x.commit_n):'';
      return '<div class="qd-commit"><div class="qd-commit-top"><span class="qd-commit-nome">'+e(x.nome||'Esperimento')+'</span>'+(cn?'<span class="qd-commit-n ds-data">'+e(cn)+'</span>':'')+'</div>'
        + (x.esito?'<span class="qd-commit-esito" style="color:'+badgeCol+';border-color:'+badgeCol+'">'+e(x.esito)+'</span>':'')
        + (x.note?'<div class="qd-commit-note">'+e(x.note)+'</div>':'')+'</div>';
    }).join('')+'</div>';
  }
  host.innerHTML=html;
}
})();
