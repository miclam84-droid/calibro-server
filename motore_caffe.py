# motore_caffe.py - MOTORE OPERATIVO Caffe' Pro (espresso + filtro).
# Calcolo VERO sugli standard CITATI della specialty coffee (SCA - Specialty Coffee Association,
# "Golden Cup" / Brewing Control Chart):
#   - resa di estrazione (Extraction Yield) target 18-22%
#   - TDS (Total Dissolved Solids) in tazza 1.15-1.35% (CAFFE' FILTRO; box ideale del Brewing Control Chart)
#   - brew ratio (caffe:acqua) ~1:15-1:18 (filtro) / ~1:2 (espresso)
#
# RELAZIONE FONDANTE (SCA Brewing Control Chart / E. Lockhart, coffee brewing handbook):
#   solidi_disciolti = TDS% * massa_bevanda
#   Extraction Yield% = solidi_disciolti / dose_secca * 100
#   massa_bevanda = acqua_in - acqua_trattenuta_dai_fondi
# Costante citata: LRR (Liquid Retained Ratio) ~2.0 g di acqua trattenuta per g di caffe' macinato
# (valore comunemente usato nei calcolatori di estrazione SCA; e' una stima, etichettata come tale).
#
# ONESTA' DEI DATI: ogni numero qui o viene dallo standard SCA citato o e' calcolato dalle sue relazioni.
# Il TDS 1.15-1.35% vale per il FILTRO: per l'espresso NON si assume un TDS (serve rifrattometro), si
# calcola solo cio' che e' fondato (resa in tazza dal brew ratio, finestra EY target, parametri operativi).

# Standard SCA "Golden Cup"
EY_MIN, EY_MAX = 18.0, 22.0          # % extraction yield
EY_TARGET = 20.0                     # centro della finestra Golden Cup
TDS_MIN, TDS_MAX = 1.15, 1.35        # % TDS in tazza (filtro)
LRR = 2.0                            # g acqua trattenuta per g di caffe' macinato (stima citata)

RATIO_FILTRO_DEFAULT = 16.0          # 1:16 (dentro la finestra SCA 1:15-1:18, ~60 g/L)
RATIO_ESPRESSO_DEFAULT = 2.0         # 1:2 (ratio espresso classico, SCA ~1:1.5-1:2.5)


def _tds_previsto(dose_g, ratio, ey_pct):
    """TDS% previsto in tazza data dose, brew ratio e resa di estrazione, via relazione SCA.
    massa_bevanda = acqua - acqua_trattenuta = dose*ratio - LRR*dose = dose*(ratio - LRR).
    TDS% = EY% * dose / massa_bevanda = EY% / (ratio - LRR).
    """
    denom = ratio - LRR
    if denom <= 0:
        raise ValueError("brew ratio troppo basso rispetto all'acqua trattenuta (ratio <= LRR)")
    return ey_pct / denom


