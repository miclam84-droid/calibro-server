# -*- coding: utf-8 -*-
# FRONTEND R5 — ENDPOINT FOTO per il frontend ricomposto (matter3).
#
# GET /v1/foto-ingrediente-nuovo/<nome>: una foto EDITORIALE per un ingrediente,
# recuperata col sistema esistente (immagini.cerca_immagine), MAI reinventato.
#
# NOTA (strangler-fig): l'endpoint del vecchio FE sta in routes/pwa.py a
# /v1/foto-ingrediente/<nome> e torna un contratto diverso (autore/fonte_nome,
# niente campo `credito`). Non si tocca pwa.py. Il FE ricomposto ha il suo
# endpoint isolato (come /nuovo, /scopri-nuovo, /causa-nuovo), qui a
# /v1/foto-ingrediente-nuovo, che torna il contratto {url, credito, fonte}
# che le viste nuove consumano, col credito gia' composto da credito_immagine.
#
# ONESTA':
#  - la foto esce SOLO se trovata davvero. Niente placeholder, niente foto finta.
#  - quando c'e' una foto, il credito/attribuzione viaggia SEMPRE con l'URL.
#  - senza chiavi API (o se cerca_immagine solleva/non trova) -> {"url": null},
#    lo diciamo onestamente e il FE non mostra nessun box foto.
#
# CACHE in-memory per nome (TTL ~1h): non martellare le API stock a ogni vista.
# Isolato: non tocca nessuna pagina/endpoint esistente, registrato con una riga sola.
import time

from flask import Blueprint, jsonify, render_template, make_response

bp_foto_nuovo = Blueprint("foto_nuovo", __name__)


@bp_foto_nuovo.route("/foto-nuovo", methods=["GET"])
def foto_nuovo_pagina():
    """ENTRATA FOTO — "Fotografa cosa hai sul banco" (strangler-fig, isolata).

    Pagina nuova nel sistema di design congelato (matter3.css). Fa fetch
    client-side di POST /v1/menu/riconosci-ingredienti (routes/api.py): carichi
    fino a 6 foto, il riconoscimento è gratuito, gli ingredienti riconosciuti
    diventano link a /lab/<ingrediente>. Nessuna logica dati qui.
    NON tocca nessuna pagina/endpoint del FE esistente. Stesso pattern delle
    altre viste *-nuovo: render_template + header anti-cache."""
    resp = make_response(render_template("foto-nuovo.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

# cache a livello di modulo: nome(lower) -> {"ts": epoch, "payload": {...}}
_CACHE = {}
_TTL = 3600  # ~1 ora


def _da_cache(chiave):
    voce = _CACHE.get(chiave)
    if not voce:
        return None
    if (time.time() - voce["ts"]) > _TTL:
        # scaduta: la togliamo e rifacciamo la ricerca
        _CACHE.pop(chiave, None)
        return None
    return voce["payload"]


def _in_cache(chiave, payload):
    _CACHE[chiave] = {"ts": time.time(), "payload": payload}
    return payload


@bp_foto_nuovo.route("/v1/foto-ingrediente-nuovo/<path:nome>", methods=["GET"])
def foto_ingrediente(nome):
    """Una foto editoriale per <nome>, via immagini.cerca_immagine (sistema esistente).
    Trovata -> {url, credito, fonte}. Non trovata / nessuna chiave / errore -> {url: null}."""
    chiave = (nome or "").strip().lower()
    if not chiave:
        return jsonify({"url": None})

    cached = _da_cache(chiave)
    if cached is not None:
        return jsonify(cached)

    # default onesto: nessuna foto
    payload = {"url": None}
    try:
        import immagini
        # FOTO DI INGREDIENTE -> ricerca SEVERA (cerca_immagine_ingrediente), la STESSA
        # dei nodi del grafo: solo stock pertinente, niente Wikimedia, niente piatti.
        # Prima l'hero usava cerca_immagine (editoriale, lasca) e pescava i piatti
        # (es. 'pomodoro' -> pasta al pomodoro). Ora hero e nodi sono coerenti.
        img = immagini.cerca_immagine_ingrediente(nome)
        if img and img.get("url"):
            payload = {
                "url": img["url"],
                "credito": immagini.credito_immagine(
                    img.get("autore", ""), img.get("fonte_nome", "") or "Pexels"
                ),
                "fonte": img.get("fonte_nome", ""),
            }
    except Exception:
        # qualunque eccezione da immagini.py -> restiamo sul default onesto {url: null},
        # senza rompere la vista.
        payload = {"url": None}

    return jsonify(_in_cache(chiave, payload))
