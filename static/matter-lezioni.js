// ═══ MATTER-LEZIONI.js — modulo lezioni/quiz (lazy, Strangler) ═══
(function(){
window.avviaLezione = function(){
  // naviga alla lezione del fenomeno del giorno se disponibile
  const disc = Matter.disciplina || localStorage.getItem('matter_disc') || 'bar';
  const fenId = Matter.fenomenoId;
  switchTab('lezione');
  if(fenId && disc){
    // trova lo step del fenomeno nella disciplina e carica direttamente
    setTimeout(()=>{ _caricaLezionePerId(disc, fenId); }, 100);
  }
}

window._precaricaLezione = async function(disc, lang, tok) {
  // Precarica i fenomeni in background dopo il primo caricamento
  try {
    const jobs = [];
    for(let i = 1; i < (Matter.totale || 30); i++) {
      if(!_lesCache[disc+'_'+i]) {
        jobs.push(
          fetch(`/lezione/${disc}/${i}?lang=${lang}&token=${tok}`)
            .then(r => r.ok ? r.json() : null)
            .then(j => { if(j && !j.errore && !j.paywall) _lesCache[disc+'_'+i] = j; })
            .catch(()=>{})
        );
      }
      if(jobs.length >= 3) { await Promise.all(jobs.splice(0,3)); }
    }
    if(jobs.length) await Promise.all(jobs);
  } catch(e) {}
}

window._caricaLezionePerId = async function(disc, fenId){
  // trova lo step del fenomeno nella disciplina e carica la lezione giusta
  try {
    const r = await fetch(`/disciplina/${disc}?lang=${_lang}`);
    if(!r.ok) return;
    const j = await r.json();
    const fenomeni = j.fenomeni || [];
    const idx = fenomeni.findIndex(f => f.id === fenId);
    if(idx >= 0){
      Matter.disciplina = disc;
      Matter.step = idx;
      Matter.totale = fenomeni.length;
      caricaLezioneStep(idx);
    } else {
      caricaLezioneStep(0);
    }
  } catch(e){ caricaLezioneStep(0); }
}

window.caricaLezioneStep = async function(step){
  const disc = Matter.disciplina || 'bar';
  var _discMap={'bar':'disc_bar','cucina':'disc_cucina','panificazione':'disc_panificazione',
    'pasticceria':'disc_pasticceria','gelateria':'disc_gelateria','caffe':'disc_caffe',
    'vino':'disc_vino','birra':'disc_birra','sicurezza':'disc_sicurezza'};
  var _discKey=_discMap[disc];
  var _discNomeUI=(_discKey&&_lang!=='it')?(_t(_discKey)||disc.charAt(0).toUpperCase()+disc.slice(1)):(disc.charAt(0).toUpperCase()+disc.slice(1));
  document.getElementById('les-disciplina-label').textContent = _discNomeUI;
  document.getElementById('les-step-label').textContent = _t('les_caricamento');
  const _lNome=document.getElementById('les-nome');
  const _lSch=document.getElementById('les-scheda');
  const _lTgt=document.getElementById('les-target');
  _lNome.textContent='\u00a0'; _lNome.classList.add('skel');
  _lSch.textContent='\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0'; _lSch.classList.add('skel');
  if(_lTgt){ _lTgt.textContent='\u00a0\u00a0\u00a0\u00a0'; _lTgt.classList.add('skel'); }
  document.getElementById('les-quiz-box').style.display='none';
  try {
    const tok = localStorage.getItem('matter_token')||'';
    // Usa cache se disponibile (precaricamento in background)
    let j = _lesCache[disc+'_'+step];
    if(!j) {
      const r = await fetch(`/lezione/${disc}/${step}?lang=${_lang}&token=${tok}`);
      if(r.status===402){ mostraPopupPro('lezione'); return; }
      if(!r.ok) throw new Error('server');
      j = await r.json();
      _lesCache[disc+'_'+step] = j;
    }
    if(j.paywall){ mostraPopupPro('lezione_locked'); return; }
    if(j.errore){ document.getElementById('les-nome').textContent = j.errore; return; }
    Matter.step = j.step;
    Matter.totale = j.totale_passi;
    Matter.nodoCorrente = j.fenomeno.id;
    // header
    document.getElementById('les-pos').textContent = `${_t('les_fenomeno')} ${j.step+1} ${_t('les_di')} ${j.totale_passi}`;
    // aggiorna progress bar
    const pct = j.totale_passi > 0 ? Math.round((j.step+1)/j.totale_passi*100) : 0;
    const barFill = document.getElementById('les-bar-fill');
    if(barFill) barFill.style.width = pct + '%';
    document.getElementById('les-step-label').textContent =
      (j.fenomeno.dominio||'') + ' · fenomeno ' + (j.step+1);
    ['les-nome','les-scheda','les-target'].forEach(id=>{
      const el=document.getElementById(id); if(el) el.classList.remove('skel');
    });
    document.getElementById('les-nome').textContent = j.fenomeno.nome;
    // popola "Quando ti serve"
    const _wbox=document.getElementById('les-quando-box');
    const _wlist=document.getElementById('les-quando-list');
    if(_wbox && _wlist){
      const _casi = _quandoCasi(j.fenomeno.nome, j.fenomeno.disciplina||Matter.disciplina||'');
      if(_casi.length){
        _wlist.innerHTML=_casi.map(c=>`<div class="sl-quando-item">${c}</div>`).join('');
        _wbox.style.display='block';
      } else { _wbox.style.display='none'; }
    }
    _formattaScheda(document.getElementById('les-scheda'), j.fenomeno.scheda || 'Scheda in aggiornamento.');
    // domanda-gancio sopra la scheda (apre col "perché", non col "cos'è")
    var _gel = document.getElementById('les-gancio');
    if(_gel){
      if(j.fenomeno.gancio){ _gel.textContent = j.fenomeno.gancio; _gel.style.display='block'; }
      else { _gel.style.display='none'; }
    }
    // target — mostra la box solo se il fenomeno ha un numero-bersaglio,
    // coerente con lo Scopri; niente "—" spoglio quando il dato non c'è
    const datoBox = document.getElementById('les-dato-box');
    if(j.fenomeno.target){
      _renderTarget(document.getElementById('les-target'), j.fenomeno.target, false);
      var _mi=document.getElementById('les-mirino-intro');
      renderMirino(document.getElementById('les-mirino'), j.fenomeno.nome, j.fenomeno.target);
      if(_mi) _mi.style.display = document.getElementById('les-mirino').style.display==='none'?'none':'';
      datoBox.style.display = '';
      _caricaStrumentoPerFenomeno(disc, j.fenomeno.nome, j.fenomeno.target);
    } else {
      datoBox.style.display = 'none';
      var _mir=document.getElementById('les-mirino'); if(_mir) _mir.style.display='none';
      var _mii=document.getElementById('les-mirino-intro'); if(_mii) _mii.style.display='none';
      var sb=document.getElementById('les-strumento-box'); if(sb) sb.style.display='none';
    }
    // stepper a puntini: quanti fenomeni, dove sei, salto diretto
    renderLesDots(j.step, j.totale_passi);
    // ═══ PAYWALL PER-PARTI (pro_locked): sfoca SOLO il numero del Mirino, la scienza è gratis ═══
    _applicaPaywallLezione(j.pro_locked === true);
    // principio
    const pb = document.getElementById('les-principio-box');
    if(j.principio){
      document.getElementById('les-principio-testo').textContent = j.principio.testo||'';
      pb.style.display='block';
    } else { pb.style.display='none'; }
    // ═══ SCAVA — le quattro porte per andare più a fondo (longevità) ═══
    renderScava(j.scava, j.fenomeno.nome);
    // quiz: caricato a parte (lazy), così la lezione appare subito.
    // La prima volta il server lo genera, poi è in cache e istantaneo.
    caricaQuizLezione(j.fenomeno.id);
    // bottoni nav
    document.getElementById('les-btn-prec').style.opacity = j.ha_precedente?'1':'0.4';
    document.getElementById('les-btn-succ').textContent =
      j.ha_successivo ? 'Avanti →' : 'Vai all\'Atlante →';
    // onboarding: nudge completamento all'ultimo fenomeno
    mostraCompletamentoLezione(j.ha_successivo);
    // Precarica i prossimi step in background
    if(step === 0) {
      setTimeout(() => _precaricaLezione(disc, _lang, localStorage.getItem('matter_token')||''), 500);
    }
  } catch(e){
    ['les-nome','les-scheda','les-target'].forEach(id=>{
      const el=document.getElementById(id); if(el) el.classList.remove('skel');
    });
    document.getElementById('les-nome').textContent = _t('les_errore');
  }
}

window._applicaPaywallLezione = function(locked){
  var mirino = document.getElementById('les-mirino');
  var datoBox = document.getElementById('les-dato-box');
  var target = document.getElementById('les-target');
  // rimuovo eventuale overlay precedente
  var vecchio = document.getElementById('les-mirino-lock'); if(vecchio) vecchio.remove();
  if(!locked){
    if(mirino) mirino.classList.remove('les-mirino-blur');
    if(target) target.classList.remove('les-mirino-blur');
    return;
  }
  // sfoco il numero e aggiungo l'overlay "Sblocca con Pro"
  var box = datoBox && datoBox.style.display!=='none' ? datoBox : mirino;
  if(box && box.style.display!=='none'){
    if(target) target.classList.add('les-mirino-blur');
    if(mirino) mirino.classList.add('les-mirino-blur');
    var lock=document.createElement('div');
    lock.id='les-mirino-lock'; lock.className='les-mirino-lockbox';
    lock.innerHTML='<span class="les-lock-ico">🔒</span><span>Il numero-bersaglio esatto è Pro</span>';
    lock.onclick=function(){ mostraPopupPro('numero'); };
    box.style.position='relative';
    box.appendChild(lock);
  }
}

window.caricaQuizLezione = async function(nodeId){
  const box = document.getElementById('les-quiz-box');
  box.style.display='none';
  try {
    const r = await fetch(`/quiz/${nodeId}?lang=${_lang}`);
    if(!r.ok) return;
    const j = await r.json();
    // guardia anti-race: se hai già cambiato passo, non mostrare un quiz vecchio
    if(j.quiz && Matter.nodoCorrente === nodeId){
      renderQuizLezione(j.quiz);
      box.style.display='block';
    }
  } catch(e){ /* nessun quiz: la lezione resta comunque completa */ }
}

window.renderQuizLezione = function(q){
  document.getElementById('quiz-domanda').textContent = q.domanda||'';
  const opts = document.getElementById('quiz-opzioni');
  opts.innerHTML='';
  document.getElementById('quiz-spiegazione').style.display='none';
  (q.opzioni||[]).forEach((op,i)=>{
    const div=document.createElement('div');
    div.className='q2-opt';
    div.innerHTML=`<span class="q2-dot"></span>${esc(op)}
      ${i===q.corretta?'<span class="q2-chk"><svg viewBox="0 0 24 24"><path d="M5 12l5 5L20 6"/></svg></span>':''}`;
    div.onclick=()=>{
      opts.querySelectorAll('.q2-opt').forEach(o=>o.classList.remove('correct'));
      if(i===q.corretta){
        div.classList.add('correct');
        const sp=document.getElementById('quiz-spiegazione');
        sp.textContent=q.spiegazione||'';
        sp.style.display='block';
      }
    };
    opts.appendChild(div);
  });
}

window.mostraCompletamentoLezione = function(haSuccessivo){
  const nudge = document.getElementById('les-complete-nudge');
  if(!haSuccessivo && nudge){
    nudge.style.display='flex';
    _segnaOnboardingFatto();
  } else if(nudge){
    nudge.style.display='none';
  }
}

window.caricaPalestra = async function(){
  try{
    var rp=await fetch('/v1/quiz/progressi', {headers:_statoHeaders()});
    var jp=await rp.json();
    var tot=jp.totale_superati||0;
    var su148=Math.min(100, Math.round((tot/148)*100));
    var fill=document.getElementById('pal-barra-fill'); if(fill) fill.style.width=su148+'%';
    var cnt=document.getElementById('pal-count'); if(cnt) cnt.textContent=tot+'/148 dominati';
  }catch(e){}
  var body=document.getElementById('pal-body');
  if(body) body.innerHTML='<div class="calc-loading">Carico le domande…</div>';
  try{
    var r=await fetch('/v1/quiz?limit=10', {headers:_statoHeaders()});
    var j=await r.json();
    _palQuiz=j.quiz||[]; _palIdx=0; _palRisposto=false;
    if(!_palQuiz.length){ if(body) body.innerHTML='<div class="quad-empty"><b>Ancora nessuna domanda</b><span>Le domande arrivano man mano. Torna tra poco.</span></div>'; return; }
    _renderQuiz();
  }catch(e){ if(body) body.innerHTML='<div class="quad-empty"><b>Errore</b><span>Riprova.</span></div>'; }
}

window._renderQuiz = function(){
  var body=document.getElementById('pal-body'); if(!body) return;
  if(_palIdx>=_palQuiz.length){
    body.innerHTML='<div class="pal-fine"><b>Set completato!</b><button class="calc-go" onclick="caricaPalestra()">Altre domande</button></div>';
    return;
  }
  var q=_palQuiz[_palIdx]; var e=_escV;
  _palRisposto=false;
  body.innerHTML=
    '<div class="pal-quiz">'
    + '<div class="pal-meta"><span class="pal-tipo">'+e(q.tipo||'')+'</span><span class="pal-diff">'+e(q.difficolta||'')+'</span></div>'
    + '<div class="pal-domanda">'+e(q.domanda||'')+'</div>'
    + '<div class="pal-opzioni" id="pal-opzioni">'
    +   (q.opzioni||[]).map(function(op,i){ return '<button class="pal-opz" data-op="'+e(op)+'" onclick="_rispondiQuiz(this,\''+e(String(q.id))+'\')">'+e(op)+'</button>'; }).join('')
    + '</div>'
    + '<div id="pal-esito"></div>'
    + '</div>';
}

window._rispondiQuiz = async function(btn, quizId){
  if(_palRisposto) return; _palRisposto=true;
  var risposta=btn.getAttribute('data-op');
  document.querySelectorAll('.pal-opz').forEach(function(b){ b.disabled=true; });
  try{
    var r=await fetch('/v1/quiz/rispondi', {method:'POST', headers:_statoHeaders({'Content-Type':'application/json'}), body:JSON.stringify({quiz_id:quizId, risposta:risposta})});
    var j=await r.json();
    var e=_escV;
    document.querySelectorAll('.pal-opz').forEach(function(b){
      var op=b.getAttribute('data-op');
      if(op===j.risposta_corretta) b.classList.add('giusta');
      else if(b===btn) b.classList.add('sbagliata');
    });
    var esito=document.getElementById('pal-esito');
    if(esito){
      esito.innerHTML='<div class="pal-verdetto '+(j.superato?'ok':'no')+'">'+(j.superato?'✓ Esatto':'✗ Non è corretta')+'</div>'
        + (j.insight?'<div class="pal-insight">'+e(j.insight)+'</div>':'')
        + '<button class="calc-go" onclick="_palProssima()">Prossima →</button>';
    }
  }catch(e){ _toast('Errore, riprova'); _palRisposto=false; document.querySelectorAll('.pal-opz').forEach(function(b){ b.disabled=false; }); }
}

})();
