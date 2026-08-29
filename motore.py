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
def scalatore_impasto(peso_totale_g, percentuali: dict) -> dict:
    """SPRINT 2 — Scala un impasto col metodo del panettiere (farina=100%).
    percentuali: {"farina":100, "acqua":70, "sale":2, "lievito":1, ...}
    Restituisce le grammature esatte per il peso totale desiderato."""
    somma_perc = sum(float(v) for v in percentuali.values())
    if somma_perc <= 0 or peso_totale_g <= 0:
        return {"errore": "percentuali o peso non validi"}
    # farina = peso_totale / (somma_percentuali/100)
    farina_g = peso_totale_g / (somma_perc / 100.0)
    grammature = {}
    for ing, perc in percentuali.items():
        grammature[ing] = round(farina_g * float(perc) / 100.0, 1)
    return {
        "calcolo": "scalatore_impasto",
        "peso_totale_g": round(peso_totale_g, 1),
        "farina_g": round(farina_g, 1),
        "grammature": grammature,
        "interpretazione": f"Per {peso_totale_g:.0f}g di impasto totale ti servono {farina_g:.0f}g di farina.",
        "leva_azione": "Pesa la farina esatta: tutto il resto è in percentuale su di essa.",
        "spiegazione": (f"Col metodo del panettiere la farina è il 100%. Somma percentuali {somma_perc:.0f}%, "
                        f"quindi farina = {peso_totale_g:.0f} / {somma_perc/100:.2f} = {farina_g:.0f}g.")
    }


def conversione_teglie(base1_cm, alt1_cm, base2_cm, alt2_cm) -> dict:
    """SPRINT 2 — Riproporziona le dosi da una teglia a un'altra (per area/superficie)."""
    area1 = base1_cm * alt1_cm
    area2 = base2_cm * alt2_cm
    if area1 <= 0:
        return {"errore": "dimensioni teglia di partenza non valide"}
    coef = area2 / area1
    return {
        "calcolo": "conversione_teglie",
        "area_partenza_cm2": round(area1, 1),
        "area_arrivo_cm2": round(area2, 1),
        "coefficiente": round(coef, 3),
        "interpretazione": (f"La teglia di arrivo ({base2_cm}×{alt2_cm}) è {coef:.2f}× quella di partenza "
                            f"({base1_cm}×{alt1_cm})."),
        "leva_azione": f"Moltiplica OGNI ingrediente della ricetta per {coef:.2f}.",
        "spiegazione": (f"Si scala per superficie: area partenza {area1:.0f}cm², area arrivo {area2:.0f}cm², "
                        f"coefficiente {coef:.2f}.")
    }


def food_cost_piatto(ingredienti: list, prezzo_vendita=None) -> dict:
    """SPRINT 2 — Food cost di un piatto. ingredienti: [{"nome","grammi","prezzo_kg"}].
    Se prezzo_kg manca per una voce, la marca come da inserire (mai trattino muto)."""
    costo_totale = 0.0; voci = []; mancanti = 0
    for i in ingredienti:
        if not isinstance(i, dict): continue
        nome = i.get("nome", "?")
        try: grammi = float(str(i.get("grammi", 0)).replace(",", "."))
        except Exception: grammi = 0
        pk = i.get("prezzo_kg")
        try: pk = float(str(pk).replace(",", ".")) if pk not in (None, "") else None
        except Exception: pk = None
        if pk is not None and grammi > 0:
            costo = (grammi / 1000.0) * pk
            costo_totale += costo
            voci.append({"nome": nome, "grammi": grammi, "prezzo_kg": pk, "costo": round(costo, 3)})
        else:
            voci.append({"nome": nome, "grammi": grammi, "costo": None,
                         "nota": "inserisci il prezzo al kg (orientativo)"})
            mancanti += 1
    costo_totale = round(costo_totale, 2)
    out = {"calcolo": "food_cost_piatto", "costo_totale": costo_totale, "voci": voci,
           "ingredienti_senza_prezzo": mancanti,
           "spiegazione": f"Costo materie prime del piatto: €{costo_totale:.2f}."}
    if prezzo_vendita:
        try:
            pv = float(prezzo_vendita)
            if pv > 0:
                pct = round(100 * costo_totale / pv, 1)
                out["prezzo_vendita"] = pv
                out["food_cost_perc"] = pct
                out["margine_lordo"] = round(pv - costo_totale, 2)
                out["interpretazione"] = (
                    f"Food cost {pct}%: " + (
                        "ottimo, sotto il 30%." if pct <= 30 else
                        "buono, sotto il 35%." if pct <= 35 else
                        "alto, sopra il 35% — rivedi porzioni o prezzo."))
                out["leva_azione"] = (
                    "Margine sano, mantieni." if pct <= 30 else
                    "Accettabile; puoi ottimizzare le grammature." if pct <= 35 else
                    "Alza il prezzo o riduci il costo degli ingredienti principali.")
        except Exception:
            pass
    return out


