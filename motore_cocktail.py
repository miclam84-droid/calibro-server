# motore_cocktail.py - MOTORE OPERATIVO Cocktail Pro.
# Parte dall'obiettivo (drink, gradazione voluta), calcola diluizione + ghiaccio + tecnica.
# Basato su Dave Arnold (Liquid Intelligence): la diluizione dipende dalla tecnica, non dal tempo.
# Output localizzato: it (default), en, es. Le etichette del frontend restano in _L; qui si traducono
# i VALORI e le note generati dal motore, che prima restavano in italiano anche a UI inglese/spagnola.

# diluizione per tecnica (% acqua aggiunta al drink finale) - Dave Arnold
TECNICHE = {
    "stirred": {"diluizione": 22,
                "nome": {"it": "Mescolato", "en": "Stirred", "es": "Mezclado"},
                "quando": {"it": "drink alcolici puliti (Martini, Negroni, Manhattan)",
                           "en": "clean spirit-forward drinks (Martini, Negroni, Manhattan)",
                           "es": "tragos espirituosos limpios (Martini, Negroni, Manhattan)"}},
    "shaken": {"diluizione": 38,
               "nome": {"it": "Shakerato", "en": "Shaken", "es": "Batido"},
               "quando": {"it": "drink con agrumi/albume/sciroppi (Daiquiri, Sour)",
                          "en": "drinks with citrus/egg white/syrups (Daiquiri, Sour)",
                          "es": "tragos con cítricos/clara/jarabes (Daiquiri, Sour)"}},
    "thrown": {"diluizione": 30,
               "nome": {"it": "Lanciato", "en": "Thrown", "es": "Lanzado"},
               "quando": {"it": "via di mezzo, aera senza schiuma (Bloody Mary)",
                          "en": "a middle ground, aerates without foam (Bloody Mary)",
                          "es": "término medio, airea sin espuma (Bloody Mary)"}},
    "built": {"diluizione": 15,
              "nome": {"it": "Costruito nel bicchiere", "en": "Built in the glass", "es": "Construido en el vaso"},
              "quando": {"it": "highball con soda (Gin Tonic)",
                         "en": "highballs with soda (Gin & Tonic)",
                         "es": "highballs con soda (Gin Tonic)"}},
}

# Fragmenti traducibili (template .format). Una sola fonte per lingua, niente numeri a memoria.
STR = {
    "obiettivo": {"it": "{V}ml a {g}% vol · tecnica {tec}",
                  "en": "{V}ml at {g}% ABV · {tec} technique",
                  "es": "{V}ml al {g}% vol · técnica {tec}"},
    "parte_alcolica": {"it": "~{x}ml (distillati/liquori a {G}%)",
                       "en": "~{x}ml (spirits/liqueurs at {G}%)",
                       "es": "~{x}ml (destilados/licores al {G}%)"},
    "altri_ingredienti": {"it": "~{x}ml (succhi, sciroppi, modificanti a bassa gradazione)",
                          "en": "~{x}ml (juices, syrups, low-proof modifiers)",
                          "es": "~{x}ml (zumos, jarabes, modificadores de baja graduación)"},
    "acqua": {"it": "~{x}ml (dal ghiaccio, NON aggiunta)",
              "en": "~{x}ml (from the ice, NOT added)",
              "es": "~{x}ml (del hielo, NO añadida)"},
    "volume_finale": {"it": "{V}ml", "en": "{V}ml", "es": "{V}ml"},
    "grad_vol": {"it": "{g}% vol", "en": "{g}% ABV", "es": "{g}% vol"},
    "grad_pre": {"it": "~{g}% vol", "en": "~{g}% ABV", "es": "~{g}% vol"},
    "grad_nota": {"it": "Costruisci il mix non diluito a ~{pre}% vol: la diluizione ({dil}%) lo porta al {g}% finale. L'alcol puro non cambia con la diluizione (si aggiunge solo acqua).",
                  "en": "Build the undiluted mix at ~{pre}% ABV: dilution ({dil}%) brings it to the final {g}%. Pure alcohol doesn't change with dilution (only water is added).",
                  "es": "Construye la mezcla sin diluir a ~{pre}% vol: la dilución ({dil}%) la lleva al {g}% final. El alcohol puro no cambia con la dilución (solo se añade agua)."},
    "ghiaccio": {"it": "Cubi grandi e freddi (-18°C) per stirred: diluiscono meno e più lento. Ghiaccio piccolo/umido = diluizione incontrollata.",
                 "en": "Large, cold cubes (-18°C) for stirred: they dilute less and more slowly. Small/wet ice = uncontrolled dilution.",
                 "es": "Cubos grandes y fríos (-18°C) para stirred: diluyen menos y más lento. Hielo pequeño/húmedo = dilución incontrolada."},
    "note": {"it": "La diluizione ({dil}%) viene dalla TECNICA e dalla superficie del ghiaccio, non dal tempo. Shakerato diluisce di più (ghiaccio frantumato = più superficie).",
             "en": "Dilution ({dil}%) comes from the TECHNIQUE and the ice surface, not from time. Shaking dilutes more (crushed ice = more surface).",
             "es": "La dilución ({dil}%) viene de la TÉCNICA y de la superficie del hielo, no del tiempo. Batir diluye más (hielo triturado = más superficie)."},
    "punto_critico": {"it": "La gradazione finale dipende dalla diluizione. Stesso drink, tecnica diversa = drink diverso.",
                      "en": "The final strength depends on dilution. Same drink, different technique = different drink.",
                      "es": "La graduación final depende de la dilución. Mismo trago, técnica distinta = trago distinto."},
    "avviso": {"it": "A {g}% vol il drink sarebbe quasi tutto distillato e la diluizione del {dil}% non basta a scendere: con distillati al {G}% e tecnica {tec} la gradazione pratica massima è ~{gmax}% vol. Alza la gradazione dei distillati o abbassa quella voluta.",
               "en": "At {g}% ABV the drink would be almost all spirit and {dil}% dilution isn't enough to bring it down: with spirits at {G}% and a {tec} technique the practical maximum is ~{gmax}% ABV. Raise the spirit strength or lower the target.",
               "es": "Al {g}% vol el trago sería casi todo destilado y la dilución del {dil}% no basta para bajar: con destilados al {G}% y técnica {tec} la graduación práctica máxima es ~{gmax}% vol. Sube la graduación de los destilados o baja la deseada."},
}

