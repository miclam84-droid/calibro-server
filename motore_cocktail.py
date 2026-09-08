# motore_cocktail.py - MOTORE OPERATIVO Cocktail Pro.
# Parte dall'obiettivo (drink, gradazione voluta), calcola diluizione + ghiaccio + tecnica.
# Basato su Dave Arnold (Liquid Intelligence): la diluizione dipende dalla tecnica, non dal tempo.

# diluizione per tecnica (% acqua aggiunta al drink finale) - Dave Arnold
TECNICHE = {
    "stirred": {"diluizione": 22, "nome": "Mescolato", "quando": "drink alcolici puliti (Martini, Negroni, Manhattan)"},
    "shaken": {"diluizione": 38, "nome": "Shakerato", "quando": "drink con agrumi/albume/sciroppi (Daiquiri, Sour)"},
    "thrown": {"diluizione": 30, "nome": "Lanciato", "quando": "via di mezzo, aera senza schiuma (Bloody Mary)"},
    "built": {"diluizione": 15, "nome": "Costruito nel bicchiere", "quando": "highball con soda (Gin Tonic)"},
}

def progetta_cocktail(volume_finale_ml=90, gradazione_voluta=22, tecnica="stirred", gradazione_ingredienti=40):
    """Progetta il cocktail: dato il volume e la gradazione voluta, calcola le proporzioni + diluizione."""
    t = TECNICHE.get(tecnica, TECNICHE["stirred"])
    dil = t["diluizione"]
    # volume di alcol prima della diluizione (a ritroso dalla gradazione voluta)
    # gradazione_finale = alcol / volume_finale; con diluizione il volume aumenta
    volume_pre_dil = round(volume_finale_ml / (1 + dil/100))
    alcol_ml = round(volume_finale_ml * gradazione_voluta/100)
    parte_alcolica = round(alcol_ml / (gradazione_ingredienti/100))
    acqua_diluizione = volume_finale_ml - volume_pre_dil
    return {
        "obiettivo": f"{volume_finale_ml}ml a {gradazione_voluta}% vol · tecnica {t['nome']}",
        "tecnica": {"nome": t["nome"], "diluizione": f"{dil}%", "quando": t["quando"]},
        "proporzioni": {
            "parte_alcolica": f"~{parte_alcolica}ml (distillati/liquori a {gradazione_ingredienti}%)",
            "acqua_da_diluizione": f"~{acqua_diluizione}ml (dal ghiaccio, NON aggiunta)",
            "volume_finale": f"{volume_finale_ml}ml",
        },
        "ghiaccio": "Cubi grandi e freddi (-18°C) per stirred: diluiscono meno e più lento. Ghiaccio "
                    "piccolo/umido = diluizione incontrollata.",
        "note": f"La diluizione ({dil}%) viene dalla TECNICA e dalla superficie del ghiaccio, non dal tempo. "
                f"Shakerato diluisce di più (ghiaccio frantumato = più superficie).",
        "punto_critico": "La gradazione finale dipende dalla diluizione. Stesso drink, tecnica diversa = drink diverso.",
    }
