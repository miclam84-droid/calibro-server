# -*- coding: utf-8 -*-
# ADMIN — causalità SPECIFICA sui protocolli (bonifica del fossato).
#
# Problema (audit 2026-10-31): la causalità dei protocolli è generica. Ogni
# protocollo salva solo il nome del fenomeno e EREDITA la causalità dal nodo-
# Fenomeno (routes/api.py leggi_protocollo ~4929-4936). Risultato: tutti i
# protocolli con lo stesso fenomeno mostrano la STESSA identica causalità.
#
# Rimedio: scrivere la causalità PROPRIA nel protocollo, in
# data.fenomeni[i].causalita. leggi_protocollo la preferisce già a quella
# ereditata (eredita solo se None). Così la causalità diventa specifica di
# QUELLA preparazione, senza toccare né il nodo-Fenomeno né altri protocolli.
#
# Contenuto INLINE qui sotto (rivedibile nella PR). Da FONTI, non inventato;
# "fonte" tracciata dentro la causalità. Da validare al banco (Michele).
#
# Sicurezza: gate ADMIN_SECRET; DRY-RUN di default, scrive SOLO con &esegui=1;
# tocca SOLO gli id nell'allowlist CAUSALITA_SPECIFICA; idempotente.
from flask import Blueprint, request, jsonify
import json
from db import connessione
from routes.admin import _admin_ok

bp_causalita = Blueprint("admin_causalita", __name__)

# ── Allowlist: id-protocollo -> {fenomeno da agganciare, causalità propria} ──
# Primo standard: Focaccia Barese (Bucolico). Fonti: ricette focaccia barese
# (agricolapiano.com, lapiadella.com) + scienza nota dell'impasto (sale↔glutine,
# assorbimento della semola di grano duro). Da validare al banco.
CAUSALITA_SPECIFICA = {
    "prot-focaccia-barese": {
        "fenomeno": "idratazione dell'impasto",
        "causalita": {
            "acceleranti": [
                {"fattore": "Semola rimacinata di grano duro — regge il 70-80% dove una farina debole mollerebbe"},
                {"fattore": "Patata lessa nell'impasto — l'amido gelatinizzato trattiene acqua: mollica più umida e che dura di più"},
                {"fattore": "Incordatura (10-12 min) e pieghe — la maglia glutinica ingabbia l'acqua"},
                {"fattore": "Acqua tiepida ~30°C — accelera la fermentazione (fredda 4-8°C per il controllo lungo)"},
            ],
            "rallentanti": [
                {"fattore": "Sale aggiunto presto o sul lievito — irrigidisce il glutine, rallenta assorbimento e lievitazione"},
                {"fattore": "Impasto oltre 26°C — fermentazione fuori controllo, maglia debole"},
                {"fattore": "Farina aggiunta perché 'appiccica' — abbassa l'idratazione reale: mollica asciutta e compatta"},
                {"fattore": "Farina debole al posto della semola — non regge l'acqua, l'impasto molla"},
            ],
            "fonte": "ricette focaccia barese (agricolapiano, lapiadella) + scienza nota dell'impasto; da validare al banco",
        },
    },
}


def applica_causalita(dd, spec, esegui):
    """Funzione PURA (testabile senza DB): inserisce spec['causalita'] nel
    fenomeno di 'dd' che combacia per nome con spec['fenomeno'].
    Normalizza un fenomeno-stringa in dict. Ritorna (dd, info).
    info['azione']: 'scritta' | 'dry-run' | 'fenomeno-assente'."""
    target = (spec.get("fenomeno") or "").strip().lower()
    fen_list = dd.get("fenomeni") or []
    nuovi = []
    trovato = False
    aveva_propria = False
    for f in fen_list:
        if isinstance(f, str):
            if f.strip().lower() == target:
                trovato = True
                nf = {"nome": f}
                if esegui:
                    nf["causalita"] = spec["causalita"]
                nuovi.append(nf)
                continue
            nuovi.append(f)
            continue
        if (f.get("nome", "").strip().lower() == target):
            trovato = True
            aveva_propria = bool(f.get("causalita"))
            if esegui:
                f = dict(f)
                f["causalita"] = spec["causalita"]
            nuovi.append(f)
            continue
        nuovi.append(f)
    if not trovato:
        return dd, {"azione": "fenomeno-assente",
                    "fenomeni_presenti": [(x.get("nome") if isinstance(x, dict) else x) for x in fen_list]}
    dd = dict(dd)
    dd["fenomeni"] = nuovi
    return dd, {"azione": ("scritta" if esegui else "dry-run"),
                "fenomeno": spec.get("fenomeno"),
                "aveva_causalita_propria_prima": aveva_propria}


@bp_causalita.route("/admin/causalita-specifica", methods=["GET"])
def causalita_specifica():
    """Scrive la causalità specifica sui protocolli dell'allowlist.
    DRY-RUN di default (mostra cosa cambierebbe). Scrive con &esegui=1.
    Auth: header X-Admin-Secret o ?s=SECRET."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    esegui = request.args.get("esegui") == "1"
    report = []
    with connessione() as conn:
        cur = conn.cursor()
        for pid, spec in CAUSALITA_SPECIFICA.items():
            cur.execute("SELECT data FROM nodes WHERE id=%s", (pid,))
            row = cur.fetchone()
            if not row:
                report.append({"id": pid, "stato": "non trovato"})
                continue
            dd = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            nuovo, info = applica_causalita(dd, spec, esegui)
            info["id"] = pid
            if info.get("azione") == "scritta" and esegui:
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(nuovo, ensure_ascii=False), pid))
            report.append(info)
        # IMPORTANTE: db.connessione() fa ROLLBACK in uscita — il commit è
        # responsabilità del chiamante, va fatto QUI o la scrittura si perde.
        if esegui:
            conn.commit()
        cur.close()
    return jsonify({"esegui": esegui, "n_protocolli": len(CAUSALITA_SPECIFICA), "report": report})
