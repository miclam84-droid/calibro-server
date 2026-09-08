// ═══ MATTER-MENU.js — modulo (lazy, Strangler) ═══
(function(){
window.apriSceltaMenu = function(){
  var tipi=[
    {cat:'pizzeria',    ico:_DISC_ICONE.panificazione, nome:'Pizzeria',    sub:'Pizze e impasti'},
    {cat:'ristorante',  ico:_DISC_ICONE.cucina,        nome:'Ristorante',  sub:'Piatti di cucina'},
    {cat:'pasticceria', ico:_DISC_ICONE.pasticceria,   nome:'Pasticceria', sub:'Dolci e lievitati'},
    {cat:'drink_list',  ico:_DISC_ICONE.bar,           nome:'Drink list',  sub:'Cocktail e miscelati'},
    {cat:'carta_vini',  ico:_DISC_ICONE.vino,          nome:'Carta dei vini', sub:'Selezione con filo conduttore'},
    {cat:'carta_birre', ico:_DISC_ICONE.birra,         nome:'Carta delle birre', sub:'Selezione birre'}
  ];
  var e=_escV;
  var cards=tipi.map(function(t){
    return '<button class="crea-card" onclick="mbScegliCategoria(\''+e(t.cat)+'\',\''+e(t.nome)+'\')">'
      + '<div class="crea-card-ico" style="font-size:22px;display:flex;align-items:center;justify-content:center">'+t.ico+'</div>'
      + '<div class="crea-card-txt"><div class="crea-card-t">'+e(t.nome)+'</div><div class="crea-card-d">'+e(t.sub)+'</div></div>'
      + '<span class="crea-card-arr">→</span></button>';
  }).join('');
  _apriVista('Crea un menu',
    '<div class="crea-intro">Che menu vuoi creare? Ogni tipo porta con sé i numeri-bersaglio della sua disciplina.</div>'
    + cards);
}

window.caricaMenuSalvati = function(){
  // v1: i menù stanno in localStorage (poi sync backend/Cifra in v2)
  const list = document.getElementById('menu-list');
  let menus = [];
  try { menus = JSON.parse(localStorage.getItem('matter_menus')||'[]'); } catch(e){}
  if(!menus.length){ list.innerHTML=''; return; }
  list.innerHTML = '<div class="menu-list-lab">I tuoi menù</div>' + menus.map((m,i)=>
    `<div class="menu-card" onclick="apriMenu(${i})">
      <div class="menu-card-nome">${_esc(m.nome||'Drink list')}</div>
      <div class="menu-card-meta">${(m.voci||[]).length} voci · ${m.tipo||'drink list'}</div>
    </div>`).join('');
}

window.mbScegliCategoria = function(cat, label){
  _mbCategoria = cat;
  _mbCategoriaLabel = label;
  document.getElementById('mm-title').textContent = label;
  document.getElementById('mm-cat-lab').textContent = label;
  var _onb=document.getElementById('onb-overlay'); if(_onb) _onb.classList.add('hidden');
  // carta vini: passa dalla FILOSOFIA (brief → filo conduttore → crea)
  if(cat==='carta_vini'){ apriCartaFilosofia(); return; }
  // carta birre: dritto al builder
  if(cat==='carta_birre'){ creaMenu(); return; }
  document.getElementById('menu-modo').classList.remove('hidden');
}

window.mbAvanti = function(){
  if(_mbStep===1){
    const nome = document.getElementById('mb-nome').value.trim();
    if(!nome){ document.getElementById('mb-nome').focus(); return; }
    _mbMostraStep(2);
  } else if(_mbStep===2){
    if(!_mbVoci.length){ alert(_L({it:'Aggiungi almeno una voce alla carta.',en:'Add at least one item to the menu.',es:'Añade al menos un elemento a la carta.'})); return; }
    _mbMostraStep(3);
  }
}

window.mbToggleVoce = function(src, nome, target, verificato){
  const idx = _mbVoci.findIndex(v=>v._src===src);
  if(idx>=0) _mbVoci.splice(idx,1);
  else _mbVoci.push({_src:src, nome, target, stato: verificato?'verified':'unverified'});
  _mbCaricaValidati();
}

window.mbAggiungiManuale = function(){
  const nome = prompt('Nome della voce (es. Negroni Sbagliato):');
  if(!nome||!nome.trim()) return;
  _mbVoci.push({_src:'man'+Date.now(), nome:nome.trim(), target:'', stato:'unverified'});
  _mbCaricaValidati();
}

window.mbScegliTemplate = function(t){
  _mbTemplate = t;
  document.querySelectorAll('.mb-tpl').forEach(b=> b.classList.toggle('active', b.dataset.tpl===t));
}

window.mbGenera = function(){
  const nome = document.getElementById('mb-nome').value.trim();
  const locale = document.getElementById('mb-locale').value.trim();
  const menu = {nome, locale, tipo:_mbCategoriaLabel, categoria:_mbCategoria, template:_mbTemplate, voci:_mbVoci, creato: Date.now()};
  // salvo in localStorage (v1)
  let menus = [];
  try { menus = JSON.parse(localStorage.getItem('matter_menus')||'[]'); } catch(e){}
  menus.unshift(menu);
  localStorage.setItem('matter_menus', JSON.stringify(menus));
  chiudiBuilder();
  apriAnteprima(menu);
}

window.apriCartaFilosofia = function(){
  _apriVista('La tua carta dei vini',
    '<div class="cf-intro">Prima dei vini, il <b>filo conduttore</b>. Raccontami il locale: Matter Bench costruisce la filosofia che tiene insieme la carta.</div>'
    + '<div class="calc-form">'
    + '<div class="calc-field"><label>Che locale è (vibe)</label><input type="text" id="cf-vibe" placeholder="es. bistrot di mare, osteria moderna…"></div>'
    + '<div class="calc-field"><label>Territorio</label><input type="text" id="cf-terr" placeholder="es. Costiera Amalfitana, Langhe…"></div>'
    + '<div class="calc-field"><label>Filo conduttore</label><input type="text" id="cf-filo" placeholder="es. agrumi e affumicato, montagna e selvaggina…"></div>'
    + '<div class="calc-field"><label>Tema grafico del PDF</label><select id="cf-tema" class="calc-select">'
    +   '<option value="enoteca-classica">Enoteca classica (elegante)</option>'
    +   '<option value="minimal-blueprint">Minimal blueprint (tecnico)</option>'
    +   '<option value="gastro-bistrot">Gastro bistrot (moderno)</option>'
    + '</select></div>'
    + '<button class="calc-go" onclick="_generaFilosofia()">Genera il filo conduttore</button>'
    + '</div><div id="cf-out"></div>');
}

window.apriMenuBuilder = function(){
  _menuIngredienti = [];
  _apriVista('Menu Lab',
    '<div class="mbv-head"><div class="mbv-h">Costruisci per composti.</div>'+
    '<div class="mbv-sub">Aggiungi ingredienti: Matter Bench trova le combinazioni che dialogano, dal grafo aromatico reale.</div>'+
    '<div class="mbv-add"><input id="mbv-input" placeholder="aggiungi un ingrediente…" onkeydown="if(event.key===\'Enter\')mbAdd()"><button onclick="mbAdd()">+</button></div>'+
    '<div class="mbv-chips" id="mbv-chips"></div>'+
    '<button class="mbv-go" id="mbv-go" onclick="mbProposte()" disabled>Trova le combinazioni</button></div>'+
    '<div id="mbv-out"></div>');
  _mbRenderChips();
}

})();
