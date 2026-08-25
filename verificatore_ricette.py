# verificatore_ricette.py
# VERIFICATORE DI RICETTE — blocca le eresie culinarie (panna nella carbonara, bacon al posto del guanciale)
# e gli errori tecnici PRIMA che una ricetta finisca davanti all'utente.
# Regole canoniche VERIFICATE su fonti italiane serie (Giallo Zafferano, Accademia Italiana della Cucina,
# Disciplinare Pecorino Romano DOP). Un professionista italiano NON deve poter contestare nulla.
#
# Ogni piatto classico ha: "vietati" (ingredienti che NON possono esserci — eresie) e
# "obbligatori" (ingredienti che DEVONO esserci). Il verificatore ritorna gli errori trovati.

import re

# ── REGOLE CANONICHE DEI PIATTI CLASSICI ──
# chiave = parola nel nome ricetta. "vietati" = liste di sinonimi; se UNO compare → ERRORE GRAVE.
# "obbligatori" = almeno uno del gruppo deve esserci.
REGOLE_CANONICHE = {
    "carbonara": {
        "vietati": [
            ["panna"], ["aglio"], ["cipolla"], ["bacon"], ["pancetta affumicata"],
            ["prezzemolo"], ["funghi"], ["piselli"], ["würstel", "wurstel", "hot dog", "salsiccia"],
            ["latte"], ["besciamella"],
        ],
        "obbligatori": [["guanciale"], ["pecorino"], ["tuorl", "uov"], ["pepe"]],
        "nota": "Carbonara vera: guanciale, tuorli, Pecorino Romano, pepe nero. MAI panna/aglio/cipolla/bacon.",
    },
    "amatriciana": {
        "vietati": [["aglio"], ["cipolla"], ["panna"], ["pancetta"], ["bacon"]],
        "obbligatori": [["guanciale"], ["pecorino"], ["pomodor"]],
        "nota": "Amatriciana: guanciale, pomodoro, pecorino romano, (peperoncino/vino). NO aglio, NO cipolla, NO panna.",
    },
    "cacio e pepe": {
        "vietati": [["panna"], ["burro"], ["aglio"], ["olio"], ["parmigiano"]],
        "obbligatori": [["pecorino"], ["pepe"]],
        "nota": "Cacio e pepe: solo pasta, pecorino romano, pepe nero, acqua di cottura. Nient'altro.",
    },
    "gricia": {
        "vietati": [["pomodor"], ["panna"], ["aglio"], ["cipolla"], ["uov"], ["bacon"]],
        "obbligatori": [["guanciale"], ["pecorino"]],
        "nota": "Gricia: guanciale, pecorino romano, pepe. NO pomodoro (sennò è amatriciana), NO uova (sennò è carbonara).",
    },
    "pesto": {  # pesto alla genovese
        "vietati": [["panna"], ["prezzemolo"], ["noci"] , ["philadelphia"], ["ricotta"]],
        "obbligatori": [["basilico"], ["pinoli"], ["parmigiano", "pecorino"], ["aglio"], ["olio"]],
        "nota": "Pesto genovese: basilico, pinoli, parmigiano+pecorino, aglio, olio EVO, sale. NO panna, NO noci, NO prezzemolo.",
    },
    "ragù": {  # ragù alla bolognese
        "vietati": [["panna"], ["aglio"], ["besciamella"]],
        "obbligatori": [["carne", "manzo", "macinat"], ["soffritto", "cipolla", "sedano", "carota"], ["pomodor", "passata", "concentrato"]],
        "nota": "Ragù bolognese: carne, soffritto (sedano-carota-cipolla), pomodoro, vino. NO aglio, NO panna.",
    },
    "pizza margherita": {
        "vietati": [["ketchup"], ["ananas"], ["panna"]],
        "obbligatori": [["pomodor"], ["mozzarella", "fior di latte"], ["basilico"]],
        "nota": "Margherita: pomodoro, mozzarella/fior di latte, basilico, olio. Impasto + cottura alta.",
    },
    "tiramisù": {
        "vietati": [["panna montata al posto", "besciamella"], ["gelatina"]],
        "obbligatori": [["mascarpone"], ["savoiard"], ["caffè", "caffe"], ["uov", "tuorl"], ["cacao"]],
        "nota": "Tiramisù: mascarpone, savoiardi, caffè, uova, zucchero, cacao. La panna è tollerata ma non tradizionale.",
    },
    "pastiera": {
        "vietati": [["cioccolato"], ["panna"]],
        "obbligatori": [["grano"], ["ricotta"], ["fiori d'arancio", "acqua di fiori"]],
        "nota": "Pastiera napoletana: grano cotto, ricotta, uova, acqua di fiori d'arancio, canditi.",
    },
}

