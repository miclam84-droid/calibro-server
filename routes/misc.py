# ============================================================
# routes/misc.py — Stripe, feedback utente, supporto.
# Dipende da: db, auth, notifiche.
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn
from auth import _utente_da_token
from notifiche import _invia_email_resend
from config import DATABASE_URL
from ai import _haiku_raw
import os, json
bp = Blueprint("misc", __name__)


@bp.route("/v1/stripe/checkout", methods=["POST"])
def stripe_checkout():
    """GT8 — Crea sessione Stripe Checkout per abbonamento Pro.
    Richiede STRIPE_SECRET_KEY nelle variabili Railway."""
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        return jsonify({"errore":"pagamenti non configurati"}), 503
    
    try:
        import urllib.request, urllib.parse
        # crea sessione checkout Stripe
        body = urllib.parse.urlencode({
            "mode": "subscription",
            "payment_method_types[]": "card",
            "line_items[0][price]": os.environ.get("STRIPE_PRICE_PRO",""),
            "line_items[0][quantity]": "1",
            "success_url": f"{request.host_url}?piano=pro&success=1",
            "cancel_url": f"{request.host_url}?cancel=1",
            "metadata[user_id]": str(user_id)
        }).encode()
        req = urllib.request.Request(
            "https://api.stripe.com/v1/checkout/sessions",
            data=body,
            headers={"Authorization": f"Bearer {stripe_key}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return jsonify({"url": data.get("url"), "checkout_url": data.get("url"), "session_id": data.get("id")})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/v1/stripe/webhook", methods=["POST"])
def stripe_webhook():
    """GT8 — Webhook Stripe: aggiorna piano utente a Pro dopo pagamento.
    Irrobustito: verifica firma (se configurata), idempotenza via stripe_events,
    e gestione errori corretta (500 se il DB fallisce → Stripe riprova).
    """
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        # Stripe non configurato (pre-P.IVA): accetta senza agire.
        return jsonify({"ok": True})

    payload = request.get_data()

    # 1. Verifica firma Stripe se il webhook secret è configurato (sicurezza).
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if webhook_secret:
        try:
            import stripe as _stripe
            sig = request.headers.get("Stripe-Signature", "")
            event = _stripe.Webhook.construct_event(payload, sig, webhook_secret)
            data = event  # oggetto verificato
        except Exception:
            # firma non valida → rifiuta (non è Stripe o payload manomesso)
            return jsonify({"errore": "firma non valida"}), 400
    else:
        # nessun secret configurato: parsing diretto (modalità test/sandbox)
        try:
            data = json.loads(payload)
        except Exception:
            return jsonify({"errore": "payload non valido"}), 400

    event_id = data.get("id", "")
    event_type = data.get("type", "")

    if event_type not in ("checkout.session.completed", "customer.subscription.created"):
        return jsonify({"ok": True, "ignorato": event_type})

    obj = data.get("data", {}).get("object", {})
    user_id = obj.get("metadata", {}).get("user_id")
    if not user_id or not DATABASE_URL:
        return jsonify({"ok": True, "nota": "nessun user_id o db"})

    # 2. Idempotenza + 3. gestione errori corretta.
    # Se il DB fallisce, restituiamo 500: Stripe riprova (non perdiamo il pagamento).
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        # tabella eventi processati (idempotenza) — creata al volo se non esiste
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT,
                user_id TEXT,
                ts TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        # se l'evento è già stato processato, esci senza riscrivere
        if event_id:
            cur.execute("SELECT 1 FROM stripe_events WHERE event_id=%s", (event_id,))
            if cur.fetchone():
                cur.close(); _release_conn(conn)
                return jsonify({"ok": True, "gia_processato": event_id})
        # attiva Pro + registra l'evento nella stessa transazione (atomico)
        cur.execute("UPDATE utenti SET piano='pro' WHERE id=%s", (user_id,))
        if event_id:
            cur.execute(
                "INSERT INTO stripe_events (event_id, event_type, user_id) VALUES (%s,%s,%s) ON CONFLICT (event_id) DO NOTHING",
                (event_id, event_type, str(user_id)))
        conn.commit(); cur.close(); _release_conn(conn)
        # evento funnel: paid (pagamento confermato). Difensivo, fuori dalla transazione critica.
        try:
            import oss
            _meta = obj.get("metadata", {}) or {}
            oss.funnel_write("paid", user_id=int(user_id) if str(user_id).isdigit() else None,
                             email=_meta.get("email"),
                             utm_campaign=_meta.get("utm_campaign"), utm_content=_meta.get("utm_content"))
        except Exception:
            pass
    except Exception as e:
        # NON silenziare: 500 → Stripe riprova l'invio
        try:
            conn.rollback(); _release_conn(conn)
        except Exception:
            pass
        return jsonify({"errore": "elaborazione fallita", "dettaglio": str(e)[:100]}), 500

    return jsonify({"ok": True, "attivato_pro": user_id})

@bp.route("/v1/feedback", methods=["POST"])
def feedback():
    """AC5 — Pollice su/giù sulla risposta di Sonnet.
    Alimenta log_domande con campo feedback per affinare il prompt."""
    body = request.json or {}
    log_id = body.get("log_id")
    voto = body.get("voto")  # 1 = positivo, -1 = negativo
    nota = body.get("nota", "")
    if not log_id or voto not in (1, -1):
        return jsonify({"errore": "log_id e voto (1/-1) obbligatori"}), 400
    if not DATABASE_URL:
        return jsonify({"ok": True})
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        # aggiunge colonna feedback se non esiste
        cur.execute("""
            ALTER TABLE log_domande
            ADD COLUMN IF NOT EXISTS feedback INTEGER,
            ADD COLUMN IF NOT EXISTS feedback_nota TEXT
        """)
        cur.execute(
            "UPDATE log_domande SET feedback=%s, feedback_nota=%s WHERE id=%s",
            (voto, nota[:200], log_id)
        )
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/v1/supporto", methods=["POST"])
def supporto():
    """Chatbot di supporto in-app. Salva in log_domande con tipo='supporto',
    risponde via Haiku (solo info prodotto reali), supporta la cronologia multi-turno.
    Notifica l'admin via email."""
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    body = request.json or {}
    testo = body.get("testo","").strip()
    history = body.get("history", [])  # [{ruolo, testo}, ...] per il multi-turno
    if not testo:
        return jsonify({"errore":"testo vuoto"}), 400

    if DATABASE_URL:
        try:
            import psycopg2
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO log_domande (tipo, domanda, esito, user_id) VALUES (%s,%s,%s,%s)",
                ("supporto", testo[:1000], "ricevuto", str(user_id) if user_id else None))
            conn.commit(); cur.close(); _release_conn(conn)
        except Exception:
            pass

    system_supporto = (
        "Sei l'assistente di supporto di Matter Lab, strumento scientifico per professionisti F&B "
        "(bar, panificazione, pasticceria, gelateria, caffetteria, cucina, vino, birra). "
        "COSA FA MATTER LAB: spiega la scienza del mestiere — oltre 140 fenomeni fisici/chimici con numeri "
        "bersaglio misurabili al banco, decine di tecniche con esecuzione passo-passo, oltre 450 ricette ancorate "
        "a fenomeni e tecniche, un flavor network di 1.530 ingredienti per gli abbinamenti (per analogia "
        "e per contrasto), e una feature foto che riconosce ingredienti e bottiglie suggerendo abbinamenti. "
        "SEZIONI: Scopri (fenomeni), Lezione (percorso guidato), Mappa (atlante), Chiedi (assistente AI). "
        "Piano Pro a 19,99€/mese, con prova gratuita. "
        "Aiuta l'utente a usare l'app. NON inventare funzioni inesistenti. Se non sai o è un problema "
        "tecnico, di' che il team risponde via email entro 24 ore. Massimo 4 frasi, tono diretto e caldo."
    )
    # costruisci il contesto multi-turno
    conversazione = ""
    for h in history[-6:]:  # ultimi 6 messaggi
        ruolo = "Utente" if h.get("ruolo") == "utente" else "Assistente"
        conversazione += f"{ruolo}: {h.get('testo','')}\n"
    conversazione += f"Utente: {testo}"

    risposta = None
    try:
        resp = _haiku_raw(system_supporto + "\n\n" + conversazione, max_tokens=350)
        if resp:
            risposta = resp
    except Exception:
        pass
    if not risposta:
        risposta = ("Non riesco a rispondere in questo momento. "
                    "Il tuo messaggio è stato registrato — ti risponderemo via email entro 24 ore.")

    # notifica admin (tu) — arriva subito sulla tua Gmail
    admin_email = os.environ.get("MATTER_ADMIN_EMAIL", "miclam84@gmail.com")
    _invia_email_resend(
        to=admin_email,
        subject="⚠ Nuova richiesta supporto — Matter",
        body_html=(f"<p><strong>Nuova richiesta di supporto su Matter.</strong></p>"
                   f"<p><strong>Utente:</strong> {str(user_id) if user_id else 'non loggato'}</p>"
                   f"<p><strong>Messaggio:</strong><br>{testo}</p>"
                   f"<p><a href='/admin/assistenza'>Apri pannello assistenza →</a></p>"),
        body_text=f"Nuova richiesta supporto Matter.\nUtente: {user_id}\n\n{testo}"
    )

    return jsonify({"risposta": risposta})


