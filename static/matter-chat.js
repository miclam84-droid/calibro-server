// ═══ MATTER-CHAT.js — modulo chat (lazy, metodo Strangler) ═══
// Funzioni spostate IDENTICHE dal core. Restano globali via window.
(function(){
window.invia = function(){const q=document.getElementById('q').value.trim();if(!q||busy)return;document.getElementById('q').value='';chiediTesto(q);}

window._diagnosiChat = function(domanda){
  switchTab('chiedi'); switchSubtab('chat');
  setTimeout(function(){ if(typeof chiediTesto==='function') chiediTesto(domanda); }, 150);
}

window.chiediTesto = function(q){
  if(busy)return;
  if(!_isPro()){
    const usate=_getDomande();
    if(usate>=FREE_LIMIT){ apriPaywall(); return; }
  }
  const e=document.getElementById('empty-state');if(e)e.remove();
  switchTab('chiedi');switchSubtab('chat');
  setBusy(true);
  // provo lo streaming; se fallisce, fallback alla chat normale
  _chiediStream(q).catch(function(){ _chiediNonStream(q); });
}

window._chiediStream = async function(q){
  const history=_historyPerBackend();
  const _tok=localStorage.getItem('matter_token')||'';
  const _ctx = _ctxChat || window._chatContesto || null;
  // creo la scheda risposta che si riempie man mano
  var card=document.createElement('div'); card.className='scheda scheda-stream';
  var flusso=document.createElement('div'); flusso.className='stream-flusso';
  card.appendChild(flusso);
  var statusEl=document.createElement('div'); statusEl.className='stream-status';
  statusEl.innerHTML='<span class="t-dots"><span class="t-dot"></span><span class="t-dot"></span><span class="t-dot"></span></span> <span id="stream-status-txt"></span>';
  card.appendChild(statusEl);
  document.getElementById('schede').prepend(card);
  card.scrollIntoView({behavior:'smooth',block:'start'});

  var resp = await fetch('/chiedi/stream?lang='+(typeof _lang!=='undefined'?_lang:'it'),
    {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}),
     body:JSON.stringify({domanda:q, history:history, token:_tok, contesto:_ctx})});
  if(resp.status===402){ card.remove(); var j=await resp.json(); mostraPopupPro('esaurito'); throw {handled:true}; }
  if(!resp.ok || !resp.body){ card.remove(); throw new Error('no stream'); }

  var reader=resp.body.getReader();
  var dec=new TextDecoder();
  var buf=''; var testoAccumulato=''; var txtEl=null; var erroreVisto=false;
  var curTxt=function(){ if(!txtEl){ txtEl=document.createElement('div'); txtEl.className='stream-txt'; flusso.appendChild(txtEl); } return txtEl; };

  while(true){
    var chunk=await reader.read();
    if(chunk.done) break;
    buf += dec.decode(chunk.value, {stream:true});
    var parti=buf.split('\n\n');
    buf=parti.pop();
    for(var i=0;i<parti.length;i++){
      var linea=parti[i].trim();
      if(!linea.indexOf('data:')===0 && linea.indexOf('data:')!==0) continue;
      var jsonStr=linea.replace(/^data:\s*/,'');
      if(!jsonStr) continue;
      var ev; try{ ev=JSON.parse(jsonStr); }catch(e){ continue; }
      if(ev.tipo==='status'){
        var st=document.getElementById('stream-status-txt'); if(st) st.textContent=ev.testo||'';
      } else if(ev.tipo==='token'){
        testoAccumulato += (ev.delta||'');
        // STREAMING FLUIDO: durante lo scorrimento mostro testo grezzo (textContent = leggero,
        // niente re-parse markdown ad ogni token). La formattazione avviene alla fine.
        curTxt().textContent = testoAccumulato;
      } else if(ev.tipo==='widget'){
        txtEl=null; // i prossimi token vanno sotto il widget
        if(ev.widget==='fenomeno' && ev.id){ _streamWidgetFenomeno(flusso, ev.id); }
        else if(ev.widget==='calcolatore'){ _streamWidgetCalcolo(flusso, ev); }
      } else if(ev.tipo==='error'){
        erroreVisto=true;
      } else if(ev.tipo==='done'){
        // chiudo
      }
    }
  }
  statusEl.remove();
  setBusy(false);
  _incDomande();
  // FINE STREAMING: ora applico la formattazione markdown UNA volta (heading, grassetto, blocchi)
  if(testoAccumulato && typeof curTxt==='function'){ try{ curTxt().innerHTML = _formattaRispostaChat(testoAccumulato); }catch(e){} }
  if(erroreVisto && !testoAccumulato){ card.remove(); throw new Error('stream error'); }
  if(testoAccumulato){ _chatHistory.push({q:q, r:testoAccumulato.slice(0,300)}); if(_chatHistory.length>_HISTORY_MAX*2) _chatHistory.splice(0,2);
    _chatCompleta.push({ruolo:'user',testo:q}); _chatCompleta.push({ruolo:'assistant',testo:testoAccumulato});
    // pulsante "Salva nei metodi" in calce alla risposta
    var salvaBtn=document.createElement('button'); salvaBtn.className='chat-salva-inline';
    salvaBtn.textContent='⌖ Salva nei metodi';
    salvaBtn.onclick=function(){ salvaConversazione(); salvaBtn.textContent='✓ Salvata nel Quaderno'; salvaBtn.classList.add('salvato'); salvaBtn.disabled=true; };
    flusso.appendChild(salvaBtn);
  }
}

