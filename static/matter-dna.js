// ═══ MATTER-DNA.js — modulo (lazy, Strangler) ═══
(function(){
window.caricaDNA = async function(){
  var cont=document.getElementById('dna-content');
  if(!cont) return;
  cont.innerHTML='<div class="quad-loading">Analizzo il tuo lavoro al banco…</div>';
  try{
    var r=await fetch('/v1/dna-professionale', {headers:_statoHeaders()});
    var j=await r.json();
    var e=_escV;
    if(!j.pronto){
      cont.innerHTML='<div class="dna-empty"><div class="dna-empty-ico">◎</div>'
        + '<b>Il tuo DNA Professionale cresce a ogni misura</b>'
        + '<span>'+e(j.messaggio||'Registra qualche misura al banco: Matter Bench imparerà come lavori e ti mostrerà i tuoi pattern reali.')+'</span>'
        + '<button class="calc-go" onclick="switchQuaderno(\'misure\')" style="margin-top:16px">Vai alle misure</button></div>';
      return;
    }
    var riep=j.riepilogo||{};
    var nome=(localStorage.getItem('matter_profilo_nome')||'Professionista');
    var html='<div class="dna-header">'
      + '<div class="dna-header-lab">Profilo Professionale</div>'
      + '<div class="dna-header-nome">'+e(nome)+'</div>'
      + '<div class="dna-riepilogo"><span><b>'+(riep.fenomeni_seguiti||0)+'</b> fenomeni seguiti</span><span><b>'+(riep.misure_totali||0)+'</b> misure totali</span></div>'
      + '</div>';
    // pattern
    html += (j.pattern||[]).map(function(p){
      var tend = p.tendenza ? '<div class="dna-tendenza"> '+e(p.tendenza)+'</div>' : '';
      var bers = p.nota_bersaglio ? '<div class="dna-bersaglio">'+e(p.nota_bersaglio)+'</div>' : '';
      return '<div class="dna-card">'
        + '<div class="dna-card-fen">'+e(p.fenomeno||'')+'</div>'
        + '<div class="dna-card-media">'+e(String(p.media))+'<span class="dna-card-u">'+e(p.unita||'')+'</span></div>'
        + '<div class="dna-card-n">'+(p.n_misure||0)+' misure</div>'
        + '<div class="dna-card-zona">'+e(p.zona||'')+'</div>'
        + bers + tend
        + '</div>';
    }).join('');
    if(j.suggerimento){ html += '<div class="dna-sugg">'+e(j.suggerimento)+'</div>'; }
    if(j.firma){ html += '<div class="dna-firma">'+e(j.firma)+'</div>'; }
    cont.innerHTML=html;
  }catch(e){ cont.innerHTML='<div class="dna-empty"><b>Errore</b><span>Riprova.</span></div>'; }
}

window._dnaContestoBanner = async function(calcKey){
  var fen=_CALC_FENOMENO[calcKey];
  if(!fen) return;
  try{
    var r=await fetch('/v1/dna-contesto?fenomeno='+encodeURIComponent(fen), {headers:_statoHeaders()});
    var j=await r.json();
    if(!j.ha_dati || !j.frase) return;
    var e=_escV;
    var aff=j.affidabilita||'indicativo';
    var cont=document.getElementById('calc-body');
    if(!cont) return;
    if(cont.querySelector('.dna-ctx')) return;
    var banner=document.createElement('div');
    banner.className='dna-ctx';
    // input principale del calcolatore da autocompilare
    var mappaInput={ impasto:'ci-peso', foodcost:'fcp-pv', vino:'cv-temp', brix:'cb-brix', calo:'rc-peso', teglie:'ct-attuale' };
    var inputId=mappaInput[calcKey];
    var usaBtn = (inputId && j.media!=null) ? '<button class="dna-ctx-usa" onclick="_dnaUsaValore(\''+e(inputId)+'\','+j.media+')">Usa valore</button>' : '';
    banner.innerHTML='<span class="dna-ctx-ico">◎</span>'
      + '<span class="dna-ctx-txt">'+e(j.frase)+'</span>'
      + '<span class="dna-ctx-badge dna-aff-'+e(aff)+'">'+e(aff)+'</span>'
      + usaBtn;
    cont.insertBefore(banner, cont.firstChild);
  }catch(e){}
}

window._dnaUsaValore = function(inputId, valore){
  var el=document.getElementById(inputId);
  if(el){ el.value=valore; el.dispatchEvent(new Event('input')); _toast('Valore inserito: '+valore); }
}

})();
