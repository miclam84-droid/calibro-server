// ═══ MATTER-LABORATORIO.js — L'ambiente unico (Board #210): 3 intenzioni ═══
(function(){
window.apriLaboratorio = function(intenzione){
  if(intenzione==='esplora'){ _caricaModulo('possibilita').then(function(){ if(window.apriPossibilita) apriPossibilita('pomodoro'); }); return; }
  if(intenzione==='crea'){ _caricaModulo('composer').then(function(){ if(window.apriComposer) apriComposer(); }); return; }
  if(intenzione==='impara'){ _caricaModulo('scienza').then(function(){ if(window.apriSchedeScienza) apriSchedeScienza(); }); return; }
  // schermata scelta intenzione
  var e=_escV;
  _apriVista('Laboratorio',
    '<div class="lab-hero"><div class="lab-hero-lab">IL LABORATORIO</div>'
    + '<div class="lab-hero-claim">Cosa vuoi fare?</div>'
    + '<div class="lab-hero-sub">Un solo ambiente. Scegli l\'intenzione: esplorare la rete degli ingredienti, creare una preparazione, o imparare la scienza del mestiere.</div></div>'
    + '<div class="lab-intenzioni">'
    +   '<button class="lab-int lab-int-esplora" onclick="apriLaboratorio(\'esplora\')">'
    +     '<i class="ph ph-graph" aria-hidden="true"></i>'
    +     '<div class="lab-int-t">Esplora</div>'
    +     '<div class="lab-int-d">Parti da un ingrediente: scopri i suoi ruoli e il piatto embrionale che può diventare.</div>'
    +   '</button>'
    +   '<button class="lab-int lab-int-crea" onclick="apriLaboratorio(\'crea\')">'
    +     '<i class="ph ph-flask" aria-hidden="true"></i>'
    +     '<div class="lab-int-t">Crea</div>'
    +     '<div class="lab-int-d">Costruisci una ricetta ingrediente per ingrediente. Vedi l\'equilibrio in tempo reale, poi salva nel Quaderno.</div>'
    +   '</button>'
    +   '<button class="lab-int lab-int-impara" onclick="apriLaboratorio(\'impara\')">'
    +     '<i class="ph ph-book-open" aria-hidden="true"></i>'
    +     '<div class="lab-int-t">Impara</div>'
    +     '<div class="lab-int-d">Le schede scienza, le tecniche, la biodiversità. I numeri e i fenomeni dietro ogni preparazione.</div>'
    +   '</button>'
    + '</div>'
    + '<div class="lab-imparalink"><button class="lab-bio-link" onclick="_caricaModulo(\'biodiversita\').then(function(){apriBiodiversita&&apriBiodiversita()})">◉ La Biodiversità italiana →</button></div>');
};
})();
