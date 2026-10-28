# ============================================================
# IMPORTA-COMPOSTI — porta il dataset proprietario (data/composti_matter.json)
# nel grafo: aggancia ogni composto al nodo 'Composto' ESISTENTE (cosi' il pairing
# lo condivide con gli altri ingredienti), crea i nodi mancanti, e scrive gli archi
# contiene_composto con la provenienza (descrittore, ruolo, concentrazione, fonte, stato).
#
# Perche' cosi': il pairing (_base_aromatica) collega gli ingredienti per NODO-COMPOSTO
# CONDIVISO (stesso to_id). Se creassimo composti nuovi a parte, i nuovi ingredienti
# resterebbero isolati. Quindi: match per nome sul nodo Composto esistente; crea solo se
# davvero non c'e'.
#
# Nodo ingrediente:
#  - se esiste gia' un nodo canonico con composti (es. ahn_lemon per 'limone') -> lo ARRICCHISCE.
#  - se non esiste o e' sbagliato/vuoto (ginepro, lime, rosa, lavanda...) -> crea ing-<slug>.
#
# Sicurezza: _admin_ok, DRY-RUN di default (mostra il tasso di aggancio e cosa farebbe),
# scrive solo con &esegui=1. Idempotente: ON CONFLICT sugli archi, nodi upsert.
#
# Uso:  /admin/importa-composti?s=SECRET        (anteprima)
#       /admin/importa-composti?s=SECRET&esegui=1   (scrive)
# ============================================================
import os, json, re, traceback
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn
from routes.admin import _admin_ok

bp_importa_composti = Blueprint("importa_composti", __name__)

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "composti_matter.json")

# Ingredienti che NON vanno agganciati a un nodo esistente ma creati/corretti ( id forzato).
# Ginepro: il nodo attuale (ahn_juniperus_sabina) e' la specie sbagliata e vuoto.
# Lime: il nodo attuale (ahn_kaffir_lime) e' una varieta' diversa.
_FORZA_NODO = {"ginepro": "ing-ginepro", "lime": "ing-lime",
               "issopo": "ing-issopo",  # Hyssopus officinalis != ahn_anise_hyssop (Agastache, specie diversa)
               "mirtillo rosso": "ing-mirtillo-rosso",  # Vaccinium macrocarpon != ahn_european_cranberry (specie diversa)
               "mirtillo rosso europeo": "ing-mirtillo-rosso-europeo",  # Vaccinium vitis-idaea (lingonberry): nodo distinto, specie diversa da macrocarpon
               "fava": "ing-fava",  # Vicia faba != fava tonka (ahn_tonka_bean_seed): evita collisione per substring
               "finger lime": "ing-finger-lime",   # contiene 'lime' -> evita collisione con ing-lime
               "cime di rapa": "ing-cime-di-rapa", # contiene 'rapa' -> evita collisione con ing-rapa
               "grani del paradiso": "ing-grani-del-paradiso",  # pinna su ing-: esisteva anche ai_grani_del_paradiso (nodo doppio, frammentava i pairing)
               "sudachi": "ing-sudachi",  # pinna su ing-: esisteva anche ai_sudachi (nodo doppio)
               "semi di zucca": "ing-semi-di-zucca"}  # contiene 'zucca' -> evita collisione con ahn_pumpkin


