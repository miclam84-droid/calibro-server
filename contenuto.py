# ============================================================
# contenuto.py — helper di contenuto/testo condivisi (schede, numero
# bersaglio, pulizia traduzioni, correzione ortografica). Funzioni pure
# su dizionari/stringhe: nessuna dipendenza da app.py, db o rete.
# Usati da app.py e dai blueprint (admin, e in futuro lezione/api).
# ============================================================

_ACC_MAP = {
 'perche':'perché','poiche':'poiché','affinche':'affinché','benche':'benché','finche':'finché',
 'giacche':'giacché','nonche':'nonché','sicche':'sicché','piu':'più','gia':'già','cosi':'così',
 'puo':'può','cioe':'cioè','citta':'città','qualita':'qualità','quantita':'quantità','acidita':'acidità',
 'umidita':'umidità','densita':'densità','viscosita':'viscosità','proprieta':'proprietà','varieta':'varietà',
 'possibilita':'possibilità','capacita':'capacità','stabilita':'stabilità','solubilita':'solubilità',
 'attivita':'attività','velocita':'velocità','unita':'unità','realta':'realtà','polarita':'polarità',
 'morbidita':'morbidità','fluidita':'fluidità','fragilita':'fragilità','porosita':'porosità',
 'plasticita':'plasticità','elasticita':'elasticità','intensita':'intensità','necessita':'necessità',
 'omogeneita':'omogeneità','affinita':'affinità','complessita':'complessità','specificita':'specificità',
 'gravita':'gravità','identita':'identità','integrita':'integrità','salinita':'salinità',
 'alcalinita':'alcalinità','reattivita':'reattività','sensibilita':'sensibilità','solidita':'solidità'}


def _corregge_it(t):
    """Correzioni ortografiche INEQUIVOCABILI su testo italiano: accenti su parole
    che senza accento non esistono, e apostrofo nelle elisioni l'/dell'/all'…
    Non tocca 'e/è' (ambiguo) né la 'L' unità (mg/L)."""
    if not isinstance(t, str) or not t:
        return t
    import re as _re
    def _repl(m):
        w = m.group(0); c = _ACC_MAP[w.lower()]
        return (c[0].upper() + c[1:]) if w[0].isupper() else c
    for wrong in _ACC_MAP:
        t = _re.sub(r"(?<![A-Za-zàèéìòùÀÈÉÌÒÙ'])" + wrong + r"(?![A-Za-zàèéìòùÀÈÉÌÒÙ])",
                    _repl, t, flags=_re.I)
    t = _re.sub(r"(?<![A-Za-zàèéìòù/'])([Ll])\s+(?=[aeiouAEIOUàèéìòù])", r"\1'", t)
    t = _re.sub(r"\b(dell|all|dall|nell|sull|coll|quell)\s+(?=[aeiouAEIOUàèéìòù])",
                r"\1'", t, flags=_re.I)
    t = _re.sub(r"\bun p[oò]\b(?!')", "un po'", t)
    return t


def _pulisci_traduzione(t):
    """Toglie intestazioni spurie che Haiku a volte antepone alla traduzione
    (es. 'ENGLISH TECHNICAL SHEET:'), indotte dal prompt: facevano sembrare la
    scheda EN un titolo. Difesa in lettura, così pulisce anche il gia' salvato."""
    if not t:
        return t
    import re
    t = t.strip()
    t = re.sub(r'^(ENGLISH\s+)?TECHNICAL\s+SHEET\s*:?\s*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'^(ENGLISH\s+)?SHEET\s*:?\s*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'^SCHEDA(\s+(TECNICA|ITALIANA))?\s*:?\s*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'^(Translation|Traduzione)\s*:?\s*', '', t, flags=re.IGNORECASE)
    return t.strip()


def _scheda_lang(data_dict, lang="it"):
    """GT4 — Legge il campo scheda nel formato multilingua.
    Supporta sia il formato legacy (stringa) sia il nuovo formato {it:"...", en:"..."}.
    Quando tutti i nodi saranno migrati al formato dizionario, il fallback legacy si rimuove."""
    scheda = data_dict.get("scheda", "")
    if isinstance(scheda, dict):
        return _pulisci_traduzione(scheda.get(lang) or scheda.get("it") or "")
    return scheda or ""


def _numero_bersaglio(data_dict):
    """Legge il numero-bersaglio di un nodo Fenomeno in modo canonico.
    Il seed usa la chiave 'numero_bersaglio'; il fallback 'target' copre
    eventuali nodi legacy. Fonte unica di verità per home, disciplina e lezione,
    così la chiave non torna a divergere tra i lettori."""
    if not data_dict:
        return ""
    return data_dict.get("numero_bersaglio") or data_dict.get("target") or ""
