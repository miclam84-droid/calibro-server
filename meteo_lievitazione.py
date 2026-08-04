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


def _nota_umidita(umidita):
    """Interpretazione QUALITATIVA dell'umidità (la scienza qui è meno lineare
    della temperatura, quindi indicazione qualitativa non numero preciso)."""
    if umidita is None:
        return None
    if umidita >= 70:
        return ("Umidità alta: l'impasto tende a restare appiccicoso e la crosta "
                "si forma più lentamente. Riduci un filo l'acqua e non coprire troppo.")
    if umidita <= 40:
        return ("Umidità bassa: la superficie dell'impasto secca in fretta. "
                "Copri bene durante la lievitazione per evitare la crosticina.")
    return ("Umidità nella norma: nessun accorgimento particolare sulla superficie "
            "dell'impasto.")


def adatta_lievitazione(lat, lon, tempo_base_ore=4.0, t_riferimento=T_RIFERIMENTO):
    """Adatta il tempo di lievitazione alle condizioni meteo reali della posizione.
    tempo_base_ore: tempo previsto dalla ricetta a t_riferimento (default 24°C).
    Ritorna dict con meteo, tempo adattato, interpretazione. {errore} se meteo non disponibile."""
    meteo = _meteo_corrente(lat, lon)
    if not meteo or meteo.get("temp") is None:
        return {"errore": "meteo non disponibile per questa posizione"}

    T = float(meteo["temp"])
    umidita = meteo.get("umidita")

    # Q10: tempo(T) = tempo_base * Q10^((T_rif - T)/10)
    fattore = Q10 ** ((t_riferimento - T) / 10.0)
    tempo_adattato = tempo_base_ore * fattore
    delta_pct = (fattore - 1.0) * 100.0

    # verdetto direzionale
    if abs(delta_pct) < 8:
        direzione = "in linea"
        verdetto = (f"Oggi da te ci sono {T:.0f}°C, vicini alla temperatura di riferimento. "
                    f"I tempi della ricetta ({_fmt_ore(tempo_base_ore)}) vanno bene così.")
    elif delta_pct < 0:  # più caldo = più veloce
        direzione = "più veloce"
        verdetto = (f"Oggi da te ci sono {T:.0f}°C: fa più caldo del riferimento, "
                    f"la lievitazione sarà più veloce. Invece di {_fmt_ore(tempo_base_ore)}, "
                    f"calcola circa {_fmt_ore(tempo_adattato)}. Controlla prima del previsto.")
    else:  # più freddo = più lento
        direzione = "più lenta"
        verdetto = (f"Oggi da te ci sono {T:.0f}°C: fa più freddo del riferimento, "
                    f"la lievitazione sarà più lenta. Invece di {_fmt_ore(tempo_base_ore)}, "
                    f"calcola circa {_fmt_ore(tempo_adattato)}. Dai più tempo all'impasto.")

    return {
        "meteo": {
            "temperatura": round(T, 1),
            "umidita": umidita,
            "posizione": {"lat": lat, "lon": lon},
        },
        "riferimento": {
            "temperatura": t_riferimento,
            "tempo_base_ore": tempo_base_ore,
            "tempo_base_label": _fmt_ore(tempo_base_ore),
        },
        "risultato": {
            "tempo_adattato_ore": round(tempo_adattato, 2),
            "tempo_adattato_label": _fmt_ore(tempo_adattato),
            "fattore": round(fattore, 2),
            "variazione_pct": round(delta_pct, 0),
            "direzione": direzione,
        },
        "verdetto": verdetto,
        "nota_umidita": _nota_umidita(umidita),
        "fondamento": "Adattamento basato sulla cinetica di fermentazione (Q10≈2) e sulla temperatura/umidità reali della tua zona.",
    }
