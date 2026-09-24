// ═══ MATTER-BIODIVERSITA.js — Il quarto pilastro (lente del Laboratorio) ═══
(function(){
var _TUTELA_CLS={ 'DOP':'dop','IGP':'igp','presidio':'presidio','Presidio Slow Food':'presidio','STG':'stg' };

window.apriBiodiversita = function(){
  _apriVista('Biodiversità',
    '<div class="bio-hero"><div class="bio-hero-lab">IMPARA · IL PATRIMONIO GASTRONOMICO</div>'
    + '<div class="bio-hero-claim">La biodiversità italiana,<br>varietà per varietà.</div>'
    + '<div class="bio-hero-sub">Ogni territorio custodisce le sue varietà. DOP, IGP, presidi Slow Food: non badge, ma il valore vero di un ingrediente.</div></div>'
    + '<div id="bio-regioni"><div class="vista-loading">Carico le regioni…</div></div>');
  fetch('/v1/biodiversita/regioni').then(function(r){return r.json();}).then(function(d){
    var reg=d.regioni||[];
    var cont=document.getElementById('bio-regioni'); if(!cont) return;
    if(!reg.length){ cont.innerHTML='<div class="vista-empty">Nessun dato.</div>'; return; }
    // ordino per ricchezza (varietà desc)
    reg.sort(function(a,b){ return (b.varieta||0)-(a.varieta||0); });
    var e=_escV;
    cont.innerHTML=reg.map(function(r){
      var badges='';
      if(r.dop) badges+='<span class="bio-badge bio-dop">'+r.dop+' DOP</span>';
      if(r.igp) badges+='<span class="bio-badge bio-igp">'+r.igp+' IGP</span>';
      if(r.presidi) badges+='<span class="bio-badge bio-presidio">'+r.presidi+' presidi</span>';
      var esempi=(r.esempi||[]).slice(0,3).map(function(x){return _escV(String(x).replace(/_/g,' '));}).join(' · ');
      return '<button class="bio-regione" onclick="apriRegioneBio(\''+e(r.regione)+'\')">'
        + '<div class="bio-reg-top"><span class="bio-reg-nome">'+e(r.regione)+'</span><span class="bio-reg-n">'+(r.varieta||0)+' varietà</span></div>'
        + (badges?'<div class="bio-reg-badges">'+badges+'</div>':'')
        + (esempi?'<div class="bio-reg-esempi">'+esempi+'</div>':'')
        + '</button>';
    }).join('');
  }).catch(function(){ var c=document.getElementById('bio-regioni'); if(c) c.innerHTML='<div class="vista-empty">Errore di rete.</div>'; });
};

window.apriRegioneBio = function(regione){
  _apriVista(regione, '<div class="vista-loading">Carico le varietà…</div>');
  fetch('/v1/biodiversita/regione/'+encodeURIComponent(regione)).then(function(r){return r.json();}).then(function(d){
    var vars=d.varieta||[];
    var e=_escV;
    var html='<div class="bio-reg-head"><div class="bio-reg-head-lab">BIODIVERSITÀ</div><div class="bio-reg-head-nome">'+e(d.regione||regione)+'</div><div class="bio-reg-head-n">'+vars.length+' varietà custodite</div></div>';
    if(!vars.length){ html+='<div class="vista-empty">Nessuna varietà.</div>'; }
    else {
      html+='<div class="bio-var-lista">'+vars.map(function(v){
        var cls=_TUTELA_CLS[v.tutela]||'';
        return '<button class="bio-var" onclick="apriSchedaIngrediente(\''+e(v.id)+'\',\''+e(String(v.nome)).replace(/'/g,"\\'")+'\')">'
          + '<div class="bio-var-top"><span class="bio-var-nome">'+e(v.nome)+'</span>'+(v.tutela?'<span class="bio-badge bio-'+cls+'">'+e(v.tutela)+'</span>':'')+'</div>'
          + (v.territorio?'<div class="bio-var-terr">◉ '+e(v.territorio)+'</div>':'')
          + '</button>';
      }).join('')+'</div>';
    }
    var b=document.getElementById('vista-body'); if(b) b.innerHTML=html;
  }).catch(function(){ var b=document.getElementById('vista-body'); if(b) b.innerHTML='<div class="vista-empty">Errore di rete.</div>'; });
};
})();