@bp.route("/v1/founding/posti", methods=["GET"])
def founding_posti():
    """Contatore posti Founding Member: {rimasti, totali}.
    Totali da env FOUNDING_TOTALI (default 100). Rimasti = totali - founding già attivi.
    Difensivo: se il DB non risponde, torna i totali pieni (non blocca la landing)."""
    import os as _os
    try:
        totali = int(_os.environ.get("FOUNDING_TOTALI", "100"))
    except Exception:
        totali = 100
    usati = 0
    if DATABASE_URL:
        try:
            conn = _get_conn(); cur = conn.cursor()
            # conto gli utenti con piano 'founding' (segnato al pagamento del piano founding)
            cur.execute("SELECT COUNT(*) FROM utenti WHERE piano = 'founding'")
            r = cur.fetchone()
            usati = int(r[0]) if r and r[0] else 0
            cur.close(); _release_conn(conn)
        except Exception:
            usati = 0
    rimasti = max(totali - usati, 0)
    return jsonify({"rimasti": rimasti, "totali": totali, "esauriti": rimasti == 0})


# ── HOOK MATTER → GALILEO (predisposto, DISATTIVATO fino a quando Galileo ha Stripe) ──
# Quando un utente Matter vuole "aprire il suo locale", questo avvia una Strategic Run su Galileo.
# NON ATTIVO al lancio: Galileo deve prima avere il billing (Fase 1 roadmap Galileo). Attivare
# mettendo GALILEO_HOOK_ATTIVO=1 su Railway quando Galileo è pronto a incassare.
@bp.route("/v1/matter/galileo-run", methods=["POST"])
def matter_avvia_galileo_run():
    """Predisposto per il futuro: avvia una Strategic Run su Galileo dal contesto Matter.
    DISATTIVATO finché Galileo non ha billing. Ritorna 503 con messaggio finché non è attivo."""
    import os
    if os.environ.get("GALILEO_HOOK_ATTIVO", "0") != "1":
        return jsonify({
            "attivo": False,
            "messaggio": "La Strategic Run di Galileo sarà presto disponibile. Stiamo completando l'integrazione.",
            "coming_soon": True
        }), 503
    # --- quando attivo (post-lancio, Galileo con Stripe): ---
    body = request.json or {}
    _galileo_url = os.environ.get("GALILEO_URL", "")
    _galileo_secret = os.environ.get("GALILEO_SECRET", "")
    if not _galileo_url or not _galileo_secret:
        return jsonify({"errore": "Galileo non configurato"}), 503
    try:
        import urllib.request as _ur, json as _j
        payload = _j.dumps({
            "contesto": "matter",
            "profilo": body.get("profilo", {}),
            "tipo_run": body.get("tipo_run", "standard"),
        }).encode()
        req = _ur.Request(f"{_galileo_url}/v1/matter/avvia-run", data=payload,
                          headers={"Content-Type": "application/json", "X-Galileo-Secret": _galileo_secret})
        with _ur.urlopen(req, timeout=30) as r:
            return jsonify(_j.loads(r.read().decode()))
    except Exception as e:
        return jsonify({"errore": "Galileo non raggiungibile", "dettaglio": str(e)[:100]}), 502


@bp.route("/v1/trail/<ingrediente>", methods=["GET"])
def knowledge_trail(ingrediente):
    """KNOWLEDGE TRAIL: percorso di scoperta da un ingrediente (longevità/retention).
    ingrediente -> composto -> affine -> fenomeno -> ricetta. Tappe reali dal grafo."""
    try:
        from db import carica_grafo
        from knowledge_trails import costruisci_trail
        db = carica_grafo()
        tappe = costruisci_trail(db, ingrediente)
        if not tappe:
            return jsonify({"ingrediente": ingrediente, "trail": [],
                            "nota": "Percorso non disponibile per questo ingrediente."})
        return jsonify({"ingrediente": ingrediente, "trail": tappe, "n_tappe": len(tappe)})
    except Exception as e:
        return jsonify({"errore": str(e)[:120], "trail": []}), 200


@bp.route("/v1/cerca", methods=["GET"])
def cerca_universale():
    """RICERCA UNIVERSALE: ricette + ingredienti + fenomeni + tecniche insieme."""
    from flask import request, jsonify
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"query": q, "risultati": [], "nota": "cerca almeno 2 caratteri"})
    pat = "%" + q + "%"
    # tokenizzo: spezzo in parole e costruisco un OR (così "olio cottura" trova "olio" o "cottura")
    parole = [p for p in q.split() if len(p) >= 2]
    if not parole:
        parole = [q]
    def _cond(campo):
        # costruisce "campo ILIKE ? OR campo ILIKE ? ..." per ogni parola + la frase intera
        conds = [f"{campo} ILIKE ?" for _ in parole] + [f"{campo} ILIKE ?"]
        return "(" + " OR ".join(conds) + ")"
    def _params():
        return tuple(f"%{p}%" for p in parole) + (pat,)
    risultati = []
    try:
        from db import carica_grafo
        db = carica_grafo()
        def _c(r, key, idx):
            return r[key] if hasattr(r, "keys") else r[idx]
        # RICETTE - cerca su nome con OR sulle parole
        rows = db.execute(f"SELECT id, nome, disciplina FROM ricette WHERE {_cond('nome')} LIMIT 10", _params()).fetchall()
        for r in rows:
            risultati.append({"tipo": "ricetta", "id": _c(r,"id",0), "nome": _c(r,"nome",1), "disciplina": _c(r,"disciplina",2)})
        rows = db.execute(f"SELECT id, name FROM nodes WHERE type='Fenomeno' AND {_cond('name')} LIMIT 6", _params()).fetchall()
        for r in rows:
            risultati.append({"tipo": "fenomeno", "id": _c(r,"id",0), "nome": _c(r,"name",1)})
        # INGREDIENTI (type Ingrediente E Prodotto) - qui stanno le cultivar/tagli/varieta
        rows = db.execute(f"SELECT id, name, data FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND {_cond('name')} AND name NOT LIKE '%%(%%' LIMIT 12", _params()).fetchall()
        for r in rows:
            _data = _c(r,"data",2) if (hasattr(r,'keys') or len(r)>2) else None
            _carat = ''
            try:
                import json as _j
                _dd = _data if isinstance(_data, dict) else (_j.loads(_data) if _data else {})
                _carat = _dd.get('caratteristica','') or ''
            except: pass
            risultati.append({"tipo": "ingrediente", "id": _c(r,"id",0), "nome": _c(r,"name",1), "caratteristica": _carat[:70]})
        rows = db.execute(f"SELECT id, name FROM nodes WHERE type='Tecnica' AND {_cond('name')} LIMIT 4", _params()).fetchall()
        for r in rows:
            risultati.append({"tipo": "tecnica", "id": _c(r,"id",0), "nome": _c(r,"name",1)})
        # dedup per id
        _visti = set(); _dedup = []
        for x in risultati:
            k = (x["tipo"], x["id"])
            if k not in _visti:
                _visti.add(k); _dedup.append(x)
        risultati = _dedup
    except Exception as e:
        return jsonify({"query": q, "risultati": risultati, "errore": str(e)[:120]})
    return jsonify({"query": q, "risultati": risultati, "totale": len(risultati)})


