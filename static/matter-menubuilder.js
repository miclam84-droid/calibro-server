// ═══ MATTER-MENUBUILDER.js — il secondo motore operativo (Board #49) ═══
(function(){
var _mb = { step:0, intenzione:null, nome:'', voci:[], analisi:null };
var _INT=[
  ['pizza','🍕','Pizza'],['cocktail','🍸','Cocktail'],['ristorante','🍝','Ristorante'],['colazione','🥐','Colazione'],['dessert','🍰','Dessert']
];

window.apriMenuBuilderPro = function(){ _mb={ step:0, intenzione:null, nome:'', voci:[], analisi:null }; _apriVista('Menu Builder', _mbRender()); };

function _mbRender(){
  if(_mb.step===0) return _mbStep0();
  if(_mb.step===1) return _mbStep1();
  if(_mb.step===2) return _mbStep2();
  if(_mb.step===3) return _mbStep3();
  return _mbStep4();
}
function _mbRR(){ var b=document.getElementById('vista-body'); if(b){ b.innerHTML=_mbRender(); b.scrollTop=0; } }
window._mbRR=_mbRR;

// STEP 0 — INTENZIONE
function _mbStep0(){
  var e=_escV;
  return '<div class="mb-head"><span class="mb-num">1/5</span><span class="mb-eyebrow">— L\'INTENZIONE</span></div>'
    + '<div class="mb-h">Che menu<br>stai costruendo?</div>'
    + '<div class="mb-int-grid">'+_INT.map(function(i){ return '<button class="mb-int" onclick="_mbSetInt(\''+i[0]+'\')"><span class="mb-int-ico">'+i[1]+'</span><span class="mb-int-lab">'+e(i[2])+'</span></button>'; }).join('')+'</div>';
}
window._mbSetInt=function(x){ _mb.intenzione=x; _mb.step=1; _mbRR(); };

// STEP 1 — NOME
function _mbStep1(){
  var e=_escV;
  return '<div class="mb-head"><span class="mb-num">2/5</span><span class="mb-eyebrow">— IL MENU</span></div>'
    + '<div class="mb-h">Come si chiama<br>questo menu?</div>'
    + '<div class="mb-field"><input id="mb-nome" placeholder="es. Menu Autunno — Trattoria" value="'+e(_mb.nome)+'" onkeydown="if(event.key===\'Enter\')_mbVai2()"></div>'
    + '<button class="mb-avanti" onclick="_mbVai2()">Avanti · Aggiungi voci →</button>';
}
window._mbVai2=function(){ var i=document.getElementById('mb-nome'); _mb.nome=(i?i.value.trim():'')||'Nuovo menu'; _mb.step=2; _mbRR(); };

// STEP 2 — VOCI (3 modi)
function _mbStep2(){
  var e=_escV;
  var voci=_mb.voci.length ? _mb.voci.map(function(v,idx){
    return '<div class="mb-voce" onclick="_mbApriVoce('+idx+')">'
      + '<div class="mb-voce-top"><span class="mb-voce-nome">'+e(v.nome)+'</span>'+(v.food_cost_pct!=null?'<span class="mb-voce-fc">'+v.food_cost_pct+'%</span>':'')+'</div>'
      + (v.ingredienti&&v.ingredienti.length?'<div class="mb-voce-ing">'+e((v.ingredienti||[]).slice(0,4).map(function(x){return typeof x==='string'?x:(x.nome||'');}).join(', '))+'</div>':'<div class="mb-voce-incerta" style="font-size:11.5px;color:#d9b24a;margin-top:3px">senza ingredienti · classificazione incerta</div>')
      + '<button class="mb-voce-x" onclick="event.stopPropagation();_mbRimuovi('+idx+')">×</button></div>';
  }).join('') : '<div class="mb-vuoto">Ancora nessuna voce. Aggiungine una qui sotto.</div>';
  return '<div class="mb-head"><span class="mb-num">3/5</span><span class="mb-eyebrow">— '+e(_mb.nome.toUpperCase())+'</span></div>'
    + '<div class="mb-voci-lab">Le voci del menu ('+_mb.voci.length+')</div>'
    + '<div class="mb-voci">'+voci+'</div>'
    + '<div class="mb-aggiungi-lab">Aggiungi una voce</div>'
    + '<div class="mb-aggiungi">'
    +   '<button class="mb-add mb-add-quad" onclick="_mbDaQuaderno()"><i class="ph ph-notebook"></i> Dal Quaderno</button>'
    +   '<button class="mb-add mb-add-foto" onclick="_mbDaFoto()"><i class="ph ph-camera"></i> Da foto</button>'
    +   '<button class="mb-add mb-add-mano" onclick="_mbDaMano()"><i class="ph ph-pencil-simple"></i> A mano</button>'
    + '</div>'
    + '<div class="mb-adv-btns">'
    +   '<button class="mb-adv-b" onclick="_mbAccostamenti()"><span class="k">◇ Accostamenti</span>Connessioni reali tra gli ingredienti, dal grafo</button>'
    +   '<button class="mb-adv-b" onclick="_mbTecnicheMenu()"><span class="k">◇ Tecniche</span>Le tecniche del banco, coi numeri-bersaglio</button>'
    + '</div>'
    + (_mb.voci.length>=2?'<button class="mb-analizza-btn" onclick="_mbAnalizza()">Analizza l\'equilibrio →</button>':'');
}
window._mbRimuovi=function(i){ _mb.voci.splice(i,1); _mbRR(); };
window._mbDaMano=function(){
  var nome=prompt('Nome del piatto:');
  if(nome && nome.trim()){ _mb.voci.push({nome:nome.trim(), ingredienti:[]}); _mbRR(); }
};
window._mbDaQuaderno=function(){
  var out=document.getElementById('vista-body');
  fetch('/v1/quaderno2/lista',{headers:_statoHeaders?_statoHeaders():{}}).then(function(r){return r.json();}).then(function(j){
    var rec=j.record||j.ricette||j.risultati||[];
    var ric=rec.map(function(x){ return {nome:(x.titolo||x.nome||'Preparazione'), dati:{ingredienti:(x.dati&&x.dati.ingredienti)||[]}, ricetta_id:x.id}; });
    if(!ric.length){ _toast&&_toast('Nessuna preparazione salvata nel Quaderno'); return; }
    var e=_escV;
    var ov=document.createElement('div'); ov.className='mb-picker-ov';
    ov.innerHTML='<div class="mb-picker"><div class="mb-picker-h">Scegli dal Quaderno</div>'
      + ric.slice(0,30).map(function(r,i){ return '<button class="mb-picker-item" onclick="_mbAddQuad('+i+')">'+e(r.nome||(r.dati&&r.dati.nome)||'Ricetta')+'</button>'; }).join('')
      + '<button class="mb-picker-chiudi" onclick="this.closest(\'.mb-picker-ov\').remove()">Chiudi</button></div>';
    window._mbQuadCache=ric;
    document.body.appendChild(ov);
  }).catch(function(){ _toast&&_toast('Errore Quaderno'); });
};
window._mbAddQuad=function(i){
  var r=(window._mbQuadCache||[])[i]; if(!r) return;
  var d=r.dati||r;
  _mb.voci.push({nome:r.nome||d.nome||'Ricetta', ingredienti:d.ingredienti||[], ricetta_id:r.ricetta_id});
  var ov=document.querySelector('.mb-picker-ov'); if(ov) ov.remove();
  _mbRR();
};
window._mbDaFoto=function(){
  // la foto è feature PRO — gestisco solo_pro come invito, non errore
  fetch('/v1/foto-analisi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({test:true})})
    .then(function(r){return r.json();})
    .then(function(j){
      if(j.solo_pro){ _mbMostraPro(); return; }
      _toast&&_toast('Apri la fotocamera dal pulsante globale');
    }).catch(function(){ _mbMostraPro(); });
};
function _mbMostraPro(){
  var ov=document.createElement('div'); ov.className='mb-picker-ov';
  ov.innerHTML='<div class="mb-picker mb-pro"><div class="mb-pro-lab">◇ FUNZIONE PRO</div>'
    + '<div class="mb-pro-h">Costruisci voci da una foto</div>'
    + '<div class="mb-pro-txt">Fotografa gli ingredienti o un piatto: Matter riconosce e propone le voci di menu con food cost e allergeni. Disponibile con Matter Pro.</div>'
    + '<button class="mb-pro-cta" onclick="this.closest(\'.mb-picker-ov\').remove()">Ho capito</button></div>';
  document.body.appendChild(ov);
}

// STEP 3 — ANALISI
window._mbAnalizza=function(){
  _mb.step=3;
  var b=document.getElementById('vista-body'); if(b) b.innerHTML='<div class="mb-head mb-head-x"><span class="mb-eyebrow">◎ L\'EQUILIBRIO</span></div><div class="vista-loading">Analizzo il menu…</div>';
  var voci=_mb.voci.map(function(v){ return {nome:v.nome, ingredienti:(v.ingredienti||[]).map(function(x){return typeof x==='string'?x:(x.nome||'');})}; });
  fetch('/v1/menu/analizza',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({voci:voci})})
    .then(function(r){return r.json();}).then(function(j){ _mb.analisi=j; _mbRR(); })
    .catch(function(){ _mb.analisi={errore:true}; _mbRR(); });
};
function _mbStep3(){
  var e=_escV, d=_mb.analisi||{};
  if(d.errore) return '<div class="mb-head mb-head-x"><span class="mb-eyebrow">◎ L\'EQUILIBRIO</span></div><div class="vista-empty">Errore. <button class="mb-btn" onclick="_mb.step=2;_mbRR()">Torna alle voci</button></div>';
  var bil=d.bilanciamento||{};
  var mod=(d.modifiche_consigliate||[]);
  var bilHtml=['carne','pesce','vegetariano','dolce'].map(function(k){ var v=bil[k]||0; return '<div class="mb-bil-row"><span class="mb-bil-k">'+e(k)+'</span><span class="mb-bil-v">'+v+'</span></div>'; }).join('');
  // ONESTÀ: una voce senza ingredienti non si può classificare con certezza;
  // l'equilibrio va incorniciato come indicativo, non dichiarato certo.
  var _senza=(_mb.voci||[]).filter(function(v){ return !(v.ingredienti&&v.ingredienti.length); }).length;
  var _cav=_senza?'<div class="mb-incerta-ban" style="background:rgba(217,178,74,.12);border:1px solid rgba(217,178,74,.4);border-radius:11px;padding:11px 13px;margin:0 0 12px;font-size:12.5px;color:#d9b24a;line-height:1.5">⚠ '+_senza+(_senza===1?' voce è senza ingredienti':' voci sono senza ingredienti')+': il bilanciamento qui sotto è <b>indicativo</b>. Aggiungi gli ingredienti (dal Quaderno o a mano) per un\'analisi affidabile.</div>':'';
  return '<div class="mb-head mb-head-x"><span class="mb-eyebrow">◎ L\'EQUILIBRIO</span><span class="mb-ricetta-lab">'+d.n_voci+' VOCI</span></div>'
    + _cav
    + '<div class="mb-analisi-box"><div class="mb-analisi-lab">Bilanciamento del menu'+(_senza?' <span style="font-weight:400;color:#d9b24a">(indicativo)</span>':'')+'</div>'+bilHtml
    + (d.ripetizione_ingredienti_pct!=null?'<div class="mb-bil-row mb-bil-rip"><span class="mb-bil-k">ripetizione ingredienti</span><span class="mb-bil-v">'+d.ripetizione_ingredienti_pct+'%</span></div>':'')+'</div>'
    + (mod.length?'<div class="mb-mod-lab">◆ Cosa migliorare</div><div class="mb-modifiche">'+mod.map(function(m){ return '<div class="mb-mod"><span class="mb-mod-ico">→</span><span class="mb-mod-txt">'+e(m)+'</span></div>'; }).join('')+'</div>':(_senza?'<div class="mb-ok" style="color:#d9b24a">Nessuna correzione evidente — ma con voci senza ingredienti l\'equilibrio resta indicativo.</div>':'<div class="mb-ok">✓ Menu equilibrato.</div>'))
    + '<div class="mb-adv-btns"><button class="mb-adv-b" style="flex:1 1 100%" onclick="_mbFilo()"><span class="k">◇ Filo conduttore</span>Dai un tema alla carta e scopri quali preparazioni la reggono</button></div>'
    + '<button class="mb-analizza-btn" onclick="_mbChiusura()">Come chiudere il menu →</button>'
    + '<button class="mb-btn-sec" onclick="_mb.step=2;_mbRR()">← Torna alle voci</button>';
}

// STEP 4 — CHIUSURA
window._mbChiusura=function(){
  _mb.step=4;
  var b=document.getElementById('vista-body'); if(b) b.innerHTML='<div class="mb-head mb-head-x"><span class="mb-eyebrow">◎ LA CHIUSURA</span></div><div class="vista-loading">Cerco la chiusura giusta…</div>';
  var voci=_mb.voci.map(function(v){return v.nome;});
  fetch('/v1/dolce-per-menu',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({voci:voci})})
    .then(function(r){return r.json();}).then(function(j){ _mb.chiusura=j; _mbRR(); })
    .catch(function(){ _mb.chiusura={errore:true}; _mbRR(); });
};
function _mbStep4(){
  var e=_escV, d=_mb.chiusura||{};
  var dess=d.dessert_consigliato;
  var html='<div class="mb-head mb-head-x"><span class="mb-eyebrow">◎ LA CHIUSURA</span></div>'
    + '<div class="mb-h">Come chiudere<br>'+e(_mb.nome)+'.</div>';
  if(d.errore){ html+='<div class="vista-empty">Nessun suggerimento.</div>'; }
  else if(dess){
    var lista=Array.isArray(dess)?dess:[dess];
    html+='<div class="mb-chiusura-lista">'+lista.map(function(x){
      var nome=typeof x==='string'?x:(x.nome||''); var perche=typeof x==='object'?(x.perche||''):'';
      return '<div class="mb-chiusura"><div class="mb-chiusura-nome">'+e(nome)+'</div>'+(perche?'<div class="mb-chiusura-perche">'+e(perche)+'</div>':'')+'</div>';
    }).join('')+'</div>';
  }
  html+='<div class="mb-completo"><div class="mb-completo-ico">✓</div><div class="mb-completo-t">Menu "'+e(_mb.nome)+'" pronto</div><div class="mb-completo-d">'+_mb.voci.length+' voci · equilibrio analizzato · chiusura scelta. La pubblicazione (PDF, QR) arriva post-lancio.</div></div>'
    + '<button class="mb-btn-sec" onclick="_mb.step=3;_mbRR()">← Torna all\'analisi</button>';
  return html;
}

// SCHEDA VOCE (tap sulla card)
window._mbApriVoce=function(idx){
  var v=_mb.voci[idx]; if(!v) return;
  var e=_escV;
  var ov=document.createElement('div'); ov.className='mb-picker-ov';
  ov.innerHTML='<div class="mb-picker mb-voce-sheet"><div class="mb-voce-sheet-nome">'+e(v.nome)+'</div>'
    + (v.ingredienti&&v.ingredienti.length?'<div class="mb-voce-sheet-lab">Ingredienti</div><div class="mb-voce-sheet-ing">'+e((v.ingredienti||[]).map(function(x){return typeof x==='string'?x:(x.nome||'');}).join(', '))+'</div>':'')
    + '<button class="mb-voce-chiedi" onclick="chiudiVista&&chiudiVista();_chatConContesto(\'ricetta\',{nome:'+JSON.stringify(v.nome).replace(/"/g,'&quot;')+',ingredienti:'+JSON.stringify(v.ingredienti||[]).replace(/"/g,'&quot;')+'})">Chiedi a Matter su questa voce →</button>'
    + '<button class="mb-picker-chiudi" onclick="this.closest(\'.mb-picker-ov\').remove()">Chiudi</button></div>';
  document.body.appendChild(ov);
};

// ═══ MENU AVANZATO — accostamenti (grafo), tecniche (banco), filo conduttore ═══
// Tre strumenti che NON toccano la macchina a 5 step. Motori gia' vivi:
// /v1/menu/proposte, /v1/menu/tecniche, /v1/menu/filo. Dati reali, con fonte.
function _mbDisc(){ return ({pizza:'bakery',cocktail:'bar',ristorante:'cucina',colazione:'cucina',dessert:'cucina'})[_mb.intenzione]||'cucina'; }
function _mbOv(inner){
  var ov=document.createElement('div'); ov.className='mb-picker-ov';
  ov.innerHTML='<div class="mb-picker">'+inner+'<button class="mb-picker-chiudi" onclick="this.closest(\'.mb-picker-ov\').remove()">Chiudi</button></div>';
  document.body.appendChild(ov); return ov;
}
function _mbTuttiIngredienti(){
  var seen={}, out=[];
  (_mb.voci||[]).forEach(function(v){ (v.ingredienti||[]).forEach(function(x){
    var n=(typeof x==='string'?x:(x.nome||'')).trim();
    if(n && !seen[n.toLowerCase()]){ seen[n.toLowerCase()]=1; out.push(n); }
  }); });
  return out;
}

// --- ACCOSTAMENTI (proposte dal grafo) ---
window._mbAccostamenti=function(){
  var ings=_mbTuttiIngredienti();
  var ov=_mbOv('<div class="mb-adv-lab">◇ Accostamenti dal grafo</div><div id="mb-acc-body"></div>');
  var body=ov.querySelector('#mb-acc-body');
  if(ings.length<2){
    body.innerHTML='<div class="mb-adv-fonte">Servono almeno 2 ingredienti. Aggiungi voci col loro contenuto, oppure scrivili qui:</div>'
      + '<input class="mb-adv-input" id="mb-acc-in" placeholder="es. pomodoro, basilico, mozzarella">'
      + '<button class="mb-adv-go" onclick="_mbAccostaDa()">Trova accostamenti</button>';
    return;
  }
  body.innerHTML='<div class="mb-adv-chips">'+ings.slice(0,10).map(function(n){return '<span class="mb-adv-chip">'+_escV(n)+'</span>';}).join('')+'</div><div class="mb-adv-fonte">Cerco le connessioni…</div>';
  _mbAccostaFetch(ings.slice(0,10), body);
};
window._mbAccostaDa=function(){
  var i=document.getElementById('mb-acc-in'); var ings=(i?i.value:'').split(',').map(function(s){return s.trim();}).filter(Boolean);
  var body=document.getElementById('mb-acc-body'); if(!body) return;
  if(ings.length<2){ _toast&&_toast('Scrivi almeno 2 ingredienti separati da virgola'); return; }
  body.innerHTML='<div class="mb-adv-fonte">Cerco le connessioni…</div>'; _mbAccostaFetch(ings, body);
};
function _mbAccostaFetch(ings, body){
  fetch('/v1/menu/proposte',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ingredienti:ings,tipo:'piatto'})})
    .then(function(r){return r.json();}).then(function(j){
      var pr=(j&&j.proposte)||[];
      if(!pr.length){ body.innerHTML='<div class="mb-adv-fonte">Nessun accostamento forte tra questi ingredienti. '+_escV(j&&j.messaggio||'')+'</div>'; return; }
      body.innerHTML=pr.slice(0,8).map(function(p){
        var rob=p.robustezza||''; var espl=p.esplorativa||rob==='da esplorare';
        var cls=espl?'espl':(rob==='media'?'media':'');
        var c=(p.connessioni!=null?p.connessioni:'');
        var badge=espl?'da esplorare al banco':(c!==''?(c+' composti condivisi · legame '+rob):'');
        return '<div class="mb-adv-item"><span class="n">'+_escV(p.nome||'')+'</span>'
          + (p.tipo?'<div class="m">'+_escV(p.tipo)+'</div>':'')
          + (badge?'<span class="b '+cls+'">'+_escV(badge)+'</span>':'')
          + '</div>';
      }).join('') + '<div class="mb-adv-fonte">'+_escV(j.fonte||'Connessioni per composti aromatici condivisi')+'</div>';
    }).catch(function(){ body.innerHTML='<div class="mb-adv-fonte">Accostamenti non raggiungibili ora.</div>'; });
}

