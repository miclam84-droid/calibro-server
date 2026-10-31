# -*- coding: utf-8 -*-
# ADMIN — causalità SPECIFICA sui protocolli (bonifica del fossato).
#
# Problema (audit 2026-10-31): la causalità dei protocolli è generica. Ogni
# protocollo salva solo il nome del fenomeno ed EREDITA la causalità dal nodo-
# Fenomeno (routes/api.py leggi_protocollo ~4929-4936). Risultato: tutti i
# protocolli con lo stesso fenomeno mostrano la STESSA identica causalità.
#
# Rimedio: scrivere la causalità PROPRIA nel protocollo, in
# data.fenomeni[i].causalita. leggi_protocollo la preferisce già a quella
# ereditata (eredita solo se None). Così diventa specifica di QUELLA
# preparazione, senza toccare né il nodo-Fenomeno né altri protocolli.
#
# Contenuto INLINE qui sotto (rivedibile nella PR). Da FONTI / tecnica nota,
# NON inventato; "fonte" tracciata dentro la causalità. Da validare al banco.
# causalita=None su un fenomeno REVERTE quel fenomeno al generico ereditato.
#
# Sicurezza: gate ADMIN_SECRET; DRY-RUN di default, scrive SOLO con &esegui=1;
# tocca SOLO gli id nell'allowlist; idempotente; funzione pura testata offline.
from flask import Blueprint, request, jsonify
import json
from db import connessione
from routes.admin import _admin_ok

bp_causalita = Blueprint("admin_causalita", __name__)

# ── Allowlist: id-protocollo -> {"fenomeni": [{"nome", "causalita"}]} ──
# causalita=None  -> reverte quel fenomeno al generico ereditato (fallback onesto).
CAUSALITA_SPECIFICA = {
    # Focaccia barese: la ricetta del protocollo è grano tenero + lievito madre
    # (NON semola/patata come la classica che avevo sorgentato). Non essendo
    # sicuro della sua causalità specifica, REVERTO al generico onesto.
    "prot-focaccia-barese": {
        "fenomeni": [
            {"nome": "idratazione dell'impasto", "causalita": None},
        ],
    },
    # Bloody Mary (Bucopertuso). Tecnica classica DOCUMENTATA: si costruisce e
    # si ROLLA (travaso tra due tin) o si mescola gentilmente, NON si shakera —
    # shakerare aera e fa schiumare il succo di pomodoro. Fonte dentro.
    "prot-bloody-mary-rivisitato": {
        "fenomeni": [
            {
                "nome": "shakerare vs mescolare",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Roll (travaso tra due tin) o mescolata gentile — raffredda e integra senza inglobare aria"},
                        {"fattore": "Succo di pomodoro denso — ha già corpo, non serve l'aria dello shake"},
                        {"fattore": "Ghiaccio grande e solido — raffredda con diluizione lenta e controllabile"},
                    ],
                    "rallentanti": [
                        {"fattore": "Shakerare — aera e schiuma il pomodoro: colore pallido, testa spumosa, diluizione troppo rapida"},
                        {"fattore": "Ghiaccio tritato o piccolo — scioglie in fretta: drink acquoso, pomodoro slavato"},
                    ],
                    "fonte": "tecnica classica del Bloody Mary (build/roll, non shake) — Difford's / Liquid Intelligence; da validare al banco",
                },
            },
            {
                "nome": "diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Roll/mescolata misurata sul ghiaccio — porta acqua quanto basta a smussare vodka e acidità"},
                        {"fattore": "Ghiaccio più 'bagnato' (vicino a 0°C) — cede acqua prima, utile se il drink è troppo aggressivo"},
                    ],
                    "rallentanti": [
                        {"fattore": "Troppa diluizione — il corpo del pomodoro si appiattisce, sale e acidità si spengono: watery"},
                        {"fattore": "Mescolata troppo breve — vodka e limone restano taglienti, non integrati"},
                    ],
                    "fonte": "equilibrio e diluizione del Bloody Mary — Liquid Intelligence; da validare al banco",
                },
            },
        ],
    },
}


def applica_causalita(dd, spec, esegui):
    """Funzione PURA (testabile senza DB). Per ogni fenomeno in spec['fenomeni'],
    trova il fenomeno di 'dd' che combacia per nome e vi scrive la causalità
    (o la RIMUOVE se causalita è None -> torna al generico ereditato).
    Normalizza un fenomeno-stringa in dict. Ritorna (dd_nuovo, info)."""
    fen_specs = spec.get("fenomeni") or []
    fen_list = list(dd.get("fenomeni") or [])
    dettagli = []
    cambiato = False
    for fs in fen_specs:
        target = (fs.get("nome") or "").strip().lower()
        nuova_caus = fs.get("causalita")  # può essere None = revert
        trovato = False
        for i, f in enumerate(fen_list):
            nome_f = (f if isinstance(f, str) else f.get("nome", "")).strip().lower()
            if nome_f != target:
                continue
            trovato = True
            if isinstance(f, str):
                f = {"nome": f}
            else:
                f = dict(f)
            prima = bool(f.get("causalita"))
            if esegui:
                if nuova_caus is None:
                    f.pop("causalita", None)           # revert al generico ereditato
                else:
                    f["causalita"] = nuova_caus
                cambiato = True
            fen_list[i] = f
            dettagli.append({"fenomeno": fs.get("nome"),
                             "azione": ("revert" if nuova_caus is None else "scrittura") + ("" if esegui else " (dry-run)"),
                             "aveva_causalita_propria_prima": prima})
            break
        if not trovato:
            dettagli.append({"fenomeno": fs.get("nome"), "azione": "fenomeno-assente",
                             "fenomeni_presenti": [(x.get("nome") if isinstance(x, dict) else x) for x in fen_list]})
    if cambiato:
        dd = dict(dd)
        dd["fenomeni"] = fen_list
    return dd, {"dettagli": dettagli, "modificato": cambiato}


@bp_causalita.route("/admin/causalita-specifica", methods=["GET"])
def causalita_specifica():
    """Scrive/reverte la causalità sui protocolli dell'allowlist.
    DRY-RUN di default; scrive con &esegui=1. Auth: header X-Admin-Secret o ?s=."""
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
            if esegui and info.get("modificato"):
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(nuovo, ensure_ascii=False), pid))
            report.append(info)
        # IMPORTANTE: db.connessione() fa ROLLBACK in uscita — il commit è
        # responsabilità del chiamante, va fatto QUI o la scrittura si perde.
        if esegui:
            conn.commit()
        cur.close()
    return jsonify({"esegui": esegui, "n_protocolli": len(CAUSALITA_SPECIFICA), "report": report})
