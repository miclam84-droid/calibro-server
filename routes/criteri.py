# -*- coding: utf-8 -*-
# MOTORE CRITERI (Laboratorio) — modulo pulito, NON tocca api_abbina.
# Decisioni congelate 8 ott 2026 (DECISIONI-LABORATORIO-CONGELATE).
#
# Regola costituzionale:
#   Matter NON assegna un voto alla compatibilita'. Mostra PERCHE' una relazione esiste.
#   Sempre: numero reale -> criterio -> interpretazione. Mai: numero inventato -> percentuale -> verdetto.
#
# Criteri V1: 1 BASE AROMATICA (composti condivisi reali) + 4 TRADIZIONE (archi documentati).
#
# Fix sistematici dopo test su dati reali (8 ott, giro largo):
#  - RISOLUZIONE NODO: preferiva la variante piu' ricca di dati (manzo->"manzo arrosto", caffe->"caffe filtro"
#    con 0 composti, cipolla->"cipolla arrostita"). Ora preferisce l'ingrediente CANONICO ahn_, scarta le
#    varianti arrosto/affumicato/filtro, e richiede che abbia davvero dei composti.
#  - FLOOD VARIANTI-PRODOTTO: brisket, fiorentina, ossobuco, tomahawk inondavano ogni ingrediente perche'
#    sono nodi 'Prodotto' che copiano la chimica del padre. Ora si abbina solo con INGREDIENTI canonici.
#  - ROBUSTEZZA: la soglia assoluta dava "Alta" a tutto (basilico 10 = manzo 179). Ora e' RELATIVA al
#    miglior risultato di quell'ingrediente.
#  - COUNT(DISTINCT) + filtro firma + padre<>base: restano (archi doppi, varianti dello stesso ingrediente).

import os
from flask import Blueprint, jsonify, request
from db import connessione