def _L(d, lang):
    """Ritorna la stringa nella lingua richiesta, fallback su italiano."""
    return d.get(lang, d["it"]) if isinstance(d, dict) else d

def _num(x):
    """22.0 -> '22', 22.5 -> '22.5' (niente .0 inutili negli output)."""
    x = round(float(x), 1)
    return str(int(x)) if x == int(x) else str(x)

def progetta_cocktail(volume_finale_ml=90, gradazione_voluta=22, tecnica="stirred", gradazione_ingredienti=40, lang="it"):
    """Progetta il cocktail: dato il volume e la gradazione voluta, calcola le proporzioni + diluizione."""
    if lang not in ("it", "en", "es"):
        lang = "it"
    t = TECNICHE.get(tecnica, TECNICHE["stirred"])
    dil = t["diluizione"]
    tec_nome = _L(t["nome"], lang)
    # volume di alcol prima della diluizione (a ritroso dalla gradazione voluta)
    volume_pre_dil = round(volume_finale_ml / (1 + dil/100))
    alcol_ml = round(volume_finale_ml * gradazione_voluta/100)
    parte_alcolica = round(alcol_ml / (gradazione_ingredienti/100))
    acqua_diluizione = volume_finale_ml - volume_pre_dil
    # Il mix COSTRUITO (prima della diluizione) vale volume_pre_dil. Di questo, parte_alcolica e' il
    # volume di distillato/liquore al grado indicato; il resto e' la parte a bassa/zero gradazione
    # (succhi, sciroppi, modificanti) necessaria a far quadrare volume e gradazione. Mostrarlo rende
    # il conto chiuso: parte_alcolica + altri_ingredienti + acqua_diluizione = volume_finale.
    altri_ingredienti = volume_pre_dil - parte_alcolica
    # Gradazione massima pratica con questo distillato e questa tecnica (oltre, il target e' irraggiungibile).
    gradazione_max = round(gradazione_ingredienti / (1 + dil/100), 1)
    # Conservazione dell'alcol (Dave Arnold): la diluizione aggiunge SOLO acqua, l'alcol puro e' invariato.
    gradazione_pre_dil = round(alcol_ml / volume_pre_dil * 100, 1) if volume_pre_dil else 0.0

    g = _num(gradazione_voluta); G = _num(gradazione_ingredienti)
    proporzioni = {
        "parte_alcolica": _L(STR["parte_alcolica"], lang).format(x=parte_alcolica, G=G),
    }
    avviso = None
    if altri_ingredienti > 0:
        proporzioni["altri_ingredienti"] = _L(STR["altri_ingredienti"], lang).format(x=altri_ingredienti)
    elif altri_ingredienti < 0:
        # Target troppo alto: servirebbe piu' distillato del volume costruito. Non invento numeri, avviso.
        avviso = _L(STR["avviso"], lang).format(g=g, dil=dil, G=G, tec=tec_nome.lower(), gmax=_num(gradazione_max))
    proporzioni["acqua_da_diluizione"] = _L(STR["acqua"], lang).format(x=acqua_diluizione)
    proporzioni["volume_finale"] = _L(STR["volume_finale"], lang).format(V=volume_finale_ml)

    risultato = {
        "obiettivo": _L(STR["obiettivo"], lang).format(V=volume_finale_ml, g=g, tec=tec_nome),
        "tecnica": {"nome": tec_nome, "diluizione": f"{dil}%", "quando": _L(t["quando"], lang)},
        "proporzioni": proporzioni,
        "gradazione": {
            "finale_voluta": _L(STR["grad_vol"], lang).format(g=g),
            "prima_della_diluizione": _L(STR["grad_pre"], lang).format(g=_num(gradazione_pre_dil)),
            "nota": _L(STR["grad_nota"], lang).format(pre=_num(gradazione_pre_dil), dil=dil, g=g),
        },
        "ghiaccio": _L(STR["ghiaccio"], lang),
        "note": _L(STR["note"], lang).format(dil=dil),
        "punto_critico": _L(STR["punto_critico"], lang),
    }
    if avviso:
        risultato["avviso"] = avviso
    return risultato