CALCOLI = {
    "diluizione": diluizione,
    "bilanciamento_sour": bilanciamento_sour,
    "idratazione_pane": idratazione_pane,
    "q10_fermentazione": q10_fermentazione,
    "estrazione_caffe": estrazione_caffe,
    "pareggia_acidita": pareggia_acidita,
    "scalatore_impasto": scalatore_impasto,
    "conversione_teglie": conversione_teglie,
    "food_cost_piatto": food_cost_piatto,
}


def _interpreta(nome, r):
    """SPRINT 2 — Livello 3: aggiunge interpretazione + leva d'azione deterministica al risultato.
    Regole if/elif sui valori (niente AI). Ogni calcolo dice: sei dentro/fuori bersaglio e cosa fare."""
    if not isinstance(r, dict) or "errore" in r:
        return r
    try:
        if nome == "diluizione":
            v = r.get("diluizione_perc", 0)
            abv = r.get("abv_finale_perc", 0)
            if v < 18:
                r["interpretazione"] = f"Sotto-diluito ({v}%): il drink risulta forte e caldo, gli aromi non si sono aperti."
                r["leva_azione"] = "Aumenta la mescolata (o lo shake) di 5-8 secondi con ghiaccio asciutto."
            elif v <= 25:
                r["interpretazione"] = f"Diluizione corretta ({v}%): bilanciamento nella finestra ideale, grado finale {abv:.0f}%."
                r["leva_azione"] = "Mantieni la tecnica. Servi subito ben freddo."
            elif v <= 30:
                r["interpretazione"] = f"Diluizione elevata ({v}%): adatta allo shakerato, attenzione a non spegnere il drink."
                r["leva_azione"] = "Se lo vuoi più deciso, riduci il tempo di shake o la quantità di ghiaccio."
            else:
                r["interpretazione"] = f"Troppo diluito ({v}%): il drink risulta acquoso e piatto."
                r["leva_azione"] = "Riduci nettamente tempo di agitazione e ghiaccio, o rifai il drink."
            r["fenomeno_id"] = "fen-diluizione"
        elif nome == "idratazione_pane":
            idr = r.get("idratazione_perc", 0)
            if idr < 55:
                r["interpretazione"] = f"Impasto asciutto ({idr}%): maglia più tenace, mollica compatta."
                r["leva_azione"] = "Per una mollica più alveolata aumenta l'acqua verso il 65-70%."
            elif idr <= 75:
                r["interpretazione"] = f"Idratazione media-alta ({idr}%): buon equilibrio maglia/alveolatura."
                r["leva_azione"] = "Cura la temperatura finale impasto (24-26°C) e le pieghe."
            else:
                r["interpretazione"] = f"Idratazione alta ({idr}%): mollica aperta ma impasto difficile da gestire."
                r["leva_azione"] = "Serve farina forte (W alto) e tecnica delle pieghe per reggere l'acqua."
            r["fenomeno_id"] = "fen-idratazione"
        elif nome == "estrazione_caffe":
            ey = r.get("extraction_yield_perc") or r.get("ey_perc")
            if ey is not None:
                if ey < 18:
                    r["interpretazione"] = f"Sotto-estratto ({ey}%): acido, aspro, corto in bocca."
                    r["leva_azione"] = "Macina più fine, o allunga il tempo/aumenta la dose acqua."
                elif ey <= 22:
                    r["interpretazione"] = f"Estrazione nella finestra ideale ({ey}%): dolcezza ed equilibrio."
                    r["leva_azione"] = "Mantieni i parametri. Ripeti identico."
                else:
                    r["interpretazione"] = f"Sovra-estratto ({ey}%): amaro, secco, astringente."
                    r["leva_azione"] = "Macina più grosso, o riduci tempo/temperatura."
                r["fenomeno_id"] = "fen-estrazione-caffe"
    except Exception:
        pass
    return r


def esegui(nome: str, parametri: dict) -> dict:
    """Punto unico di ingresso. Chiamato da app.py con nome calcolo e parametri."""
    fn = CALCOLI.get(nome)
    if not fn:
        return {"errore": f"calcolo '{nome}' non trovato. Disponibili: {list(CALCOLI)}"}
    try:
        r = fn(**parametri)
        return _interpreta(nome, r)
    except TypeError as e:
        return {"errore": f"parametri errati per '{nome}': {e}"}
    except Exception as e:
        return {"errore": str(e)}
