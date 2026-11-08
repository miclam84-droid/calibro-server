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
    # Il mix COSTRUITO (prima della diluizione) vale volume_pre_dil. Di questo, parte_alcolica e' il
    # volume di distillato/liquore al grado indicato; il resto e' la parte a bassa/zero gradazione
    # (succhi, sciroppi, modificanti) necessaria a far quadrare volume e gradazione. Mostrarlo rende
    # il conto chiuso: parte_alcolica + altri_ingredienti + acqua_diluizione = volume_finale.
    altri_ingredienti = volume_pre_dil - parte_alcolica
    # Gradazione massima pratica con questo distillato e questa tecnica (oltre, il target e' irraggiungibile).
    gradazione_max = round(gradazione_ingredienti / (1 + dil/100), 1)
    # Conservazione dell'alcol (Dave Arnold, Liquid Intelligence - cap. su proof/diluizione):
    # la diluizione aggiunge SOLO acqua, l'alcol puro e' invariato. Quindi la gradazione PRIMA della
    # diluizione e' piu' alta, ricavabile per pura algebra (nessuna costante nuova):
    #   gradazione_pre = alcol_ml / volume_pre_dil * 100 = gradazione_voluta * volume_finale / volume_pre_dil
    gradazione_pre_dil = round(alcol_ml / volume_pre_dil * 100, 1) if volume_pre_dil else 0.0
    proporzioni = {
        "parte_alcolica": f"~{parte_alcolica}ml (distillati/liquori a {gradazione_ingredienti}%)",
    }
    avviso = None
    if altri_ingredienti > 0:
        proporzioni["altri_ingredienti"] = f"~{altri_ingredienti}ml (succhi, sciroppi, modificanti a bassa gradazione)"
    elif altri_ingredienti < 0:
        # Target troppo alto: servirebbe piu' distillato del volume costruito. Non invento numeri, avviso.
        avviso = (f"A {gradazione_voluta}% vol il drink sarebbe quasi tutto distillato e la diluizione del "
                  f"{dil}% non basta a scendere: con distillati al {gradazione_ingredienti}% e tecnica "
                  f"{t['nome'].lower()} la gradazione pratica massima e' ~{gradazione_max}% vol. "
                  f"Alza la gradazione dei distillati o abbassa quella voluta.")
    proporzioni["acqua_da_diluizione"] = f"~{acqua_diluizione}ml (dal ghiaccio, NON aggiunta)"
    proporzioni["volume_finale"] = f"{volume_finale_ml}ml"
    risultato = {
        "obiettivo": f"{volume_finale_ml}ml a {gradazione_voluta}% vol · tecnica {t['nome']}",
        "tecnica": {"nome": t["nome"], "diluizione": f"{dil}%", "quando": t["quando"]},
        "proporzioni": proporzioni,
        "gradazione": {
            "finale_voluta": f"{gradazione_voluta}% vol",
            # fondata su conservazione dell'alcol (tecnica documentata di Arnold), non su un numero inventato
            "prima_della_diluizione": f"~{gradazione_pre_dil}% vol",
            "nota": "Costruisci il mix non diluito a ~"
                    f"{gradazione_pre_dil}% vol: la diluizione ({dil}%) lo porta al {gradazione_voluta}% finale. "
                    "L'alcol puro non cambia con la diluizione (si aggiunge solo acqua).",
        },
        "ghiaccio": "Cubi grandi e freddi (-18°C) per stirred: diluiscono meno e più lento. Ghiaccio "
                    "piccolo/umido = diluizione incontrollata.",
        "note": f"La diluizione ({dil}%) viene dalla TECNICA e dalla superficie del ghiaccio, non dal tempo. "
                f"Shakerato diluisce di più (ghiaccio frantumato = più superficie).",
        "punto_critico": "La gradazione finale dipende dalla diluizione. Stesso drink, tecnica diversa = drink diverso.",
    }
    if avviso:
        risultato["avviso"] = avviso
    return risultato
