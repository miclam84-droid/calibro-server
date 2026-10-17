# ============================================================
# AUDIT-FONTI — endpoint READ-ONLY (dry-run, ZERO scritture MAI).
#
# Elenca i singoli nodi/campi la cui PROVENIENZA ('fonte' / 'cas') sembra
# FABBRICATA dal vecchio bug (l'AI inventava citazioni e numeri CAS). Non
# corregge nulla: produce la LISTA PUNTUALE che Michele usa per ripulire a mano.
#
# Differenza da /admin/audit-provenienza (che dà conteggi aggregati + campione):
# qui ogni sospetto è una riga {id, nome, campo, valore_fonte, motivo}, così si
# vede ESATTAMENTE dove sta il dato sporco e perché.
#
# Euristiche ONESTE (funzioni pure, testabili senza DB), vedi CRITERIO sotto.
# Gate: ADMIN_SECRET + ?s= (hmac.compare_digest), stesso schema di routes/pwa.py.
# Solo SELECT id, type, name, data FROM nodes — nessun UPDATE/INSERT/DELETE.
# ============================================================
import os
import re
import hmac

from flask import Blueprint, request, jsonify

from db import connessione, _dati

bp_audit_fonti = Blueprint("audit_fonti", __name__)

# ── Fonti REALI citabili ──────────────────────────────────────────────────
# Token che, se compaiono nella stringa 'fonte', indicano una provenienza
# verificabile (dataset pubblico, misura al banco, derivazione dichiarata).
# NON sono fabbricate dall'AI. Allineati alle fonti davvero in uso nel codice
# (deriva_gusti scrive "USDA FDC <id>") e a quelle citabili del progetto.
FONTI_NOTE = (
    "usda", "fdc", "ciqual", "wikidata", "ahn",      # dataset pubblici
    "matter", "banco", "misura", "ricetta",          # scala/misura interna
    "tabella", "densit", "resa", "etichetta",        # misure dichiarate
    "verificat", "derivat", "stima_ai", "stimato",   # stati dichiarati onesti
)

# ── Impronte di CITAZIONE INVENTATA dall'AI ─────────────────────────────────
# Il buco peggiore erano 'fonte' che *sembrano* bibliografia autorevole ma sono
# generate dal modello: "Food Chemistry 2019 / McGee", "Belitz et al.", ecc.
# Questi segnali sono un indizio FORTE di fabbricazione (non solo "fonte ignota").
_RE_ANNO = re.compile(r"\b(18|19|20)\d{2}\b")            # un anno tipo 2019
_RE_ET_AL = re.compile(r"\bet\s+al\.?", re.IGNORECASE)   # "et al."
_NOMI_MODELLO = (
    "gpt", "gpt-4", "openai", "claude", "anthropic", "gemini",
    "mistral", "llm", "modello", "chatgpt", "language model",
)
# riviste/autori ricorrenti nelle citazioni inventate (lista conservativa,
# usata solo come segnale aggiuntivo, non come unica prova)
_TERMINI_BIBLIO = (
    "et al", "food chemistry", "journal", "mcgee", "belitz",
    "handbook", "press", "edition", "vol.", "pp.", "doi:",
)

# ── Formato CAS valido: 2-7 cifre - 2 cifre - 1 cifra di controllo ──────────
_RE_CAS = re.compile(r"^\d{2,7}-\d{2}-\d$")
_CAS_NULLI = {"", "null", "none", "n/a", "na", "-", "sconosciuto", "ignoto"}

CRITERIO = {
    "fonte_testo_libero_ai": (
        "Il valore di 'fonte' ha l'impronta di una CITAZIONE INVENTATA dal modello: "
        "contiene un anno (es. 2019), 'et al.', un nome di rivista/autore ricorrente "
        "o il nome di un modello AI. Segnale forte di fabbricazione: va segnalato "
        "ANCHE se il nodo dichiara la stima, perché è proprio il residuo che il fix "
        "marca_provenienza_ai avrebbe dovuto rimuovere."
    ),
    "fonte_non_citabile": (
        "Il valore di 'fonte' è una stringa non vuota che NON cita nessuna fonte "
        "reale nota (USDA/FDC, CIQUAL, Wikidata, Ahn, scala Matter, banco, misura, "
        "ricetta, tabella...) e il nodo NON dichiara onestamente la stima. Sospetta "
        "perché una fonte vera è sempre riconducibile a un dataset/misura citabile."
    ),
    "cas_malformato": (
        "Un numero 'cas' presente (non nullo) che non rispetta il formato CAS "
        "(NNNNNNN-NN-N) oppure non supera la cifra di controllo. L'AI generava CAS "
        "plausibili ma sbagliati; un CAS inventato quasi mai supera il checksum."
    ),
}