@bp.route("/v1/abbina-esteso/<ingrediente>", methods=["GET"])
def abbina_esteso(ingrediente):
    """Abbinamenti VERIFICATI (Ahn) + ESPLORATIVI (AI, marcati). Il Flavour esteso.
    I due livelli restano DISTINTI: verificati = scienza, esplorativi = da provare."""
    from flask import jsonify
    import os
    risultato = {"ingrediente": ingrediente, "verificati": [], "esplorativi": []}
    # 1. VERIFICATI dal grafo Ahn (la fonte scientifica)
    try:
        from db import carica_grafo
        db = carica_grafo()
        ing_l = ingrediente.lower()
        _it_en = {"basilico":"basil","pomodoro":"tomato","limone":"lemon","aglio":"garlic",
                  "cioccolato":"chocolate","caffè":"coffee","fragola":"strawberry"}
        ing_en = _it_en.get(ing_l, ing_l)
        rows = db.execute("""SELECT n2.name FROM nodes n1 JOIN edges e ON e.from_id=n1.id
                             JOIN nodes n2 ON n2.id=e.to_id
                             WHERE lower(n1.name)=? AND e.relation='abbinamento_aromatico' LIMIT 20""", (ing_en,)).fetchall()
        for r in rows:
            nome = r["name"] if hasattr(r,"keys") else r[0]
            risultato["verificati"].append(nome.replace("_"," "))
    except Exception:
        pass
    # 2. ESPLORATIVI: prima cerco in tabella cache abbinamenti_ai, poi genero se manca
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS abbinamenti_ai (ingrediente TEXT, abbinato TEXT, forza TEXT, PRIMARY KEY(ingrediente,abbinato))")
        cur.execute("SELECT abbinato, forza FROM abbinamenti_ai WHERE ingrediente=%s", (ingrediente.lower(),))
        cached = cur.fetchall()
        if cached:
            risultato["esplorativi"] = [{"ingrediente": r[0], "forza": r[1]} for r in cached]
        else:
            from arricchisci_abbinamenti import genera_abbinamenti_ai
            gen = genera_abbinamenti_ai(ingrediente)
            for g in gen:
                try:
                    cur.execute("INSERT INTO abbinamenti_ai (ingrediente,abbinato,forza) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                                (ingrediente.lower(), g["ingrediente"], g["forza"]))
                except Exception:
                    pass
            conn.commit()
            risultato["esplorativi"] = [{"ingrediente": g["ingrediente"], "forza": g["forza"]} for g in gen]
        cur.close(); conn.close()
    except Exception as e:
        risultato["_nota_esplorativi"] = str(e)[:80]
    risultato["_avviso"] = "Verificati: scienza (Ahn). Esplorativi: stima AI, da provare al banco."
    return jsonify(risultato)


@bp.route("/admin/aggiungi-ingrediente/<ingrediente>", methods=["GET"])
def admin_aggiungi_ingrediente(ingrediente):
    """Aggiunge un ingrediente NUOVO al grafo generando i suoi COMPOSTI aromatici (via AI, fatti
    chimici). Poi il grafo trova gli abbinamenti DA SOLO dai composti condivisi. Il modo GIUSTO."""
    from flask import request, jsonify
    import os
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        from db import carica_grafo
        import importlib, aggiungi_ingrediente
        importlib.reload(aggiungi_ingrediente)
        from aggiungi_ingrediente import genera_composti_ingrediente, aggiungi_al_grafo
        composti = genera_composti_ingrediente(ingrediente)
        if not composti:
            return jsonify({"errore": "AI non ha generato composti, riprova", "ingrediente": ingrediente})
        db = carica_grafo()
        res = aggiungi_al_grafo(db, ingrediente, composti)
        # ora conto quanti abbinamenti EMERGONO dal grafo (ingredienti che condividono i composti)
        import re
        ing_id = res["id"]
        abb = db.execute("""SELECT DISTINCT n3.name FROM edges e1
                            JOIN edges e2 ON e1.to_id = e2.to_id
                            JOIN nodes n3 ON n3.id = e2.from_id
                            WHERE e1.from_id = ? AND e1.relation='contiene_composto'
                            AND e2.relation='contiene_composto' AND n3.type='Ingrediente'
                            AND e2.from_id <> ? LIMIT 30""", (ing_id, ing_id)).fetchall()
        abbinamenti = [(r["name"] if hasattr(r,"keys") else r[0]).replace("_"," ") for r in abb]
        return jsonify({
            "ingrediente": ingrediente,
            "composti_generati": composti,
            "composti_aggiunti": res["composti_aggiunti"],
            "abbinamenti_emersi_dal_grafo": abbinamenti[:20],
            "totale_abbinamenti": len(abbinamenti),
            "nota": "I composti sono fatti chimici (AI). Gli abbinamenti EMERGONO dal grafo (composti condivisi), non sono stime."
        })
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/diag-composti", methods=["GET"])
def admin_diag_composti():
    """Diagnostica: come sono nominati i composti nel grafo (per allineare l'aggiunta ingredienti)."""
    from flask import request, jsonify
    import os
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        from db import carica_grafo
        db = carica_grafo()
        # esempi di composti che contengono 'limon' (limonene)
        rows = db.execute("SELECT id, name FROM nodes WHERE type='Composto' AND (name ILIKE '%limon%' OR name ILIKE '%linal%') LIMIT 10").fetchall()
        composti = [{"id": (r["id"] if hasattr(r,"keys") else r[0]), "name": (r["name"] if hasattr(r,"keys") else r[1])} for r in rows]
        # totale composti
        tot = db.execute("SELECT COUNT(*) FROM nodes WHERE type='Composto'").fetchone()
        totale = tot["count"] if hasattr(tot,"keys") else tot[0]
        return jsonify({"totale_composti": totale, "esempi_limonene_linalolo": composti})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/diag-composti2", methods=["GET"])
def admin_diag_composti2():
    from flask import request, jsonify
    import os
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    out = {}
    try:
        from db import carica_grafo
        db = carica_grafo()
        # primi 15 composti a caso col loro id e name
        rows = db.execute("SELECT id, name FROM nodes WHERE type='Composto' LIMIT 15").fetchall()
        out["esempi"] = [{"id": (r["id"] if hasattr(r,"keys") else r[0]), "name": (r["name"] if hasattr(r,"keys") else r[1])} for r in rows]
    except Exception as e:
        out["errore_esempi"] = str(e)[:100]
    try:
        from db import carica_grafo
        db = carica_grafo()
        # cerco qualsiasi composto che contenga 'limon' in id o name
        rows = db.execute("SELECT id, name FROM nodes WHERE type='Composto' AND (id ILIKE '%limon%' OR name ILIKE '%limon%') LIMIT 5").fetchall()
        out["limonene_match"] = [{"id": (r["id"] if hasattr(r,"keys") else r[0]), "name": (r["name"] if hasattr(r,"keys") else r[1])} for r in rows]
    except Exception as e:
        out["errore_limon"] = str(e)[:100]
    return jsonify(out)


@bp.route("/admin/diag-aggancio/<ingrediente>", methods=["GET"])
def admin_diag_aggancio(ingrediente):
    """Diagnostica DEEP: mostra a quali comp_id si collega un ingrediente e se quei comp_id
    sono condivisi con gli ingredienti Ahn (per capire perché gli abbinamenti non emergono)."""
    from flask import request, jsonify
    import os, re
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    out = {"ingrediente": ingrediente}
    try:
        from db import carica_grafo
        db = carica_grafo()
        ing_id = "ai_" + re.sub(r"[^a-z0-9]+", "_", ingrediente.lower()).strip("_")
        # a quali composti è collegato questo ingrediente?
        rows = db.execute("SELECT to_id FROM edges WHERE from_id=? AND relation='contiene_composto'", (ing_id,)).fetchall()
        comp_ids = [(r["to_id"] if hasattr(r,"keys") else r[0]) for r in rows]
        out["comp_ids_ingrediente"] = comp_ids[:15]
        # per il primo composto, quanti ALTRI ingredienti (Prodotto) lo contengono?
        if comp_ids:
            c0 = comp_ids[0]
            rows2 = db.execute("SELECT COUNT(*) FROM edges WHERE to_id=? AND relation='contiene_composto'", (c0,)).fetchall()
            n = (rows2[0]["count"] if hasattr(rows2[0],"keys") else rows2[0][0]) if rows2 else 0
            out["composto_test"] = c0
            out["quanti_ingredienti_lo_contengono"] = n
            # quali ingredienti Prodotto?
            rows3 = db.execute("""SELECT n.name FROM edges e JOIN nodes n ON n.id=e.from_id
                                  WHERE e.to_id=? AND e.relation='contiene_composto' AND n.type='Prodotto' LIMIT 8""", (c0,)).fetchall()
            out["ingredienti_col_composto"] = [(r["name"] if hasattr(r,"keys") else r[0]) for r in rows3]
    except Exception as e:
        out["errore"] = str(e)[:120]
    return jsonify(out)


@bp.route("/admin/diag-ahn/<ingrediente>", methods=["GET"])
def admin_diag_ahn(ingrediente):
    """Mostra a quali comp_id è collegato un ingrediente AHN (per vedere il formato reale)."""
    from flask import request, jsonify
    import os
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    out = {"ingrediente": ingrediente}
    try:
        from db import carica_grafo
        db = carica_grafo()
        _it_en = {"arancia":"orange","limone":"lemon","pompelmo":"grapefruit","basilico":"basil"}
        nome_en = _it_en.get(ingrediente.lower(), ingrediente.lower())
        # trovo il nodo ahn
        rows = db.execute("SELECT id FROM nodes WHERE type='Prodotto' AND name ILIKE ? LIMIT 1", (nome_en + "%",)).fetchall()
        if not rows:
            out["nota"] = f"ingrediente Ahn '{nome_en}' non trovato"
            return jsonify(out)
        ahn_id = rows[0]["id"] if hasattr(rows[0],"keys") else rows[0][0]
        out["ahn_id"] = ahn_id
        # a quali composti (id + name) è collegato?
        rows2 = db.execute("""SELECT n.id, n.name FROM edges e JOIN nodes n ON n.id=e.to_id
                              WHERE e.from_id=? AND e.relation='contiene_composto' LIMIT 12""", (ahn_id,)).fetchall()
        out["composti_ahn"] = [{"id": (r["id"] if hasattr(r,"keys") else r[0]), "name": (r["name"] if hasattr(r,"keys") else r[1])} for r in rows2]
    except Exception as e:
        out["errore"] = str(e)[:120]
    return jsonify(out)


@bp.route("/admin/diag-grafo-conta", methods=["GET"])
def admin_diag_grafo_conta():
    """Conta i nodi che vede carica_grafo() - per capire se è il grafo completo o parziale."""
    from flask import request, jsonify
    import os
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    out = {}
    try:
        from db import carica_grafo
        db = carica_grafo()
        for tipo in ["Prodotto", "Composto", "Ingrediente", "Fenomeno"]:
            r = db.execute("SELECT COUNT(*) FROM nodes WHERE type=?", (tipo,)).fetchall()
            out[tipo] = (r[0]["count"] if hasattr(r[0],"keys") else r[0][0]) if r else 0
        # esempi di nomi Prodotto
        rows = db.execute("SELECT id, name FROM nodes WHERE type='Prodotto' LIMIT 8").fetchall()
        out["esempi_prodotto"] = [{"id":(r["id"] if hasattr(r,"keys") else r[0]),"name":(r["name"] if hasattr(r,"keys") else r[1])} for r in rows]
        # cerco basil in QUALSIASI modo
        rows2 = db.execute("SELECT id, name, type FROM nodes WHERE id ILIKE ? OR name ILIKE ? LIMIT 5", ("%basil%","%basil%")).fetchall()
        out["ricerca_basil"] = [{"id":(r["id"] if hasattr(r,"keys") else r[0]),"name":(r["name"] if hasattr(r,"keys") else r[1]),"type":(r["type"] if hasattr(r,"keys") else r[2])} for r in rows2]
    except Exception as e:
        out["errore"] = str(e)[:120]
    return jsonify(out)


@bp.route("/v1/libro-affiliato", methods=["GET"])
def libro_affiliato():
    """Ritorna il libro di riferimento (link affiliato Amazon) per una disciplina o fenomeno.
    Il frontend lo mostra nelle schede fenomeno/ricetta come 'Approfondisci'."""
    from flask import request, jsonify
    disciplina = request.args.get("disciplina", "")
    fenomeno = request.args.get("fenomeno", "")
    try:
        from affiliati_libri import libro_per_fenomeno, libro_per_disciplina
        if fenomeno:
            libro = libro_per_fenomeno(fenomeno, disciplina or None)
        else:
            libro = libro_per_disciplina(disciplina)
        if not libro:
            return jsonify({"libro": None})
        return jsonify({"libro": libro})
    except Exception as e:
        return jsonify({"libro": None, "_err": str(e)[:80]})


@bp.route("/v1/motore/panificazione", methods=["POST"])
def motore_panificazione_endpoint():
    """MOTORE OPERATIVO Panificazione Pro: dato l'obiettivo, progetta il processo completo.
    Il differenziatore vs MasterBiga - parte dall'obiettivo, non dagli ingredienti."""
    from flask import request, jsonify
    try:
        d = request.get_json(force=True) or {}
        from motore_panificazione import progetta
        r = progetta(
            tipo=d.get("tipo", "pizza_napoletana"),
            n_panetti=int(d.get("n_panetti", 6)),
            peso_panetto=int(d.get("peso_panetto", 280)),
            metodo=d.get("metodo", "diretto"),
            idratazione=d.get("idratazione"),
            temp_ambiente=float(d.get("temp_ambiente", 22)),
            temp_farina=float(d.get("temp_farina", 20)),
            ore_lievitazione=float(d.get("ore_lievitazione", 8)),
            ora_sfornata=d.get("ora_sfornata", "20:00"),
            temp_finale_voluta=d.get("temp_finale_voluta"),
        )
        return jsonify(r)
    except Exception as e:
        return jsonify({"errore": str(e)[:150]}), 200


@bp.route("/v1/motore/panificazione/sbalzo", methods=["POST"])
def motore_sbalzo_endpoint():
    """KILLER FEATURE: ricalcola la timeline per uno sbalzo di temperatura al banco.
    L'utente ha un impasto in corso, la temperatura cambia, Matter ricalibra i tempi."""
    from flask import request, jsonify
    try:
        d = request.get_json(force=True) or {}
        from motore_panificazione import ricalcola_sbalzo
        return jsonify(ricalcola_sbalzo(
            float(d.get("temp_originale", 22)),
            float(d.get("temp_nuova", 22)),
            float(d.get("ore_rimanenti", 8))
        ))
    except Exception as e:
        return jsonify({"errore": str(e)[:150]}), 200


@bp.route("/v1/motore/gelato", methods=["POST"])
def motore_gelato_endpoint():
    from flask import request, jsonify
    try:
        d = request.get_json(force=True) or {}
        from motore_gelato import progetta_gelato
        return jsonify(progetta_gelato(d.get("tipo","crema"), int(d.get("quantita_g",1000)), int(d.get("temp_vetrina",-12))))
    except Exception as e:
        return jsonify({"errore": str(e)[:150]}), 200


@bp.route("/v1/motore/cocktail", methods=["POST"])
def motore_cocktail_endpoint():
    from flask import request, jsonify
    try:
        d = request.get_json(force=True) or {}
        from motore_cocktail import progetta_cocktail
        return jsonify(progetta_cocktail(int(d.get("volume_finale_ml",90)), float(d.get("gradazione_voluta",22)),
                                         d.get("tecnica","stirred"), float(d.get("gradazione_ingredienti",40))))
    except Exception as e:
        return jsonify({"errore": str(e)[:150]}), 200


@bp.route("/v1/motore/caffe", methods=["POST"])
def motore_caffe_endpoint():
    from flask import request, jsonify
    try:
        d = request.get_json(force=True) or {}
        from motore_caffe import progetta_caffe
        return jsonify(progetta_caffe(d.get("metodo","espresso"), int(d.get("dose_g",18))))
    except Exception as e:
        return jsonify({"errore": str(e)[:150]}), 200


@bp.route("/v1/ingrediente/<ingrediente_id>", methods=["GET"])
def scheda_ingrediente(ingrediente_id):
    """Scheda ingrediente: proprieta' sensoriali, caratteristica, uso, varieta' (figli), con cosa dialoga.
    Per il tap su un ingrediente dai risultati di ricerca."""
    from flask import jsonify
    import json as _j
    try:
        from db import carica_grafo
        db = carica_grafo()
        def _c(r, key, idx): return r[key] if hasattr(r, "keys") else r[idx]
        # trovo per id o per nome
        rows = db.execute("SELECT id, name, data FROM nodes WHERE (id=? OR LOWER(name)=LOWER(?)) AND type IN ('Ingrediente','Prodotto') LIMIT 1", (ingrediente_id, ingrediente_id)).fetchall()
        if not rows:
            return jsonify({"errore": "ingrediente non trovato"}), 404
        r = rows[0]
        nid = _c(r,"id",0); nome = _c(r,"name",1); data = _c(r,"data",2)
        dd = data if isinstance(data, dict) else (_j.loads(data) if data else {})
        prop = dd.get("proprieta", {})
        # varieta' figlie (stesso genitore o categoria)
        cat = dd.get("categoria")
        varieta = []
        if cat:
            vr = db.execute("SELECT name FROM nodes WHERE type='Ingrediente' AND json_extract(data,'$.categoria')=? AND id!=? LIMIT 12", (cat, nid)).fetchall() if False else []
        # con cosa dialoga (abbinamenti aromatici)
        abb = db.execute("SELECT n.name FROM edges e JOIN nodes n ON n.id=e.to_id WHERE e.from_id=? AND e.relation='abbinamento_aromatico' LIMIT 8", (nid,)).fetchall()
        dialoga = [_c(x,"name",0) for x in abb]
        prop_alte = {k: v for k, v in prop.items() if abs(v) >= 4} if prop else {}
        return jsonify({
            "id": nid, "nome": nome,
            "caratteristica": dd.get("caratteristica",""),
            "uso_tipico": dd.get("uso_tipico",""),
            "categoria": cat,
            "origine": dd.get("origine",""),
            "proprieta_principali": prop_alte,
            "dialoga_con": dialoga,
        })
    except Exception as e:
        return jsonify({"errore": str(e)[:120]}), 500


@bp.route("/v1/nodo-completo/<nodo_id>", methods=["GET"])
def nodo_completo(nodo_id):
    """NODO-PORTALE: tutto di un ingrediente per il pannello del grafo (tap su un nodo).
    Proprieta', operativo, fenomeni collegati, con cosa dialoga, ricette che lo usano, link Composer."""
    from flask import jsonify
    import json as _j
    try:
        from db import carica_grafo
        db = carica_grafo()
        def _c(r, key, idx): return r[key] if hasattr(r, "keys") else r[idx]
        rows = db.execute("SELECT id, name, data FROM nodes WHERE (id=? OR LOWER(name)=LOWER(?)) AND type IN ('Ingrediente','Prodotto') LIMIT 1", (nodo_id, nodo_id)).fetchall()
        if not rows:
            return jsonify({"errore": "nodo non trovato"}), 404
        r = rows[0]
        nid = _c(r,"id",0); nome = _c(r,"name",1); data = _c(r,"data",2)
        dd = data if isinstance(data, dict) else (_j.loads(data) if data else {})
        prop = dd.get("proprieta", {})
        prop_alte = {k: v for k, v in prop.items() if abs(v) >= 4} if prop else {}
        # fenomeni collegati (ogni query a prova di errore: una rotta non azzera tutto)
        fenomeni = []
        try:
            fen = db.execute("""SELECT n2.name FROM edges e JOIN nodes n2 ON n2.id=e.to_id
                                WHERE e.from_id=? AND n2.type='Fenomeno' LIMIT 5""", (nid,)).fetchall()
            fenomeni = [_c(x,"name",0) for x in fen]
        except Exception: pass
        dialoga = []
        try:
            abb = db.execute("""SELECT n2.name FROM edges e JOIN nodes n2 ON n2.id=e.to_id
                                WHERE e.from_id=? AND e.relation='abbinamento_aromatico' LIMIT 8""", (nid,)).fetchall()
            dialoga = [_c(x,"name",0) for x in abb]
        except Exception: pass
        ricette = []
        try:
            ric = db.execute("""SELECT DISTINCT nome FROM ricette WHERE LOWER(ingredienti) LIKE LOWER(?) LIMIT 5""", (f"%{nome}%",)).fetchall()
            ricette = [_c(x,"nome",0) for x in ric]
        except Exception: pass
        return jsonify({
            "id": nid, "nome": nome,
            "caratteristica": dd.get("caratteristica",""),
            "uso_tipico": dd.get("uso_tipico",""),
            "categoria": dd.get("categoria",""),
            "origine": dd.get("origine",""),
            "proprieta_principali": prop_alte,
            "operativo": dd.get("operativo", {}),
            "fenomeni": fenomeni,
            "dialoga_con": dialoga,
            "ricette": ricette,
            "azioni": {"componi": f"/v1/composer/prossimi", "chiedi": "/chiedi"},
        })
    except Exception as e:
        return jsonify({"errore": str(e)[:120]}), 500


@bp.route("/v1/ingrediente-fenomeni/<nodo_id>", methods=["GET"])
def ingrediente_fenomeni(nodo_id):
    """Vista FENOMENI del grafo: i fenomeni scientifici collegati a un ingrediente (Maillard, pectina...)."""
    from flask import jsonify
    try:
        from db import carica_grafo
        db = carica_grafo()
        def _c(r, key, idx): return r[key] if hasattr(r, "keys") else r[idx]
        rows = db.execute("SELECT id, name FROM nodes WHERE (id=? OR LOWER(name)=LOWER(?)) AND type IN ('Ingrediente','Prodotto') LIMIT 1", (nodo_id, nodo_id)).fetchall()
        if not rows:
            return jsonify({"errore": "non trovato"}), 404
        nid = _c(rows[0],"id",0); nome = _c(rows[0],"name",1)
        fen = []
        try:
            r = db.execute("""SELECT DISTINCT n2.name FROM edges e JOIN nodes n2 ON n2.id=e.to_id
                              WHERE e.from_id=? AND n2.type='Fenomeno' LIMIT 12""", (nid,)).fetchall()
            fen = [_c(x,"name",0) for x in r]
        except Exception: pass
        return jsonify({"centro": nome, "fenomeni": fen, "totale": len(fen)})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]}), 500


