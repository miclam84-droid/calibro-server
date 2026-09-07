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
    risultati = []
    try:
        from db import carica_grafo
        db = carica_grafo()
        # RICETTE (stesso pattern del ricettario che funziona)
        def _c(r, key, idx):
            return r[key] if hasattr(r, "keys") else r[idx]
        rows = db.execute("SELECT id, nome, disciplina FROM ricette WHERE nome ILIKE ? LIMIT 8", (pat,)).fetchall()
        for r in rows:
            risultati.append({"tipo": "ricetta", "id": _c(r,"id",0), "nome": _c(r,"nome",1), "disciplina": _c(r,"disciplina",2)})
        rows = db.execute("SELECT id, name FROM nodes WHERE type='Fenomeno' AND name ILIKE ? LIMIT 5", (pat,)).fetchall()
        for r in rows:
            risultati.append({"tipo": "fenomeno", "id": _c(r,"id",0), "nome": _c(r,"name",1)})
        rows = db.execute("SELECT id, name FROM nodes WHERE type='Prodotto' AND name ILIKE ? LIMIT 5", (pat,)).fetchall()
        for r in rows:
            risultati.append({"tipo": "ingrediente", "id": _c(r,"id",0), "nome": _c(r,"name",1)})
        rows = db.execute("SELECT id, name FROM nodes WHERE type='Tecnica' AND name ILIKE ? LIMIT 3", (pat,)).fetchall()
        for r in rows:
            risultati.append({"tipo": "tecnica", "id": _c(r,"id",0), "nome": _c(r,"name",1)})
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
                            AND e2.relation='contiene_composto' AND n3.type='Prodotto'
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
