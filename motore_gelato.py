# motore_gelato.py - MOTORE OPERATIVO Gelato Pro.
# Parte dall'obiettivo (tipo gelato, quantità), calcola il BILANCIAMENTO (zuccheri/grassi/solidi)
# + PAC (potere anticongelante) + POD (potere dolcificante). Da Modernist/gelato science.

# valori di riferimento per il bilanciamento (% sul totale miscela) - fonte gelato professionale
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

def progetta_gelato(tipo="crema", quantita_g=1000, temp_vetrina=-12):
    """Progetta il bilanciamento del gelato. PAC target dipende dalla temperatura di vetrina voluta."""
    b = BILANCIAMENTO.get(tipo, BILANCIAMENTO["crema"])
    def mid(rng): return round((rng[0]+rng[1])/2, 1)
    zuccheri_pct = mid(b["zuccheri"])
    grassi_pct = mid(b["grassi"])
    solidi_pct = mid(b["solidi_totali"])
    # PAC target: più freddo il servizio, più PAC serve (per restare cremoso). ~-12°C = PAC ~26-28
    pac_target = 27 if temp_vetrina <= -12 else 24
    return {
        "obiettivo": f"{quantita_g}g di gelato {tipo} · servizio {temp_vetrina}°C",
        "bilanciamento": {
            "zuccheri": f"{zuccheri_pct}% ({round(quantita_g*zuccheri_pct/100)}g)",
            "grassi": f"{grassi_pct}% ({round(quantita_g*grassi_pct/100)}g)",
            "solidi_totali": f"{solidi_pct}% ({round(quantita_g*solidi_pct/100)}g)",
            "acqua": f"{round(100-solidi_pct,1)}% ({round(quantita_g*(100-solidi_pct)/100)}g)",
        },
        "pac_target": pac_target,
        "mix_zuccheri_consigliato": "70% saccarosio + 30% destrosio (per PAC bilanciato)",
        "note": f"PAC target ~{pac_target} per servizio a {temp_vetrina}°C (cremosità senza durezza). "
                f"Sotto: il gelato è duro in vetrina. Sopra: si scioglie troppo. Il destrosio alza il PAC.",
        "punto_critico": "Il bilanciamento zuccheri decide la spatolabilità in vetrina. Non solo 'quanto zucchero'.",
    }