window._formattaRispostaChat = function(t){
  var e=_escV(t);
  // grassetto/corsivo prima (per applicarli dentro i blocchi)
  e=e.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
  e=e.replace(/(^|[^*])\*([^*\n]+)\*($|[^*])/g,'$1<em>$2</em>$3');
  // heading markdown ### → titolo referto
  e=e.replace(/^#{1,6}\s*(.+)$/gm, function(m,txt){ return '\n@@H@@'+txt.replace(/:$/,'')+'\n'; });
  // PARTE C: i marcatori diventano BLOCCHI ETICHETTATI (referto, non prosa)
  // inserisco un separatore prima di ogni marcatore
  e=e.replace(/\s*(PROBLEMA|DIAGNOSI|PERCHÉ|PERCHE|NUMERO|MISURA|AZIONE)\s*:\s*/g, function(m,lab){
    var L=lab.toUpperCase().replace('PERCHE','PERCHÉ');
    var cls = (L==='NUMERO'||L==='MISURA') ? 'referto-num' : 'referto-blocco';
    return '@@B@@'+cls+'@@'+L+'@@';
  });
  // liste
  e=e.replace(/^\s*(\d+)\.\s+(.+)$/gm, '<span class="chat-li"><b>$1.</b> $2</span>');
  e=e.replace(/^\s*[-•]\s+(.+)$/gm, '<span class="chat-li chat-li-bullet">$1</span>');
  // ora costruisco i blocchi
  var parti=e.split('@@B@@');
  var html='';
  // testo prima del primo marcatore (introduzione)
  if(parti[0].trim()){ html+='<div class="chat-par">'+parti[0].replace(/@@H@@(.+)/g,'<div class="chat-h">$1</div>').replace(/\n\n/g,'<br><br>').replace(/\n/g,'<br>')+'</div>'; }
  for(var i=1;i<parti.length;i++){
    var seg=parti[i].split('@@');
    var cls=seg[0], lab=seg[1], testo=seg.slice(2).join('@@');
    testo=testo.replace(/@@H@@(.+)/g,'<div class="chat-h">$1</div>').replace(/\n\n/g,'<br><br>').replace(/\n/g,'<br>').trim();
    html+='<div class="'+cls+'"><div class="referto-lab">'+lab+'</div><div class="referto-txt">'+testo+'</div></div>';
  }
  return html || '<div class="chat-par">'+e.replace(/@@H@@(.+)/g,'<div class="chat-h">$1</div>')+'</div>';
}

window._streamWidgetFenomeno = async function(flusso, id){
  var ph=document.createElement('div'); ph.className='stream-widget'; ph.innerHTML='<div class="calc-loading">Carico la scheda…</div>';
  flusso.appendChild(ph);
  try{
    var r=await fetch('/nodo?traccia=1',{method:'POST',headers:_statoHeaders({'Content-Type':'application/json'}),body:JSON.stringify({id:id})});
    var j=await r.json();
    if(j && j.tipo_fenomeno){ ph.innerHTML=''; ph.appendChild(_costruisciMiniSchedaFenomeno(j, id)); }
    else { ph.remove(); }
  }catch(e){ ph.remove(); }
}

window._streamWidgetCalcolo = function(flusso, ev){
  var d=ev.dati||{};
  var wrap=document.createElement('div'); wrap.className='stream-widget';
  var num = d.numero || d.risultato || '';
  var h='<div class="stream-calc"><div class="stream-calc-lab">'+_escV(ev.calcolo||'calcolo')+'</div>';
  if(num) h+='<div class="stream-calc-num">'+_escV(String(num))+'</div>';
  if(d.interpretazione) h+='<div class="calc-interp">'+_escV(d.interpretazione)+'</div>';
  if(d.leva_azione) h+='<div class="calc-leva"><span class="calc-leva-lab">Cosa fare</span>'+_escV(d.leva_azione)+'</div>';
  if(d.fenomeno_id) h+='<button class="calc-fen-link" onclick="apriNodo(\''+_escV(d.fenomeno_id)+'\',\'\')">Studia il fenomeno →</button>';
  h+='</div>';
  wrap.innerHTML=h;
  flusso.appendChild(wrap);
}

window._costruisciMiniSchedaFenomeno = function(j, id){
  var div=document.createElement('div'); div.className='stream-fen';
  var e=_escV;
  var principio = (j.principi_diretti&&j.principi_diretti[0]) ? j.principi_diretti[0].nome : '';
  div.innerHTML='<div class="stream-fen-nome" onclick="apriNodo(\''+e(id)+'\',\'\')">'+e(j.titolo||'Fenomeno')+' →</div>'
    + (principio?'<div class="stream-fen-princ">'+e(principio)+'</div>':'')
    + (j.target_numero?'<div class="stream-fen-num">'+e(String(j.target_numero))+(j.unita?' '+e(j.unita):'')+'</div>':'');
  return div;
}

window._chiediNonStream = function(q){
  aggiungiThinking(); setBusy(true);
  // passa gli ultimi scambi per dare continuità alla conversazione
  const history=_historyPerBackend();
  const _tok=localStorage.getItem('matter_token')||'';
  // contesto: da scheda ricetta/menu (FLUSSO 2) o da lezione
  const _ctx = _ctxChat || window._chatContesto || null;
  fetch('/chiedi',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({domanda:q, history, token:_tok, contesto:_ctx})})
    .then(r=>{
      if(r.status===402) return r.json().then(j=>{throw {trial:true,...j};});
      return r.json();
    }).then(j=>{
      _incDomande();
      if(j.risposta){
        _chatHistory.push({q, r:j.risposta.slice(0,300)});
        if(_chatHistory.length>_HISTORY_MAX*2) _chatHistory.splice(0,2);
      }
      // Gestione trial
      const tr=j.trial||{};
      if(tr.notifica){
        mostraNotificaTrial(tr.chat_rimaste);
      }
      if(tr.ultimo){
        mostraPopupPro('ultima_chat');
      }
      renderRisp(q,j);
    }).catch(e=>{
      if(e&&e.trial){
        mostraPopupPro('esaurito');
        const t=document.getElementById('thinking');if(t)t.remove();
      } else {
        renderErr();
      }
    }).finally(()=>setBusy(false));
}