@bp.route("/v1/ingrediente-tecniche/<nodo_id>", methods=["GET"])
def ingrediente_tecniche(nodo_id):
    """Vista TECNICHE del grafo: le tecniche applicabili a un ingrediente (dal campo uso_tipico + euristica)."""
    from flask import jsonify
    import json as _j
    try:
        from db import carica_grafo
        db = carica_grafo()
        def _c(r, key, idx): return r[key] if hasattr(r, "keys") else r[idx]
        rows = db.execute("SELECT id, name, data FROM nodes WHERE (id=? OR LOWER(name)=LOWER(?)) AND type IN ('Ingrediente','Prodotto') LIMIT 1", (nodo_id, nodo_id)).fetchall()
        if not rows:
            return jsonify({"errore": "non trovato"}), 404
        nid = _c(rows[0],"id",0); nome = _c(rows[0],"name",1); data = _c(rows[0],"data",2)
        dd = data if isinstance(data, dict) else (_j.loads(data) if data else {})
        # tecniche dal campo uso_tipico + categoria
        tecniche = set()
        uso = (dd.get("uso_tipico","") or "").lower()
        cat = dd.get("categoria","")
        MAPPA_TECNICHE = {
            "griglia":"Grigliatura","forno":"Cottura al forno","frigg":"Frittura","fritto":"Frittura",
            "brasa":"Brasatura","bollit":"Bollitura","lessat":"Lessatura","confit":"Confit",
            "riduzione":"Riduzione","essicca":"Essiccazione","affumica":"Affumicatura","ferment":"Fermentazione",
            "crudo":"Crudo/Marinatura","marina":"Marinatura","risott":"Mantecatura","vellutat":"Vellutata",
            "spuma":"Spuma","gel":"Gelificazione","sciropp":"Sciroppo","salsa":"Salsa"}
        for k, v in MAPPA_TECNICHE.items():
            if k in uso: tecniche.add(v)
        # tecniche tipiche per categoria (se poche)
        if cat == "carne_bovina" and len(tecniche) < 3:
            tecniche.update(["Grigliatura","Brasatura","Scottatura"])
        elif cat == "pesce" and len(tecniche) < 3:
            tecniche.update(["Crudo/Marinatura","Cottura al forno","Scottatura"])
        elif cat in ("verdura","legume") and len(tecniche) < 2:
            tecniche.update(["Bollitura","Saltare in padella"])
        return jsonify({"centro": nome, "tecniche": sorted(tecniche), "totale": len(tecniche)})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]}), 500