# ── Funzioni PURE (testabili senza DB né rete) ──────────────────────────────

def _norm(x):
    """Stringa normalizzata (trim, minuscola) o '' se non è una stringa."""
    return x.strip().lower() if isinstance(x, str) else ""


def fonte_e_citabile(testo):
    """True se la stringa 'fonte' cita una fonte reale/nota (non fabbricata)."""
    t = _norm(testo)
    return any(tok in t for tok in FONTI_NOTE)


def fonte_sembra_ai(testo):
    """True se la 'fonte' ha l'impronta di una citazione inventata dal modello.
    Impronte: un anno, 'et al.', nome di modello AI, termini bibliografici tipici."""
    if not isinstance(testo, str):
        return False
    t = testo.strip()
    if not t:
        return False
    tl = t.lower()
    if _RE_ANNO.search(t):
        return True
    if _RE_ET_AL.search(t):
        return True
    if any(m in tl for m in _NOMI_MODELLO):
        return True
    if any(b in tl for b in _TERMINI_BIBLIO):
        return True
    return False


def _cifra_controllo_cas(testo):
    """Verifica la cifra di controllo CAS. Assume il formato già validato dal
    regex. L'ultima cifra deve eguagliare (somma di cifra_i * posizione_i) % 10,
    con le posizioni contate da destra a partire da 1, escludendo la cifra di
    controllo stessa."""
    cifre = [c for c in testo if c.isdigit()]
    if len(cifre) < 4:  # min 2+2+1 = 5 cifre; sotto è comunque malformato
        return False
    check = int(cifre[-1])
    corpo = cifre[:-1]
    somma = sum(int(d) * pos for pos, d in enumerate(reversed(corpo), start=1))
    return (somma % 10) == check


def cas_valido(testo):
    """True se la stringa è un numero CAS sintatticamente valido E supera il
    checksum. I valori nulli/placeholder NON sono 'cas presenti' (vedi cas_presente)."""
    if not isinstance(testo, str):
        return False
    t = testo.strip()
    if not _RE_CAS.match(t):
        return False
    return _cifra_controllo_cas(t)


def cas_presente(valore):
    """True se c'è un valore CAS da valutare (non nullo/placeholder/vuoto).
    Un CAS assente non è mai sospetto: il prompt chiede esplicitamente 'null'."""
    if valore is None:
        return False
    if isinstance(valore, str):
        return _norm(valore) not in _CAS_NULLI
    # un cas numerico/altro tipo è comunque un valore da controllare
    return True


def _disclosure(stato_norm):
    """True se uno 'stato'/'provenienza' dichiara onestamente una stima/origine AI.
    Copre l'enum onesto e le stringhe libere tipo 'c_stima_ai' / '..._ai'."""
    if not stato_norm:
        return False
    if stato_norm in ("stimato", "stimato_ai", "derivato", "corretto", "verificato"):
        return True
    return ("stima" in stato_norm) or stato_norm.endswith("_ai")


def _prov_dichiara_stima(dd):
    """True se il NODO dichiara la stima a livello provenienza (dict o stringa)."""
    prov = dd.get("provenienza")
    if isinstance(prov, dict):
        return _disclosure(_norm(prov.get("stato")))
    if isinstance(prov, str):
        return _disclosure(_norm(prov))
    return False


def classifica_fonte(valore, disclosed):
    """Dato il valore grezzo di un campo 'fonte' e se il nodo/entry dichiara la
    stima, ritorna il motivo di sospetto (str) oppure None se la fonte è pulita.

    Priorità:
      1) fonte citabile/nota -> None (mai sospetta).
      2) impronta di citazione AI -> 'fonte_testo_libero_ai' (anche se disclosed:
         è il residuo da ripulire).
      3) altrimenti non citabile e NON dichiarata -> 'fonte_non_citabile'.
         Se dichiarata, conservativo: None (niente rumore).
    """
    if not isinstance(valore, str) or not valore.strip():
        return None
    if fonte_e_citabile(valore):
        return None
    if fonte_sembra_ai(valore):
        return "fonte_testo_libero_ai"
    if not disclosed:
        return "fonte_non_citabile"
    return None


