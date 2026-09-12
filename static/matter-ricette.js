// ═══ MATTER-RICETTE.js — modulo ricettario/vetrina (lazy, Strangler) ═══
(function(){
window.caricaLeMieRicette = async function(){
  var list=document.getElementById('quad-ricette-list');
  var empty=document.getElementById('quad-ricette-empty');
  if(!list) return;
  list.innerHTML='<div class="quad-loading">Carico le tue ricette…</div>';
  try{
    var r=await fetch('/v1/ricette/le-mie', {headers: _statoHeaders()});
    var j=await r.json();
    var ricette=j.ricette||[];
    if(!ricette.length){ if(empty){ empty.style.display=''; list.innerHTML=''; } else { list.innerHTML='<div class="quad-empty"><b>Non hai ancora salvato ricette</b><span>Quando trovi una ricetta utile, salvala qui dal pulsante Salva nel Quaderno.</span></div>'; } return; }
    if(empty) empty.style.display='none';
    list.innerHTML=ricette.map(function(r){
      var d=r.dati||{};
      var nIng=(d.ingredienti||[]).length;
      return '<div class="quad-ric-card" onclick=\'riapriRicettaSalvata('+JSON.stringify(JSON.stringify(r)).replace(/'/g,"&#39;")+')\'>'
        +'<div class="quad-ric-nome">'+_esc(r.nome||d.nome||'Ricetta')+'</div>'
        +'<div class="quad-ric-meta">'+(nIng?nIng+' ingredienti':'')+(d.disciplina?' · '+_esc(d.disciplina):'')+'</div>'
        +'<button class="quad-ric-rimuovi" onclick=\'event.stopPropagation();rimuoviRicettaSalvata("'+_esc(r.ricetta_id)+'")\'>Rimuovi</button>'
        +'</div>';
    }).join('');
  }catch(e){
    list.innerHTML='<div class="quad-empty"><b>Non riesco a caricare le ricette</b><span>Riprova tra poco.</span></div>';
  }
}

window.apriVetrina = async function(){
  _vetrinaOffset = 0;
  _apriVista('Vetrina del Banco',
    '<div class="vetr-intro">Ricette vere da chi sta al banco. Clona quelle che ti servono, connettiti con chi le ha fatte.</div>'
    + '<div class="vetr-feed" id="vetr-feed"></div>'
    + '<button class="vetr-more" id="vetr-more" onclick="_vetrinaCarica()" style="display:none">Carica altre</button>');
  _vetrinaCarica();
}

window._vetrinaCarica = async function(){
  if(_vetrinaBusy) return; _vetrinaBusy=true;
  var feed=document.getElementById('vetr-feed');
  var more=document.getElementById('vetr-more');
  if(_vetrinaOffset===0 && feed){ feed.innerHTML='<div class="vetr-loading">Carico la vetrina…</div>'; }
  if(more && _vetrinaOffset>0){ more.textContent='Caricamento…'; more.disabled=true; }
  try{
    var lang=(typeof _lang!=='undefined'?_lang:'it');
    var r=await fetch('/v1/community/feed?lingua='+lang+'&offset='+_vetrinaOffset);
    var j=await r.json();
    var ricette=j.ricette||[];
    if(_vetrinaOffset===0){ feed.innerHTML=''; }
    if(!ricette.length && _vetrinaOffset===0){
      feed.innerHTML='<div class="vetr-empty"><b>La vetrina è ancora vuota</b><span>Pubblica tu la prima ricetta dal Quaderno.</span></div>';
      if(more) more.style.display='none';
      _vetrinaBusy=false; return;
    }
    feed.insertAdjacentHTML('beforeend', ricette.map(_vetrinaCard).join(''));
    _vetrinaOffset += ricette.length;
    // tre stati del bottone
    if(more){
      more.disabled=false;
      if(ricette.length>=10){
        more.textContent='Carica altre'; more.style.display='';
      } else {
        // feed finito
        more.textContent='Hai visto tutte le ricette ('+_vetrinaOffset+')';
        more.style.display='';
        more.disabled=true;
        more.classList.add('vetr-more-fine');
      }
    }
  }catch(e){
    if(feed && _vetrinaOffset===0) feed.innerHTML='<div class="vetr-empty"><b>Non riesco a caricare la vetrina</b><span>Riprova tra poco.</span></div>';
    if(more){ more.textContent='Riprova'; more.disabled=false; }
  }
  _vetrinaBusy=false;
}

window.apriRicettario = async function(){
  _apriVista('Ricettario dei Professionisti',
    '<div class="ric-search"><input type="text" id="ricp-q" placeholder="Cerca tra le 454 ricette certificate…" onkeydown="if(event.key===\'Enter\')_ricettarioCerca()"><button onclick="_ricettarioCerca()">Cerca</button></div>'
    + '<div class="ric-disc-chips" id="ricp-chips"></div>'
    + '<div id="ricp-out"><div class="skel-grid">'+('<div class="skeleton skel-card"></div>').repeat(6)+'</div></div>');
  try{
    var r=await fetch('/v1/ricettario/discipline');
    var j=await r.json();
    _ricettarioDisc=j.discipline||[];
    var e=_escV;
    var chips=document.getElementById('ricp-chips');
    if(chips){
      chips.innerHTML=(j.discipline||[]).map(function(d){
        return '<span class="ric-disc-chip" onclick="_ricettarioDisciplina(\''+e(d.disciplina)+'\',this)">'+e(d.disciplina)+' <span class="ric-disc-n">'+d.n+'</span></span>';
      }).join('');
    }
    // carico la prima disciplina di default
    if((j.discipline||[]).length){ _ricettarioDisciplina(j.discipline[0].disciplina, null); }
  }catch(e){ var o=document.getElementById('ricp-out'); if(o) o.innerHTML='<div class="vista-empty">Errore di rete.</div>'; }
}

window._ricettarioCarica = async function(query){
  var out=document.getElementById('ricp-out'); if(out) out.innerHTML='<div class="skel-grid">'+('<div class="skeleton skel-card"></div>').repeat(6)+'</div>';
  // cache client: se ho già caricato questa query in sessione, uso quella (istantaneo)
  var cacheKey='ric-'+query;
  try{ var cached=sessionStorage.getItem(cacheKey); if(cached){ _ricettarioRender(JSON.parse(cached)); return; } }catch(e){}
  try{
    var r=await fetch('/v1/ricettario/canonico?'+query+'&limit=30');
    var j=await r.json();
    try{ sessionStorage.setItem(cacheKey, JSON.stringify(j)); }catch(e){}
    _ricettarioRender(j);
  }catch(e){ if(out) out.innerHTML='<div class="vista-empty">Errore.</div>'; }
}

window._ricettarioRender = function(j){
    var out=document.getElementById('ricp-out');
    var ric=j.ricette||[];
    var e=_escV;
    if(!ric.length){ out.innerHTML='<div class="vista-empty">Nessuna ricetta trovata.</div>'; return; }
    out.innerHTML='<div class="ricp-griglia">'+ric.map(function(x){
      var img='';
      if(x.immagine){
        if(x.immagine.tipo==='foto' && x.immagine.url){ img='<img src="'+e(x.immagine.url)+'" alt="" loading="lazy">'; }
        else if(x.immagine.tipo==='blueprint' && x.immagine.famiglia){ img='<img src="/static/blueprints/'+e(x.immagine.famiglia)+'.svg" alt="" loading="lazy">'; }
      }
      return '<div class="ricp-card" onclick="_ricettarioApri(\''+e(x.id)+'\',\''+e(String(x.nome)).replace(/'/g,"\\'")+'\')">'
        + '<div class="ricp-img">'+img+(x.certificata?'<span class="ricp-cert">✓ Lab</span>':'')+'</div>'
        + '<div class="ricp-nome">'+e(x.nome||'')+'</div>'
        + (x.fenomeno?'<div class="ricp-fen">'+e(x.fenomeno)+'</div>':'')
        + '</div>';
    }).join('')+'</div>';
}

window._ricettarioApri = async function(id, nome){
  if(!id) return;
  _apriVista(nome||'Ricetta', '<div class="gen-loading">'+_mirinoLoaderHtml()+'<div class="gen-txt">Apro la ricetta…</div></div>');
  try{
    var r=await fetch('/v1/ricetta/'+encodeURIComponent(id)+'/completa', {headers:_statoHeaders()});
    var j=await r.json();
    var ric=j.ricetta||j;
    if(!ric || !ric.nome){ chiudiVista(); apriNodo(id, nome||''); return; }
    mostraRicettaGen(ric, id);
    // arricchimenti Parte D: badge variante, perché funziona, collegate
    setTimeout(function(){ _arricchisciSchedaRicetta(ric); }, 100);
  }catch(e){ chiudiVista(); apriNodo(id, nome||''); }
}

window._caricaLibroAffiliato = async function(params, containerSelector){
  try{
    var r=await fetch('/v1/libro-affiliato?'+params);
    var j=await r.json();
    var l=j.libro;
    if(!l || !l.titolo) return;
    var e=_escV;
    var cont=document.querySelector(containerSelector);
    if(!cont) return;
    if(cont.querySelector('.libro-aff')) return;
    var box=document.createElement('div');
    box.className='libro-aff';
    box.innerHTML='<div class="libro-aff-lab">Approfondisci la scienza</div>'
      + '<div class="libro-aff-tit">'+e(l.titolo)+'</div>'
      + (l.autore?'<div class="libro-aff-aut">'+e(l.autore)+'</div>':'')
      + (l.perche?'<div class="libro-aff-perche">'+e(l.perche)+'</div>':'')
      + (l.link?'<a class="libro-aff-link" href="'+e(l.link)+'" target="_blank" rel="noopener">Vedi su Amazon →</a>':'');
    cont.appendChild(box);
  }catch(e){}
}

})();