// --- TECNICHE (del banco, per disciplina del menu) ---
window._mbTecnicheMenu=function(){
  var disc=_mbDisc();
  var ov=_mbOv('<div class="mb-adv-lab">◇ Tecniche del banco — '+_escV(disc)+'</div><div id="mb-tec-body"><div class="mb-adv-fonte">Cerco…</div></div>');
  var body=ov.querySelector('#mb-tec-body');
  fetch('/v1/menu/tecniche',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({disciplina:disc})})
    .then(function(r){return r.json();}).then(function(j){
      var tec=(j&&j.tecniche)||[];
      if(!tec.length){ body.innerHTML='<div class="mb-adv-fonte">Nessuna tecnica col numero-bersaglio per questa disciplina.</div>'; return; }
      body.innerHTML=tec.slice(0,12).map(function(t){
        return '<div class="mb-adv-item"><span class="n">'+_escV(t.nome||'')+'</span>'
          + (t.famiglia?'<div class="m">'+_escV(t.famiglia)+'</div>':'')
          + (t.numeri?'<span class="b">'+_escV(t.numeri)+'</span>':'')
          + '</div>';
      }).join('') + '<div class="mb-adv-fonte">Tecniche dall\'archivio Matter, col numero-bersaglio misurabile al banco.</div>';
    }).catch(function(){ body.innerHTML='<div class="mb-adv-fonte">Tecniche non raggiungibili ora.</div>'; });
};

