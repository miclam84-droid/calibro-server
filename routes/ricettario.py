"""Ricettario canonico: le 454 ricette certificate Matter, navigabili e cercabili.
SEPARATO dal Quaderno (che è il patrimonio dell'utente). Questo è il patrimonio Matter.
Endpoint leggero: solo i campi per la griglia + foto/blueprint + fenomeno + numero-bersaglio."""
from flask import Blueprint, request, jsonify
from db import carica_grafo
import json

bp_ricettario = Blueprint("ricettario", __name__)


@bp_ricettario.route("/v1/ricettario/canonico", methods=["GET"])
def ricettario_canonico():
    """Le 454 ricette certificate. Filtri: ?disciplina= ?fenomeno= ?q= (ricerca) ?limit= ?offset=
    Restituisce card leggere: id, nome (pulito), disciplina, foto o blueprint, fenomeno, punto critico."""
    disciplina = (request.args.get("disciplina") or "").strip().lower()
    fenomeno = (request.args.get("fenomeno") or "").strip()
    q = (request.args.get("q") or "").strip().lower()
    try:
        limit = min(int(request.args.get("limit", 60)), 200)
        offset = int(request.args.get("offset", 0))
    except Exception:
        limit, offset = 60, 0
    db = carica_grafo()
    # famiglie blueprint (per il fallback immagine)
    try:
        from routes.immagini_ricette import _famiglia_da_testo, _FAMIGLIA_DEFAULT
    except Exception:
        _famiglia_da_testo = lambda x: None
        _FAMIGLIA_DEFAULT = "reazione-termica"
    try:
        where = []; params = []
        if disciplina:
            where.append("lower(disciplina)=%s"); params.append(disciplina)
        if q:
            where.append("(lower(nome) LIKE %s OR lower(descrizione) LIKE %s)")
            params.extend(["%"+q+"%", "%"+q+"%"])
        sql = ("SELECT id, nome, disciplina, punto_critico, fenomeni, immagine, immagine_autore, numeri "
               "FROM ricette")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY disciplina, nome LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        rows = db.execute(sql, tuple(params)).fetchall()
        out = []
        for row in rows:
            r = dict(row) if hasattr(row, "keys") else row
            fen_raw = r["fenomeni"] if "fenomeni" in r else None
            try:
                fen_list = fen_raw if isinstance(fen_raw, list) else (json.loads(fen_raw) if fen_raw else [])
            except Exception:
                fen_list = []
            fen_primo = ""
            if fen_list:
                f0 = fen_list[0]
                fen_primo = f0 if isinstance(f0, str) else (f0.get("nome") or f0.get("id") or "")
            # filtro per fenomeno se richiesto
            if fenomeno and fenomeno.lower() not in " ".join(str(x).lower() for x in fen_list):
                continue
            # immagine: foto vera o blueprint
            img = r.get("immagine")
            if img and isinstance(img, str) and img.strip():
                immagine = {"tipo": "foto", "url": img.strip(), "autore": r.get("immagine_autore") or ""}
            else:
                fam = _famiglia_da_testo(fen_primo) or _famiglia_da_testo(r.get("disciplina") or "") or _FAMIGLIA_DEFAULT
                immagine = {"tipo": "blueprint", "famiglia": fam}
            # numero-bersaglio dai numeri
            numeri = r.get("numeri")
            num_str = ""
            try:
                nd = numeri if isinstance(numeri, dict) else (json.loads(numeri) if numeri else {})
                if isinstance(nd, dict) and nd:
                    k, v = list(nd.items())[0]
                    num_str = f"{k}: {v}"
            except Exception:
                pass
            out.append({
                "id": r["id"], "nome": r["nome"], "disciplina": r["disciplina"],
                "punto_critico": (r.get("punto_critico") or "")[:120],
                "fenomeno": fen_primo, "numero_bersaglio": num_str,
                "immagine": immagine, "certificata": True,
            })
        return jsonify({"ricette": out, "totale": len(out),
                        "filtri": {"disciplina": disciplina, "fenomeno": fenomeno, "q": q}})
    except Exception as e:
        return jsonify({"ricette": [], "errore": str(e)[:100]}), 200


@bp_ricettario.route("/v1/ricettario/discipline", methods=["GET"])
def ricettario_discipline():
    """Le discipline del ricettario coi conteggi (per le chip di navigazione)."""
    db = carica_grafo()
    try:
        rows = db.execute("SELECT disciplina, COUNT(*) n FROM ricette GROUP BY disciplina ORDER BY n DESC").fetchall()
        disc = [{"disciplina": (r["disciplina"] if hasattr(r, "keys") else r[0]),
                 "n": (r["n"] if hasattr(r, "keys") else r[1])} for r in rows]
        return jsonify({"discipline": disc, "totale_ricette": sum(d["n"] for d in disc)})
    except Exception as e:
        return jsonify({"discipline": [], "errore": str(e)[:100]}), 200


