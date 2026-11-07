# ============================================================
# routes/backup.py — backup del database (grafo + dati) su volume.
#
# Un backup è utile solo se è RIPRISTINABILE: usiamo pg_dump in formato
# custom (-Fc, compresso), che si ripristina con
#     pg_restore --clean --if-exists -d "$DATABASE_URL" <file>.dump
#
# Destinazione: il volume montato (Railway: RAILWAY_VOLUME_MOUNT_PATH),
# oppure BACKUP_DIR. Se nessuno dei due è configurato NON si scrive in un
# percorso effimero fingendo sicurezza: fail-loud con istruzioni.
#
# Endpoint admin-guarded (stesso standard fail-closed del resto):
#   GET|POST /admin/backup-grafo         → esegue un backup + rotazione
#   GET      /admin/backup-grafo/lista   → elenca i backup presenti
# ============================================================
import os
import re
import hmac
import time
import shutil
import subprocess
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from config import DATABASE_URL

bp = Blueprint("backup", __name__)

_PREFISSO = "matter-"
_SUFFISSO = ".dump"
_NOME_RE = re.compile(r"^matter-\d{8}-\d{6}\.dump$")


def _admin_ok(req):
    """Auth admin fail-closed: nega se ADMIN_SECRET è assente, confronto a
    tempo costante, secret da header X-Admin-Secret (preferito) o ?s=."""
    _secret = os.environ.get("ADMIN_SECRET") or ""
    if not _secret:
        return False
    _dato = req.headers.get("X-Admin-Secret", "") or req.args.get("s", "")
    return hmac.compare_digest(str(_dato), str(_secret))


def _dir_backup():
    """Cartella di destinazione dei backup, dentro il volume persistente.
    Ordine: RAILWAY_VOLUME_MOUNT_PATH, poi BACKUP_DIR. None se nessuno è
    configurato (il chiamante fa fail-loud: un backup su disco effimero
    sarebbe un backup finto)."""
    base = (os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
            or os.environ.get("BACKUP_DIR") or "").strip()
    if not base:
        return None
    d = os.path.join(base, "backup")
    os.makedirs(d, exist_ok=True)
    return d


def _quanti_tenere():
    try:
        n = int(os.environ.get("BACKUP_KEEP", "14"))
        return max(1, n)
    except Exception:
        return 14


def _elenco(d):
    """Backup presenti, dal più recente al più vecchio (il nome è ordinabile:
    timestamp UTC). Solo file col nostro schema di nome."""
    try:
        nomi = [n for n in os.listdir(d) if _NOME_RE.match(n)]
    except Exception:
        return []
    nomi.sort(reverse=True)
    out = []
    for n in nomi:
        p = os.path.join(d, n)
        try:
            st = os.stat(p)
            out.append({"file": n, "bytes": st.st_size,
                        "quando": datetime.fromtimestamp(st.st_mtime, timezone.utc)
                        .strftime("%Y-%m-%d %H:%M UTC")})
        except Exception:
            continue
    return out


def _ruota(d, tieni):
    """Tiene solo gli ultimi `tieni` backup, cancella i più vecchi. Ritorna i
    nomi cancellati."""
    nomi = [n for n in os.listdir(d) if _NOME_RE.match(n)]
    nomi.sort(reverse=True)
    cancellati = []
    for n in nomi[tieni:]:
        try:
            os.remove(os.path.join(d, n))
            cancellati.append(n)
        except Exception:
            pass
    return cancellati


@bp.route("/admin/backup-grafo", methods=["GET", "POST"])
def backup_grafo():
    """Esegue un backup del DB (pg_dump -Fc) nel volume e ruota i vecchi.
    Admin-guarded. Il DATABASE_URL non compare mai nella risposta né nei log."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    if not DATABASE_URL:
        return jsonify({"errore": "DATABASE_URL non configurata"}), 503
    if not shutil.which("pg_dump"):
        return jsonify({"errore": "pg_dump non disponibile nell'immagine: "
                        "aggiungi il pacchetto postgresql-client al build"}), 503
    d = _dir_backup()
    if not d:
        return jsonify({"errore": "nessun volume configurato: imposta "
                        "RAILWAY_VOLUME_MOUNT_PATH (volume Railway) o BACKUP_DIR"}), 503

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    nome = _PREFISSO + ts + _SUFFISSO
    percorso = os.path.join(d, nome)
    parz = percorso + ".parziale"

    t0 = time.time()
    try:
        # -Fc: formato custom (compresso, ripristinabile con pg_restore).
        # Scrive prima su .parziale e poi rinomina: un backup troncato (crash,
        # timeout) non viene mai scambiato per valido.
        proc = subprocess.run(
            ["pg_dump", "-Fc", "--no-owner", "--no-privileges",
             "-d", DATABASE_URL, "-f", parz],
            capture_output=True, text=True, timeout=600,
        )
        if proc.returncode != 0:
            try:
                if os.path.exists(parz):
                    os.remove(parz)
            except Exception:
                pass
            # stderr di pg_dump può contenere dettagli ma NON la password (è in DATABASE_URL,
            # non la stampa); taglio comunque per prudenza.
            err = (proc.stderr or "").strip().splitlines()
            msg = err[-1] if err else "pg_dump fallito"
            return jsonify({"errore": "backup fallito", "dettaglio": msg[:300]}), 500
        os.replace(parz, percorso)
    except subprocess.TimeoutExpired:
        try:
            if os.path.exists(parz):
                os.remove(parz)
        except Exception:
            pass
        return jsonify({"errore": "backup fallito: timeout (oltre 600s)"}), 504
    except Exception as e:
        try:
            if os.path.exists(parz):
                os.remove(parz)
        except Exception:
            pass
        return jsonify({"errore": "backup fallito", "dettaglio": str(e)[:200]}), 500

    try:
        dim = os.path.getsize(percorso)
    except Exception:
        dim = None
    cancellati = _ruota(d, _quanti_tenere())

    return jsonify({
        "ok": True,
        "file": nome,
        "bytes": dim,
        "secondi": round(time.time() - t0, 1),
        "tenuti": _quanti_tenere(),
        "cancellati_rotazione": cancellati,
        "totale_backup": len(_elenco(d)),
        "ripristino": "pg_restore --clean --if-exists -d \"$DATABASE_URL\" " + nome,
    })


@bp.route("/admin/backup-grafo/lista", methods=["GET"])
def backup_lista():
    """Elenca i backup presenti nel volume. Admin-guarded."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    d = _dir_backup()
    if not d:
        return jsonify({"errore": "nessun volume configurato: imposta "
                        "RAILWAY_VOLUME_MOUNT_PATH o BACKUP_DIR"}), 503
    elenco = _elenco(d)
    return jsonify({"ok": True, "cartella": d, "totale": len(elenco),
                    "tenuti_max": _quanti_tenere(), "backup": elenco})
