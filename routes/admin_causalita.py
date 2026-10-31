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
    # Boulevardier (Bucopertuso). Ricetta protocollo: bourbon 30 / vermouth rosso
    # 30 / bitter Campari 30 — equal-parts, spirit-forward, SENZA agrumi. Tecnica
    # classica: si MESCOLA nel mixing glass, non si shakera (texture setosa).
    "prot-boulevardier-classico": {
        "fenomeni": [
            {
                "nome": "Diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Mescolare 20-30s nel mixing glass con ghiaccio grande — porta ~20-25% d'acqua che smussa l'alcol del bourbon"},
                        {"fattore": "Vermouth rosso e Campari (già bassa gradazione e zuccherini) abbassano la gradazione media — serve meno acqua che per un drink di solo distillato"},
                        {"fattore": "Ghiaccio asciutto da freezer — raffredda cedendo poca acqua: diluizione fine e controllabile"},
                    ],
                    "rallentanti": [
                        {"fattore": "Shakerare — qui dà microbolle e velo: il Boulevardier equal-parts va mescolato, non agitato"},
                        {"fattore": "Ghiaccio piccolo/bagnato o mescolata troppo lunga — troppa acqua: amaro del Campari e corpo del vermouth si appiattiscono"},
                    ],
                    "fonte": "tecnica classica degli stirred spirit-forward equal-parts (Boulevardier) — Difford's Guide / Regan; da validare al banco",
                },
            },
        ],
    },
    # Americano (Bucopertuso). Ricetta protocollo: vermouth rosso 30 / bitter 30 /
    # acqua frizzante 60 — long drink COSTRUITO nel bicchiere e allungato con soda.
    "prot-americano-rivisitato": {
        "fenomeni": [
            {
                "nome": "diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Build diretto sul ghiaccio con mescolata breve — basta a integrare vermouth e bitter: la soda fa già da allungo"},
                        {"fattore": "Ghiaccio grande e abbondante — raffredda cedendo poca acqua: la diluizione la porta la soda, non lo scioglimento"},
                    ],
                    "rallentanti": [
                        {"fattore": "Mescolata lunga o ghiaccio piccolo — aggiunge acqua di troppo sopra ai 60 ml di soda: drink slavato, bitter spento"},
                        {"fattore": "Ghiaccio scarso in un drink lungo — scioglie in fretta e si scalda: diluizione incontrollata"},
                    ],
                    "fonte": "tecnica classica dell'Americano (build sul ghiaccio, allungato con soda) — Difford's Guide; da validare al banco",
                },
            },
            {
                "nome": "carbonatazione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Soda fredda versata per ultima e piano sul ghiaccio — trattiene più CO2: perlage fine e persistente"},
                        {"fattore": "Soda e bicchiere ben freddi — a bassa temperatura la CO2 resta più disciolta"},
                        {"fattore": "Una sola mescolata minima dal basso dopo la soda — integra senza sbattere fuori le bolle"},
                    ],
                    "rallentanti": [
                        {"fattore": "Versare la soda di getto o mescolare con energia — sbatte fuori la CO2: drink piatto in pochi minuti"},
                        {"fattore": "Soda a temperatura ambiente — perde gas subito al contatto col ghiaccio"},
                    ],
                    "fonte": "comportamento della CO2 nei long drink allungati con soda — tecnica di bar documentata; da validare al banco",
                },
            },
        ],
    },
    # Old Fashioned (Bucopertuso). Ricetta protocollo: bourbon/rye 60 / sciroppo di
    # zucchero 10 / Angostura 3 dash / scorza d'arancia — stirred, servito su rock.
    "prot-old-fashioned": {
        "fenomeni": [
            {
                "nome": "diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Mescolare a lungo (30-40s) su ghiaccio grande — un drink quasi di solo distillato (60 ml) chiede più acqua per aprirsi"},
                        {"fattore": "Servire su un cubo grande singolo — continua a diluire lentamente nel bicchiere, tenendo l'equilibrio nel tempo"},
                        {"fattore": "Ghiaccio molto freddo e asciutto — consente mescolate lunghe senza annacquare di colpo"},
                    ],
                    "rallentanti": [
                        {"fattore": "Servire quasi senza diluizione (mescolata breve) — il bourbon resta spigoloso e alcolico, lo zucchero non si lega"},
                        {"fattore": "Ghiaccio tritato — scioglie troppo: perde subito corpo e diventa acquoso"},
                    ],
                    "fonte": "tecnica classica dell'Old Fashioned (stir, big rock, ~25-30% diluizione) — Liquid Intelligence (Arnold) / Difford's; da validare al banco",
                },
            },
            {
                "nome": "equilibrio del cocktail",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "~10 ml di sciroppo contro 60 di distillato — zucchero appena sufficiente ad arrotondare senza dolcificare"},
                        {"fattore": "3 dash di Angostura — amaro e spezia che legano zucchero e whiskey"},
                        {"fattore": "Olio della scorza d'arancia espresso sopra — profuma e bilancia la dolcezza senza aggiungere acidità"},
                    ],
                    "rallentanti": [
                        {"fattore": "Troppo sciroppo — drink stucchevole, perde il carattere del whiskey"},
                        {"fattore": "Spremere la parte bianca (albedo) della scorza — note amare/verdi fuori posto"},
                    ],
                    "fonte": "equilibrio classico dell'Old Fashioned (distillato-zucchero-bitter) — Regan / Difford's; da validare al banco",
                },
            },
        ],
    },
    # Whiskey Sour (Bucopertuso). Ricetta protocollo: bourbon 60 / succo di limone
    # 30 / sciroppo 1:1 20 / albume 20 — sour CON albume, SHAKERATO (serve aria).
    "prot-whiskey-sour": {
        "fenomeni": [
            {
                "nome": "shakerare vs mescolare",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Shakerare con forza — emulsiona l'albume e integra il limone: senza aria non c'è la schiuma setosa del sour"},
                        {"fattore": "Dry shake (prima senza ghiaccio, poi con) — monta l'albume e dà la testa cremosa e stabile"},
                        {"fattore": "Ghiaccio solido nello shake — raffredda e diluisce al punto giusto mentre si aera"},
                    ],
                    "rallentanti": [
                        {"fattore": "Mescolare invece di shakerare — niente emulsione: albume slegato, drink piatto e sbilanciato sull'acido"},
                        {"fattore": "Shake troppo breve — schiuma scarsa e instabile, collassa nel bicchiere"},
                    ],
                    "fonte": "tecnica classica del sour con albume (shake / dry shake per l'emulsione) — Difford's / Liquid Intelligence; da validare al banco",
                },
            },
            {
                "nome": "diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Shake energico ~10-15s con ghiaccio grande — porta l'acqua che bilancia l'acidità del limone e la gradazione del bourbon"},
                        {"fattore": "Ghiaccio abbondante e duro — raffredda in fretta diluendo il giusto durante lo shake"},
                    ],
                    "rallentanti": [
                        {"fattore": "Shake troppo lungo o ghiaccio già bagnato — troppa acqua: il sour diventa debole e slavato"},
                        {"fattore": "Ghiaccio tritato — eccesso di diluizione in pochi secondi"},
                    ],
                    "fonte": "diluizione nello shake dei sour — Liquid Intelligence (Arnold); da validare al banco",
                },
            },
            {
                "nome": "equilibrio del cocktail",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Rapporto ~60/30/20 (bourbon/limone/sciroppo) — struttura classica del sour: acido e zucchero in tensione sul distillato"},
                        {"fattore": "Succo di limone fresco — acidità viva che taglia dolcezza e gradazione"},
                        {"fattore": "Albume — non cambia il gusto ma arrotonda e lega acido e zucchero in bocca"},
                    ],
                    "rallentanti": [
                        {"fattore": "Troppo sciroppo o poco limone — drink dolce e piatto, perde la spinta 'sour'"},
                        {"fattore": "Succo di limone vecchio/ossidato — acidità spenta e amara, squilibrio"},
                    ],
                    "fonte": "equilibrio acido-zucchero-distillato del Whiskey Sour — Regan / Difford's; da validare al banco",
                },
            },
        ],
    },
    # French 75 (Bucopertuso). Ricetta protocollo: gin 30 / succo di limone 15 /
    # sciroppo 15 / champagne 60 — base shakerata, top di champagne, servito in flute.
    "prot-french-75-classico": {
        "fenomeni": [
            {
                "nome": "diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Shakerare brevemente la base gin-limone-zucchero con ghiaccio — raffredda e diluisce la parte alcolica prima dello champagne"},
                        {"fattore": "Champagne ben freddo versato per ultimo — allunga e raffredda senza bisogno d'altra acqua o ghiaccio nel flute"},
                    ],
                    "rallentanti": [
                        {"fattore": "Shake troppo lungo della base — troppa acqua: con l'aggiunta dello champagne il drink è già slavato"},
                        {"fattore": "Ghiaccio nel flute con lo champagne — diluisce e scalda inutilmente, smorza le bolle"},
                    ],
                    "fonte": "tecnica classica del French 75 (base shakerata, top di champagne, flute senza ghiaccio) — Difford's Guide; da validare al banco",
                },
            },
            {
                "nome": "carbonatazione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Champagne freddissimo aggiunto alla fine e versato piano sulla base già fredda — trattiene la CO2: bollicine fini e durature"},
                        {"fattore": "Base gin-limone pre-raffreddata — meno shock termico allo champagne, meno gas perso"},
                        {"fattore": "Flute stretto — riduce la superficie e rallenta la perdita di bolle"},
                    ],
                    "rallentanti": [
                        {"fattore": "Versare lo champagne di getto o mescolare dopo — sbatte fuori la CO2: drink piatto"},
                        {"fattore": "Base calda o champagne poco freddo — la CO2 esce subito in schiuma"},
                    ],
                    "fonte": "ritenzione della CO2 nei cocktail con top di spumante (French 75) — tecnica di bar documentata; da validare al banco",
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