def progetta_caffe(metodo="espresso", dose_g=18, brew_ratio=None, target_ey=EY_TARGET):
    """Progetta l'estrazione sugli standard SCA.
    Espresso: resa in tazza dal brew ratio 1:2 (cit.), finestra EY 18-22%.
    Filtro: calcola acqua, massa bevanda (LRR), e TDS previsto alla resa target; verifica il box SCA 1.15-1.35%.
    """
    if dose_g <= 0:
        raise ValueError("dose deve essere > 0")

    if metodo == "espresso":
        ratio = brew_ratio if brew_ratio else RATIO_ESPRESSO_DEFAULT
        resa_g = round(dose_g * ratio, 1)
        return {
            "obiettivo": f"Espresso da {dose_g}g",
            "standard": "SCA (espresso ratio ~1:1.5-1:2.5; Golden Cup EY 18-22%)",
            "brew_ratio": f"1:{ratio:g} (caffe:bevanda in tazza)",
            "resa": f"{dose_g}g caffe' → {resa_g}g in tazza",
            "resa_estrazione_target": f"{EY_MIN:g}-{EY_MAX:g}% (centro {target_ey:g}%) — richiede rifrattometro per misurarla",
            "tempo": "25-30 secondi",
            "temperatura": "90-94°C (SCA ~90-96°C)",
            "macinatura": "fine (regola per centrare i 25-30s)",
            "nota_onesta": "Per l'espresso NON stimo il TDS: il box 1.15-1.35% e' uno standard FILTRO. "
                           "TDS e resa dell'espresso vanno misurati al rifrattometro; qui calcolo solo la resa in "
                           "tazza dal brew ratio citato e do la finestra EY target.",
            "punto_critico": "Il tempo (25-30s) e il brew ratio 1:2 decidono forza ed estrazione; "
                             "il tempo si regola con la macinatura.",
        }

    # ---- FILTRO: calcolo vero sul Brewing Control Chart ----
    ratio = brew_ratio if brew_ratio else RATIO_FILTRO_DEFAULT
    acqua_g = round(dose_g * ratio, 1)
    acqua_trattenuta_g = round(LRR * dose_g, 1)
    massa_bevanda_g = round(acqua_g - acqua_trattenuta_g, 1)
    if massa_bevanda_g <= 0:
        raise ValueError("ratio troppo basso: nessuna bevanda dopo l'acqua trattenuta dai fondi")

    tds_target = _tds_previsto(dose_g, ratio, target_ey)
    tds_a_ey_min = _tds_previsto(dose_g, ratio, EY_MIN)
    tds_a_ey_max = _tds_previsto(dose_g, ratio, EY_MAX)
    nel_box = TDS_MIN <= tds_target <= TDS_MAX

    if tds_target > TDS_MAX:
        verdetto = f"TDS previsto {tds_target:.2f}% sopra il box SCA ({TDS_MIN}-{TDS_MAX}%): tazza troppo forte, alza il ratio (piu' acqua)."
    elif tds_target < TDS_MIN:
        verdetto = f"TDS previsto {tds_target:.2f}% sotto il box SCA ({TDS_MIN}-{TDS_MAX}%): tazza troppo debole, abbassa il ratio (meno acqua)."
    else:
        verdetto = f"TDS previsto {tds_target:.2f}% dentro il box SCA ({TDS_MIN}-{TDS_MAX}%)."

    return {
        "obiettivo": f"Caffe' filtro da {dose_g}g",
        "standard": "SCA Brewing Control Chart / Golden Cup (EY 18-22%, TDS 1.15-1.35%, ratio ~1:15-1:18)",
        "brew_ratio": f"1:{ratio:g} (caffe:acqua)",
        "acqua": f"{acqua_g}g acqua",
        "acqua_trattenuta": f"~{acqua_trattenuta_g}g trattenuti dai fondi (LRR~{LRR} g/g, stima citata)",
        "massa_bevanda": f"~{massa_bevanda_g}g in tazza",
        "resa_estrazione_target": f"{target_ey:g}% (finestra SCA {EY_MIN:g}-{EY_MAX:g}%)",
        "tds_previsto": {
            "al_target": f"{tds_target:.2f}% (a resa {target_ey:g}%)",
            "alla_resa_18pct": f"{tds_a_ey_min:.2f}%",
            "alla_resa_22pct": f"{tds_a_ey_max:.2f}%",
            "dentro_box_sca": nel_box,
            "verdetto": verdetto,
        },
        "tempo": "2:30-3:30 (V60), 4min (French press)",
        "temperatura": "92-96°C (SCA ~90-96°C)",
        "macinatura": "media (sabbia grossa); piu' fine alza la resa, piu' grossa la abbassa",
        "nota_onesta": "TDS calcolato dalla relazione SCA (TDS% = EY% / (ratio - LRR)), non misurato. "
                       "LRR~2.0 g/g e' una stima: la bevanda reale dipende da macina, fondi e metodo.",
        "punto_critico": "Brew ratio e resa di estrazione decidono forza (TDS) e gusto: "
                         "il ratio sposta la forza, la macinatura/tempo spostano la resa.",
    }