@bp_ricettario.route("/v1/ricetta/<rid>/completa", methods=["GET"])
def ricetta_completa(rid):
    """Ricetta completa con EREDITARIETÀ madre/figlia. Se è una figlia, eredita dalla madre i
    campi mancanti (punto critico, numeri, procedimento, esperimento) e sovrascrive coi propri.
    Così le figlie non sono più gusci vuoti."""
    db = carica_grafo()
    campi = ("id,nome,disciplina,descrizione,ingredienti,fenomeni,tecniche,numeri,punto_critico,"
             "abbinamenti,procedimento,esperimento,limite,twist,tempo_prep,tempo_cottura,difficolta,"
             "porzioni,recipe_type,parent_recipe_id,variante_di,immagine")
    try:
        row = db.execute(f"SELECT {campi} FROM ricette WHERE id=?", (rid,)).fetchone()
        if not row:
            return jsonify({"errore": "ricetta non trovata"}), 404
        r = dict(row) if hasattr(row, "keys") else dict(zip(campi.split(","), row))
        # se è figlia, carico la madre per ereditare i campi mancanti
        if r.get("recipe_type") == "figlia" and r.get("parent_recipe_id"):
            madre_row = db.execute(f"SELECT {campi} FROM ricette WHERE id=?", (r["parent_recipe_id"],)).fetchone()
            if madre_row:
                madre = dict(madre_row) if hasattr(madre_row, "keys") else dict(zip(campi.split(","), madre_row))
                # eredito i campi che la figlia non ha (la figlia sovrascrive solo ciò che ha di suo)
                for campo in ("punto_critico", "numeri", "procedimento", "esperimento", "limite",
                              "tecniche", "tempo_prep", "tempo_cottura", "difficolta", "abbinamenti"):
                    val = r.get(campo)
                    vuoto = (val is None or (isinstance(val, str) and not val.strip())
                             or (isinstance(val, (list, dict)) and not val))
                    if vuoto and madre.get(campo):
                        r[campo] = madre[campo]
                r["_ereditata_da"] = madre.get("nome")
                r["_nota_variante"] = r.get("descrizione") or ""
                # alias per il badge "Variante di" del frontend (nomi campo richiesti)
                r["ricetta_madre_nome"] = madre.get("nome")
                r["ricetta_madre_id"] = r.get("parent_recipe_id")
        # "PERCHÉ FUNZIONA" (audit OpenAI): fenomeni + ingredienti protagonisti + spiegazione.
        try:
            _fen = r.get("fenomeni") or []
            _fen_list = _fen if isinstance(_fen, list) else []
            _ing = r.get("ingredienti") or []
            _ing_nomi = []
            for _i in (_ing if isinstance(_ing, list) else [])[:3]:
                _n = _i.get("nome") if isinstance(_i, dict) else str(_i)
                if _n: _ing_nomi.append(_n)
            _pc = (r.get("punto_critico") or "").strip()
            if _fen_list or _pc:
                _fen_txt = ", ".join(str(f) for f in _fen_list[:3]) if _fen_list else ""
                r["perche_funziona"] = {
                    "fenomeni": _fen_list[:3],
                    "ingredienti_protagonisti": _ing_nomi,
                    "spiegazione": (f"Questo piatto sfrutta {_fen_txt}. " if _fen_txt else "") + _pc
                }
        except Exception:
            pass
        # RICETTE COLLEGATE DAL GRAFO (audit OpenAI): stesso fenomeno / stessa disciplina.
        try:
            _disc = r.get("disciplina")
            _fen0 = None
            _fen = r.get("fenomeni") or []
            if isinstance(_fen, list) and _fen:
                _fen0 = _fen[0] if isinstance(_fen[0], str) else (_fen[0].get("nome") if isinstance(_fen[0], dict) else None)
            collegate = []
            _visti_nomi = set()
            if _fen0:
                _rows = db.execute(
                    "SELECT id, nome FROM ricette WHERE id<>? AND disciplina=? "
                    "AND fenomeni::text LIKE ? LIMIT 10", (rid, _disc, f"%{_fen0}%")).fetchall()
                for _rr in _rows:
                    _nm = _rr["nome"] if hasattr(_rr, "keys") else _rr[1]
                    _nm_key = (_nm or "").strip().lower()
                    if _nm_key in _visti_nomi:
                        continue  # dedup: niente ricette collegate duplicate
                    _visti_nomi.add(_nm_key)
                    collegate.append({"id": _rr["id"] if hasattr(_rr, "keys") else _rr[0],
                                      "nome": _nm, "legame": "stesso fenomeno"})
                    if len(collegate) >= 3:
                        break
            r["ricette_collegate"] = collegate
        except Exception:
            r["ricette_collegate"] = []
        return jsonify({"ricetta": r})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]}), 200
