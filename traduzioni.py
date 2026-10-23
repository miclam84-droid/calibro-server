"""Traduzione centralizzata con cache DB. Ogni stringa italiana viene tradotta IT→EN/ES una sola
volta (via AI economica), salvata in cache_traduzioni, e riusata. Copre tutte le stringhe
utente-facing generate dal backend (calcolatori, insight, scarti, ecc.) senza duplicare il codice."""
from db import _get_conn, _release_conn
from config import DATABASE_URL
import hashlib


def _ensure_cache(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS cache_traduzioni (
        chiave TEXT PRIMARY KEY,
        testo_it TEXT NOT NULL,
        lang TEXT NOT NULL,
        traduzione TEXT NOT NULL,
        creato_il TIMESTAMP DEFAULT NOW()
    )""")


def _chiave(testo_it, lang):
    h = hashlib.sha256(f"{lang}::{testo_it}".encode("utf-8")).hexdigest()[:40]
    return h


def traduci(testo_it, lang="it"):
    """Traduce una stringa italiana nella lingua richiesta. it → ritorna com'è.
    en/es → cerca in cache, altrimenti traduce con AII e salva. Robusto: se qualcosa fallisce,
    ritorna l'italiano (mai un errore all'utente)."""
    if not testo_it or lang == "it" or lang not in ("en", "es"):
        return testo_it
    if not DATABASE_URL:
        return testo_it
    chiave = _chiave(testo_it, lang)
    conn = None
    try:
        conn = _get_conn(); cur = conn.cursor()
        _ensure_cache(cur)
        cur.execute("SELECT traduzione FROM cache_traduzioni WHERE chiave=%s", (chiave,))
        r = cur.fetchone()
        if r:
            cur.close(); _release_conn(conn)
            return r[0]
        # non in cache: traduco con AI economica
        _lingua = "inglese" if lang == "en" else "spagnolo"
        prompt = (f"Traduci in {_lingua} questo testo tecnico di ristorazione, mantenendo numeri, "
                  f"unità di misura e termini tecnici. Rispondi SOLO con la traduzione, niente altro:\n\n{testo_it}")
        try:
            from ai_gateway import route_fast
            trad = (route_fast(prompt, max_tokens=300) or "").strip()
        except Exception:
            trad = ""
        if not trad:
            cur.close(); _release_conn(conn)
            return testo_it  # fallback all'italiano
        cur.execute("INSERT INTO cache_traduzioni (chiave, testo_it, lang, traduzione) "
                    "VALUES (%s,%s,%s,%s) ON CONFLICT (chiave) DO NOTHING",
                    (chiave, testo_it, lang, trad))
        conn.commit(); cur.close(); _release_conn(conn)
        return trad
    except Exception:
        try:
            if conn: _release_conn(conn)
        except Exception:
            pass
        return testo_it


def traduci_dict(d, lang="it", campi=None):
    """Traduce i campi di stringa indicati in un dizionario (in-place safe: ritorna copia)."""
    if lang == "it" or not isinstance(d, dict):
        return d
    out = dict(d)
    for k in (campi or []):
        v = out.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = traduci(v, lang)
    return out


def traduci_molti(testi, lang="it", solo_cache=False):
    """Traduce molte stringhe IT in un colpo solo: UNA sola SELECT per leggere tutta la cache.
    Ritorna dict {testo_it: traduzione}. Se solo_cache=True NON chiama mai l'AI dal vivo: le
    stringhe non ancora in cache restano in italiano (fallback onesto, zero rischio di timeout).
    Pensato per liste grandi e statiche (es. l'intero catalogo strumenti) servite sulla hot path."""
    testi = [t for t in (testi or []) if isinstance(t, str) and t.strip()]
    out = {t: t for t in testi}  # default: italiano
    if lang == "it" or lang not in ("en", "es") or not testi or not DATABASE_URL:
        return out
    uniq = list(dict.fromkeys(testi))
    conn = None
    try:
        conn = _get_conn(); cur = conn.cursor()
        _ensure_cache(cur)
        chiavi = {_chiave(t, lang): t for t in uniq}
        cur.execute("SELECT chiave, traduzione FROM cache_traduzioni WHERE chiave = ANY(%s)",
                    (list(chiavi.keys()),))
        trovati = set()
        for k, trad in cur.fetchall():
            if k in chiavi:
                out[chiavi[k]] = trad
                trovati.add(chiavi[k])
        mancanti = [t for t in uniq if t not in trovati]
        if mancanti and not solo_cache:
            from ai_gateway import route_fast
            _lingua = "inglese" if lang == "en" else "spagnolo"
            for t in mancanti:
                prompt = (f"Traduci in {_lingua} questo testo tecnico di ristorazione, mantenendo numeri, "
                          f"unità di misura e termini tecnici. Rispondi SOLO con la traduzione, niente altro:\n\n{t}")
                try:
                    trad = (route_fast(prompt, max_tokens=300) or "").strip()
                except Exception:
                    trad = ""
                if trad:
                    out[t] = trad
                    cur.execute("INSERT INTO cache_traduzioni (chiave, testo_it, lang, traduzione) "
                                "VALUES (%s,%s,%s,%s) ON CONFLICT (chiave) DO NOTHING",
                                (_chiave(t, lang), t, lang, trad))
            conn.commit()
        cur.close(); _release_conn(conn)
        return out
    except Exception:
        try:
            if conn: _release_conn(conn)
        except Exception:
            pass
        return out
