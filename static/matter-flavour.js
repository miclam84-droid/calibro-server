// ═══ MATTER-FLAVOUR.js — modulo abbinamenti (lazy, Strangler) ═══
(function(){
window.cercaFlavorMappa = async function(){
  const q = document.getElementById('flavor-query').value.trim();
  if(!q) return;
  const res = document.getElementById('flavor-results-mappa');
  res.innerHTML = `<div style="color:var(--ink-muted);font-size:12px;padding:8px 0">${_t('caricamento')}</div>`;
  const ing = q.toLowerCase().replace(/\s+/g,'_');
  try {
    const r = await fetch('/v1/abbina/'+encodeURIComponent(ing));
    const j = await r.json();
    if(!j.abbinamenti || !j.abbinamenti.length){
      res.innerHTML=`<div style="color:var(--ink-muted);font-size:12px;padding:8px 0">Nessun abbinamento trovato per <b>${esc(q)}</b>.</div>`;
      return;
    }
    _incFlavorUse();
    caricaComposti(ing);
    const usate = _getFlavorUse();
    const isPro = _isPro();
    const tutti = j.abbinamenti;
    const visibili = isPro ? tutti : tutti.slice(0, FLAVOR_FREE);
    const nascosti = isPro ? [] : tutti.slice(FLAVOR_FREE);
    const _ingFlavor = ing; // ingrediente cercato

    let html = visibili.map(a=>{
      // uso il livello A/B/C del backend (già calcolato con confidence)
      var liv = a.livello==='A' ? 'forte' : (a.livello==='B' ? 'medio' : (a.livello==='C' ? 'creativo' : 'medio'));
      var barW = liv==='forte' ? 100 : (liv==='medio' ? 60 : 30);
      return `
      <div class="flavor-result-item flavor-liv-${liv}" style="align-items:center">
        <div class="flavor-peso" title="${liv}"><div class="flavor-peso-bar" style="width:${barW}%"></div></div>
        <span class="flavor-result-name">${esc(a.ingrediente.replace(/_/g,' '))}</span>
        <div style="display:flex;align-items:center;gap:6px">
          <span class="flavor-result-why">${esc(a.livello_nome||a.composto||'')}</span>
          <button onclick="feedbackAbb('${esc(a.ingrediente)}','${esc(_ingFlavor)}',1,this)" title="Mi piace" style="background:none;border:none;cursor:pointer;font-size:14px;padding:2px;opacity:.5" class="fb-btn"><i class="ph ph-thumbs-up"></i></button>
          <button onclick="feedbackAbb('${esc(a.ingrediente)}','${esc(_ingFlavor)}',-1,this)" title="Non mi piace" style="background:none;border:none;cursor:pointer;font-size:14px;padding:2px;opacity:.5" class="fb-btn"><i class="ph ph-thumbs-down"></i></button>
        </div>
      </div>`;}).join('');

    if(nascosti.length){
      html += nascosti.map(a=>`
        <div class="flavor-result-item cap-blur">
          <span class="flavor-result-name">${esc(a.ingrediente.replace(/_/g,' '))}</span>
          <span class="flavor-result-why">${esc(a.composto||'')} · ${a.overlap||''}</span>
        </div>`).join('');
      html += `<div class="cap-lock">
        <svg viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/></svg>
        <span class="cap-lock-txt">${FLAVOR_FREE} abbinamenti liberi per ricerca. Vedi tutto con Pro.</span>
        <span class="cap-lock-cta" onclick="vaiAPro()">Passa a Pro →</span>
      </div>`;
    }
    res.innerHTML = html;

    // ── abbinamento per contrasto (fisico-percettivo) ────────
    const resC = document.getElementById('contrasto-results-mappa');
    if(resC){
      resC.innerHTML=`<div style="color:var(--ink-muted);font-size:12px;padding:4px 0">${_t('caricamento')}</div>`;
      try{
        const rc = await fetch('/v1/contrasto/'+encodeURIComponent(ing));
        const jc = await rc.json();
        if(jc.contrasti && jc.contrasti.length){
          resC.innerHTML = '<div style="font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--teal);margin:10px 0 6px">per contrasto</div>' +
            jc.contrasti.map(c=>`
              <div class="flavor-result-item">
                <span class="flavor-result-name" style="color:var(--teal)">${esc(c.ingrediente.replace(/_/g,' '))}</span>
                <span class="flavor-result-why" style="color:var(--teal);opacity:.8">${esc(c.meccanismo.replace(/_/g,' '))}</span>
              </div>
              <div style="font-size:11px;color:var(--ink-muted);padding:0 0 6px 0;line-height:1.4">${esc(c.perche)}</div>
            `).join('');
        } else {
          resC.innerHTML='';
        }
      }catch(e){ resC.innerHTML=''; }
    }
  } catch(e){
    res.innerHTML=`<div style="color:var(--e700);font-size:12px;padding:8px 0">Errore. Riprova.</div>`;
  }
}

window.cercaAbbinamenti = async function(ingrediente){
  switchTab('chiedi');
  const ing = (ingrediente||'').toLowerCase().replace(/[\s/]+/g,'_');
  try {
    const r = await fetch('/v1/abbina/'+encodeURIComponent(ing));
    const j = await r.json();
    const card = document.createElement('div'); card.className='scheda';
    if(!j.abbinamenti || !j.abbinamenti.length){
      card.innerHTML=`<div class="s-body" style="color:var(--ink-muted)">Nessun abbinamento trovato per ${esc(ingrediente)}.</div>`;
    } else {
      const items = j.abbinamenti.map(a=>
        `<div style="padding:6px 0;border-bottom:1px solid var(--border);font-size:13px">
          <b style="color:var(--flavor)">${esc((a.ingrediente||'').replace(/_/g,' '))}</b>
          <span style="color:var(--ink-muted);font-size:12px"> — ${esc(a.composto||'')} (${a.overlap||''})</span>
        </div>`).join('');
      card.innerHTML=`<div class="s-q" style="color:var(--flavor)"><i class="ph ph-leaf"></i> perché funzionano insieme — ${esc(ingrediente)}</div>
        <div style="padding:8px 14px">${items}</div>
        <div style="font-family:var(--mono);font-size:10px;color:var(--ink-muted);padding:6px 14px">${esc(j.nota||'')}</div>`;
    }
    document.getElementById('schede').prepend(card);
  } catch(e){ _logErr('flavor', e); }
}

window.apriFlavour = function(ingredienteIniziale){
  // se arrivo con un ingrediente (da un link), vado dritto al workflow
  if(ingredienteIniziale){ _flavourWorkflow(ingredienteIniziale); return; }
  // altrimenti mostro la dashboard (Cos'è / da dove parti)
  var e=_escV;
  var punti=[
    ['ingrediente','Parti da un ingrediente','Vedi con cosa dialoga e perché'],
    ['piatto','Parti da un piatto','Scopri gli accostamenti nascosti'],
    ['molecola','Parti da una molecola','Segui un composto aromatico tra gli ingredienti'],
    ['famiglia','Parti da una famiglia','Esplora agrumi, erbe, spezie e i loro ponti']
  ];
  var cards=punti.map(function(p){
    return '<button class="crea-card" onclick="_flavourWorkflow()"><div class="crea-card-txt"><div class="crea-card-t">'+e(p[1])+'</div><div class="crea-card-d">'+e(p[2])+'</div></div><span class="crea-card-arr">→</span></button>';
  }).join('');
  _apriVista('Flavour Network',
    '<div class="crea-intro">Esplora il dialogo aromatico degli ingredienti — la rete dei composti condivisi.</div>'
    + cards);
};
window._flavourWorkflow = function(ingredienteIniziale){
  _apriVista('Flavour Network',
    '<div class="fnv-head"><div class="fnv-h">Cosa dialoga con cosa.</div>'+
    '<div class="fnv-sub">Non opinioni: composti aromatici condivisi.</div>'+
    '<div class="fnv-search"><input id="fnv-input" placeholder="fragola, lime, pomodoro…" '+
    'onkeydown="if(event.key===\'Enter\')caricaFlavour()"><button onclick="caricaFlavour()">Cerca</button></div>'+
    '<div class="fnv-chips">'+['fragola','pomodoro','lime','cioccolato','basilico'].map(c=>'<span class="fnv-chip" onclick="caricaFlavour(\''+c+'\')">'+c+'</span>').join('')+'</div>'+
    '</div><div id="fnv-out"></div>');
  if(ingredienteIniziale) caricaFlavour(ingredienteIniziale);
};

window.caricaFlavour = async function(term){
  const inp = document.getElementById('fnv-input') || document.getElementById('flavor-query');
  const q = (term || (inp?inp.value:'') || '').trim();
  if(!q) return;
  if(inp) inp.value = q;
  // feedback netto: evidenzio la chip attiva
  document.querySelectorAll('.fnv-chip').forEach(function(c){ c.classList.toggle('attiva', c.textContent.trim().toLowerCase()===q.toLowerCase()); });
  const out = document.getElementById('fnv-out');
  if(!out) return;
  out.innerHTML = '<div class="vista-loading">Leggo il grafo dei composti…</div>';
  try{
    const r = await fetch('/v1/abbina/'+encodeURIComponent(q)+'?lang='+_vistaLang());
    const d = await r.json();
    if(!d.abbinamenti || !d.abbinamenti.length){ out.innerHTML = '<div class="vista-empty">Nessun dato per questo ingrediente.</div>'; return; }
    const sorpr = d.abbinamenti.filter(a=>a.sorprendente);
    const classici = d.abbinamenti.filter(a=>!a.sorprendente);
    let h = '<div class="fnv-center"><div class="fnv-center-lab">◉ Ingrediente</div><div class="fnv-center-name">'+_escV(d.ingrediente||q)+'</div>'+(d.nota?'<div class="fnv-center-nota">'+_escV(d.nota)+'</div>':'')+'</div>';
    if(sorpr.length){
      h += '<div class="fnv-sec-h"><span class="t">Sorprendenti</span><span class="rule"></span><span class="cnt">'+sorpr.length+'</span></div>';
      h += sorpr.map((a,i)=>_flavourNode(a,'s'+i,true,d.ingrediente||q)).join('');
    }
    if(classici.length){
      h += '<div class="fnv-sec-h"><span class="t">'+(sorpr.length?'Classici':'Abbinamenti')+'</span><span class="rule"></span><span class="cnt">'+classici.length+'</span></div>';
      h += classici.map((a,i)=>_flavourNode(a,'c'+i,false,d.ingrediente||q)).join('');
    }
    out.innerHTML = h;
  }catch(e){ out.innerHTML = '<div class="vista-empty">Errore di rete. Riprova.</div>'; }
}

window._flavourNode = function(a,key,surprise,centro){
  const n = Math.round(a.overlap||0);
  // TUTTI i nodi (classici e sorprendenti) hanno il dettaglio espandibile con il bottone "Crea ricetta"
  const perche = surprise
    ? (_escV(centro)+' e '+_escV(a.ingrediente)+' condividono <b>'+n+' composti aromatici</b>. '+_escV(a.perche||'')+' Non è un\'opinione: è chimica.')
    : (_escV(centro)+' e '+_escV(a.ingrediente)+' condividono <b>'+n+' composti aromatici</b>. '+_escV(a.perche||'Un abbinamento classico, confermato dalla chimica.'));
  const det = '<div class="fnv-detail" id="fnv-det-'+key+'"><div class="fnv-detail-why">'+perche+'</div><button class="fnv-cta" onclick="event.stopPropagation();_flavourCrea(\''+_escV(centro)+'\',\''+_escV(a.ingrediente)+'\')">Crea una ricetta con questo abbinamento →</button></div>';
  return '<div class="fnv-node'+(surprise?' surprise':'')+'" onclick="_flavourToggle(\''+key+'\')">'+
    '<div class="fnv-mirino">'+(surprise?_mirinoSorpresa():_mirinoClassico())+'</div>'+
    '<div class="fnv-node-body"><div class="fnv-node-name">'+_escV(a.ingrediente)+'</div>'+
    '<div class="fnv-node-why">'+(surprise?'Sorprendente — tocca per il perché':'Tocca per il perché')+'</div></div>'+
    '<div class="fnv-node-n">'+n+'<span class="u">composti</span></div></div>'+det;
}

window._flavourToggle = function(key){ const d=document.getElementById('fnv-det-'+key); if(d) d.classList.toggle('show'); }

window._flavourCrea = async function(a,b){
  _generaRicettaAsync(a+' e '+b, 'Creo la ricetta…');
}

window._doveComprare = async function(ingrediente, el){
  if(!ingrediente) return;
  var esistente = el && el.parentElement ? el.parentElement.querySelector('.store-box') : null;
  if(esistente){ esistente.remove(); return; }
  var box=document.createElement('div'); box.className='store-box'; box.innerHTML='<div class="store-loading">Cerco…</div>';
  if(el && el.parentElement) el.parentElement.appendChild(box);
  try{
    var lang=(typeof _lang!=='undefined'?_lang:'it');
    var r=await fetch('/v1/prodotto?q='+encodeURIComponent(ingrediente)+'&lang='+lang);
    var j=await r.json();
    var e=_escV;
    var stores=j.stores||[];
    if(!stores.length){ box.innerHTML='<div class="store-vuoto">Nessun negozio trovato.</div>'; return; }
    var html=stores.map(function(s){
      return '<a class="store-btn'+(/special/i.test(s.store||'')?' store-special':'')+'" href="'+e(s.url||'#')+'" target="_blank" rel="noopener sponsored">'
        + '<span class="store-nome">Compra su '+e(s.store||'')+'</span>'
        + (s.nota?'<span class="store-nota">'+e(s.nota)+'</span>':'')
        + '</a>';
    }).join('');
    if(j.disclosure){ html+='<div class="store-disclosure">'+e(j.disclosure)+'</div>'; }
    box.innerHTML=html;
  }catch(e){ box.innerHTML='<div class="store-vuoto">Non riesco a cercare ora.</div>'; }
}

})();
