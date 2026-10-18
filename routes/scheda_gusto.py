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

from flask import Blueprint, jsonify, Response

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
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scheda · Matter</title>
<link href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@600;700;800&family=Hanken+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--ink:#1D2A22;--muted:#4A5B50;--verde:#1E593C;--seg:#2F8A5F;--ocra:#A9802F;--oxblood:#A8504A;
--disp:'Schibsted Grotesk';--read:'Hanken Grotesk';--r:20px;--r-sm:13px}
*{box-sizing:border-box;margin:0}
body{font-family:var(--read);color:var(--ink);
background:linear-gradient(165deg,#F3F5EF 0%,#E4EDE3 60%,#D3E1D5 100%);min-height:100vh;
padding:22px 16px 48px}
.wrap{max-width:620px;margin:0 auto}
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
.nm{grid-column:2 / 4;color:var(--muted);font-size:12px;font-style:italic}
.badge{display:inline-block;font-family:var(--disp);font-weight:700;font-size:9.5px;letter-spacing:.03em;
text-transform:uppercase;padding:2px 7px;border-radius:6px;margin-left:7px;vertical-align:1px}
.b-der{background:rgba(47,138,95,.16);color:var(--verde)}
.b-sti{background:rgba(169,128,47,.16);color:#8a6a28}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin:16px 2px 0;font-size:12px;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.dot{width:10px;height:10px;border-radius:3px;display:inline-block}
.nota{font-size:11.5px;color:var(--muted);margin-top:14px;line-height:1.5}
.src{font-size:10.5px;color:var(--muted)}
.ph{color:var(--muted);text-align:center;padding:30px 0}
.foto-box{margin:2px 0 16px}
.foto-box img{display:block;width:100%;max-height:220px;object-fit:cover;border-radius:var(--r);border:1px solid rgba(29,42,34,.08)}
.foto-cred{font-size:10.5px;color:var(--muted);margin-top:5px}
.search{display:flex;gap:8px;margin-bottom:18px}
.search input{flex:1;font-family:var(--read);font-size:14px;padding:10px 13px;border-radius:var(--r-sm);
border:1px solid rgba(29,42,34,.15);background:rgba(255,255,255,.7)}
.search button{font-family:var(--disp);font-weight:700;font-size:13px;color:#fff;background:var(--verde);
border:none;border-radius:var(--r-sm);padding:0 16px;cursor:pointer}
</style></head>
<body><div class="wrap">
<div class="search">
  <input id="q" placeholder="cerca un ingrediente (es. parmigiano)" />
  <button onclick="vai()">Cerca</button>
</div>
<div id="out"><div class="ph">Scrivi un ingrediente e premi Cerca.</div></div>
</div>
<script>
var ASSI=["dolce","salato","acido","amaro","umami","grasso","corposita","croccante","astringente","piccante","termico","aroma_fresco","aroma_caldo","effervescenza","fermentato","alcolico"];
var ETI={corposita:"corposita'",aroma_fresco:"aroma fresco",aroma_caldo:"aroma caldo"};
function vai(){var v=document.getElementById('q').value.trim();if(v)location.hash=encodeURIComponent(v);}
document.getElementById('q').addEventListener('keydown',function(e){if(e.key==='Enter')vai();});
function pct(asse,val){ if(asse==='termico'){return ((val+10)/20*100);} return (val/10*100); }
function render(d){
  var out=document.getElementById('out');
  if(!d.trovato){out.innerHTML='<div class="ph">Nessun ingrediente trovato per "'+(d.nome_cercato||'')+'".</div>';return;}
  var prop=d.proprieta||{}, meta=d.proprieta_meta||{};
  var righe=ASSI.map(function(a){
    var lab=ETI[a]||a;
    if(!(a in prop) || prop[a]===null){
      return '<div class="row"><div class="lab">'+lab+'</div><div class="nm">non mappato</div></div>';
    }
    var v=prop[a]; var st=(meta[a]&&meta[a].stato)||'stimato';
    var cls=(st==='derivato')?'derivato':'stimato';
    var badge=(st==='derivato')?'<span class="badge b-der">derivato</span>':'<span class="badge b-sti">stimato</span>';
    var src=(meta[a]&&meta[a].fonte)?('<div class="src">'+meta[a].fonte+(meta[a].grezzo!=null?(' \\u00b7 '+meta[a].grezzo):'')+'</div>'):'';
    return '<div class="row"><div class="lab">'+lab+badge+'</div>'+
      '<div><div class="track"><div class="fill '+cls+'" style="width:'+Math.max(0,Math.min(100,pct(a,v)))+'%"></div></div>'+src+'</div>'+
      '<div class="val">'+v+'</div></div>';
  }).join('');
  out.innerHTML='<div class="top"><span class="kick">Profilo del gusto</span></div>'+
    '<h1>'+d.nome+'</h1>'+
    '<div class="sub">'+(d.origine?('origine: '+d.origine+' \\u00b7 '):'')+'scala 0-10 \\u00b7 termico da -10 a +10</div>'+
    '<div class="foto-box" id="foto-box"></div>'+
    '<div class="card">'+righe+'</div>'+
    '<div class="legend"><span><i class="dot" style="background:#2F8A5F"></i>derivato (da misura USDA)</span>'+
    '<span><i class="dot" style="background:#A9802F;opacity:.5"></i>stimato (modello AI)</span>'+
    '<span><i class="dot" style="background:rgba(29,42,34,.12)"></i>non mappato</span></div>'+
    '<div class="nota">I valori <b>derivati</b> sono calcolati da una formula dichiarata sulla composizione misurata (USDA), non sono una misura sensoriale diretta: sono un indice compositivo, correggibile al banco. I valori <b>stimati</b> sono una valutazione del modello. Dove non c\\'e dato, si dichiara - non si inventa uno zero.</div>';
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
  if(!h){return;}
  document.getElementById('q').value=h;
  document.getElementById('out').innerHTML='<div class="ph">Carico...</div>';
  fetch('/v1/profilo-gusto/'+encodeURIComponent(h)).then(function(r){return r.json();})
    .then(render).catch(function(){document.getElementById('out').innerHTML='<div class="ph">Errore di rete.</div>';});
}
window.addEventListener('hashchange',carica); carica();
</script>
</body></html>"""


@bp_scheda.route("/scheda-gusto/", defaults={"nome": ""})
@bp_scheda.route("/scheda-gusto/<path:nome>")
def scheda_gusto_page(nome):
    return Response(_PAGE, mimetype="text/html")