def classifica_cas(valore):
    """Ritorna 'cas_malformato' se un CAS presente non è valido, altrimenti None.
    Indipendente dalla disclosure: un CAS sbagliato è un dato errato in sé."""
    if not cas_presente(valore):
        return None
    if cas_valido(valore):
        return None
    return "cas_malformato"


def audita_nodo(nid, nome, dd):
    """Funzione PURA: dato un nodo (id, nome, data-dict) ritorna la lista dei
    sospetti {id, nome, campo, valore_fonte, motivo}. Tollerante: data strano
    non rompe e non genera falsi positivi."""
    sospetti = []
    if not isinstance(dd, dict):
        return sospetti

    disclosed_nodo = _prov_dichiara_stima(dd)

    def _aggiungi(campo, valore, motivo):
        if motivo:
            sospetti.append({
                "id": nid,
                "nome": nome,
                "campo": campo,
                "valore_fonte": valore if isinstance(valore, str) else str(valore),
                "motivo": motivo,
            })

    # 1) fonte di primo livello
    _aggiungi("fonte", dd.get("fonte"),
              classifica_fonte(dd.get("fonte"), disclosed_nodo))

    # 2) fonte dentro proprieta_meta[asse] (deriva_gusti scrive qui 'USDA FDC ..')
    meta = dd.get("proprieta_meta")
    if isinstance(meta, dict):
        for asse, v in meta.items():
            if isinstance(v, dict):
                disclosed = disclosed_nodo or _disclosure(_norm(v.get("stato")))
                _aggiungi("proprieta_meta.%s.fonte" % asse, v.get("fonte"),
                          classifica_fonte(v.get("fonte"), disclosed))

    # 3) composti aromatici: fonte + cas per ogni voce
    comp = dd.get("composti_aromatici")
    if isinstance(comp, list):
        for i, c in enumerate(comp):
            if not isinstance(c, dict):
                continue
            disclosed = disclosed_nodo or _disclosure(_norm(c.get("stato")))
            _aggiungi("composti_aromatici[%d].fonte" % i, c.get("fonte"),
                      classifica_fonte(c.get("fonte"), disclosed))
            _aggiungi("composti_aromatici[%d].cas" % i, c.get("cas"),
                      classifica_cas(c.get("cas")))

    return sospetti


def audita_righe(righe):
    """Funzione PURA: dato un iterabile di (id, type, name, data) ritorna il
    report {totale_esaminati, sospetti:[...], per_motivo:{...}}. Isolata dal DB."""
    totale = 0
    sospetti = []
    per_motivo = {}

    for nid, _ntype, nome, data in righe:
        totale += 1
        dd = _dati(data)
        for s in audita_nodo(nid, nome, dd):
            sospetti.append(s)
            per_motivo[s["motivo"]] = per_motivo.get(s["motivo"], 0) + 1

    return {
        "ok": True,
        "totale_esaminati": totale,
        "sospetti": sospetti,
        "per_motivo": per_motivo,
        "criterio": CRITERIO,
        "nota": "Audit read-only (dry-run): nessuna scrittura al DB. Lista da "
                "ripulire a mano. Un campo pulito o una fonte citabile non compaiono.",
    }


@bp_audit_fonti.route("/admin/audit-fonti")
def audit_fonti():
    """READ-ONLY. ?s=ADMIN_SECRET. Elenca i nodi/campi con provenienza sospetta.
    Solo SELECT id, type, name, data FROM nodes — zero scritture, mai."""
    atteso = os.environ.get("ADMIN_SECRET") or ""
    secret = request.args.get("s", "")
    if not atteso or not hmac.compare_digest(str(secret), str(atteso)):
        return jsonify({"errore": "non autorizzato"}), 403

    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, type, name, data FROM nodes")
            righe = cur.fetchall()
            cur.close()
    except Exception as e:
        return jsonify({"errore": str(e)[:200]}), 500

    return jsonify(audita_righe(righe))