// --- FILO CONDUTTORE (tema → preparazioni che lo reggono) ---
window._mbFiloTipo='ingrediente';
window._mbFilo=function(){
  var ov=_mbOv('<div class="mb-adv-lab">◇ Filo conduttore</div>'
    + '<div class="mb-adv-fonte" style="margin-top:0;margin-bottom:10px">Scegli attorno a cosa ruota la carta. Matter ti mostra quali preparazioni dell\'archivio reggono quel filo.</div>'
    + '<div class="mb-adv-seg"><button id="mb-filo-ing" class="on" onclick="_mbFiloSeg(\'ingrediente\')">Ingrediente</button><button id="mb-filo-fen" onclick="_mbFiloSeg(\'fenomeno\')">Fenomeno</button></div>'
    + '<input class="mb-adv-input" id="mb-filo-in" placeholder="es. pomodoro — oppure Maillard" onkeydown="if(event.key===\'Enter\')_mbFiloGo()">'
    + '<button class="mb-adv-go" onclick="_mbFiloGo()">Trova il filo</button>'
    + '<div id="mb-filo-body" style="margin-top:12px"></div>');
};
window._mbFiloSeg=function(t){
  window._mbFiloTipo=t;
  var a=document.getElementById('mb-filo-ing'), b=document.getElementById('mb-filo-fen');
  if(a) a.className=(t==='ingrediente'?'on':''); if(b) b.className=(t==='fenomeno'?'on':'');
  var inp=document.getElementById('mb-filo-in'); if(inp) inp.placeholder=(t==='fenomeno'?'es. Maillard, emulsione, fermentazione':'es. pomodoro, limone, nocciola');
};
window._mbFiloGo=function(){
  var inp=document.getElementById('mb-filo-in'); var tema=(inp?inp.value:'').trim();
  var body=document.getElementById('mb-filo-body'); if(!body) return;
  if(!tema){ _toast&&_toast('Scrivi un tema'); return; }
  body.innerHTML='<div class="mb-adv-fonte">Cerco il filo…</div>';
  fetch('/v1/menu/filo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tema:tema,tipo_filo:window._mbFiloTipo,preparazioni:[]})})
    .then(function(r){return r.json();}).then(function(j){
      if(!j || j.errore){ body.innerHTML='<div class="mb-adv-fonte">Filo non calcolabile ora.</div>'; return; }
      var sug=j.suggeriti_per_il_filo||[];
      if(!sug.length){ body.innerHTML='<div class="mb-adv-fonte">Nessuna preparazione nell\'archivio regge il filo «'+_escV(tema)+'». Prova un tema più comune (un ingrediente diffuso o un fenomeno).</div>'; return; }
      body.innerHTML='<div class="mb-adv-lab" style="margin-bottom:8px">Preparazioni che reggono «'+_escV(tema)+'»</div>'
        + sug.map(function(n){ return '<div class="mb-adv-item"><span class="n">'+_escV(n)+'</span></div>'; }).join('')
        + '<div class="mb-adv-fonte">Dall\'archivio preparazioni di Matter. Aggiungile dal Quaderno per tenerle nella carta.</div>';
    }).catch(function(){ body.innerHTML='<div class="mb-adv-fonte">Filo non raggiungibile ora.</div>'; });
};
})();

