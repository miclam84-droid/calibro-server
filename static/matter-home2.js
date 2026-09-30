// ═══ MATTER-HOME2.js — La Home rifondata (Design v1 congelato): 6 blocchi ═══
// "La Home è la Costituzione resa visibile" — ogni schermata racconta un esperimento vivo.
(function(){
var _DISC_LAB={cucina:'Cucina',bar:'Bar',panificazione:'Panificazione',pasticceria:'Pasticceria',caffetteria:'Caffetteria',gelateria:'Gelateria',birra:'Birra',vino:'Vino',trasversale:'Trasversale'};
var _DIAGNOSI_ESEMPI=[
  ['Il cornicione non si apre','panificazione'],
  ['Il Negroni è troppo amaro','bar'],
  ['La crema pasticcera ha i grumi','pasticceria'],
  ['La carne è dura e stopposa','cucina'],
  ['La maionese è impazzita','cucina'],
  ['L\'espresso esce troppo acido','caffetteria']
];

window.renderHome2 = function(){
  var host=document.getElementById('home2-host'); if(!host) return;
  var e=_escV;
  host.innerHTML=''
    // BLOCCO 1 — Esperimento del Giorno (hero) — caricato async
    + '<section class="h2-hero ds-grid-bg" id="h2-hero"><div class="h2-hero-load"><div class="skel-line w40"></div><div class="skel-box"></div></div></section>'
    // BLOCCO 2 — La Diagnosi è il cuore
    + '<section class="h2-diagnosi"><div class="ds-eyebrow">◎ COSA NON FUNZIONA AL BANCO?</div>'
    +   '<div class="h2-diag-titolo">Parti da un problema.<br>Matter risale alla causa.</div>'
    +   '<div class="h2-diag-esempi">'+_DIAGNOSI_ESEMPI.map(function(x){ return '<button class="h2-diag-chip" onclick="_h2Diagnosi(\''+e(x[0]).replace(/'/g,"\\'")+'\')">'+e(x[0])+'</button>'; }).join('')+'</div>'
    +   '<button class="h2-diag-libero" onclick="_h2DiagnosiLibera()">…oppure descrivilo a Matter →</button>'
    + '</section>'
    // BLOCCO 3 — Science x Craft (widget)
    + '<section class="h2-sxc" id="h2-sxc"></section>'
    // BLOCCO 4 — Protocol Hub
    + '<section class="h2-hub"><div class="ds-eyebrow">◎ IL LABORATORIO</div>'
    +   '<div class="h2-hub-titolo">Cerca un esperimento</div>'
    +   '<div class="h2-hub-search"><input id="h2-hub-input" placeholder="pomodoro, maionese, lievitazione…" onkeydown="if(event.key===\'Enter\')_h2Hub()"><button onclick="_h2Hub()">→</button></div>'
    +   '<div class="h2-hub-hint">Ingredienti · preparazioni · esperimenti · fenomeni</div>'
    + '</section>'
    // BLOCCO 5 — Composer + BLOCCO 6 — Esperimenti recenti
    + '<section class="h2-doppia">'
    +   '<button class="h2-composer" onclick="if(typeof _caricaModulo===\'function\'){_caricaModulo(\'composer\').then(function(){apriComposer&&apriComposer()})}"><span class="h2-comp-ico">◈</span><span class="h2-comp-t">Simula un esperimento</span><span class="h2-comp-d">Costruisci, vedi l\'equilibrio</span></button>'
    +   '<button class="h2-quaderno" onclick="switchTab(\'quaderno\')"><span class="h2-comp-ico">◱</span><span class="h2-comp-t">Esperimenti recenti</span><span class="h2-comp-d">I tuoi commit</span></button>'
    + '</section>';
  _h2CaricaEsperimento();
  _h2CaricaScienceCraft();
};

// BLOCCO 1 — Esperimento del giorno (dati veri da /v1/esperimento-del-giorno)
function _h2CaricaEsperimento(){
  fetch('/v1/esperimento-del-giorno').then(function(r){return r.json();}).then(function(d){
    var hero=document.getElementById('h2-hero'); if(!hero||!d||!d.nome) return;
    var e=_escV;
    var scala = (window.dsScala && d.bersaglio && d.bersaglio.valore) ? dsScala(d.bersaglio, 'Bersaglio · '+e(d.variabile_critica||'')) : '';
    var sens = d.sensori || {};
    var sensChip = window.dsSensore ? [
      sens.vista?dsSensore('vista',sens.vista):'',
      sens.tatto?dsSensore('tatto',sens.tatto):'',
      sens.olfatto?dsSensore('olfatto',sens.olfatto):''
    ].filter(Boolean).slice(0,2).join('') : '';
    var badge = window.dsBadge ? dsBadge(d.stato_epistemico) : '';
    hero.innerHTML=''
      + '<div class="h2-hero-top"><span class="ds-eyebrow">◎ ESPERIMENTO DEL GIORNO</span>'+badge+'</div>'
      + '<div class="ds-display h2-hero-nome">'+e(d.nome)+'</div>'
      + (d.ipotesi?'<div class="h2-hero-ipotesi"><span class="h2-hero-ip-lab">Ipotesi</span> '+e(d.ipotesi)+'</div>':'')
      + (scala?'<div class="h2-hero-scala">'+scala+'</div>':'')
      + (sensChip?'<div class="h2-hero-sensori"><div class="h2-hero-sens-lab">I sensori — cosa osservare</div><div class="h2-hero-sens-chips">'+sensChip+'</div></div>':'')
      + '<button class="h2-hero-cta" onclick="_h2ApriProtocollo(\''+e(d.id)+'\')">Apri l\'esperimento →</button>';
  }).catch(function(){ var h=document.getElementById('h2-hero'); if(h) h.innerHTML='<div class="ds-eyebrow">ESPERIMENTO DEL GIORNO</div><div class="ds-caption" style="margin-top:8px">Caricamento non riuscito. Riprova.</div>'; });
}

// BLOCCO 3 — Science x Craft (dal fenomeno di oggi)
function _h2CaricaScienceCraft(){
  var box=document.getElementById('h2-sxc'); if(!box) return;
  var e=_escV;
  box.innerHTML='<div class="h2-sxc-lab">SCIENCE × CRAFT</div>'
    + '<div class="h2-sxc-grid">'
    +   '<div class="h2-sxc-craft"><div class="h2-sxc-side">IL GESTO</div><div class="h2-sxc-craft-ph ds-grid-bg">◇</div><div class="h2-sxc-txt">La crosta suona vuota se la batti sotto</div></div>'
    +   '<div class="h2-sxc-science"><div class="h2-sxc-side">IL DATO</div><div class="h2-sxc-num ds-data">96<span class="h2-sxc-u">°C</span></div><div class="h2-sxc-txt">al cuore = amido gelatinizzato, mollica pronta</div></div>'
    + '</div>';
}

window._h2ApriProtocollo=function(id){ if(typeof apriProtocollo==='function'){ apriProtocollo(id); } else if(typeof _caricaModulo==='function'){ _caricaModulo('protocollo').then(function(){ if(window.apriProtocollo) apriProtocollo(id); }); } };
window._h2Diagnosi=function(testo){ switchTab('chiedi'); setTimeout(function(){ if(typeof chiediTesto==='function') chiediTesto(testo); },250); };
window._h2DiagnosiLibera=function(){ switchTab('chiedi'); setTimeout(function(){ var i=document.getElementById('q')||document.getElementById('ask-input'); if(i) i.focus(); },250); };
window._h2Hub=function(){ var i=document.getElementById('h2-hub-input'); var q=i?i.value.trim():''; if(!q) return; if(typeof apriHub==='function'){ apriHub(q); } };
})();
