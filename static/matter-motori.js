// ═══ MATTER-MOTORI.js — Motore Panificazione (form 3 schermate, mockup) ═══
(function(){
var _mp = { tipo:'pizza_napoletana', n_panetti:6, peso_panetto:280, metodo:'biga',
            temp_ambiente:22, temp_farina:20, idratazione:62, ora_sfornata:'20:00', step:1 };

// parametri per tipo di prodotto (idratazione default, temperatura forno, tempi)
var _MP_TIPI = {
  pizza_napoletana:{ nome:'Pizza napoletana', idr:62, forno:485, cottura:'60-90s', lievitazione:8 },
  pizza_teglia:    { nome:'Pizza in teglia',  idr:75, forno:250, cottura:'12-15min', lievitazione:24 },
  pane:            { nome:'Pane',             idr:68, forno:230, cottura:'40-50min', lievitazione:18 },
  focaccia:        { nome:'Focaccia',         idr:78, forno:220, cottura:'20-25min', lievitazione:12 }
};
var _MP_METODI = {
  diretto:{ nome:'Diretto',  lievito_pct:0.4, prefermento:false, ore_pre:0 },
  biga:   { nome:'Biga',     lievito_pct:0.17, prefermento:true, ore_pre:17, pre_idr:44, temp_pre:18 },
  poolish:{ nome:'Poolish',  lievito_pct:0.2, prefermento:true, ore_pre:12, pre_idr:100, temp_pre:20 },
  madre:  { nome:'Lievito madre', lievito_pct:15, prefermento:true, ore_pre:4, pre_idr:50, temp_pre:26 }
};

window.apriMotorePanificazione = function(){
  _mp.step = 1;
  _apriVista('Motore · Panificazione', _mpRender());
};

function _mpRender(){
  if(_mp.step===1) return _mpStep1();
  if(_mp.step===2) return _mpStep2();
  return _mpStep3();
}

function _mpStep1(){
  var e=_escV;
  var tipi=[['pizza_napoletana','Pizza napoletana'],['pizza_teglia','Pizza teglia'],['pane','Pane'],['focaccia','Focaccia']];
  return '<div class="mp-head"><span class="mp-num">1/3</span><span class="mp-eyebrow">— L\'OBIETTIVO</span></div>'
    + '<div class="mp-h">Cosa vuoi<br>sfornare?</div>'
    + '<div class="mp-lab">PRODOTTO</div>'
    + '<div class="mp-prod-grid">'
    + tipi.map(function(t){ return '<button class="mp-prod'+(_mp.tipo===t[0]?' sel':'')+'" onclick="_mpSetTipo(\''+t[0]+'\')">'+e(t[1])+'</button>'; }).join('')
    + '</div>'
    + '<div class="mp-row2">'
    +   '<div><div class="mp-lab">N° PANETTI</div><input class="mp-inp" type="number" inputmode="numeric" id="mp-npanetti" value="'+_mp.n_panetti+'"></div>'
    +   '<div><div class="mp-lab">PESO (g)</div><input class="mp-inp" type="number" inputmode="numeric" id="mp-peso" value="'+_mp.peso_panetto+'"></div>'
    + '</div>'
    + '<div class="mp-lab">ORA DI SFORNATA</div>'
    + '<input class="mp-inp" type="time" id="mp-ora" value="'+_mp.ora_sfornata+'">'
    + '<button class="mp-avanti" onclick="_mpVai2()">Avanti · Contesto →</button>';
}

function _mpStep2(){
  var e=_escV;
  var metodi=[['diretto','Diretto'],['biga','Biga'],['poolish','Poolish'],['madre','Madre']];
  return '<div class="mp-head"><span class="mp-num">2/3</span><span class="mp-eyebrow">— IL CONTESTO</span></div>'
    + '<div class="mp-h">Dove lavori<br>oggi?</div>'
    + '<div class="mp-row2">'
    +   '<div><div class="mp-lab">TEMP. AMBIENTE</div><div class="mp-inp-u"><input type="number" id="mp-tamb" value="'+_mp.temp_ambiente+'"><span>°C</span></div></div>'
    +   '<div><div class="mp-lab">TEMP. FARINA</div><div class="mp-inp-u"><input type="number" id="mp-tfar" value="'+_mp.temp_farina+'"><span>°C</span></div></div>'
    + '</div>'
    + '<div class="mp-lab">METODO</div>'
    + '<div class="mp-metodo-grid">'
    + metodi.map(function(m){ return '<button class="mp-metodo'+(_mp.metodo===m[0]?' sel':'')+'" onclick="_mpSetMetodo(\''+m[0]+'\')">'+e(m[1])+'</button>'; }).join('')
    + '</div>'
    + '<div class="mp-lab">IDRATAZIONE</div>'
    + '<div class="mp-inp-u"><input type="number" id="mp-idr" value="'+_mp.idratazione+'"><span>%</span></div>'
    + '<button class="mp-progetta" onclick="_mpVai3()">Progetta il processo →</button>';
}

function _mpStep3(){
  var e=_escV;
  var t=_MP_TIPI[_mp.tipo], m=_MP_METODI[_mp.metodo];
  // ── CALCOLO DOSI (metodo del panettiere) ──
  var pesoTot = _mp.n_panetti * _mp.peso_panetto;
  // farina = pesoTot / (1 + idr/100 + sale% + lievito%)
  var salePct = 2.5, lievPct = m.lievito_pct;
  var farina = pesoTot / (1 + _mp.idratazione/100 + salePct/100 + lievPct/100);
  var acqua = farina * _mp.idratazione/100;
  var sale = farina * salePct/100;
  var lievito = farina * lievPct/100;
  // temperatura acqua (DDT ~24°C): T_acqua = 3*DDT - T_amb - T_farina - T_frizione
  var DDT = 24, frizione = 2;
  var tAcqua = 3*DDT - _mp.temp_ambiente - _mp.temp_farina - frizione;
  tAcqua = Math.max(4, Math.min(40, tAcqua));

  var dosi = [
    ['Farina', Math.round(farina)+' g', false],
    ['Acqua', Math.round(acqua)+' g', false],
    ['Sale', (Math.round(sale*10)/10)+' g', false],
    ['Lievito fresco', (Math.round(lievito*10)/10)+' g · '+(Math.round(lievPct*100)/100)+'%', false],
    ['Temp. acqua', Math.round(tAcqua)+'°C', true]
  ];

  // ── TIMELINE A RITROSO ──
  var timeline = _mpTimeline(t, m);

  var dosiHtml = dosi.map(function(d){
    return '<div class="mp-dosi-row"><span class="mp-dosi-k">'+e(d[0])+'</span><span class="mp-dosi-v'+(d[2]?' evid':'')+'">'+e(d[1])+'</span></div>';
  }).join('');

  var tlHtml = timeline.map(function(f){
    return '<div class="mp-tl-item">'
      + '<div class="mp-tl-dot"></div>'
      + '<div class="mp-tl-ora">'+e(f.ora)+'</div>'
      + '<div class="mp-tl-body"><div class="mp-tl-fase">'+e(f.fase)+(f.check?' ✓':'')+'</div><div class="mp-tl-nota">'+e(f.nota)+'</div></div>'
      + '</div>';
  }).join('');

  return '<div class="mp-head mp-head3"><span class="mp-eyebrow">◎ IL PROGETTO</span><span class="mp-ricetta-lab">RICETTA</span></div>'
    + '<div class="mp-sommario">'+_mp.n_panetti+' PANETTI · '+_mp.peso_panetto+'G · '+e(m.nome.toUpperCase())+'</div>'
    + '<div class="mp-dosi-box">'+dosiHtml+'</div>'
    + '<div class="mp-tl-lab">— LA TIMELINE · A RITROSO</div>'
    + '<div class="mp-tl">'+tlHtml+'</div>'
    + '<button class="mp-genera-btn" onclick="_mpGeneraRicetta()">Genera la ricetta completa →</button>'
    + '<button class="mp-chiedi-btn" onclick="_mpChiediChat()">◎ Chiedi a Matter su questo impasto</button>'
    + '<button class="mp-back-btn" onclick="_mp.step=2;_mpReRender()">← Modifica il contesto</button>';
}

function _mpTimeline(t, m){
  // calcolo a ritroso dall'ora di sfornata
  function parseH(s){ var p=(s||'20:00').split(':'); return (+p[0])*60 + (+(p[1]||0)); }
  function fmt(min){ min=((min%1440)+1440)%1440; var h=Math.floor(min/60), mm=min%60; return (h<10?'0':'')+h+':'+(mm<10?'0':'')+mm; }
  var sforna = parseH(_mp.ora_sfornata);
  var tl = [];
  // durata cottura in minuti (approx)
  var cottura = t.forno>400?2:15;
  var inforna = sforna - cottura;
  var appretto = 5*60; // 5h appretto
  var staglio = inforna - appretto;
  var puntata = 2*60;
  var impasto = staglio - puntata;
  if(m.prefermento){
    var startPre = impasto - m.ore_pre*60;
    tl.push({ora:'ieri '+fmt(startPre), fase:'START '+m.nome.toUpperCase(), nota:m.ore_pre+'h a '+(m.temp_pre||18)+'°C', check:false});
  }
  tl.push({ora:fmt(impasto), fase:'IMPASTO FINALE', nota:'poi puntata 2h', check:false});
  tl.push({ora:fmt(staglio), fase:'STAGLIO', nota:'panetti, appretto 5h', check:false});
  tl.push({ora:fmt(inforna), fase:'INFORNA', nota:t.forno+'°C, '+t.cottura, check:false});
  tl.push({ora:fmt(sforna), fase:'SFORNA', nota:'pronto', check:true});
  return tl;
}

window._mpSetTipo = function(tp){ _mp.tipo=tp; if(_MP_TIPI[tp]) _mp.idratazione=_MP_TIPI[tp].idr; _mpReRender(); };
window._mpSetMetodo = function(md){ _mp.metodo=md; _mpReRender(); };
window._mpVai2 = function(){
  _mp.n_panetti = +document.getElementById('mp-npanetti').value||6;
  _mp.peso_panetto = +document.getElementById('mp-peso').value||280;
  _mp.ora_sfornata = document.getElementById('mp-ora').value||'20:00';
  _mp.step=2; _mpReRender();
};
window._mpVai3 = function(){
  _mp.temp_ambiente = +document.getElementById('mp-tamb').value||22;
  _mp.temp_farina = +document.getElementById('mp-tfar').value||20;
  _mp.idratazione = +document.getElementById('mp-idr').value||62;
  _mp.step=3; _mpReRender();
};
function _mpReRender(){ var b=document.getElementById('vista-body'); if(b){ b.innerHTML=_mpRender(); b.scrollTop=0; } }
window._mpReRender = _mpReRender;
window._mp = _mp;

window._mpGeneraRicetta = function(){
  var t=_MP_TIPI[_mp.tipo], m=_MP_METODI[_mp.metodo];
  var richiesta = t.nome+' con metodo '+m.nome+', '+_mp.n_panetti+' panetti da '+_mp.peso_panetto+'g, idratazione '+_mp.idratazione+'%';
  if(typeof _generaRicettaAsync==='function'){ chiudiVista(); _generaRicettaAsync(richiesta, 'Creo la ricetta…', false, 'panificazione'); }
};
window._mpChiediChat = function(){
  var t=_MP_TIPI[_mp.tipo], m=_MP_METODI[_mp.metodo];
  _ctxChat = { ricetta:{ nome:t.nome+' ('+m.nome+')', ingredienti:[], punto_critico:'idratazione '+_mp.idratazione+'%, metodo '+m.nome } };
  chiudiVista();
  switchTab('chiedi'); if(typeof switchSubtab==='function') switchSubtab('chat');
  setTimeout(function(){ if(typeof chiediTesto==='function') chiediTesto('Come gestisco un impasto '+t.nome+' con '+m.nome+' al '+_mp.idratazione+'% di idratazione?'); }, 200);
};
})();
