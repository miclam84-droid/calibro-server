// ═══ MATTER-SCALA.js — la Scala Graduata: la firma di Matter (più del logo) ═══
// Il bersaglio come FINESTRA, non numero. Una grammatica visiva unica per ogni tipo.
(function(){
  // range di default per tipo di misura (per posizionare la finestra sensatamente)
  var _RANGE={
    '°C':[0,120],'°c':[0,120],'C':[0,120],
    '%':[0,100],
    'pH':[0,14],'ph':[0,14],
    'min':[0,120],'h':[0,72],'ore':[0,72],
    '°Bx':[0,70],'Brix':[0,70],'brix':[0,70],
    'g/L':[0,200],'g':[0,500]
  };
  // costruisce la scala graduata come HTML+SVG. bersaglio = {valore, unita}, label opzionale
  window.dsScala = function(bersaglio, label){
    if(!bersaglio || bersaglio.valore==null || bersaglio.valore==='') return '';
    var e=(window._escV||function(x){return String(x==null?'':x);});
    var unita=String(bersaglio.unita||'');
    // il valore può essere "25" o un range "60-80"
    var raw=String(bersaglio.valore).replace(',', '.');
    var nums=(raw.match(/-?\d+\.?\d*/g)||[]).map(Number);
    if(!nums.length) return '';
    var vmin=nums[0], vmax=nums.length>1?nums[1]:nums[0];
    var range=_RANGE[unita]||[Math.min(0,vmin-Math.abs(vmin)), vmax+Math.abs(vmax||1)];
    var lo=range[0], hi=range[1];
    var span=(hi-lo)||1;
    var pctMin=Math.max(0,Math.min(100,((vmin-lo)/span)*100));
    var pctMax=Math.max(0,Math.min(100,((vmax-lo)/span)*100));
    var winL=pctMin, winW=Math.max(3,pctMax-pctMin);
    // tacche (10 segni)
    var ticks='';
    for(var i=1;i<10;i++){ ticks+='<div class="ds-scala-tick" style="left:'+(i*10)+'%"></div>'; }
    var valTxt = nums.length>1 ? (vmin+'–'+vmax) : String(vmin);
    var centro = winL + winW/2;
    // il valore va sopra la finestra se c'è spazio a sx, altrimenti a dx (mai sovrapposto alle tacche)
    var valPos = centro<15 ? 'left:'+(winL+winW)+'%;transform:translate(6px,-50%)' : (centro>85 ? 'left:'+winL+'%;transform:translate(-100%,-50%);padding-right:6px' : 'left:'+centro+'%;transform:translate(-50%,-50%)');
    return '<div class="ds-scala">'
      + (label?'<div class="ds-scala-lab">◎ '+e(label)+'</div>':'')
      + '<div class="ds-scala-track">'+ticks
      +   '<div class="ds-scala-finestra" style="left:'+winL+'%;width:'+winW+'%"></div>'
      +   '<div class="ds-scala-valore" style="'+valPos+'">'+e(valTxt)+(unita?'<span style="font-size:11px;color:var(--ds-rame);margin-left:3px">'+e(unita)+'</span>':'')+'</div>'
      + '</div>'
      + '<div class="ds-scala-cap"><span>'+lo+'</span><span>'+hi+(unita?' '+e(unita):'')+'</span></div>'
      + '</div>';
  };
  // badge epistemico dal campo stato_epistemico (o dedotto da verificato)
  window.dsBadge = function(stato, verificato){
    var s=(stato||'').toLowerCase();
    if(!s){ s = verificato===true?'verificato':(verificato===false?'esperimento':'esperimento'); }
    var _LAB={canon:'Canon',verificato:'Verificato',scoperta:'Scoperta',esperimento:'Esperimento'};
    if(!_LAB[s]) s='esperimento';
    return '<span class="ds-badge ds-badge-'+s+'">'+_LAB[s]+'</span>';
  };
  // chip sensore (vista/tatto/olfatto...) — la tastiera di Matter
  window.dsSensore = function(tipo, testo){
    var e=(window._escV||function(x){return String(x==null?'':x);});
    var _ICO={vista:'◠',tatto:'▚',olfatto:'∿',udito:'≋',suono:'≋',gusto:'•'};
    if(!testo) return '';
    return '<span class="ds-sensore"><span class="ds-sensore-ico">'+(_ICO[tipo]||'◦')+'</span>'+e(testo)+'</span>';
  };
})();