def _norm(s):
    """Normalizza un nome composto per il match: minuscolo, togli parentesi, separatori -> spazio."""
    s = (s or "").lower().strip()
    s = re.sub(r"\(.*?\)", "", s)          # togli "(citrale)", "(methyl chavicol)" ecc.
    s = s.split(" / ")[0]                   # "delta-octalactone / gamma-nonalactone" -> primo
    s = s.replace("-", " ").replace("_", " ")
    s = re.sub(r"[^a-z0-9, ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _slug(s):
    s = _norm(s).replace(",", "").replace(" ", "-")
    return re.sub(r"-+", "-", s).strip("-")


# sinonimi comune -> forma come salvata nel grafo (nomi sistematici verificati nel vocabolario reale)
_SINONIMI = {
    "furaneol": "4 hydroxy 2 5 dimethyl 3 2h furanone",
    "hdmf": "4 hydroxy 2 5 dimethyl 3 2h furanone",
    "eucalyptol": "1 8 cineole",
    "diacetyl": "2 3 butanedione",
    "raspberry ketone": "4 4 hydroxyphenyl butan 2 one",
    "citral": "geranial",
}


def _candidati(nome):
    """Genera i nomi-candidato normalizzati per un composto: gestisce nomi combinati
    (2-/3-, 'a / b'), sinonimi, e la forma base. Ritorna una lista ordinata, piu' specifico prima."""
    cand = []
    def add(x):
        x = _norm(x)
        if x and x not in cand:
            cand.append(x)
    grezzo = (nome or "").lower()
    # 1) nome pieno normalizzato
    add(nome)
    # 2) split su ' / '  (es. "delta-octalactone / gamma-nonalactone")
    for p in re.split(r"\s*/\s*", nome):
        add(p)
    # 3) combinati "2-/3-metilX" -> "2 metilX" e "3 metilX"
    m = re.match(r"\s*([0-9]+)\s*[-,/]\s*([0-9]+)\s*[- ](.+)", grezzo)
    if m:
        add(m.group(1) + " " + m.group(3))
        add(m.group(2) + " " + m.group(3))
    # 4) sinonimi (match sulla forma normalizzata del nome pieno o del primo pezzo)
    nfull = _norm(nome)
    for k, v in _SINONIMI.items():
        if k in nfull:
            add(v)
    return cand


def _trova_composto(cur, nome):
    """Trova il nodo Composto esistente che matcha questo nome, provando piu' candidati.
    Ritorna id o None."""
    for n in _candidati(nome):
        if len(n) < 3:
            continue
        # match a parola intera sul name normalizzato del nodo
        cur.execute("""SELECT id FROM nodes WHERE type='Composto'
                       AND regexp_replace(lower(name), '[^a-z0-9 ]', ' ', 'g') ~ ('(^| )' || %s || '( |$)')
                       ORDER BY length(name) ASC LIMIT 1""", (re.escape(n),))
        r = cur.fetchone()
        if r:
            return r[0]
    # fallback prudente: primo token lungo del nome principale
    primo = _norm(nome).split(" ")[0]
    if len(primo) >= 6:
        cur.execute("""SELECT id FROM nodes WHERE type='Composto' AND lower(name) LIKE %s
                       ORDER BY length(name) ASC LIMIT 1""", (primo + "%",))
        r = cur.fetchone()
        if r:
            return r[0]
    return None


def _trova_ingrediente_esistente(cur, nome):
    """Nodo ingrediente canonico esistente CON composti (da arricchire). None se non c'e'."""
    ing = (nome or "").strip().lower()
    cur.execute("""SELECT n.id FROM nodes n
                   JOIN edges e ON e.from_id=n.id AND e.relation='contiene_composto'
                   WHERE n.type IN ('Ingrediente','Prodotto')
                     AND (lower(n.name)=%s OR n.id=%s)
                   GROUP BY n.id HAVING COUNT(e.to_id) > 0
                   ORDER BY (n.id LIKE 'ahn_%%') DESC, COUNT(e.to_id) DESC LIMIT 1""",
                (ing, "ahn_" + ing.replace(" ", "_")))
    r = cur.fetchone()
    return r[0] if r else None


@bp_importa_composti.route("/admin/importa-composti")
def importa_composti():
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    esegui = request.args.get("esegui") in ("1", "true", "si", "yes")
    try:
        dati = json.load(open(_PATH, encoding="utf-8"))
    except Exception as e:
        return jsonify({"errore": "dataset non leggibile: " + str(e)[:150]}), 500

    conn = _get_conn()
    try:
        cur = conn.cursor()
        tot_comp = 0
        agganciati = 0
        creati_comp = 0
        archi = 0
        nodi_ing_creati = 0
        nodi_ing_arricchiti = 0
        per_ingrediente = []

        for ing in dati.get("ingredienti", []):
            nome = ing.get("ingrediente", "")
            composti = ing.get("composti", [])
            # --- nodo ingrediente target ---
            forzato = _FORZA_NODO.get(nome.lower())
            if forzato:
                nid = forzato
                azione = "creato/corretto"
                if esegui:
                    cur.execute("""INSERT INTO nodes (id,type,name,domain,data)
                                   VALUES (%s,'Ingrediente',%s,%s,%s)
                                   ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, data=EXCLUDED.data""",
                                (nid, nome, ing.get("dominio", ""),
                                 json.dumps({"specie": ing.get("specie", ""), "origine": "matter_dataset",
                                             "nota": ing.get("CORREGGE") or ing.get("nota") or ""}, ensure_ascii=False)))
                    nodi_ing_creati += 1
            else:
                esistente = _trova_ingrediente_esistente(cur, nome)
                if esistente:
                    nid = esistente
                    azione = "arricchito (" + nid + ")"
                    if esegui:
                        nodi_ing_arricchiti += 1
                else:
                    nid = "ing-" + _slug(nome)
                    azione = "creato (nuovo)"
                    if esegui:
                        cur.execute("""INSERT INTO nodes (id,type,name,domain,data)
                                       VALUES (%s,'Ingrediente',%s,%s,%s)
                                       ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name""",
                                    (nid, nome, ing.get("dominio", ""),
                                     json.dumps({"specie": ing.get("specie", ""), "origine": "matter_dataset"}, ensure_ascii=False)))
                        nodi_ing_creati += 1

            # --- composti ---
            match_i = 0
            nuovi_i = 0
            for c in composti:
                tot_comp += 1
                cnome = c.get("composto", "")
                cid = _trova_composto(cur, cnome)
                if cid:
                    agganciati += 1
                    match_i += 1
                else:
                    cid = "comp_matter_" + _slug(cnome)
                    creati_comp += 1
                    nuovi_i += 1
                    if esegui:
                        cur.execute("""INSERT INTO nodes (id,type,name,domain,data)
                                       VALUES (%s,'Composto',%s,'chimica','{}')
                                       ON CONFLICT (id) DO NOTHING""", (cid, cnome))
                if esegui:
                    edata = json.dumps({"descrittore": c.get("descrittore"), "ruolo": c.get("ruolo"),
                                        "concentrazione": c.get("concentrazione"), "stato": c.get("stato"),
                                        "fonte": c.get("fonte"), "origine": "matter_dataset"}, ensure_ascii=False)
                    cur.execute("""INSERT INTO edges (from_id,to_id,relation,data)
                                   VALUES (%s,%s,'contiene_composto',%s)
                                   ON CONFLICT DO NOTHING""", (nid, cid, edata))
                    archi += 1

            per_ingrediente.append({"ingrediente": nome, "nodo": nid, "azione": azione,
                                    "composti": len(composti), "agganciati_esistenti": match_i, "nuovi": nuovi_i})

        if esegui:
            conn.commit()

        return jsonify({
            "modo": "SCRITTO" if esegui else "ANTEPRIMA (dry-run) — aggiungi &esegui=1 per scrivere",
            "ingredienti": len(dati.get("ingredienti", [])),
            "composti_totali": tot_comp,
            "agganciati_a_nodo_esistente": agganciati,
            "composti_nuovi_creati": creati_comp,
            "tasso_aggancio": (round(100.0 * agganciati / tot_comp, 1) if tot_comp else 0),
            "archi_scritti": archi if esegui else "(dry-run)",
            "nodi_ingrediente_creati": nodi_ing_creati if esegui else "(dry-run)",
            "nota": "tasso_aggancio alto = il pairing condividera' bene i composti coi ingredienti esistenti. "
                    "I 'nuovi' sono composti che non erano nel grafo: entrano ora, condivisi appena un altro ingrediente li usa.",
            "per_ingrediente": per_ingrediente,
        })
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({"errore": str(e)[:200], "trace": traceback.format_exc()[:400]}), 500
    finally:
        _release_conn(conn)
