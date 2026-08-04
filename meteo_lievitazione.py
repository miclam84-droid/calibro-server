# ============================================================
# meteo_lievitazione.py — Misura attiva AUTOMATICA per la panificazione.
# Data la posizione dell'utente, prende temp+umidità reali da Open-Meteo
# e adatta i tempi di lievitazione con la fisica del Q10 (cinetica fermentazione).
# Fondato su fisica nota (Q10), non su diagnosi da validare.
# ============================================================
import urllib.request
import json as _j

OPENMETEO = "https://api.open-meteo.com/v1/forecast"

# Q10 della fermentazione dei lieviti: ~2 nel range operativo (ogni +10°C ~raddoppia)
Q10 = 2.0
# temperatura standard di riferimento per i tempi-base delle ricette
T_RIFERIMENTO = 24.0


def _meteo_corrente(lat, lon):
    """Temp (°C) e umidità relativa (%) correnti dalla posizione. None se fallisce."""
    url = f"{OPENMETEO}?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code"
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            d = _j.loads(r.read())
            c = d.get("current", {})
            return {
                "temp": c.get("temperature_2m"),
                "umidita": c.get("relative_humidity_2m"),
                "weather_code": c.get("weather_code"),
            }
    except Exception:
        return None


def _fmt_ore(ore_decimali):
    """Converte ore decimali in 'Xh YYm'."""
    if ore_decimali is None:
        return "—"
    ore = int(ore_decimali)
    minuti = int(round((ore_decimali - ore) * 60))
    if minuti == 60:
        ore += 1; minuti = 0
    if ore == 0:
        return f"{minuti} min"
    return f"{ore}h{minuti:02d}"


def _nota_umidita(umidita, lang="it"):
    """Interpretazione QUALITATIVA dell'umidità, nella lingua richiesta."""
    if umidita is None:
        return None
    T = {
        "it": {
            "alta": "Umidità alta: l'impasto tende a restare appiccicoso e la crosta si forma più lentamente. Riduci un filo l'acqua e non coprire troppo.",
            "bassa": "Umidità bassa: la superficie dell'impasto secca in fretta. Copri bene durante la lievitazione per evitare la crosticina.",
            "norma": "Umidità nella norma: nessun accorgimento particolare sulla superficie dell'impasto.",
        },
        "en": {
            "alta": "High humidity: the dough tends to stay sticky and the crust forms more slowly. Reduce the water slightly and don't cover it too much.",
            "bassa": "Low humidity: the dough surface dries quickly. Cover it well during proofing to avoid a skin forming.",
            "norma": "Normal humidity: no particular care needed on the dough surface.",
        },
        "es": {
            "alta": "Humedad alta: la masa tiende a quedar pegajosa y la corteza se forma más lentamente. Reduce un poco el agua y no la cubras demasiado.",
            "bassa": "Humedad baja: la superficie de la masa se seca rápido. Cúbrela bien durante el leudado para evitar que se forme una costra.",
            "norma": "Humedad normal: sin cuidados particulares en la superficie de la masa.",
        },
    }.get(lang, None) or T_IT_FALLBACK
    if umidita >= 70:
        return T["alta"]
    if umidita <= 40:
        return T["bassa"]
    return T["norma"]

T_IT_FALLBACK = {
    "alta": "Umidità alta: l'impasto tende a restare appiccicoso.",
    "bassa": "Umidità bassa: la superficie dell'impasto secca in fretta.",
    "norma": "Umidità nella norma.",
}