# ── ERESIE UNIVERSALI (valgono per QUALSIASI piatto italiano tradizionale) ──
# se il piatto è marcato come "tradizionale/classico" e compaiono queste, è sospetto.
ERESIE_GRAVI_UNIVERSALI = {
    "bacon": "In un piatto italiano il 'bacon' (affumicato anglosassone) è quasi sempre un errore: si usa guanciale o pancetta.",
    "wurstel": "I würstel non appartengono alla cucina italiana tradizionale.",
    "würstel": "I würstel non appartengono alla cucina italiana tradizionale.",
}


def _norm(testo):
    return (testo or "").lower()


def verifica_ricetta(nome, ingredienti):
    """Verifica una ricetta contro le regole canoniche.
    nome: stringa. ingredienti: lista di dict {nome,...} o lista di stringhe.
    Ritorna: {"ok": bool, "errori_gravi": [...], "avvisi": [...], "piatto_riconosciuto": str|None}
    """
    nome_l = _norm(nome)
    # una RIVISITAZIONE dichiarata può discostarsi dal canone: le eresie diventano avvisi, non blocchi
    is_rivisitazione = any(w in nome_l for w in ["rivisitat", "rivisitazione", "twist", "moderna", "moderno", "destrutturat", "creativ"])
    # testo unico degli ingredienti
    ingr_testi = []
    for i in (ingredienti or []):
        if isinstance(i, dict):
            ingr_testi.append(_norm(i.get("nome", "")))
        else:
            ingr_testi.append(_norm(str(i)))
    ingr_blob = " | ".join(ingr_testi)

    errori_gravi = []
    avvisi = []
    piatto = None

    # 1) match col piatto canonico
    for chiave, regola in REGOLE_CANONICHE.items():
        if chiave in nome_l:
            piatto = chiave
            # vietati: se UNO compare → errore grave
            for gruppo in regola["vietati"]:
                for sinonimo in gruppo:
                    if sinonimo in ingr_blob:
                        msg = f"'{sinonimo}' non va nella {chiave}. {regola['nota']}"
                        if is_rivisitazione:
                            # rivisitazione: è una scelta dichiarata, segnalo ma non blocco
                            avvisi.append(f"(rivisitazione) {msg}")
                        else:
                            errori_gravi.append(msg)
                        break
            # obbligatori: se un gruppo manca del tutto → avviso
            for gruppo in regola["obbligatori"]:
                if not any(s in ingr_blob for s in gruppo):
                    avvisi.append(
                        f"la {chiave} dovrebbe contenere {' o '.join(gruppo)} (non trovato)."
                    )
            break

    # 2) eresie universali (solo se il nome suggerisce piatto italiano tradizionale)
    for parola, spiegazione in ERESIE_GRAVI_UNIVERSALI.items():
        if parola in ingr_blob:
            # bacon/wurstel sono errori quasi sempre in cucina italiana
            if parola not in [s for g in REGOLE_CANONICHE.get(piatto, {}).get("vietati", []) for s in g]:
                avvisi.append(spiegazione)

    return {
        "ok": len(errori_gravi) == 0,
        "errori_gravi": errori_gravi,
        "avvisi": avvisi,
        "piatto_riconosciuto": piatto,
    }
