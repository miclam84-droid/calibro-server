// ═══ MATTER-PROTOCOLLO.js — Scheda Protocollo (board 3): l'esperimento aperto ═══
// "Matter non possiede ricette. Possiede esperimenti." Il numero verifica, il sensore convince.
// Ordine come lo vive il professionista: IPOTESI → BERSAGLIO → SENSORE → VARIABILE → REAGENTI → TIMELINE
(function(){
window.apriProtocollo = function(id){
  _apriVista('Esperimento', '<div id="prot-host"><div class="vista-loading"></div></div>');
  fetch('/v1/protocollo/'+encodeURIComponent(id)).then(function(r){return r.json();}).then(function(d){
    if(!d || !d.nome){ var h=document.getElementById('prot-host'); if(h) h.innerHTML='<div class="vista-empty">Esperimento non trovato.</div>'; return; }
    _protRender(d);
  }).catch(function(){ var h=document.getElementById('prot-host'); if(h) h.innerHTML='<div class="vista-empty">Errore di rete.</div>'; });
};

function _protRender(d){
  var e=_escV, host=document.getElementById('prot-host'); if(!host) return;
  var sens=d.sensori||{};
  var sensPrimo = sens.vista||sens.tatto||sens.olfatto||'';
  var badge = window.dsBadge ? dsBadge(d.stato_epistemico, d.verificato) : '';
  var scala = (window.dsScala && d.bersaglio && d.bersaglio.valore) ? dsScala(d.bersaglio, 'Bersaglio · '+e(d.variabile_critica||'')) : '';

  // 1. HERO — ipotesi + bersaglio + sensore (si capisce tutto in 3 righe)
  var html='<div class="prot-hero ds-grid-bg"><div class="prot-hero-top"><span class="ds-eyebrow">◎ ESPERIMENTO</span>'+badge+'</div>'
    + '<div class="ds-display prot-hero-nome">'+e(d.nome)+'</div>'
    + (d.ipotesi?'<div class="prot-hero-ip"><span class="prot-lab">Ipotesi</span> '+e(d.ipotesi)+'</div>':'')
    + (scala?'<div class="prot-hero-scala">'+scala+'</div>':'')
    + (sensPrimo?'<div class="prot-hero-sens">'+(window.dsSensore?dsSensore('vista',sensPrimo):e(sensPrimo))+'</div>':'')
    + '</div>';

  // 2. VARIABILE CRITICA (una sola, la leva)
  if(d.variabile_critica){
    html+='<div class="prot-var"><div class="prot-var-lab">◎ LA VARIABILE CRITICA</div>'
      + '<div class="prot-var-nome">'+e(d.variabile_critica)+'</div>'
      + '<div class="prot-var-d">È la leva che governa l\'esperimento. Controlla questa, e il resto segue.</div></div>';
  }

  // 3. I SENSORI (cosa osservare al banco — Craft)
  var sChips=[sens.vista?['vista',sens.vista]:null, sens.tatto?['tatto',sens.tatto]:null, sens.olfatto?['olfatto',sens.olfatto]:null].filter(Boolean);
  if(sChips.length && window.dsSensore){
    html+='<div class="prot-sez-lab">◎ I SENSORI — la tua osservazione</div><div class="prot-sensori">'
      + sChips.map(function(s){ return dsSensore(s[0],s[1]); }).join('')+'</div>';
  }

  // 4. REAGENTI (mini Protocol Hub — ogni reagente apre il suo)
  var reag=(d.reagenti||[]);
  if(reag.length){
    html+='<div class="prot-sez-lab">◎ I REAGENTI</div><div class="prot-reag-lista">'
      + reag.map(function(r){
          var q=(r.quantita!=null?r.quantita:'')+(r.unita?' '+r.unita:'');
          return '<button class="prot-reag" onclick="apriHub&&apriHub(\''+e(String(r.nome)).replace(/'/g,"\\'")+'\')">'
            + '<span class="prot-reag-nome">'+e(r.nome)+'</span>'
            + (q?'<span class="prot-reag-q ds-data">'+e(q)+'</span>':'')
            + (r.ruolo?'<span class="prot-reag-ruolo">'+e(r.ruolo)+'</span>':'')
            + '</button>';
        }).join('')+'</div>';
  }

  // 5. FENOMENI (le trasformazioni, con causalità se c'è)
  var fen=(d.fenomeni||[]);
  if(fen.length){
    html+='<div class="prot-sez-lab">◎ COSA SUCCEDE — i fenomeni</div><div class="prot-fen-lista">'
      + fen.map(function(f){
          var nome=typeof f==='string'?f:(f.nome||'');
          var slug=typeof f==='object'?(f.slug||''):'';
          return '<button class="prot-fen" onclick="'+(slug?'_protFenomeno(\''+e(slug)+'\')':'')+'">'+e(nome)+' <span class="prot-fen-arr">→</span></button>';
        }).join('')+'</div>';
  }

  // 6. DIAGNOSI contestuale (cucitura, non bottone)
  html+='<div class="prot-diagnosi"><div class="prot-diag-q">Qualcosa non torna al banco?</div>'
    + '<button class="prot-diag-cta" onclick="_protDiagnosi(\''+e(d.nome)+'\')">Apri la diagnosi →</button></div>';

  host.innerHTML=html;
}
window._protFenomeno=function(slug){ if(typeof apriSchedaScienza==='function'){ chiudiVista&&chiudiVista(); _caricaModulo('scienza').then(function(){ apriSchedaScienza(slug); }); } };
window._protDiagnosi=function(nome){ chiudiVista&&chiudiVista(); switchTab('chiedi'); setTimeout(function(){ if(typeof chiediTesto==='function') chiediTesto('Ho un problema con: '+nome+'. Aiutami a capire cosa non va.'); },250); };
})();