def adatta_lievitazione(lat, lon, tempo_base_ore=4.0, t_riferimento=T_RIFERIMENTO, lang="it"):
    """Adatta il tempo di lievitazione alle condizioni meteo reali della posizione.
    tempo_base_ore: tempo previsto dalla ricetta a t_riferimento (default 24°C).
    lang: it|en|es. Ritorna dict con meteo, tempo adattato, interpretazione."""
    meteo = _meteo_corrente(lat, lon)
    if not meteo or meteo.get("temp") is None:
        return {"errore": "meteo non disponibile per questa posizione"}

    T = float(meteo["temp"])
    umidita = meteo.get("umidita")

    # Q10: tempo(T) = tempo_base * Q10^((T_rif - T)/10)
    fattore = Q10 ** ((t_riferimento - T) / 10.0)
    tempo_adattato = tempo_base_ore * fattore
    delta_pct = (fattore - 1.0) * 100.0

    tb = _fmt_ore(tempo_base_ore)
    ta = _fmt_ore(tempo_adattato)
    Tr = f"{T:.0f}"

    # verdetti tradotti
    VERD = {
        "it": {
            "linea": ("in linea", f"Oggi da te ci sono {Tr}°C, vicini alla temperatura di riferimento. I tempi della ricetta ({tb}) vanno bene così."),
            "veloce": ("più veloce", f"Oggi da te ci sono {Tr}°C: fa più caldo del riferimento, la lievitazione sarà più veloce. Invece di {tb}, calcola circa {ta}. Controlla prima del previsto."),
            "lenta": ("più lenta", f"Oggi da te ci sono {Tr}°C: fa più freddo del riferimento, la lievitazione sarà più lenta. Invece di {tb}, calcola circa {ta}. Dai più tempo all'impasto."),
        },
        "en": {
            "linea": ("on target", f"It's {Tr}°C where you are, close to the reference temperature. Your recipe's timing ({tb}) works as is."),
            "veloce": ("faster", f"It's {Tr}°C where you are: warmer than the reference, so proofing will be faster. Instead of {tb}, expect about {ta}. Check earlier than planned."),
            "lenta": ("slower", f"It's {Tr}°C where you are: colder than the reference, so proofing will be slower. Instead of {tb}, expect about {ta}. Give the dough more time."),
        },
        "es": {
            "linea": ("en línea", f"Hoy tienes {Tr}°C, cerca de la temperatura de referencia. Los tiempos de la receta ({tb}) están bien así."),
            "veloce": ("más rápido", f"Hoy tienes {Tr}°C: hace más calor que la referencia, el leudado será más rápido. En vez de {tb}, calcula unas {ta}. Revisa antes de lo previsto."),
            "lenta": ("más lento", f"Hoy tienes {Tr}°C: hace más frío que la referencia, el leudado será más lento. En vez de {tb}, calcula unas {ta}. Dale más tiempo a la masa."),
        },
    }.get(lang) or None
    if VERD is None:
        VERD = {
            "linea": ("in linea", f"{Tr}°C — tempi ok ({tb})."),
            "veloce": ("più veloce", f"{Tr}°C — più veloce: ~{ta}."),
            "lenta": ("più lenta", f"{Tr}°C — più lenta: ~{ta}."),
        }

    if abs(delta_pct) < 8:
        direzione, verdetto = VERD["linea"]
    elif delta_pct < 0:
        direzione, verdetto = VERD["veloce"]
    else:
        direzione, verdetto = VERD["lenta"]

    FOND = {
        "it": "Adattamento basato sulla cinetica di fermentazione (Q10≈2) e sulla temperatura/umidità reali della tua zona.",
        "en": "Adjustment based on fermentation kinetics (Q10≈2) and the real temperature/humidity of your area.",
        "es": "Ajuste basado en la cinética de fermentación (Q10≈2) y la temperatura/humedad reales de tu zona.",
    }.get(lang, None) or "Adattamento basato sulla cinetica di fermentazione (Q10≈2)."

    return {
        "meteo": {
            "temperatura": round(T, 1),
            "umidita": umidita,
            "posizione": {"lat": lat, "lon": lon},
        },
        "riferimento": {
            "temperatura": t_riferimento,
            "tempo_base_ore": tempo_base_ore,
            "tempo_base_label": tb,
        },
        "risultato": {
            "tempo_adattato_ore": round(tempo_adattato, 2),
            "tempo_adattato_label": ta,
            "fattore": round(fattore, 2),
            "variazione_pct": round(delta_pct, 0),
            "direzione": direzione,
        },
        "verdetto": verdetto,
        "nota_umidita": _nota_umidita(umidita, lang),
        "fondamento": FOND,
    }
