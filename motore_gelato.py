# motore_gelato.py - MOTORE OPERATIVO Gelato Pro.
# Parte dall'obiettivo (tipo gelato, quantita') e calcola:
#  - il BILANCIAMENTO target (zuccheri/grassi/solidi) come RANGE professionale (niente media spacciata per valore esatto);
#  - il PAC (potere anticongelante) e il POD (potere dolcificante) del mix zuccheri scelto, calcolati DAVVERO
#    dalla tabella ZUCCHERI (indici relativi al saccarosio=100) con media pesata sulle proporzioni.
#
# ONESTA' DEI DATI:
#  - PAC/POD indici relativi (saccarosio=100): valori standard del bilanciamento gelato professionale
#    (destrosio ~190/70, zucchero invertito/miele ~190/130, sciroppo di glucosio DE~60 ~55/50).
#    La media pesata di questi indici e' l'uso canonico della tabella -> calcolo FONDATO sul dato gia' presente.
#  - La mappa temperatura-di-vetrina -> "numero PAC bersaglio" NON e' derivabile dalla tabella presente:
#    resta una REGOLA PRATICA qualitativa, etichettata come tale. Nessun numero di PAC bersaglio inventato.

# valori di riferimento per il bilanciamento (% sul totale miscela) - fonte: bilanciamento gelato professionale (range)
BILANCIAMENTO = {
    "crema": {"zuccheri": (16, 20), "grassi": (6, 10), "solidi_magri_latte": (9, 11), "solidi_totali": (36, 42)},
    "frutta": {"zuccheri": (24, 28), "grassi": (0, 2), "solidi_magri_latte": (0, 3), "solidi_totali": (32, 38)},
    "cioccolato": {"zuccheri": (18, 22), "grassi": (8, 12), "solidi_magri_latte": (8, 10), "solidi_totali": (40, 46)},
}
# PAC (potere anticongelante) e POD (potere dolcificante) per zucchero (riferito al saccarosio=100)
ZUCCHERI = {
    "saccarosio": {"pac": 100, "pod": 100},
    "destrosio": {"pac": 190, "pod": 70},
    "sciroppo_glucosio": {"pac": 55, "pod": 50},
    "zucchero_invertito": {"pac": 190, "pod": 130},
    "miele": {"pac": 190, "pod": 130},
}

# mix zuccheri di default: regola classica del gelato alla crema (saccarosio + destrosio per alzare il PAC)
MIX_DEFAULT = {"saccarosio": 0.70, "destrosio": 0.30}


def _indici_blend(mix):
    """Media pesata di PAC e POD del mix zuccheri, usando la tabella ZUCCHERI (saccarosio=100).
    Ritorna (pac_index, pod_index, mix_normalizzato). Solleva ValueError su zucchero ignoto o proporzioni nulle.
    """
    tot = 0.0
    for nome, prop in mix.items():
        if nome not in ZUCCHERI:
            raise ValueError(f"zucchero sconosciuto: {nome}")
        if prop < 0:
            raise ValueError(f"proporzione negativa per {nome}")
        tot += prop
    if tot <= 0:
        raise ValueError("mix zuccheri vuoto")
    pac_index = sum(ZUCCHERI[n]["pac"] * p for n, p in mix.items()) / tot
    pod_index = sum(ZUCCHERI[n]["pod"] * p for n, p in mix.items()) / tot
    mix_norm = {n: round(p / tot, 3) for n, p in mix.items()}
    return pac_index, pod_index, mix_norm


def progetta_gelato(tipo="crema", quantita_g=1000, temp_vetrina=-12, mix_zuccheri=None):
    """Progetta il bilanciamento del gelato.
    Il BILANCIAMENTO e' dato come range professionale (con centro etichettato, non spacciato per valore esatto).
    PAC/POD del mix zuccheri sono CALCOLATI dalla tabella ZUCCHERI (media pesata, saccarosio=100).
    """
    b = BILANCIAMENTO.get(tipo, BILANCIAMENTO["crema"])
    mix = mix_zuccheri if mix_zuccheri else dict(MIX_DEFAULT)

    def centro(rng):
        return round((rng[0] + rng[1]) / 2, 1)

    # massa zuccheri stimata sul centro del range professionale (la base e' il range, non un numero "preciso")
    zuccheri_centro = centro(b["zuccheri"])
    massa_zuccheri_g = round(quantita_g * zuccheri_centro / 100)

    # calcolo VERO su tabella: indici PAC/POD del mix e loro equivalente in grammi-di-saccarosio
    pac_index, pod_index, mix_norm = _indici_blend(mix)
    # equivalente saccarosio: quanti g di saccarosio "pesano" come anticongelante / dolcificante questo mix
    antigelo_eq_sacc_g = round(massa_zuccheri_g * pac_index / 100)
    dolcezza_eq_sacc_g = round(massa_zuccheri_g * pod_index / 100)

    def pct_range(rng):
        return f"{rng[0]}-{rng[1]}% (centro {centro(rng)}%)"

    mix_desc = " + ".join(f"{round(p * 100)}% {n}" for n, p in mix_norm.items())

    return {
        "obiettivo": f"{quantita_g}g di gelato {tipo} · servizio {temp_vetrina}°C",
        "bilanciamento_target": {
            # RANGE professionale, non un singolo numero: onesto su dove sta il margine
            "zuccheri": pct_range(b["zuccheri"]),
            "grassi": pct_range(b["grassi"]),
            "solidi_magri_latte": pct_range(b["solidi_magri_latte"]),
            "solidi_totali": pct_range(b["solidi_totali"]),
        },
        "mix_zuccheri": {
            "composizione": mix_desc,
            "pac_index": round(pac_index, 1),   # saccarosio=100; >100 = piu' anticongelante (gelato piu' morbido)
            "pod_index": round(pod_index, 1),   # saccarosio=100; <100 = meno dolce a parita' di peso
            "nota": "PAC/POD = media pesata della tabella ZUCCHERI (saccarosio=100). "
                    "PAC>100: il mix abbassa il punto di congelamento piu' del solo saccarosio (gelato piu' spatolabile a freddo). "
                    "POD<100: a parita' di grammi e' meno dolce del saccarosio.",
        },
        "stima_su_massa_zuccheri": {
            "massa_zuccheri_g": f"~{massa_zuccheri_g}g (sul centro {zuccheri_centro}% del range {tipo})",
            "potere_anticongelante": f"~{antigelo_eq_sacc_g}g equivalenti-saccarosio (PAC)",
            "potere_dolcificante": f"~{dolcezza_eq_sacc_g}g equivalenti-saccarosio (POD)",
        },
        "servizio_vetrina": {
            # REGOLA PRATICA, non derivata dalla tabella: etichettata come tale, nessun numero-bersaglio inventato
            "etichetta": "regola pratica (NON calcolata dalla tabella)",
            "indicazione": f"Per servire a {temp_vetrina}°C il gelato deve restare spatolabile: "
                           "piu' freddo il servizio, piu' PAC serve (piu' destrosio/invertito nel mix). "
                           "La direzione e' fondata (PAC piu' alto = punto di congelamento piu' basso); "
                           "il valore esatto di PAC-bersaglio per ogni temperatura va tarato al banco, non e' in tabella.",
        },
        "punto_critico": "Il mix zuccheri (non solo 'quanto zucchero') decide la spatolabilita' in vetrina: "
                         "stesso zucchero totale, PAC diverso = consistenza diversa.",
    }