window.caricaChatSalvate = async function(){
  var list=document.getElementById('chat-salvate-list');
  if(!list) return;
  list.innerHTML='<div class="quad-loading">Carico le conversazioni…</div>';
  try{
    var r=await fetch('/v1/chat/mie', {headers:_statoHeaders()});
    var j=await r.json();
    var conv=j.conversazioni||[];
    if(!conv.length){
      list.innerHTML='<div class="quad-empty"><b>Nessuna conversazione salvata</b><span>Quando l\'Assistente ti dà una risposta preziosa, salvala: la ritrovi qui il giorno dopo.</span></div>';
      return;
    }
    var e=_escV;
    list.innerHTML=conv.map(function(c){
      var data='';
      try{ var d=new Date(c.data); data=d.toLocaleDateString('it-IT',{day:'2-digit',month:'short'}); }catch(x){}
      var tag = c.tag ? '<span class="chat-tag chat-tag-'+e(c.tag)+'">'+e(c.tag)+'</span>' : '';
      return '<div class="chat-salvata-card" onclick="riapriChatSalvata('+c.id+')">'
        + '<div class="chat-salvata-titolo">'+e(c.titolo||'Conversazione')+'</div>'
        + '<div class="chat-salvata-meta">'+tag+'<span class="chat-salvata-data">'+data+'</span></div></div>';
    }).join('');
  }catch(e){ list.innerHTML='<div class="quad-empty"><b>Errore</b><span>Riprova.</span></div>'; }
}

