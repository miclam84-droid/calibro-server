# ============================================================
# SCHEDA GUSTO — vetrina visibile del profilo sensoriale di un ingrediente
# Due parti:
#  1) /v1/profilo-gusto/<nome>  -> JSON: {nome, proprieta, proprieta_meta} letto dal nodo
#  2) /scheda-gusto/<nome>      -> pagina (design congelato) che lo rende con badge di provenienza
# Grammatica (SPEC-DESIGN): provenienza visibile per asse (derivato/stimato/non mappato),
# "non mappato" MAI sostituito con zero. derivato = verde pieno; stimato = ocra desaturato.
# ============================================================
import os
import json

from flask import Blueprint, jsonify, Response, redirect

bp_scheda = Blueprint("scheda_gusto", __name__)

ASSI = ["dolce", "salato", "acido", "amaro", "umami", "grasso", "corposita",
        "croccante", "astringente", "piccante", "termico", "aroma_fresco",
        "aroma_caldo", "effervescenza", "fermentato", "alcolico"]


@bp_scheda.route("/v1/profilo-gusto/<path:nome>", methods=["GET"])
def profilo_gusto(nome):
    import psycopg2
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "no db"}), 400
    conn = None
    try:
        conn = psycopg2.connect(dburl)
        cur = conn.cursor()
        cur.execute("""SELECT name, data FROM nodes
                       WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name) LIKE LOWER(%s)
                       ORDER BY LENGTH(name) LIMIT 1""", (f"%{nome}%",))
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return jsonify({"trovato": False, "nome_cercato": nome})
        nome_reale, data = row
        dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
        return jsonify({
            "trovato": True,
            "nome": nome_reale,
            "proprieta": dd.get("proprieta", {}) or {},
            "proprieta_meta": dd.get("proprieta_meta", {}) or {},
            "origine": dd.get("origine", ""),
            "kind": dd.get("kind", ""),
        })
    except Exception as e:
        try:
            if conn: conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:150]}), 500