bp = Blueprint("criteri", __name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

# IT -> nome Ahn canonico, per i casi che la risoluzione per nome sbagliava.
_ALIAS = {
    "caffe": "coffee", "caffè": "coffee", "cioccolato": "cocoa", "cacao": "cocoa",
    "manzo": "beef", "cipolla": "onion", "melanzana": "eggplant", "melanzane": "eggplant",
    "pomodoro": "tomato", "aglio": "garlic", "limone": "lemon", "lime": "lime",
    "fragola": "strawberry", "basilico": "basil", "gambero": "shrimp", "gamberi": "shrimp",
    "maiale": "pork", "pollo": "chicken", "mela": "apple", "pera": "pear",
    "vino": "wine", "vino bianco": "white_wine", "vino rosso": "red_wine", "birra": "beer",
    "arancia": "orange", "banana": "banana", "ananas": "pineapple", "mango": "mango",
    "zenzero": "ginger", "menta": "mint", "rosmarino": "rosemary", "timo": "thyme",
    "prezzemolo": "parsley", "salvia": "sage", "cannella": "cinnamon", "vaniglia": "vanilla",
    "burro": "butter", "panna": "cream", "latte": "milk", "uovo": "egg", "uova": "egg",
    "salmone": "salmon", "tonno": "tuna", "patata": "potato", "carota": "carrot",
    "funghi": "mushroom", "zucca": "pumpkin", "miele": "honey", "mandorla": "almond",
    "nocciola": "hazelnut", "cocco": "coconut", "peperoncino": "chili",
}

# varianti "preparate" da evitare quando l'utente cerca l'ingrediente base
_PREP_RX = r"roast|smoke|dried|dry|filter|grill|fried|cured|_oil"


def _nome_composto(cid):
    """comp_pub_1_octanol -> '1 octanol'. Toglie prefissi tecnici, non inventa traduzioni."""
    s = (cid or "").replace("comp_", "")
    if s.startswith("pub_"):
        s = s[4:]
    return s.replace("_", " ").strip()


# Le connessioni passano dalla porta unica del pool: db.connessione() (vedi PULIZIA-BACKEND-DIARIO).


def _risolvi_nodo(cur, ingrediente):
    """Trova il nodo CANONICO con la chimica. Preferisce: ingrediente base (non arrosto/filtro),
    nodo ahn_, match esatto di nome, e con composti veri (nc>0). Ritorna (id, nome_mostrato) o None."""
    ing = (ingrediente or "").strip().lower()

    # 1) alias diretto -> ahn_<name>, se esiste e ha composti
    alias = _ALIAS.get(ing)
    if alias:
        cur.execute(
            """SELECT n.id, n.name, COUNT(e.to_id) nc
               FROM nodes n LEFT JOIN edges e ON e.from_id=n.id AND e.relation='contiene_composto'
               WHERE n.id = %s GROUP BY n.id, n.name""",
            ("ahn_" + alias,),
        )
        r = cur.fetchone()
        if r and (r[2] or 0) > 0:
            return (r[0], ingrediente.strip())

    # 2) ricerca per nome/id, preferendo: non-preparato, canonico ahn_, match esatto, piu' ricco.
    cur.execute(
        r"""
        SELECT n.id, n.name,
               (CASE WHEN (n.id ~ %s) THEN 1 ELSE 0 END) AS prep,
               (CASE WHEN n.id LIKE 'ahn_%%' THEN 0 ELSE 1 END) AS noncanon,
               (CASE WHEN LOWER(n.name) = %s THEN 0 ELSE 1 END) AS nonexact,
               COUNT(e.to_id) AS nc
        FROM nodes n
        LEFT JOIN edges e ON e.from_id = n.id AND e.relation = 'contiene_composto'
        WHERE n.type IN ('Ingrediente','Prodotto')
          AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
          AND (LOWER(n.name) = %s OR LOWER(n.name) LIKE %s OR LOWER(n.id) = %s)
        GROUP BY n.id, n.name
        HAVING COUNT(e.to_id) > 0
        ORDER BY prep ASC, noncanon ASC, nonexact ASC, nc DESC, LENGTH(n.name) ASC
        LIMIT 1
        """,
        (_PREP_RX, ing, ing, f"%{ing}%", "ahn_" + ing.replace(" ", "_")),
    )
    r = cur.fetchone()
    if r:
        return (r[0], ingrediente.strip())

    # 3) fallback: nessun nodo con composti (es. melanzana, pochi volatili). Prendo comunque il
    #    miglior match, così la TRADIZIONE si vede lo stesso. base_aromatica tornerà vuota, onesto.
    cur.execute(
        """SELECT n.id, n.name FROM nodes n
           WHERE n.type IN ('Ingrediente','Prodotto')
             AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
             AND (LOWER(n.name) = %s OR LOWER(n.name) LIKE %s OR LOWER(n.id) = %s)
           ORDER BY (LOWER(n.name) = %s) DESC, LENGTH(n.name) ASC
           LIMIT 1""",
        (ing, f"%{ing}%", "ahn_" + ing.replace(" ", "_"), ing),
    )
    r = cur.fetchone()
    if r:
        return (r[0], ingrediente.strip())
    return None


def _base_aromatica(cur, ing_id, base_nome, limit=12, min_shared=3, pool=120):
    """Criterio 1: ingredienti che condividono composti volatili reali.
    - solo partner INGREDIENTE canonico (niente nodi 'Prodotto' = varianti/tagli che copiano la chimica);
    - COUNT(DISTINCT): il grafo ha archi doppi;
    - filtro firma aromatica: stessa firma di composti = di fatto stessa famiglia -> max 2;
    - robustezza RELATIVA al miglior risultato di questo ingrediente (la soglia assoluta non ha senso)."""
    cur.execute(
        r"""
        SELECT n.name,
               COUNT(DISTINCT b.to_id) AS shared,
               (array_agg(DISTINCT b.to_id ORDER BY b.to_id))[1:6] AS compounds
        FROM edges a
        JOIN edges b ON a.to_id = b.to_id AND b.relation = 'contiene_composto'
        JOIN nodes n ON n.id = b.from_id
        WHERE a.from_id = %s AND a.relation = 'contiene_composto'
          AND b.from_id <> %s
          AND n.type = 'Ingrediente'
          AND n.padre_ahn_id IS NULL
          AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
          AND n.name NOT LIKE '%%\_%%'
          AND LOWER(n.name) NOT LIKE LOWER(%s)
        GROUP BY n.name
        HAVING COUNT(DISTINCT b.to_id) >= %s
        ORDER BY shared DESC, n.name ASC
        LIMIT %s
        """,
        (ing_id, ing_id, f"%{base_nome}%", min_shared, pool),
    )
    rows = cur.fetchall()
    if not rows:
        return []
    max_n = max(int(r[1]) for r in rows) or 1
    out = []
    firma_count = {}
    for name, shared, compounds in rows:
        ids = list(compounds or [])
        firma = tuple(sorted(ids)[:5])
        if firma and firma_count.get(firma, 0) >= 2:
            continue  # stessa firma = stessa famiglia -> max 2
        firma_count[firma] = firma_count.get(firma, 0) + 1
        frac = int(shared) / max_n
        banda = "Alta" if frac >= 0.6 else ("Media" if frac >= 0.33 else "Esplorativa")
        comps = [_nome_composto(c) for c in ids]
        out.append({
            "ingrediente": name,
            "criterio": "base_aromatica",
            "evidenza": {"composti_condivisi": int(shared), "composti": comps},
            "robustezza": banda,
            "perche": "condivide una base aromatica"
                      + (f" — {shared} composti ({', '.join(comps[:3])})" if comps else f" — {shared} composti"),
        })
        if len(out) >= limit:
            break
    return out


def _tradizione(cur, ing_id, limit=6):
    """Criterio 4: accostamenti documentati. Etichettati come CULTURA, non come chimica."""
    out = []
    try:
        cur.execute(
            r"""
            SELECT DISTINCT n.name
            FROM edges e
            JOIN nodes n ON n.id = e.to_id
            WHERE e.from_id = %s AND e.relation = 'abbinamento_tradizionale'
              AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
              AND n.name NOT LIKE '%%\_%%'
            LIMIT %s
            """,
            (ing_id, limit),
        )
        for (name,) in cur.fetchall():
            out.append({
                "ingrediente": name,
                "criterio": "tradizione",
                "evidenza": {"tipo": "documentato"},
                "robustezza": None,
                "perche": "accostamento tradizionale documentato (cultura, non chimica)",
            })
    except Exception:
        pass
    return out


def _contrasto(cur, ing_id, limit=6):
    """Criterio: contrasto documentato (archi abbinamento_contrasto, bidirezionali).
    Relazione curata nel grafo, NON l'euristica fisico-chimica (quella richiede dati
    grassi/ph/amaro oggi non popolati — vedi mappa dati)."""
    out = []
    try:
        cur.execute(
            r"""
            SELECT DISTINCT n.name
            FROM edges e
            JOIN nodes n ON n.id = CASE WHEN e.from_id = %s THEN e.to_id ELSE e.from_id END
            WHERE (e.from_id = %s OR e.to_id = %s) AND e.relation = 'abbinamento_contrasto'
              AND n.id <> %s
              AND n.type IN ('Ingrediente', 'Prodotto')
              AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
              AND n.name NOT LIKE '%%\_%%'
            LIMIT %s
            """,
            (ing_id, ing_id, ing_id, ing_id, limit),
        )
        for (name,) in cur.fetchall():
            out.append({
                "ingrediente": name,
                "criterio": "contrasto",
                "evidenza": {"tipo": "documentato"},
                "robustezza": None,
                "perche": "contrasto documentato nel grafo (relazione curata, non euristica)",
            })
    except Exception:
        pass
    return out


# NOTA (3d, dietrofront verificato sui dati): i "sostituti" NON sono calcolabili dai soli composti
# aromatici. Test live: pomodoro -> te nero/patate (senza senso), parmigiano -> vuoto (ahn_parmesan ha
# 6 composti). La sostituibilita' richiede il RUOLO/categoria (acido/grasso/struttura), dato oggi assente.
# sostituti resta nel gruppo bloccato-dai-dati (vedi PULIZIA-BACKEND-DIARIO / mappa dati).


@bp.route("/v1/criteri/<ingrediente>", methods=["GET"])
def criteri(ingrediente):
    """Relazioni di un ingrediente, per criterio, con evidenza reale. NIENTE percentuale di abbinabilita'."""
    if not DATABASE_URL:
        return jsonify({"ingrediente": ingrediente, "relazioni": [], "nota": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            nodo = _risolvi_nodo(cur, ingrediente)
            if not nodo:
                cur.close()
                return jsonify({"ingrediente": ingrediente, "relazioni": [],
                                "non_riconosciuto": True,
                                "nota": "Ingrediente non trovato nel grafo con un profilo di composti."})
            ing_id, ing_nome = nodo
            base = _base_aromatica(cur, ing_id, ing_nome)
            trad = _tradizione(cur, ing_id)
            contr = _contrasto(cur, ing_id)
            cur.close()
        # declassa gli hub generici (riuso il filtro gia' provato di api.py)
        try:
            from routes.api import _pulisci_abbinamenti
            base = _pulisci_abbinamenti(base, campo="ingrediente", max_famiglia=3, ingrediente_base=ing_nome)
        except Exception:
            pass
        base = base[:12]
        nomi_base = {r["ingrediente"].lower() for r in base}
        trad = [r for r in trad if r["ingrediente"].lower() not in nomi_base]
        gia_visti = nomi_base | {r["ingrediente"].lower() for r in trad}
        contr = [r for r in contr if r["ingrediente"].lower() not in gia_visti]
        return jsonify({
            "ingrediente": ing_nome,
            "nodo_id": ing_id,
            "regola": "Matter mostra perche' una relazione esiste, non un voto di compatibilita'.",
            "relazioni": base + trad + contr,
            "conteggio": {"base_aromatica": len(base), "tradizione": len(trad), "contrasto": len(contr)},
        })
    except Exception as e:
        return jsonify({"ingrediente": ingrediente, "errore": str(e)[:160]}), 500


@bp.route("/v1/criteri/diag/<ingrediente>", methods=["GET"])
def criteri_diag(ingrediente):
    """Diagnostica: quale nodo e' stato risolto e quanti composti ha."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            nodo = _risolvi_nodo(cur, ingrediente)
            if not nodo:
                cur.close()
                return jsonify({"ingrediente": ingrediente, "trovato": False})
            ing_id, ing_nome = nodo
            cur.execute("SELECT COUNT(*) FROM edges WHERE from_id=%s AND relation='contiene_composto'", (ing_id,))
            n_comp = cur.fetchone()[0]
            cur.execute(
                "SELECT to_id FROM edges WHERE from_id=%s AND relation='contiene_composto' LIMIT 8", (ing_id,))
            esempi = [_nome_composto(r[0]) for r in cur.fetchall()]
            cur.close()
        return jsonify({
            "cercato": ingrediente,
            "nodo_risolto": ing_id,
            "nome_mostrato": ing_nome,
            "composti_totali": n_comp,
            "composti_esempio": esempi,
        })
    except Exception as e:
        return jsonify({"errore": str(e)[:160]}), 500


@bp.route("/v1/criteri/grafo-stato", methods=["GET"])
def grafo_stato():
    """Inventario reale del grafo: nodi per tipo, composti, ingredienti visibili/nascosti, archi per relazione."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute("SELECT type, COUNT(*) FROM nodes GROUP BY type ORDER BY COUNT(*) DESC")
            nodi_per_tipo = {(t or "(senza tipo)"): n for t, n in cur.fetchall()}
            cur.execute(r"SELECT COUNT(*) FROM nodes WHERE id LIKE 'comp\_%' OR id LIKE 'pub\_%'")
            composti = cur.fetchone()[0]
            cur.execute(
                """SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')
               AND (data->>'visibility') IS DISTINCT FROM 'hidden'""")
            ing_visibili = cur.fetchone()[0]
            cur.execute(
                """SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')
               AND (data->>'visibility') = 'hidden'""")
            ing_nascosti = cur.fetchone()[0]
            cur.execute("SELECT relation, COUNT(*) FROM edges GROUP BY relation ORDER BY COUNT(*) DESC")
            archi_per_relazione = {(r or "(senza relazione)"): n for r, n in cur.fetchall()}
            # COPERTURA DATI (per la mappa-dati / moat): quanti ingredienti+prodotti hanno
            # il profilo organolettico 'proprieta' e quanti hanno almeno un composto.
            cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')")
            ip_totali = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND (data ? 'proprieta')")
            con_proprieta = cur.fetchone()[0]
            cur.execute("""SELECT COUNT(DISTINCT from_id) FROM edges
                           WHERE relation = 'contiene_composto'""")
            con_composti = cur.fetchone()[0]
            # RECUPERABILITA' composti: chi eredita da un padre Ahn (padre_ahn_id) e
            # chi e' orfano (ne' composti propri ne' padre) = i candidati-da-collegare / buchi veri.
            cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND padre_ahn_id IS NOT NULL")
            con_padre_ahn = cur.fetchone()[0]
            cur.execute("""SELECT COUNT(*) FROM nodes n
                           WHERE n.type IN ('Ingrediente','Prodotto')
                             AND n.padre_ahn_id IS NULL
                             AND NOT EXISTS (SELECT 1 FROM edges e
                                             WHERE e.from_id = n.id AND e.relation = 'contiene_composto')""")
            senza_composti_ne_padre = cur.fetchone()[0]
            cur.close()
        return jsonify({
            "nodi_per_tipo": nodi_per_tipo,
            "composti_totali": composti,
            "ingredienti_visibili": ing_visibili,
            "ingredienti_nascosti": ing_nascosti,
            "archi_per_relazione": archi_per_relazione,
            "copertura_dati": {
                "ingredienti_prodotti_totali": ip_totali,
                "con_proprieta_organolettiche": con_proprieta,
                "nodi_con_composti": con_composti,
                "con_padre_ahn_eredita": con_padre_ahn,
                "orfani_senza_composti_ne_padre": senza_composti_ne_padre,
            },
        })
    except Exception as e:
        return jsonify({"errore": str(e)[:160]}), 500


@bp.route("/v1/criteri/orfani", methods=["GET"])
def criteri_orfani():
    """DIAGNOSTICO (strategia Ahn): ingredienti/prodotti senza composti e senza padre_ahn.
    Raggruppa per prefisso id e campiona i nomi, per classificarli (varieta' di Ahn / preparazioni /
    genuinamente nuovi) e capire cosa si recupera gratis col link al padre e cosa no."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute(
                r"""SELECT regexp_replace(id, '[-_].*$', '') AS pref, COUNT(*)
                    FROM nodes n
                    WHERE n.type IN ('Ingrediente','Prodotto')
                      AND n.padre_ahn_id IS NULL
                      AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id = n.id AND e.relation = 'contiene_composto')
                    GROUP BY pref ORDER BY COUNT(*) DESC""")
            per_prefisso = {(p or "(vuoto)"): c for p, c in cur.fetchall()}
            cur.execute(
                r"""SELECT id, name FROM nodes n
                    WHERE n.type IN ('Ingrediente','Prodotto')
                      AND n.padre_ahn_id IS NULL
                      AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id = n.id AND e.relation = 'contiene_composto')
                    ORDER BY n.name
                    LIMIT 120""")
            campione = [{"id": i, "nome": nm} for i, nm in cur.fetchall()]
            cur.close()
        return jsonify({"per_prefisso_id": per_prefisso, "campione_nomi": campione, "n_campione": len(campione)})
    except Exception as e:
        return jsonify({"errore": str(e)[:160]}), 500


@bp.route("/v1/criteri/orfani-match", methods=["GET"])
def criteri_orfani_match():
    """DRY-RUN (strategia Ahn): per ogni orfano prova ad agganciarlo a un nodo con composti (futuro
    padre_ahn). NON scrive niente. Salta i chimici mis-tipati. Mostra cosa collegherebbe e cosa no,
    coi conteggi per bucket: agganciabili (recupero gratis) / chimici / non-agganciabili (comprare o buco)."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import re as _re
    _qualif = _re.compile(r"\b(dop|igp|docg|doc|pdo|pgi|igt|stg|tradizionale|riserva|extra|biologico|bio)\b|\d+\s*anni|\d{4}", _re.I)
    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, lower(name) FROM nodes n
                   WHERE n.type IN ('Ingrediente','Prodotto')
                     AND EXISTS (SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='contiene_composto')""")
            padri = {}
            padri_id = set()
            for pid, pn in cur.fetchall():
                padri_id.add(pid)
                if pn and pn not in padri:
                    padri[pn] = pid
            cur.execute(
                """SELECT id, name FROM nodes n
                   WHERE n.type IN ('Ingrediente','Prodotto')
                     AND n.padre_ahn_id IS NULL
                     AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='contiene_composto')""")
            orfani = cur.fetchall()
            cur.close()
        chimici = 0
        proposte = []
        non_match = []
        for oid, onome in orfani:
            nl = (onome or "").strip().lower()
            # euristica chimici mis-tipati: underscore, 'acido ...', suffisso oil
            if (not nl) or ("_" in nl) or nl.startswith("acido ") or nl == "acetaldeide" or nl.endswith(" oil"):
                chimici += 1
                continue
            base = _re.sub(r"\s+", " ", _qualif.sub(" ", nl)).strip()
            parent = None
            metodo = None
            for it_word, ahn in _ALIAS.items():
                if it_word in base:
                    cand = "ahn_" + ahn
                    if cand in padri_id:
                        parent = cand
                        metodo = f"alias:{it_word}->{ahn}"
                        break
            if not parent:
                for w in base.split():
                    if len(w) >= 4 and w in padri:
                        parent = padri[w]
                        metodo = f"parola:{w}"
                        break
            if parent:
                proposte.append({"orfano": onome, "padre": parent, "metodo": metodo})
            else:
                non_match.append(onome)
        return jsonify({
            "totale_orfani": len(orfani),
            "chimici_mis_tipati": chimici,
            "agganciabili": len(proposte),
            "non_agganciabili": len(non_match),
            "proposte_campione": proposte[:60],
            "non_agganciabili_campione": non_match[:60],
            "nota": "DRY-RUN: nessuna scrittura. Rivedi le proposte prima di applicare i link.",
        })
    except Exception as e:
        return jsonify({"errore": str(e)[:160]}), 500


@bp.route("/v1/criteri/link-fenomeni", methods=["GET"])
def criteri_link_fenomeni():
    """DRY-RUN (moat, collegamenti verticali): legge il testo-fenomeni di ogni Protocollo e propone
    l'arco al nodo Fenomeno giusto (match per radice della parola). NON scrive. Mostra proposte,
    gia'-linkati, e non-matchati (spesso tecniche, non fenomeni -> arco a Tecnica in un passo dopo).
    Param opzionale ?ingrediente=pomodoro per limitare ai protocolli di un ingrediente."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import re as _re
    import json as _json
    from flask import request
    filtro_ing = (request.args.get("ingrediente") or "").strip().lower()
    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM nodes WHERE type='Fenomeno'")
            fen = []
            for fid, fname in cur.fetchall():
                words = [w for w in _re.sub(r"[^a-zàèéìòù ]", " ", (fname or "").lower()).split() if len(w) >= 5]
                stems = [w[:7] for w in words]
                if stems:
                    fen.append((fid, fname, stems))
            if filtro_ing:
                cur.execute("""SELECT DISTINCT n.id, n.name, n.data FROM edges e JOIN nodes n ON n.id=e.from_id
                               JOIN nodes i ON i.id=e.to_id
                               WHERE e.relation='usa_reagente' AND n.type='Protocollo'
                                 AND LOWER(i.name) LIKE %s AND n.data ? 'fenomeni'""", (f"%{filtro_ing}%",))
            else:
                cur.execute("SELECT id, name, data FROM nodes WHERE type='Protocollo' AND data ? 'fenomeni'")
            prot = cur.fetchall()
            cur.close()
        gia_linkati = 0
        testo_totale = 0
        proposte = []
        non_match = []
        for pid, pname, data in prot:
            dd = data if isinstance(data, dict) else (_json.loads(data) if data else {})
            for f in (dd.get("fenomeni") or []):
                if isinstance(f, dict):
                    if f.get("slug") or f.get("fenomeno_id"):
                        gia_linkati += 1
                        continue
                    txt = str(f.get("nome", ""))
                else:
                    txt = str(f)
                if not txt.strip():
                    continue
                testo_totale += 1
                tl = txt.lower()
                best = None  # (stem_len, -len(nome)), fid, fname
                for fid, fname, stems in fen:
                    m = max((len(s) for s in stems if s in tl), default=0)
                    if m > 0:
                        key = (m, -len(fname))
                        if best is None or key > best[0]:
                            best = (key, fid, fname)
                if best:
                    proposte.append({"protocollo": pname, "testo": txt, "fenomeno": best[1], "nome_fen": best[2]})
                else:
                    non_match.append({"protocollo": pname, "testo": txt})
        return jsonify({
            "filtro_ingrediente": filtro_ing or "(tutti)",
            "protocolli_con_fenomeni": len(prot),
            "voci_fenomeno_testo": testo_totale,
            "gia_linkati": gia_linkati,
            "proposte_arco": len(proposte),
            "non_matchati": len(non_match),
            "proposte_campione": proposte[:50],
            "non_matchati_campione": non_match[:40],
            "nota": "DRY-RUN: nessuna scrittura. Rivedi prima di materializzare gli archi protocollo->fenomeno.",
        })
    except Exception as e:
        return jsonify({"errore": str(e)[:200]}), 500
