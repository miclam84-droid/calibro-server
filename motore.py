"""
motore.py — calcoli esatti per Calibro.
Viene chiamato da app.py quando Sonnet rileva che la domanda richiede un numero calcolato.
Nessuna dipendenza esterna. Ogni funzione restituisce un dict con risultato + spiegazione.
"""


def diluizione(ingredienti: list, dil_perc: float) -> dict:
    """
    ingredienti: [{"nome": str, "vol_ml": float, "abv_perc": float}, ...]
    dil_perc: percentuale di diluizione attesa (22 mescolato, 27 shakerato)
    """
    vol0 = sum(i["vol_ml"] for i in ingredienti)
    etanolo = sum(i["vol_ml"] * i["abv_perc"] / 100 for i in ingredienti)
    if vol0 <= 0:
        return {"errore": "volume totale zero"}
    acqua = vol0 * dil_perc / 100
    vol_fin = vol0 + acqua
    abv0 = etanolo / vol0 * 100
    abv_fin = etanolo / vol_fin * 100
    return {
        "calcolo": "diluizione",
        "vol_iniziale_ml": round(vol0, 1),
        "abv_iniziale_perc": round(abv0, 1),
        "diluizione_perc": dil_perc,
        "acqua_fusione_ml": round(acqua, 1),
        "vol_finale_ml": round(vol_fin, 1),
        "abv_finale_perc": round(abv_fin, 1),
        "spiegazione": (
            f"Con {vol0:.0f}ml totali e {dil_perc}% di diluizione ({acqua:.0f}ml di acqua di fusione), "
            f"il grado scende da {abv0:.1f}% a {abv_fin:.1f}% su {vol_fin:.0f}ml nel bicchiere."
        )
    }


def bilanciamento_sour(spirit_vol, spirit_abv, agrume_vol, agrume_acid_perc,
                        sciroppo_vol, sciroppo_brix, dil_perc=25) -> dict:
    """Bilancia un sour e dice se è in equilibrio."""
    sub = spirit_vol + agrume_vol + sciroppo_vol
    acqua = sub * dil_perc / 100
    vf = sub + acqua
    if vf <= 0:
        return {"errore": "volume zero"}
    abv_fin = (spirit_vol * spirit_abv / 100) / vf * 100
    # densità sciroppo approssimata: 1.23 per 50 Brix, 1.31 per 65 Brix
    dens = 1.0 + (sciroppo_brix / 100) * 0.46
    zucchero = sciroppo_vol * dens * sciroppo_brix / 100
    brix_fin = zucchero / vf * 100
    acido_fin = (agrume_vol * agrume_acid_perc / 100) / vf * 100
    # zone classiche sour
    ok_abv = 14 <= abv_fin <= 19
    ok_brix = 9 <= brix_fin <= 14
    ok_acid = 0.9 <= acido_fin <= 1.4
    if ok_abv and ok_brix and ok_acid:
        verdetto = "in equilibrio — i tre assi cadono nella zona classica del sour"
    else:
        fix = []
        if not ok_abv:
            fix.append("forza " + ("bassa: più distillato" if abv_fin < 14 else "alta: più diluizione"))
        if not ok_brix:
            fix.append("dolce " + ("basso: più sciroppo" if brix_fin < 9 else "alto: meno sciroppo"))
        if not ok_acid:
            fix.append("acido " + ("basso: più agrume" if acido_fin < 0.9 else "alto: meno agrume"))
        verdetto = "fuori equilibrio — " + " · ".join(fix)
    return {
        "calcolo": "bilanciamento_sour",
        "vol_finale_ml": round(vf, 1),
        "abv_finale_perc": round(abv_fin, 1),
        "brix_finale": round(brix_fin, 1),
        "acidita_finale_perc": round(acido_fin, 2),
        "verdetto": verdetto,
        "spiegazione": (
            f"Nel bicchiere: {abv_fin:.1f}% ABV, {brix_fin:.1f} Brix, {acido_fin:.2f}% acido titolabile. "
            f"Risultato: {verdetto}."
        )
    }


def idratazione_pane(farina_g, acqua_g) -> dict:
    """Baker's % — idratazione impasto."""
    if farina_g <= 0:
        return {"errore": "farina zero"}
    idr = acqua_g / farina_g * 100
    if idr < 60:
        zona = "molto bassa — pane compatto, crosta dura (crackers, pane di semola)"
    elif idr < 65:
        zona = "bassa — pizza napoletana (60-65%), ciabatta compatta"
    elif idr == 65:
        zona = "limite superiore pizza napoletana / standard pane comune e baguette (65-72%)"
    elif idr < 72:
        zona = "standard — pane comune, baguette (65-72%)"
    elif idr < 80:
        zona = "alta — ciabatta, focaccia, pizza romana (72-80%)"
    else:
        zona = "molto alta — pastella, pane in cassetta (>80%)"
    return {
        "calcolo": "idratazione_pane",
        "farina_g": farina_g,
        "acqua_g": acqua_g,
        "idratazione_perc": round(idr, 1),
        "zona": zona,
        "spiegazione": f"Idratazione {idr:.1f}% ({acqua_g:.0f}g acqua su {farina_g:.0f}g farina). Zona: {zona}."
    }