_PAGE = """<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Scheda · Matter</title>
<link href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@600;700;800&family=Hanken+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--ink:#1D2A22;--muted:#4A5B50;--ink-soft:#4A5B50;--verde:#1E593C;--seg:#2F8A5F;--segnale:#2F8A5F;
--ocra:#A9802F;--oxblood:#A8504A;--tint:rgba(47,138,95,.10);--riga:rgba(29,42,34,.12);
--disp:'Schibsted Grotesk';--read:'Hanken Grotesk';
--sans:'Hanken Grotesk',ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;
--r:20px;--r-sm:13px;--r-pill:999px}
*{box-sizing:border-box;margin:0}
body{font-family:var(--read);color:var(--ink);
background:linear-gradient(165deg,#F3F5EF 0%,#E4EDE3 60%,#D3E1D5 100%);min-height:100vh;
padding:18px 16px 48px;overflow-x:hidden}
.wrap{max-width:620px;margin:0 auto}
/* barra in alto: wordmark + occhiello; lo switcher lingua si monta qui da solo */
.topbar-in{display:flex;align-items:center;gap:12px;margin-bottom:14px}
.wm{display:inline-flex;align-items:baseline;gap:5px;font-family:var(--disp);font-weight:700;
font-size:18px;letter-spacing:-.01em;color:var(--ink)}
.wm .bench{background:var(--verde);color:#fff;padding:2px 8px;border-radius:0;font-weight:700}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-soft);font-weight:600}
.top{display:flex;align-items:baseline;gap:10px;margin-bottom:4px}
.kick{font-family:var(--disp);font-weight:700;font-size:12px;color:var(--seg);letter-spacing:.04em;text-transform:uppercase}
h1{font-family:var(--disp);font-weight:800;font-size:30px;letter-spacing:-.02em;line-height:1.05;margin:6px 0 2px;text-transform:capitalize}
.sub{color:var(--muted);font-size:13px;margin-bottom:18px}
.card{background:rgba(255,255,255,.55);border:1px solid rgba(29,42,34,.08);border-radius:var(--r);padding:18px 18px 10px}
.row{display:grid;grid-template-columns:96px 1fr 70px;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid rgba(29,42,34,.07)}
.row:last-child{border-bottom:none}
.lab{font-family:var(--disp);font-weight:600;font-size:13px;text-transform:capitalize}
.track{height:9px;border-radius:999px;background:rgba(29,42,34,.08);position:relative;overflow:hidden}
.fill{position:absolute;left:0;top:0;bottom:0;border-radius:999px}
.fill.derivato{background:var(--seg)}
.fill.stimato{background:var(--ocra);opacity:.5}
.val{text-align:right;font-variant-numeric:tabular-nums;font-weight:700;font-size:14px}
.badge{display:inline-block;font-family:var(--disp);font-weight:700;font-size:9.5px;letter-spacing:.03em;
text-transform:uppercase;padding:2px 7px;border-radius:6px;margin-left:7px;vertical-align:1px}
.b-der{background:rgba(47,138,95,.16);color:var(--verde)}
.b-sti{background:rgba(169,128,47,.16);color:#8a6a28}
/* riga sobria dei non mappati: l'onestà resta (si dice cosa non c'è), ma non è più un muro grigio */
.nonmap{margin:12px 2px 0;font-size:12px;color:var(--muted);line-height:1.5}
.nonmap b{font-weight:600;color:var(--ink-soft);text-transform:capitalize}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin:16px 2px 0;font-size:12px;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.dot{width:10px;height:10px;border-radius:3px;display:inline-block;flex:0 0 auto}
.nota{font-size:11.5px;color:var(--muted);margin-top:14px;line-height:1.5}
.src{font-size:10.5px;color:var(--muted)}
.ph{color:var(--muted);text-align:center;padding:30px 0}
.foto-box{margin:2px 0 16px}
.foto-box img{display:block;width:100%;max-height:220px;object-fit:cover;border-radius:var(--r);border:1px solid rgba(29,42,34,.08)}
.foto-cred{font-size:10.5px;color:var(--muted);margin-top:5px}
.search{display:flex;gap:8px;margin-bottom:18px}
.search input{flex:1;min-width:0;font-family:var(--read);font-size:16px;padding:10px 13px;border-radius:var(--r-sm);
border:1px solid rgba(29,42,34,.15);background:rgba(255,255,255,.7)}
.search button{font-family:var(--disp);font-weight:700;font-size:13px;color:#fff;background:var(--verde);
border:none;border-radius:var(--r-sm);padding:0 16px;cursor:pointer}
</style></head>
<body><div class="wrap">
<div class="topbar-in">
  <span class="wm">Matter<span class="bench">Bench</span></span>
  <span class="eyebrow" data-i18n="kick_top">scheda</span>
</div>
<div class="search">
  <input id="q" data-i18n-ph="cerca_ph" placeholder="cerca un ingrediente (es. parmigiano)" />
  <button onclick="vai()" data-i18n="cerca_btn">Cerca</button>
</div>
<div id="out"><div class="ph" data-i18n="ph_iniziale">Scrivi un ingrediente e premi Cerca.</div></div>
</div>

<!-- i18n (it · en · es) — dizionario di pagina + motore condiviso (prima dell'IIFE: serve _L) -->
<script>
window.I18N_TITLE = {it:"Scheda · Matter", en:"Profile · Matter", es:"Ficha · Matter"};
window.I18N_DICT = {
  kick_top:   {it:"scheda", en:"profile", es:"ficha"},
  cerca_ph:   {it:"cerca un ingrediente (es. parmigiano)", en:"search an ingredient (e.g. parmesan)", es:"busca un ingrediente (p. ej. parmesano)"},
  cerca_btn:  {it:"Cerca", en:"Search", es:"Buscar"},
  ph_iniziale:{it:"Scrivi un ingrediente e premi Cerca.", en:"Type an ingredient and press Search.", es:"Escribe un ingrediente y pulsa Buscar."}
};
</script>
<script src="/static/i18n-nuovo.js"></script>

<script>
var ASSI=["dolce","salato","acido","amaro","umami","grasso","corposita","croccante","astringente","piccante","termico","aroma_fresco","aroma_caldo","effervescenza","fermentato","alcolico"];
/* nomi degli assi tradotti (gli ingredienti NO). Chiave = asse del backend. */
var ASSI_ETI={
  dolce:{it:"dolce",en:"sweet",es:"dulce"},
  salato:{it:"salato",en:"salty",es:"salado"},
  acido:{it:"acido",en:"sour",es:"ácido"},
  amaro:{it:"amaro",en:"bitter",es:"amargo"},
  umami:{it:"umami",en:"umami",es:"umami"},
  grasso:{it:"grasso",en:"fat",es:"graso"},
  corposita:{it:"corposità",en:"body",es:"cuerpo"},
  croccante:{it:"croccante",en:"crunchy",es:"crujiente"},
  astringente:{it:"astringente",en:"astringent",es:"astringente"},
  piccante:{it:"piccante",en:"spicy",es:"picante"},
  termico:{it:"termico",en:"thermal",es:"térmico"},
  aroma_fresco:{it:"aroma fresco",en:"fresh aroma",es:"aroma fresco"},
  aroma_caldo:{it:"aroma caldo",en:"warm aroma",es:"aroma cálido"},
  effervescenza:{it:"effervescenza",en:"effervescence",es:"efervescencia"},
  fermentato:{it:"fermentato",en:"fermented",es:"fermentado"},
  alcolico:{it:"alcolico",en:"alcoholic",es:"alcohólico"}
};
function eti(a){ return (window._L && ASSI_ETI[a]) ? _L(ASSI_ETI[a]) : a; }
var _ultima=null; // ultima risposta, per ri-render al cambio lingua senza refetch
function vai(){var v=document.getElementById('q').value.trim();if(v)location.hash=encodeURIComponent(v);}
document.getElementById('q').addEventListener('keydown',function(e){if(e.key==='Enter')vai();});
function pct(asse,val){ if(asse==='termico'){return ((val+10)/20*100);} return (val/10*100); }
function render(d){
  _ultima=d;
  var out=document.getElementById('out');
  if(!d.trovato){
    out.innerHTML='<div class="ph">'+_L({it:'Nessun ingrediente trovato per ',en:'No ingredient found for ',es:'Ningún ingrediente encontrado para '})+'"'+esc(d.nome_cercato||'')+'".</div>';
    return;
  }
  var prop=d.proprieta||{}, meta=d.proprieta_meta||{};
  // DATA-FIRST: prima gli assi CON un dato (in ordine canonico), poi i non mappati compressi in una riga.
  var mappati=[], nonMap=[];
  ASSI.forEach(function(a){
    if(!(a in prop) || prop[a]===null){ nonMap.push(a); } else { mappati.push(a); }
  });
  var righe=mappati.map(function(a){
    var lab=eti(a);
    var v=prop[a]; var st=(meta[a]&&meta[a].stato)||'stimato';
    var cls=(st==='derivato')?'derivato':'stimato';
    var badge=(st==='derivato')
      ?'<span class="badge b-der">'+_L({it:'derivato',en:'derived',es:'derivado'})+'</span>'
      :'<span class="badge b-sti">'+_L({it:'stimato',en:'estimated',es:'estimado'})+'</span>';
    var src=(meta[a]&&meta[a].fonte)?('<div class="src">'+esc(meta[a].fonte)+(meta[a].grezzo!=null?(' \\u00b7 '+esc(String(meta[a].grezzo))):'')+'</div>'):'';
    return '<div class="row"><div class="lab">'+lab+badge+'</div>'+
      '<div><div class="track"><div class="fill '+cls+'" style="width:'+Math.max(0,Math.min(100,pct(a,v)))+'%"></div></div>'+src+'</div>'+
      '<div class="val">'+v+'</div></div>';
  }).join('');
  var corpoCard;
  if(mappati.length){
    corpoCard='<div class="card">'+righe+'</div>';
  }else{
    corpoCard='<div class="card"><div class="ph">'+_L({it:'Nessun asse del gusto mappato per questo ingrediente.',en:'No taste axis mapped for this ingredient.',es:'Ningún eje del sabor mapeado para este ingrediente.'})+'</div></div>';
  }
  var nonMapHtml='';
  if(nonMap.length){
    var nomi=nonMap.map(function(a){return '<b>'+esc(eti(a))+'</b>';}).join(', ');
    nonMapHtml='<div class="nonmap">'+_L({it:'Non mappati: ',en:'Not mapped: ',es:'No mapeados: '})+nomi+'.</div>';
  }
  var sub=(d.origine?(_L({it:'origine: ',en:'origin: ',es:'origen: '})+esc(d.origine)+' \\u00b7 '):'')+
    _L({it:'scala 0–10 \\u00b7 termico da −10 a +10',en:'scale 0–10 \\u00b7 thermal from −10 to +10',es:'escala 0–10 \\u00b7 térmico de −10 a +10'});
  out.innerHTML='<div class="top"><span class="kick">'+_L({it:'Profilo del gusto',en:'Taste profile',es:'Perfil de sabor'})+'</span></div>'+
    '<h1>'+esc(d.nome)+'</h1>'+
    '<div class="sub">'+sub+'</div>'+
    '<div class="foto-box" id="foto-box"></div>'+
    corpoCard+nonMapHtml+
    '<div class="legend"><span><i class="dot" style="background:#2F8A5F"></i>'+_L({it:'derivato (da misura compositiva, fonte citata per asse)',en:'derived (from compositional measurement, source cited per axis)',es:'derivado (de medida composicional, fuente citada por eje)'})+'</span>'+
    '<span><i class="dot" style="background:#A9802F;opacity:.5"></i>'+_L({it:'stimato (modello AI)',en:'estimated (AI model)',es:'estimado (modelo IA)'})+'</span>'+
    '<span><i class="dot" style="background:rgba(29,42,34,.12)"></i>'+_L({it:'non mappato',en:'not mapped',es:'no mapeado'})+'</span></div>'+
    '<div class="nota">'+_L({
      it:'I valori <b>derivati</b> sono calcolati da una formula dichiarata sulla composizione misurata; la fonte è citata su ogni asse. Non sono una misura sensoriale diretta: sono un indice compositivo, correggibile al banco. I valori <b>stimati</b> sono una valutazione del modello. Dove non c\\u2019è dato, si dichiara — non si inventa uno zero.',
      en:'<b>Derived</b> values are computed from a declared formula on the measured composition; the source is cited on each axis. They are not a direct sensory measurement: they are a compositional index, correctable at the bench. <b>Estimated</b> values are a model judgement. Where there is no data, it is declared — no zero is invented.',
      es:'Los valores <b>derivados</b> se calculan con una fórmula declarada sobre la composición medida; la fuente se cita en cada eje. No son una medida sensorial directa: son un índice composicional, corregible en la mesa de trabajo. Los valores <b>estimados</b> son una valoración del modelo. Donde no hay dato, se declara — no se inventa un cero.'
    })+'</div>';
  caricaFoto(d.nome);
}
function esc(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
// FOTO editoriale: SUPPORTO, non sostituisce nome/provenienza. Esce solo se trovata davvero,
// col credito sempre visibile. Se url null -> nessun box foto (niente placeholder finto).
function caricaFoto(nome){
  var box=document.getElementById('foto-box'); if(!box){return;}
  fetch('/v1/foto-ingrediente-nuovo/'+encodeURIComponent(nome)).then(function(r){return r.json();})
    .then(function(f){
      if(f&&f.url){
        var cr=f.credito?('<div class="foto-cred">'+esc(f.credito)+'</div>'):'';
        box.innerHTML='<img src="'+esc(f.url)+'" alt="'+esc(nome)+'" loading="lazy">'+cr;
      }
    }).catch(function(){});
}
function carica(){
  var h=decodeURIComponent((location.hash||'').replace(/^#/,''));
  if(!h){var m=location.pathname.match(/\\/scheda-gusto\\/(.+)$/);if(m&&m[1]){h=decodeURIComponent(m[1]);}}
  if(!h){return;}
  document.getElementById('q').value=h;
  document.getElementById('out').innerHTML='<div class="ph">'+((window._L)?_L({it:'Carico…',en:'Loading…',es:'Cargando…'}):'…')+'</div>';
  fetch('/v1/profilo-gusto/'+encodeURIComponent(h)).then(function(r){return r.json();})
    .then(render).catch(function(){document.getElementById('out').innerHTML='<div class="ph">'+_L({it:'Errore di rete.',en:'Network error.',es:'Error de red.'})+'</div>';});
}
// al cambio lingua: ri-rende l'ultima scheda (senza refetch) così assi/legenda/nota si traducono
window.onI18nApply=function(){ if(_ultima) render(_ultima); };
window.addEventListener('hashchange',carica); carica();
</script>
</body></html>"""


@bp_scheda.route("/scheda-gusto/", defaults={"nome": ""})
@bp_scheda.route("/scheda-gusto/<path:nome>")
def scheda_gusto_page(nome):
    # Pagina orfana dopo PR #266 (Componi ricollegato al lab): la vecchia scheda
    # con skin propria e zero navigazione di ritorno era una trappola. Il perno
    # ora e' il dettaglio-ingrediente /lab/<nome>. Reindirizziamo la', senza
    # toccare l'endpoint dati /v1/profilo-gusto/<nome>, ancora usato da Componi.
    nome = (nome or "").strip()
    if not nome:
        return redirect("/nuovo", code=302)
    return redirect("/lab/" + nome, code=302)