@bp.route("/v1/cifra/ingrediente/<nodo_id>", methods=["GET"])
def cifra_ingrediente(nodo_id):
    """Per CIFRA: dati operativi di un ingrediente per food cost + HACCP in un colpo."""
    from flask import jsonify
    import json as _j
    try:
        from db import carica_grafo
        db = carica_grafo()
        def _c(r, key, idx): return r[key] if hasattr(r, "keys") else r[idx]
        rows = db.execute("SELECT id, name, data FROM nodes WHERE (id=? OR LOWER(name)=LOWER(?)) AND type IN ('Ingrediente','Prodotto') LIMIT 10", (nodo_id, nodo_id)).fetchall()
        if not rows:
            return jsonify({"errore": "ingrediente non trovato"}), 404
        def _ha_op(row):
            dt = _c(row,"data",2)
            try:
                d2 = dt if isinstance(dt, dict) else (_j.loads(dt) if dt else {})
                return 'operativo' in d2
            except: return False
        rows = sorted(rows, key=_ha_op, reverse=True)
        r = rows[0]
        nome = _c(r,"name",1); data = _c(r,"data",2)
        dd = data if isinstance(data, dict) else (_j.loads(data) if data else {})
        op = dd.get("operativo", {})
        yld = op.get("yield", 100)
        molt = round(100 / yld, 3) if yld else 1.0
        sl = op.get("shelf_life_giorni", 999)
        if sl <= 2: semaforo = "rosso"
        elif sl <= 7: semaforo = "giallo"
        else: semaforo = "verde"
        return jsonify({
            "nome": nome, "yield_perc": yld, "scarto_perc": op.get("scarto_perc", 100-yld),
            "moltiplicatore_costo_reale": molt, "allergeni": op.get("allergeni", []),
            "shelf_life_giorni": sl, "conservazione": op.get("conservazione", ""),
            "semaforo_haccp": semaforo, "stagione": op.get("stagione", ""),
        })
    except Exception as e:
        return jsonify({"errore": str(e)[:120]}), 500


