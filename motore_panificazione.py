# motore_panificazione.py - il MOTORE OPERATIVO Panificazione Pro.
# Non un calcolatore (divisione), ma un motore: parte dall'OBIETTIVO, progetta il PROCESSO.
# Formule dal grounding verificato (Hamelman, Modernist Bread). Il differenziatore vs MasterBiga.

def _lievito_per_temperatura(temp_c, ore, base_pct=0.3):
    """Lievito fresco % sulla farina, calcolato sulla temperatura (Hamelman: fermentazione x3 ogni 9°C).
    Base: 0.3% per ~8h a 24°C. Aggiusta per temperatura e tempo reali."""
    # fattore temperatura: ogni +9°C la fermentazione tripla → serve 1/3 del lievito
    delta = temp_c - 24.0
    fattore_temp = 3.0 ** (delta / 9.0)  # >1 se più caldo (serve meno lievito → divido)
    # fattore tempo: più ore → meno lievito (proporzionale inverso, base 8h)
    fattore_tempo = 8.0 / max(ore, 1)
    lievito = base_pct / fattore_temp * fattore_tempo
    return max(0.01, round(lievito, 3))

def _temp_acqua(temp_finale_voluta, temp_farina, temp_ambiente, calore_impasto=6):
    """Temperatura dell'acqua per centrare la temperatura finale impasto.
    Regola classica: TempAcqua = (TempFinale × 3) - TempFarina - TempAmbiente - CaloreImpastamento."""
    ta = (temp_finale_voluta * 3) - temp_farina - temp_ambiente - calore_impasto
    return round(ta, 1)

# parametri per tipo di prodotto (dal grounding)
TIPI = {
    "pizza_napoletana": {"idratazione": 62, "sale": 2.8, "olio": 0, "W": "260-320", "temp_finale": 24, "cottura": "485°C, 60-90s"},
    "pizza_teglia":     {"idratazione": 78, "sale": 2.5, "olio": 3, "W": "320-380", "temp_finale": 24, "cottura": "250°C, 15-20min"},
    "pane":             {"idratazione": 68, "sale": 2.2, "olio": 0, "W": "260-320", "temp_finale": 24, "cottura": "230°C, 40-50min"},
    "focaccia":         {"idratazione": 80, "sale": 2.2, "olio": 5, "W": "300-340", "temp_finale": 24, "cottura": "220°C, 20-25min"},
}

# metodi prefermento (dal grounding)
METODI = {
    "diretto": {"nome": "Impasto diretto", "pre_pct": 0},
    "biga":    {"nome": "Biga", "pre_pct": 50, "pre_idr": 45, "pre_lievito": 1, "pre_tempo": "16-18h a 18°C"},
    "poolish": {"nome": "Poolish", "pre_pct": 30, "pre_idr": 100, "pre_lievito": 0.8, "pre_tempo": "12-16h a 20°C"},
    "madre":   {"nome": "Lievito madre", "pre_pct": 25, "pre_idr": 50, "pre_lievito": 0, "pre_tempo": "8-24h secondo maturazione"},
}

def progetta(tipo, n_panetti, peso_panetto, metodo="diretto", idratazione=None,
             temp_ambiente=22, temp_farina=20, ore_lievitazione=8):
    """IL MOTORE: dato l'obiettivo, progetta il processo completo.
    Ritorna dosi + lievito + temp acqua + timeline + parametri."""
    tp = TIPI.get(tipo, TIPI["pizza_napoletana"])
    idr = idratazione or tp["idratazione"]
    met = METODI.get(metodo, METODI["diretto"])

    # 1. FARINA TOTALE (a ritroso dal peso finale)
    peso_totale = n_panetti * peso_panetto
    # peso impasto = farina + acqua + sale + lievito(~0) → farina = peso / (1 + idr/100 + sale/100 + olio/100)
    denom = 1 + idr/100 + tp["sale"]/100 + tp["olio"]/100
    farina_tot = round(peso_totale / denom)
    acqua_tot = round(farina_tot * idr/100)
    sale = round(farina_tot * tp["sale"]/100, 1)
    olio = round(farina_tot * tp["olio"]/100, 1) if tp["olio"] else 0

    # 2. LIEVITO sulla temperatura (Hamelman)
    lievito_pct = _lievito_per_temperatura(temp_ambiente, ore_lievitazione)
    lievito_g = round(farina_tot * lievito_pct/100, 2)

    # 3. TEMPERATURA ACQUA
    temp_acqua = _temp_acqua(tp["temp_finale"], temp_farina, temp_ambiente)

    # 4. PREFERMENTO (se biga/poolish/madre)
    prefermento = None
    if met["pre_pct"] > 0:
        farina_pre = round(farina_tot * met["pre_pct"]/100)
        acqua_pre = round(farina_pre * met["pre_idr"]/100)
        lievito_pre = round(farina_pre * met.get("pre_lievito",0)/100, 2)
        prefermento = {
            "tipo": met["nome"], "farina": farina_pre, "acqua": acqua_pre,
            "lievito": lievito_pre, "tempo": met.get("pre_tempo",""),
            "farina_impasto_finale": farina_tot - farina_pre,
            "acqua_impasto_finale": acqua_tot - acqua_pre,
        }

    return {
        "obiettivo": f"{n_panetti} panetti da {peso_panetto}g ({tp.get('W','')} · idratazione {idr}%)",
        "dosi": {"farina": farina_tot, "acqua": acqua_tot, "sale": sale, "olio": olio or None,
                 "lievito_fresco": lievito_g, "lievito_pct": lievito_pct},
        "temperatura_acqua": temp_acqua,
        "temp_finale_impasto": tp["temp_finale"],
        "prefermento": prefermento,
        "cottura": tp["cottura"],
        "note": f"Lievito calcolato per {temp_ambiente}°C ambiente / {ore_lievitazione}h (Hamelman: x3 ogni 9°C). "
                f"A temperatura più alta serve meno lievito. Temperatura acqua per centrare {tp['temp_finale']}°C finali.",
        "diagnosi_disponibile": True,  # collegamento alla chat: "chiedi a Matter su questo impasto"
    }