window.riapriChatSalvata = async function(id){
  try{
    var r=await fetch('/v1/chat/'+encodeURIComponent(id), {headers:_statoHeaders()});
    var j=await r.json();
    var msg=j.messaggi||[];
    if(!msg.length){ _toast('Conversazione vuota'); return; }
    // ripopolo la chat con i messaggi salvati
    switchTab('chiedi'); switchSubtab('chat');
    var schede=document.getElementById('schede');
    if(schede){
      schede.innerHTML='';
      // mostro i messaggi come schede (dal più vecchio al più recente, prepend inverte)
      msg.slice().reverse().forEach(function(m){
        var card=document.createElement('div'); card.className='scheda';
        if(m.ruolo==='user'){ card.innerHTML='<div class="chat-msg-user">'+_escV(m.testo)+'</div>'; }
        else { card.innerHTML='<div class="stream-txt">'+_formattaRispostaChat(m.testo)+'</div>'; }
        schede.prepend(card);
      });
    }
    _toast('Conversazione riaperta');
  }catch(e){ _toast('Errore nel caricamento'); }
}

window.salvaConversazione = async function(){
  if(!_chatCompleta.length){ _toast('Nessuna conversazione da salvare'); return; }
  var btn=document.getElementById('btn-salva-chat');
  if(btn){ btn.disabled=true; }
  try{
    var r=await fetch('/v1/chat/salva', {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}),
      body:JSON.stringify({messaggi:_chatCompleta})});
    var j=await r.json();
    if(j && j.ok){ _toast('✓ Conversazione salvata nel Quaderno'); }
    else { _toast('Non riuscita, riprova'); }
  }catch(e){ _toast('Errore, riprova'); }
  if(btn){ btn.disabled=false; }
}

window._historyPerBackend = function(){
  var out=[];
  _chatHistory.slice(-_HISTORY_MAX).forEach(function(h){
    if(h.q) out.push({role:'user', content:String(h.q)});
    var risp = h.r || h.a; if(risp) out.push({role:'assistant', content:String(risp)});
  });
  return out;
}

window.aggiungiThinking = function(){
  const d=document.createElement('div');d.className='scheda';d.id='thinking';
  d.innerHTML=`<div class="thinking"><span class="t-dots"><span class="t-dot"></span><span class="t-dot"></span><span class="t-dot"></span></span><span class="t-step" id="t-step">${_t('chat_thinking')}</span></div>`;
  document.getElementById('schede').prepend(d);
  const fasi=[_t('chat_thinking'), _lang==='it'?'raccolgo i fenomeni':'gathering phenomena', _lang==='it'?'scrivo la risposta':'writing the answer'];
  let i=0;
  const tmr=setInterval(()=>{
    i=(i+1)%fasi.length;
    const el=document.getElementById('t-step');
    if(!el){clearInterval(tmr);return;}
    el.style.opacity=0;setTimeout(()=>{if(el){el.textContent=fasi[i];el.style.opacity=1;}},250);
  },1100);
  const obs=new MutationObserver(()=>{if(!document.getElementById('thinking')){clearInterval(tmr);obs.disconnect();}});
  obs.observe(document.getElementById('schede'),{childList:true});
}