def q10_fermentazione(tempo_base_h, temp_ref_c, temp_reale_c) -> dict:
    """Calcola il tempo di fermentazione corretto per Q10 (~2 ogni 8°C)."""
    if tempo_base_h <= 0:
        return {"errore": "tempo base zero"}
    t_new = tempo_base_h * (2 ** ((temp_ref_c - temp_reale_c) / 8))
    delta = temp_reale_c - temp_ref_c
    if delta > 0:
        direzione = f"{abs(delta):.0f}°C più caldo del riferimento — fermentazione accelerata"
    elif delta < 0:
        direzione = f"{abs(delta):.0f}°C più freddo del riferimento — fermentazione rallentata"
    else:
        direzione = "stessa temperatura di riferimento"
    return {
        "calcolo": "q10_fermentazione",
        "tempo_base_h": tempo_base_h,
        "temp_ref_c": temp_ref_c,
        "temp_reale_c": temp_reale_c,
        "tempo_previsto_h": round(t_new, 1),
        "direzione": direzione,
        "spiegazione": (
            f"A {temp_reale_c}°C ({direzione}), il tempo di fermentazione previsto è "
            f"{t_new:.1f}h invece di {tempo_base_h:.1f}h a {temp_ref_c}°C."
        )
    }


def estrazione_caffe(dose_g, bevanda_g, tds_perc) -> dict:
    """Calcola EY% e diagnostica estrazione."""
    if dose_g <= 0:
        return {"errore": "dose zero"}
    ey = bevanda_g * tds_perc / dose_g
    # diagnostica a 4 quadranti
    if ey < 18 and tds_perc < 7:
        diag = "sottoestratto e debole — macinatura più fine o più dose"
    elif ey < 18 and tds_perc >= 7:
        diag = "sottoestratto ma concentrato — macinatura più fine, meno dose"
    elif ey > 22 and tds_perc < 7:
        diag = "sovrestratto e debole — macinatura più grossa, più dose"
    elif ey > 22 and tds_perc >= 7:
        diag = "sovrestratto e concentrato — macinatura più grossa o meno tempo"
    else:
        diag = "nella zona di equilibrio (EY 18-22%)"
    ratio = bevanda_g / dose_g if dose_g else 0
    return {
        "calcolo": "estrazione_caffe",
        "dose_g": dose_g,
        "bevanda_g": bevanda_g,
        "tds_perc": tds_perc,
        "ey_perc": round(ey, 1),
        "ratio": f"1:{ratio:.1f}",
        "diagnostica": diag,
        "spiegazione": (
            f"EY {ey:.1f}% con TDS {tds_perc}% su ratio 1:{ratio:.1f}. {diag.capitalize()}."
        )
    }


def pareggia_acidita(vol_ml, acido_cur_perc, acido_tgt_perc) -> dict:
    """Grammi di acido citrico da aggiungere per portare un succo al target."""
    if vol_ml <= 0:
        return {"errore": "volume zero"}
    if acido_tgt_perc <= acido_cur_perc:
        return {
            "calcolo": "pareggia_acidita",
            "vol_ml": vol_ml,
            "acido_attuale_perc": acido_cur_perc,
            "acido_target_perc": acido_tgt_perc,
            "acido_citrico_g": 0,
            "spiegazione": (
                f"Il succo è già a {acido_cur_perc}% di acidità titolabile, "
                f"superiore al target di {acido_tgt_perc}%. "
                f"L'acido citrico aggiunge acidità, non la rimuove: "
                f"per abbassare l'acidità devi diluire con acqua o aggiungere un tampone basico."
            )
        }
    g = (acido_tgt_perc - acido_cur_perc) / 100 * vol_ml
    return {
        "calcolo": "pareggia_acidita",
        "vol_ml": vol_ml,
        "acido_attuale_perc": acido_cur_perc,
        "acido_target_perc": acido_tgt_perc,
        "acido_citrico_g": round(g, 1),
        "spiegazione": (
            f"Per portare {vol_ml:.0f}ml di succo da {acido_cur_perc}% a {acido_tgt_perc}% "
            f"di acidità titolabile: aggiungi {g:.1f}g di acido citrico e mescola fino a sciogliere."
        )
    }


# ── DISPATCHER ────────────────────────────────────────────────────────────────
CALCOLI = {
    "diluizione": diluizione,
    "bilanciamento_sour": bilanciamento_sour,
    "idratazione_pane": idratazione_pane,
    "q10_fermentazione": q10_fermentazione,
    "estrazione_caffe": estrazione_caffe,
    "pareggia_acidita": pareggia_acidita,
}


def esegui(nome: str, parametri: dict) -> dict:
    """Punto unico di ingresso. Chiamato da app.py con nome calcolo e parametri."""
    fn = CALCOLI.get(nome)
    if not fn:
        return {"errore": f"calcolo '{nome}' non trovato. Disponibili: {list(CALCOLI)}"}
    try:
        return fn(**parametri)
    except TypeError as e:
        return {"errore": f"parametri errati per '{nome}': {e}"}
    except Exception as e:
        return {"errore": str(e)}
