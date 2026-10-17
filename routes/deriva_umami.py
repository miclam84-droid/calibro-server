# ============================================================
# DERIVA-UMAMI — pipeline dell'umami da GLUTAMMATO LIBERO (mg/100g)
# L'umami NON sta nelle tabelle nutrizionali (USDA/CIQUAL): serve una tabella
# di glutammato libero da FONTE CITABILE (es. letteratura — Ninomiya 1998 — o
# Umami Information Center con licenza verificata). QUI c'è la MACCHINA pronta:
# curva glutammato->0-10 + ingestione fill-only taggata. La tabella dati
# (data/glutammato.csv) si riempie da una fonte vera — NON si inventano i numeri.
# Ancore della scala (SCALE-SENSORIALI): 0 olio/zucchero · 2 latte · 4 pomodoro
# maturo · 6 funghi secchi · 8 parmigiano · 10 colatura/dashi.
# ============================================================
import os
import csv
import json

from flask import Blueprint, request, jsonify
from routes.deriva_gusti import _interp, _ESCLUDI

bp_umami = Blueprint("deriva_umami", __name__)

FORMULA_VER = "umami-v1"

# Curva glutammato libero (mg/100g) -> asse umami 0-10. Ancorata alle ancore della scala.
_UMAMI = [(0, 0), (10, 1), (50, 2), (150, 4), (400, 6), (1200, 8), (3000, 10)]

_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "glutammato.csv")
_TBL = None


def _tabella():
    """Carica (una volta) la tabella glutammato: {nome_lower: (mg, fonte)}.
    Vuota finché non si carica una fonte vera — niente numeri inventati."""
    global _TBL
    if _TBL is not None:
        return _TBL
    _TBL = {}
    try:
        with open(_CSV, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                nome = (r.get("nome") or "").strip().lower()
                if not nome or nome.startswith("#"):
                    continue
                try:
                    mg = float((r.get("glutammato_mg_100g") or "").strip())
                except (ValueError, TypeError):
                    continue
                _TBL[nome] = (mg, (r.get("fonte") or "").strip())
    except FileNotFoundError:
        _TBL = {}
    return _TBL


def _deriva(mg):
    """Glutammato mg/100g -> voto umami 0-10."""
    return {"val": _interp(mg, _UMAMI), "grezzo": round(mg, 1)}


@bp_umami.route("/admin/deriva-umami")
def deriva_umami():
    """DRY-RUN di default (?s=SECRET). &esegui=1 scrive (fill-only, backup, transazione).
    Richiede data/glutammato.csv popolato da fonte vera: se è vuoto, non scrive niente."""
    import psycopg2

    sec = os.environ.get("ADMIN_SECRET")
    if not sec or request.args.get("s") != sec:
        return jsonify({"errore": "non autorizzato"}), 403
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400

    tbl = _tabella()
    if not tbl:
        return jsonify({
            "dry_run": True, "fonte_tabella": "data/glutammato.csv",
            "voci_tabella": 0,
            "nota": "Tabella glutammato VUOTA. La macchina è pronta: carica una tabella "
                    "glutammato-libero da fonte citabile (Ninomiya 1998 / Umami Information "
                    "Center con licenza verificata) in data/glutammato.csv (colonne: nome, "
                    "glutammato_mg_100g, fonte). Nessun numero viene inventato.",
            "campione": [],
        })

    esegui = request.args.get("esegui") == "1"
    conn = None
    try:
        conn = psycopg2.connect(dburl)
        conn.autocommit = False
        cur = conn.cursor()
        if esegui:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_umami
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")

        campione, scritti, nomatch, protetti = [], 0, 0, 0
        for nome_it, (mg, fonte) in tbl.items():
            cur.execute("""SELECT id, name, data FROM nodes
                           WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s)
                           ORDER BY (id LIKE 'ing-%%') DESC LIMIT 1""", (nome_it,))
            row = cur.fetchone()
            if not row:
                nomatch += 1
                continue
            nid, nome_nodo, data = row
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            testo = (str(nome_nodo) + " " + str(dd.get("kind", ""))).lower()
            if dd.get("kind") == "varieta" or any(x in testo for x in _ESCLUDI):
                protetti += 1
                continue
            prop = dict(dd.get("proprieta", {}) or {})
            meta = dict(dd.get("proprieta_meta", {}) or {})
            stato_vecchio = (meta.get("umami", {}) or {}).get("stato")
            scrivibile = stato_vecchio in (None, "stimato")
            der = _deriva(mg)
            campione.append({"nodo": nid, "nome": nome_nodo, "vecchio": prop.get("umami"),
                             "nuovo_derivato": der["val"], "grezzo_mg": der["grezzo"],
                             "fonte": fonte, "scrivibile": scrivibile})
            if esegui and scrivibile:
                cur.execute("INSERT INTO _backup_umami (id, data_old) VALUES (%s, %s)",
                            (nid, json.dumps(dd, ensure_ascii=False)))
                prop["umami"] = der["val"]
                meta["umami"] = {"stato": "derivato", "fonte": f"glutammato — {fonte}",
                                 "formula": FORMULA_VER, "grezzo": der["grezzo"]}
                dd["proprieta"] = prop
                dd["proprieta_meta"] = meta
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(dd, ensure_ascii=False), nid))
                scritti += 1

        if esegui:
            conn.commit()
        cur.close()
        conn.close()
        return jsonify({
            "dry_run": (not esegui), "fonte_tabella": "data/glutammato.csv",
            "voci_tabella": len(tbl), "nodi_non_trovati": nomatch,
            "saltati_protetti": protetti, "scritti": scritti if esegui else 0,
            "nota": ("DRY RUN: nessun dato scritto. &esegui=1 per scrivere."
                     if not esegui else
                     "ESEGUITO: fill-only, backup in _backup_umami, umami taggato con la fonte del glutammato."),
            "campione": campione[:50],
        })
    except Exception as e:
        try:
            if conn:
                conn.rollback(); conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500