# ═══ SCHEDE SCIENZA (Documento Madre A3, Rule #189/#190) — infrastruttura cognitiva ═══
# Struttura fissa a 8 blocchi. Ogni Preparazione Madre ha la sua scheda PRIMA della ricetta.
SCHEDE_SCIENZA = {
    "panettone": {
        "nome": "Panettone (grande lievitato)",
        "categoria": "grande lievitato",
        "fenomeno": "Gelatinizzazione dell'amido + coagulazione delle proteine dell'uovo, in una maglia glutinica sviluppata da lunga lievitazione con lievito madre.",
        "principio": "L'impasto acido (pH 4.5-5.0 da lievito madre) rinforza il glutine e rallenta la retrogradazione dell'amido: per questo il panettone resta morbido settimane. La struttura alveolata viene dall'incordatura e dai grassi (burro, tuorli) che lubrificano la maglia.",
        "numero_bersaglio": "94-96°C al cuore a fine cottura",
        "punto_critico": "Sotto 94°C l'amido non ha gelatinizzato del tutto: la struttura collassa allo sforno (avvallamento). Sopra 98°C si secca la mollica e si perde l'umidità che dà la lunga conservazione.",
        "segnale_reale": "Sonda a spillo al cuore del panettone (non al bordo). Raffreddamento CAPOVOLTO sugli spilloni per 8-12h: la struttura è troppo debole a caldo e collasserebbe sotto il proprio peso.",
        "tecnica": "Due impasti (primo la sera con madre+farina+acqua+zucchero+parte burro/tuorli; secondo la mattina con aromi, canditi). Lievitazione 12-14h totali a 26-28°C. Cottura 170°C, ~50min per pezzatura da 1kg.",
        "errori_comuni": "Madre debole → poca spinta, alveolo fitto. Impasto surriscaldato in planetaria (>26°C) → il burro fonde, la maglia si rompe. Non capovolgere → avvallamento. Cottura troppo alta → crosta scura e cuore crudo.",
    },
    "pane": {
        "nome": "Pane (pasta di pane a lievitazione naturale)",
        "categoria": "lievitato",
        "fenomeno": "Fermentazione (lieviti e batteri lattici producono CO2 e acidi) + gelatinizzazione dell'amido e reazione di Maillard in crosta.",
        "principio": "Il glutine idratato forma una maglia elastica che trattiene la CO2. L'acidita' del lievito madre rallenta la retrogradazione e da' aroma. La crosta si forma per Maillard e caramellizzazione dove la superficie supera i 140°C.",
        "numero_bersaglio": "96-98°C al cuore; forno di partenza 240-250°C",
        "punto_critico": "Sotto 94°C al cuore la mollica resta gommosa (gelatinizzazione incompleta). Poca idratazione → mollica fitta. Sovralievitazione → la maglia cede e il pane si affloscia.",
        "segnale_reale": "Suono cavo battendo il fondo. Sonda al cuore 96-98°C. Colore crosta ambrato scuro (Maillard completo). Vapore nei primi 10min per la spinta e la crosta lucida.",
        "tecnica": "Autolisi, impasto, pieghe, lievitazione (bulk 3-4h + appretto). Cottura con vapore iniziale a 240°C poi calando a 210°C.",
        "errori_comuni": "Impasto poco incordato → non tiene i gas. Niente vapore → crosta spessa e poca spinta. Forno troppo basso → pane pallido e pesante. Taglio (grigne) assente → spacca a caso.",
    },
    "ragu": {
        "nome": "Ragu' (preparazione madre)",
        "categoria": "base/sugo",
        "fenomeno": "Reazione di Maillard sulla carne (rosolatura) + collagene che si scioglie in gelatina nella cottura lunga a bassa temperatura.",
        "principio": "La rosolatura iniziale (>140°C, carne asciutta) crea i composti bruni del sapore. Poi la cottura lenta (80-90°C) converte il collagene duro in gelatina morbida: la carne diventa tenera e il sugo corposo.",
        "numero_bersaglio": "Sobbollire a 85-90°C per 3+ ore (mai bollore violento)",
        "punto_critico": "Bollore forte (>95°C) indurisce le fibre muscolari prima che il collagene si sciolga → carne stopposa. Rosolatura in pentola affollata → la carne bolle invece di rosolare (niente Maillard).",
        "segnale_reale": "Superficie che 'sbuffa' piano, non ribolle. La carne si sfalda alla forchetta. Il grasso affiora e il sugo si vela.",
        "tecnica": "Rosolare la carne a lotti (non affollare), sfumare, soffritto, pomodoro, cottura lenta scoperta 3-4h. Sale a fine per non estrarre acqua troppo presto.",
        "errori_comuni": "Pentola affollata → niente rosolatura. Fuoco alto → carne dura. Poco tempo → collagene non sciolto. Troppo pomodoro → acidita' che copre.",
    },
    "besciamella": {
        "nome": "Besciamella (salsa madre)",
        "categoria": "base/salsa",
        "fenomeno": "Gelatinizzazione dell'amido della farina che addensa il latte, veicolata da un roux (grasso+farina).",
        "principio": "L'amido della farina, disperso nel grasso (roux), gonfia e gelatinizza tra 60-85°C legando il liquido. Il grasso evita i grumi separando i granuli d'amido prima che incontrino il latte.",
        "numero_bersaglio": "Addensa a 82-85°C (poco sotto il bollore)",
        "punto_critico": "Latte freddo su roux caldo (o viceversa senza frusta) → grumi. Cottura insufficiente del roux → sapore di farina cruda. Bollore prolungato → si stacca/impazzisce.",
        "segnale_reale": "Vela il dorso del cucchiaio. Nessun sapore di farina cruda (roux cotto 2-3min). Superficie lucida, non granulosa.",
        "tecnica": "Roux (burro+farina pari peso, cotto 2-3min), latte caldo a filo con frusta, cottura finche' vela. Proporzione classica 100g roux : 1L latte per densita' media.",
        "errori_comuni": "Frusta assente → grumi. Roux crudo → sapore di farina. Latte freddo di colpo → grumi. Sale/noce moscata dimenticati → piatta.",
    },
    "frolla": {
        "nome": "Pasta frolla (impasto base)",
        "categoria": "base/pasticceria",
        "fenomeno": "Impermeabilizzazione della farina col grasso (sablage) che LIMITA lo sviluppo del glutine → friabilita'.",
        "principio": "Il grasso che avvolge la farina impedisce all'acqua di idratare le proteine: poco glutine = struttura friabile, non elastica. Al contrario del pane, qui il glutine e' il nemico.",
        "numero_bersaglio": "Cottura 160-170°C; burro a 14-16°C in lavorazione",
        "punto_critico": "Impasto lavorato troppo o burro troppo caldo → glutine sviluppato → frolla dura e che si ritira. Troppo freddo → non si amalgama.",
        "segnale_reale": "Impasto che si sbriciola leggermente ma sta insieme. Non elastico. Riposo in frigo 30min prima di stendere (rilassa e solidifica il burro).",
        "tecnica": "Sablage (sabbiare burro freddo+farina) poi zucchero, uova, veloce. Riposo freddo. Cottura 160-170°C. Metodo classico 1:2:3 (zucchero:grasso:farina).",
        "errori_comuni": "Impastare troppo → dura. Burro caldo → si spatascia. Niente riposo → si ritira in cottura. Forno alto → brucia i bordi, cuore crudo.",
    },
    "maionese": {
        "nome": "Maionese (emulsione madre)",
        "categoria": "base/salsa",
        "fenomeno": "Emulsione stabile olio-in-acqua: la lecitina del tuorlo tiene sospese microgocce di olio nell'acqua.",
        "principio": "La lecitina (tensioattivo del tuorlo) ha una parte che ama il grasso e una che ama l'acqua: avvolge le gocce d'olio e impedisce che si riuniscano. L'olio va aggiunto lentamente per creare tante microgocce.",
        "numero_bersaglio": "Rapporto ~1 tuorlo : 200ml olio; tutto a temperatura ambiente",
        "punto_critico": "Olio troppo veloce all'inizio → l'emulsione non si forma (impazzisce). Ingredienti freddi → emulsione instabile. Troppo olio per tuorlo → si rompe.",
        "segnale_reale": "Diventa densa e chiara man mano che monta. Se impazzisce: ricominci con un tuorlo nuovo e aggiungi la salsa rotta a filo.",
        "tecnica": "Tuorlo + senape + poco aceto, olio a filo montando costante. Temperatura ambiente. Frusta o minipimer.",
        "errori_comuni": "Olio di colpo → impazzisce. Ingredienti freddi → instabile. Niente acido → piatta e instabile. Frusta discontinua → non monta.",
    },
    "pasta-fresca": {
        "nome": "Pasta fresca all'uovo (impasto base)",
        "categoria": "base",
        "fenomeno": "Sviluppo del glutine (elasticita') idratato dalle uova, senza lievitazione.",
        "principio": "Le proteine della farina (di grano tenero o semola) idratate dall'uovo e lavorate formano una maglia glutinica elastica ed estensibile, che regge la trafilatura/sfoglia e la cottura.",
        "numero_bersaglio": "~1 uovo (55g) per 100g farina; riposo 30min",
        "punto_critico": "Poca idratazione → sfoglia che si spacca. Impasto poco lavorato → glutine non sviluppato, pasta molle. Niente riposo → si ritira e strappa alla sfoglia.",
        "segnale_reale": "Impasto liscio, sodo, elastico che riprende forma se premuto. Sfoglia che non si strappa e resta velata.",
        "tecnica": "Fontana, uova, impasto 10min, riposo coperto 30min, sfoglia sottile. Semola per pasta piu' tenace, 00 per sfoglia delicata.",
        "errori_comuni": "Impasto poco lavorato → molle. Niente riposo → si ritira. Sfoglia spessa → gommosa. Farina sbagliata → non tiene.",
    },
    "caramello": {
        "nome": "Caramello (cottura dello zucchero)",
        "categoria": "base/pasticceria",
        "fenomeno": "Caramellizzazione: lo zucchero fuso oltre i 160°C si decompone in centinaia di composti aromatici e bruni.",
        "principio": "Il saccarosio fonde a 160°C e sopra i 170°C inizia a caramellizzare (imbrunire e sviluppare aroma). E' una reazione diversa dal Maillard (qui non servono proteine): solo zucchero e calore.",
        "numero_bersaglio": "Caramello chiaro 160-170°C, ambrato 170-180°C, scuro 180-190°C",
        "punto_critico": "Sopra 190°C brucia (amaro). Cristallizzazione se si mescola o ci sono impurita' (aggiungere glucosio o poca acqua/limone la previene).",
        "segnale_reale": "Il colore E' il termometro: paglierino→ambra→nocciola→bruno. Fermare la cottura (togliere dal fuoco) prima del punto voluto, continua da solo.",
        "tecnica": "A secco (solo zucchero) o a umido (con acqua). Non mescolare, ruotare la pentola. Bloccare con panna calda o burro.",
        "errori_comuni": "Mescolare → cristallizza. Fuoco troppo alto → brucia ai bordi. Panna fredda → schizza e rapprende. Aspettare troppo → amaro.",
    },
    "sciroppo": {
        "nome": "Sciroppo di zucchero (base bar)",
        "categoria": "base/bar",
        "fenomeno": "Dissoluzione dello zucchero in acqua fino a soluzione satura stabile.",
        "principio": "L'acqua scioglie il saccarosio; a caldo si scioglie di piu' (soluzione piu' concentrata). Il rapporto zucchero:acqua determina densita' e dolcezza, e influenza equilibrio e texture del cocktail.",
        "numero_bersaglio": "Simple 1:1 (peso); rich syrup 2:1 (piu' denso, meno diluizione nel drink)",
        "punto_critico": "Troppo caldo/lungo → inizia a caramellare (cambia sapore). Rapporto sbagliato → drink squilibrato. Senza conservazione → fermenta in pochi giorni.",
        "segnale_reale": "Limpido, senza cristalli residui. Il rich (2:1) e' visibilmente piu' denso e vela il cucchiaio.",
        "tecnica": "Scaldare acqua (non bollire), sciogliere lo zucchero, raffreddare. Un goccio di vodka o acido citrico allunga la conservazione. Conservare in frigo.",
        "errori_comuni": "Bollire → caramella. Rapporto a caso → dolcezza incoerente tra drink. Non filtrare → torbido. Niente conservante → ammuffisce.",
    },
    "brodo": {"nome":"Brodo / Fondo (base madre)","categoria":"base","fenomeno":"Estrazione di gelatina (dal collagene delle ossa), proteine e aromi in acqua a bassa temperatura prolungata.","principio":"Il collagene si scioglie lentamente in gelatina che da' corpo. La cottura DOLCE (mai bollore) evita che grassi e proteine intorbidino. La tostatura delle ossa (fondo bruno) aggiunge Maillard.","numero_bersaglio":"Sobbollire 85-90°C per 4-8h (ossa) o 1h (verdure)","punto_critico":"Bollore → brodo torbido e grasso. Salare presto → troppo salato riducendo.","segnale_reale":"Superficie che tremola appena. Limpido. Da freddo GELIFICA (collagene estratto). Schiumare.","tecnica":"Partire da acqua fredda, portare piano, schiumare, sobbollire scoperto. Fondo bruno: tostare prima. Filtrare.","errori_comuni":"Bollore → torbido. Acqua calda in partenza → meno estrazione. Non schiumare → sporco. Sale presto → salato."},
    "risotto": {"nome":"Risotto (mantecatura)","categoria":"base","fenomeno":"Rilascio graduale dell'amido del riso che, legato a grasso freddo a fine cottura, crea la cremosita'.","principio":"I chicchi (Carnaroli/Arborio) rilasciano amido con brodo caldo aggiunto poco a poco. A fine, burro/formaggio FREDDI fuori dal fuoco emulsionano l'amido creando l'onda senza separare i grassi.","numero_bersaglio":"Cottura ~16-18min; mantecatura fuori dal fuoco","punto_critico":"Brodo freddo → slega. Mantecare sul fuoco → unto. Riso scotto → colla.","segnale_reale":"All'onda: si muove come un'onda. Chicco al dente. Lucido dopo mantecatura.","tecnica":"Tostatura, sfuma, brodo caldo poco a poco, a fine fuori dal fuoco burro+parmigiano freddi, riposo 1min.","errori_comuni":"Brodo freddo → slega. Mantecare sul fuoco → unto. Riso sbagliato → non tiene."},
    "crema-pasticcera": {"nome":"Crema pasticcera","categoria":"base/pasticceria","fenomeno":"Addensamento doppio: coagulazione dei tuorli + gelatinizzazione dell'amido nel latte caldo.","principio":"I tuorli coagulano a 65-70°C ma l'amido alza la soglia e stabilizza, permettendo il bollore senza stracciare le uova. L'amido gelatinizza e da' corpo.","numero_bersaglio":"Portare a 82-85°C (con amido si sfiora il bollore)","punto_critico":"Senza amido, sopra 70°C le uova stracciano. Poca cottura → amido crudo. Raffreddamento lento → rischio batterico.","segnale_reale":"Vela il cucchiaio poi al bollore si addensa di colpo. Lucida, senza grumi. Pellicola a contatto.","tecnica":"Tuorli+zucchero+amido, latte caldo a filo, sul fuoco fino a addensare. Pellicola a contatto, abbattere.","errori_comuni":"Latte caldo di colpo → straccia. Poca cottura → amido crudo. Niente pellicola → crosta."},
    "meringa": {"nome":"Meringa","categoria":"base/pasticceria","fenomeno":"Denaturazione delle proteine dell'albume che montate intrappolano aria, stabilizzate dallo zucchero.","principio":"Montando, le proteine si aprono e formano pareti attorno alle bolle. Lo zucchero stabilizza legando acqua. Il grasso (traccia di tuorlo) impedisce il montaggio.","numero_bersaglio":"~2:1 zucchero:albume (francese); italiana con sciroppo a 121°C","punto_critico":"Tracce di grasso → non monta. Zucchero presto → non incorpora aria. Sovramontata → granulosa e collassa.","segnale_reale":"Becco d'uccello: punta ferma e lucida. Non scivola capovolgendo la ciotola. Liscia.","tecnica":"Francese: zucchero a pioggia dopo la schiuma. Italiana: sciroppo 121°C a filo. Ciotola sgrassata.","errori_comuni":"Grasso → non monta. Zucchero subito → piatta. Sovramontata → collassa. Umidita' → smonta."},
    "sfoglia": {"nome":"Pasta sfoglia (laminato)","categoria":"base/pasticceria","fenomeno":"Laminazione: strati alternati di impasto e burro che in cottura sviluppano vapore, gonfiando in centinaia di foglie.","principio":"Le pieghe creano strati sottili di burro tra impasto. In forno l'acqua evapora e il vapore intrappolato spinge gli strati in alto. Il burro deve restare solido e separato.","numero_bersaglio":"Burro e impasto stessa consistenza; cottura 190-200°C; 3-6 pieghe","punto_critico":"Burro caldo → si assorbe (niente strati). Troppo freddo → si rompe. Forno basso → il burro cola.","segnale_reale":"Strati visibili sul taglio. Gonfia dritta. Il burro non trasuda.","tecnica":"Pastello + panetto di burro, pieghe con riposi freddi. Cottura alta e stabile.","errori_comuni":"Burro caldo → niente strati. Poco riposo → si ritira. Forno basso → cola."},
    "ganache": {"nome":"Ganache","categoria":"base/pasticceria","fenomeno":"Emulsione di grassi (burro di cacao + panna) che unisce cioccolato e liquido in una crema lucida.","principio":"Cioccolato fuso e panna calda formano un'emulsione: cacao e grassi si legano all'acqua della panna. Il rapporto cioccolato:panna decide la durezza (1:1 morbida, 2:1 soda).","numero_bersaglio":"Panna a ~85°C sul cioccolato; emulsionare dal centro","punto_critico":"Panna troppo calda → il grasso separa. Mescolare male → si rompe. Cioccolato scarso → non emulsiona.","segnale_reale":"Lucida, liscia, elastica. Se rotta: poco latte caldo e frullare per riemulsionare.","tecnica":"Panna calda sul cioccolato tritato, attendere, emulsionare dal centro. Aromi/burro a fine.","errori_comuni":"Panna bollente → separa. Mescolare a caso → rompe. Cioccolato scarso → opaca."},
    "cottura-carne": {"nome":"Cottura della carne (bistecca/arrosto)","categoria":"tecnica","fenomeno":"Maillard in crosta (>140°C) + denaturazione progressiva delle proteine muscolari col salire della temperatura al cuore.","principio":"La crosta viene dal Maillard sulla superficie asciutta e calda. Al cuore le proteine si contraggono col calore: piu' sale la temperatura, piu' perde succhi. Il grado di cottura E' la temperatura al cuore.","numero_bersaglio":"Al cuore: 50-52°C sangue, 55-57°C media, 63-68°C ben cotta","punto_critico":"Superficie umida → niente Maillard. Cuore oltre 70°C → asciutta. Non far riposare → succhi persi al taglio.","segnale_reale":"Sonda al cuore per il grado. Crosta bruna asciutta. Riposo 5-10min prima di tagliare.","tecnica":"Carne a temp. ambiente, superficie asciutta, padella rovente per la crosta, poi calore dolce per il cuore. Riposo.","errori_comuni":"Carne fredda → cuore crudo. Superficie bagnata → grigia. Girare sempre → niente crosta. Niente riposo → asciutta."},
    "fermentazione": {"nome":"Fermentazione (lattica, sott'aceti, basi bar)","categoria":"tecnica","fenomeno":"Batteri lattici convertono zuccheri in acido lattico, abbassando il pH e conservando mentre sviluppano aromi.","principio":"In ambiente anaerobico e salato (~2-3%), i lattobacilli prevalgono su muffe e patogeni: l'acido porta il pH sotto 4.6, soglia che blocca i batteri dannosi. Sale e temperatura governano la velocita'.","numero_bersaglio":"Salamoia 2-3% sul peso; pH finale sotto 4.6; 18-22°C","punto_critico":"Poco sale o ossigeno → muffe. Troppo caldo → incontrollata. pH sopra 4.6 → non sicuro. Verdure a galla → ammuffiscono.","segnale_reale":"Bollicine, torbidita', profumo acidulo (non putrido). pH sotto 4.6. Tutto sotto la salamoia.","tecnica":"Salamoia pesata, tutto sommerso e anaerobico, temperatura controllata, assaggio nel tempo. Poi frigo.","errori_comuni":"Sale a occhio → fallisce. Verdure a galla → muffa. Troppo caldo → sgradevole. Fretta → pH non sicuro."},
}

@bp.route("/v1/scheda-scienza/<slug>", methods=["GET"])
def scheda_scienza(slug):
    """Restituisce la Scheda Scienza di una preparazione (8 blocchi fissi). Infrastruttura, Rule #189."""
    from flask import jsonify
    s = SCHEDE_SCIENZA.get(slug.lower().strip())
    if not s:
        return jsonify({"errore": "scheda non trovata", "disponibili": list(SCHEDE_SCIENZA.keys())}), 404
    return jsonify(s)

@bp.route("/v1/schede-scienza", methods=["GET"])
def schede_scienza_lista():
    """Lista delle Schede Scienza disponibili."""
    from flask import jsonify
    return jsonify({"schede": [{"slug": k, "nome": v["nome"], "categoria": v["categoria"]} for k,v in SCHEDE_SCIENZA.items()]})