window.rimuoviThinking = function(){ var t=document.getElementById("thinking"); if(t) t.remove(); }

window.renderRisp = function(domanda,j,fromNode){
  const t=document.getElementById('thinking');if(t)t.remove();
  if(!j.risposta){renderNota(domanda,j.nota,j.connessi);return;}
  // REGOLA 1 — la chat è un ponte, non il laboratorio: se il backend segnala crea_ricetta,
  // mostro la frase breve + un pulsante grande [GENERA SCHEDA RICETTA] invece di generare qui.
  if(j._azione==='crea_ricetta'){
    const rich = (j._richiesta||domanda||'').replace(/'/g,"\\'");
    const card=document.createElement('div');card.className='scheda';
    card.innerHTML=`<div class="s-q"><b>${esc(domanda)}</b></div>
      <div class="s-body" style="padding-bottom:6px">${_formattaRispostaChat(j.risposta)}</div>
      <button class="rg-btn rg-btn-salva" style="margin:4px 14px 14px;width:calc(100% - 28px)" onclick="_generaDaChat('${rich}')">Genera scheda ricetta →</button>`;
    document.getElementById('schede').prepend(card);
    card.scrollIntoView({behavior:'smooth',block:'start'});
    _chatHistory.push({q:domanda,a:j.risposta});
    return;
  }
  const fens=(j.trovato||[]).map(f=>{
    const match=(j.connessi||[]).find(c=>c.nome===f);
    const fid=match?match.id:'';
    return `<span class="fenchip" style="cursor:pointer;text-decoration:underline dotted" onclick="${fid?`apriNodo('${fid}','${f.replace(/'/g,"\'")}')`:'switchTab(\"lezione\")'}" title="Esplora fenomeno">${esc(f)}</span>`;
  }).join('');
  const conns=(j.connessi||[]).map(c=>{
    const col=DOMCOL[c.dominio]||'#5A6C70';
    const tg=c.target?`<span class="tg">${esc(c.target)}</span>`:'';
    return `<span class="conn" onclick="apriNodo('${c.id}','${(c.nome||'').replace(/'/g,"\\'")}')"><span class="dot" style="background:${col}"></span>${esc(c.nome)}${tg}</span>`;
  }).join('');
  // FL4b: chip flavor dal primo fenomeno trovato
  const trovati = j.trovato || [];
  const flavorChip = trovati.length > 0
    ? `<div class="s-conn" style="border-top:1px solid var(--border)">
        <div class="s-conn-lab" style="color:var(--flavor)">cerca abbinamenti nell'Atlante →</div>
        <div class="conns"><span class="conn" style="color:var(--flavor);border-color:var(--flavor-border)" onclick="switchTab('mappa')">
          <span class="dot" style="background:var(--flavor)"></span>Vai all'Atlante aromatico →
        </span></div>
      </div>` : '';
  // AC5: feedback
  const logId = j.log_id;
  const feedbackHtml = logId ? `<div class="s-feedback">
    <span>Risposta utile?</span>
    <button onclick="inviaFeedback(${logId},1,this)"><i class="ph ph-thumbs-up"></i></button>
    <button onclick="inviaFeedback(${logId},-1,this)"><i class="ph ph-thumbs-down"></i></button>
  </div>` : '';
  const card=document.createElement('div');card.className='scheda';
  // Estrai numero bersaglio dalla risposta se disponibile
  const numBersaglio = j.numero_bersaglio || j.target || '';
  // dati per il form di misura (dal backend /nodo)
  const fenId = j.id || '';
  const targetNum = j.target_numero || null;   // null = fenomeno "si assaggia", niente confronto
  const targetUnita = j.unita || '';
  let numBox = '';
  if(fromNode && fenId && targetNum){
    // fenomeno misurabile: bersaglio + campo "la tua misura" con confronto
    numBox = `<div class="s-num-box">
      <div class="s-num-head"><svg class="s-num-mirino" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.6" stroke="#5EA0C8" stroke-width="1.2"/><circle cx="7" cy="7" r="2" fill="#5EA0C8"/><path d="M7 0v2.2M7 11.8V14M0 7h2.2M11.8 7H14" stroke="#5EA0C8" stroke-width="1.2"/></svg><div class="s-num-label">bersaglio</div></div>
      <div class="s-num-val">${esc(targetNum)}${targetUnita?' <span class="s-num-u">'+esc(targetUnita)+'</span>':''}</div>
      <div class="s-misura" data-fen="${esc(fenId)}" data-target="${esc(targetNum)}" data-unita="${esc(targetUnita)}">
        <div class="s-misura-lab">la tua misura</div>
        <div class="s-misura-row">
          <input type="text" inputmode="decimal" class="s-misura-input" placeholder="${esc(String(targetNum).split(/[–-]/)[0])}" onkeydown="if(event.key==='Enter')fissaMisura(this)">
          ${targetUnita?'<span class="s-misura-u">'+esc(targetUnita)+'</span>':''}
          <button class="s-misura-btn" onclick="fissaMisura(this)">Fissa</button>
        </div>
        <div class="s-misura-esito"></div>
      </div>
    </div>`;
  } else if(numBersaglio){
    // Il box Mirino "bersaglio" deve contenere un NUMERO/valore corto, non una frase.
    // Se il backend manda testo descrittivo (contiene freccia, punti elenco, o è lungo),
    // NON mostro il box bersaglio: un Mirino con dentro un paragrafo è sbagliato.
    const numStr = String(numBersaglio).trim();
    const sembraFrase = numStr.length > 24 || /→|·|:|,/.test(numStr) || numStr.split(/\s+/).length > 4;
    if(!sembraFrase){
      numBox = `<div class="s-num-box">
        <div class="s-num-head"><svg class="s-num-mirino" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.6" stroke="#5EA0C8" stroke-width="1.2"/><circle cx="7" cy="7" r="2" fill="#5EA0C8"/><path d="M7 0v2.2M7 11.8V14M0 7h2.2M11.8 7H14" stroke="#5EA0C8" stroke-width="1.2"/></svg><div class="s-num-label">bersaglio</div></div>
        <div class="s-num-val">${esc(numBersaglio)}</div>
      </div>`;
    }
  }
  
  card.innerHTML=`<div class="s-q">${fromNode?'<i class=\'ph ph-caret-right\'></i> ':''}<b>${esc(domanda)}</b></div>
    <div class="fenchips">${fens}</div>
    ${numBox}
    ${(()=>{
      const r = j.risposta || '';
      // Prova a parsare risposta strutturata con label IT/EN/ES
      const labelsIT = ['PROBLEMA','PERCHÉ','NUMERO','MISURA','AZIONE'];
      const labelsEN = ['PROBLEM','WHY','NUMBER','MEASURE','ACTION'];
      const labelsES = ['PROBLEMA','POR QUÉ','NÚMERO','MIDE','ACCIÓN'];
      const allLabels = [...labelsIT, ...labelsEN, ...labelsES];
      const labelColors = {
        'PROBLEMA':'var(--ink-muted)','PROBLEM':'var(--ink-muted)','PROBLEMA':'var(--ink-muted)',
        'PERCHÉ':'var(--ink-muted)','WHY':'var(--ink-muted)','POR QUÉ':'var(--ink-muted)',
        'NUMERO':'var(--e700)','NUMBER':'var(--e700)','NÚMERO':'var(--e700)',
        'MISURA':'var(--teal)','MEASURE':'var(--teal)','MIDE':'var(--teal)',
        'AZIONE':'var(--ink)','ACTION':'var(--ink)','ACCIÓN':'var(--ink)',
      };
      // Cerca se la risposta ha la struttura con label
      const hasStructure = allLabels.some(l => r.includes(l + ':'));
      if(!hasStructure) {
        // risposta libera (non strutturata): rendo in paragrafi puliti invece
        // di un blocco unico grezzo che sembra "codice rotto"
        const paragrafi = r.split(/\n{2,}/).map(p => p.trim()).filter(p => p);
        if(paragrafi.length <= 1) return '<div class="s-body">'+esc(r)+'</div>';
        return '<div class="s-body">' + paragrafi.map(p => '<p style="margin:0 0 10px 0">'+esc(p)+'</p>').join('') + '</div>';
      }
      // Parsa i blocchi
      const lines = r.split('\n').filter(l => l.trim());
      let html = '<div class="s-blocks">';
      lines.forEach(line => {
        const match = line.match(/^([A-ZÀÁÉÍÓÚÜÑ\s]+?):\s*(.+)$/);
        if(match && allLabels.some(l => match[1].trim() === l)) {
          const label = match[1].trim();
          const val = match[2].trim();
          const col = labelColors[label] || 'var(--ink-muted)';
          const isNum = label === 'NUMERO' || label === 'NUMBER' || label === 'NÚMERO';
          const isAct = label === 'AZIONE' || label === 'ACTION' || label === 'ACCIÓN' || label === 'NUMERO' || label === 'NUMBER' || label === 'NÚMERO';
        const tagBg = isAct ? '#12545D' : '#5E9BA3';
        html += '<div class="s-block">' +
            '<div class="s-block-label" style="background:'+tagBg+'">' + esc(label) + '</div>' +
            '<div class="s-block-body"' + (isNum ? ' style="font-family:var(--mono);font-size:15px;font-weight:700;color:var(--e700)"' : '') + '>' + esc(val) + '</div>' +
            '</div>';
        } else {
          html += '<div class="s-block"><div class="s-block-body">' + esc(line) + '</div></div>';
        }
      });
      html += '</div>';
      return html;
    })()}
    <div class="s-ai-label">Risposta generata da AI · Matter usa modelli linguistici per elaborare le risposte</div>
    ${conns?`<div class="s-conn"><div class="s-conn-lab">esplora le connessioni</div><div class="conns">${conns}</div></div>`:''}
    ${flavorChip}
    ${feedbackHtml}
    <div class="s-actions">
      <button class="s-action-btn" onclick="copiaRisposta(this)" title="Copia testo"><i class="ph ph-copy"></i> Copia</button>
      <button class="s-action-btn" onclick="scaricaPDF(this)" title="Salva PDF"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align:-2px"><path d="M12 3v12M7 11l5 4 5-4"/><path d="M5 21h14"/></svg> PDF</button>
    </div>
    `;
  document.getElementById('schede').prepend(card);
}

window.renderNota = function(domanda,nota,connessi){
  const card=document.createElement('div');card.className='scheda';
  const conns=(connessi||[]).map(c=>{
    const col=DOMCOL[c.dominio]||'#5A6C70';
    return `<span class="conn" onclick="apriNodo('${c.id}','${(c.nome||'').replace(/'/g,"\\'")}')"><span class="dot" style="background:${col}"></span>${esc(c.nome)}</span>`;
  }).join('');
  card.innerHTML=`<div class="s-q"><b>${esc(domanda)}</b></div>
    <div class="s-body" style="color:var(--ink-muted)">${esc(nota||'Niente trovato nel grafo.')}</div>
    ${conns?`<div class="s-conn"><div class="s-conn-lab">parti da un fenomeno</div><div class="conns">${conns}</div></div>`:''}`;
  document.getElementById('schede').prepend(card);
}

window.renderErr = function(){const t=document.getElementById('thinking');if(t)t.remove();const card=document.createElement('div');card.className='scheda';card.innerHTML=`<div class="s-body" style="color:var(--ink-muted)">${_t('auth_errore_rete')}</div>`;document.getElementById('schede').prepend(card);}

})();
