"""
AI Gateway — Matter Lab
=======================
Layer di astrazione obbligatorio tra l'applicazione e i provider AI.
L'app non chiama mai i provider direttamente — passa sempre da qui.

Principio: ogni provider ha un adapter dedicato.
Aggiungere Gemini/Grok/Llama = 1 adapter, zero modifiche applicative.

Route disponibili:
  route_chat()        → Claude Sonnet 4.6  (ragionamento, chat F&B con tool-calling)
  route_fast()        → Haiku 4.5 → Mistral (quiz, traduzioni, task rapidi)
  route_embeddings()  → OpenAI text-embedding-3-small (ricerca semantica)
  route_stt()         → OpenAI Whisper gpt-4o-mini-transcribe (voce al banco)
  route_vision()      → OpenAI Vision gpt-4o-mini (foto schede tecniche)
  route_moderation()  → OpenAI Moderation (filtra contenuti)

Logging centralizzato: ogni chiamata logga provider, modello, latenza, costo stimato.
"""

import json
import os
import time
import urllib.request
import urllib.error
import re

# ── Costanti ────────────────────────────────────────────────────────────────
_ANTHROPIC_URL  = "https://api.anthropic.com/v1/messages"
_MISTRAL_URL    = "https://api.mistral.ai/v1/chat/completions"
_OPENAI_URL     = "https://api.openai.com/v1"

_MODEL_SONNET   = "claude-sonnet-4-5"
_MODEL_HAIKU    = "claude-haiku-4-5"
_MODEL_MISTRAL  = "mistral-small-latest"
_MODEL_EMBED    = "text-embedding-3-small"
_MODEL_WHISPER  = "whisper-1"
_MODEL_VISION   = "gpt-4o-mini"
_MODEL_GPT_CHAT = "gpt-4o-mini"   # chat economica per domande semplici (routing)
_MODEL_MODERAT  = "omni-moderation-latest"

# Costi stimati per MTok (USD) — per logging
_COSTS = {
    _MODEL_SONNET:  {"in": 3.00,  "out": 15.00},
    _MODEL_HAIKU:   {"in": 1.00,  "out": 5.00},
    _MODEL_MISTRAL: {"in": 0.10,  "out": 0.30},
    _MODEL_EMBED:   {"in": 0.02,  "out": 0.00},
    _MODEL_VISION:  {"in": 0.15,  "out": 0.60},
}


# ── Log centralizzato ────────────────────────────────────────────────────────
def _log(provider, model, route, latency_ms, tokens_in=0, tokens_out=0, error=None):
    cost = _COSTS.get(model, {"in":0,"out":0})
    cost_usd = (tokens_in * cost["in"] + tokens_out * cost["out"]) / 1_000_000
    status = "ERROR" if error else "OK"
    print(
        f"[GW] {status} provider={provider} model={model} route={route} "
        f"lat={latency_ms:.0f}ms tok_in={tokens_in} tok_out={tokens_out} "
        f"cost=${cost_usd:.6f}" + (f" err={error}" if error else ""),
        flush=True
    )


# ── Sanitize output ──────────────────────────────────────────────────────────
def _sanitize(text):
    """Rimuove caratteri di controllo non validi in JSON."""
    if not text:
        return text
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text


# ── Adapter Anthropic ────────────────────────────────────────────────────────
def _anthropic_call(model, messages, max_tokens=800, temperature=0, tools=None):
    """Chiamata grezza all'API Anthropic. Ritorna (data_dict, latency_ms)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY non configurata")

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages
    }
    if tools:
        payload["tools"] = tools

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _ANTHROPIC_URL,
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read().decode("utf-8"))
    latency = (time.time() - t0) * 1000

    usage = data.get("usage", {})
    _log(
        "anthropic", model, "call",
        latency,
        tokens_in=usage.get("input_tokens", 0),
        tokens_out=usage.get("output_tokens", 0)
    )
    return data, latency


# ── Adapter Mistral ──────────────────────────────────────────────────────────
def _mistral_call(prompt, max_tokens=None):
    """Chiamata grezza all'API Mistral. Ritorna (testo, latency_ms)."""
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        raise ValueError("MISTRAL_API_KEY non configurata")

    payload = {
        "model": _MODEL_MISTRAL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _MISTRAL_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    latency = (time.time() - t0) * 1000

    usage = data.get("usage", {})
    _log(
        "mistral", _MODEL_MISTRAL, "call",
        latency,
        tokens_in=usage.get("prompt_tokens", 0),
        tokens_out=usage.get("completion_tokens", 0)
    )
    return data["choices"][0]["message"]["content"], latency


# ── Adapter OpenAI ───────────────────────────────────────────────────────────
def tts_openai(testo, voce="onyx", lang="it"):
    """Text-to-speech via OpenAI. Ritorna bytes audio MP3 (o None se errore).
    Costo: ~$15/1M caratteri (tts-1). Un output foto ~600 char = ~$0.009."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY non configurata")
    # limito la lunghezza per sicurezza sui costi (max ~1200 char = ~$0.018)
    testo = (testo or "").strip()[:1200]
    if not testo:
        return None
    payload = {"model": "tts-1", "voice": voce, "input": testo}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_OPENAI_URL}/audio/speech",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()  # audio MP3 binario


def _openai_call(endpoint, payload, timeout=30):
    """Chiamata grezza all'API OpenAI. Ritorna (data_dict, latency_ms)."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY non configurata")

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_OPENAI_URL}/{endpoint}",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    latency = (time.time() - t0) * 1000
    return data, latency


# ── ROUTE PUBBLICHE ───────────────────────────────────────────────────────────

def _gpt_chat(prompt, history=None, max_tokens=1500):
    """Chat via GPT-4o mini (economico). Per domande semplici senza tool.
    Ritorna testo o None."""
    messages = []
    if history:
        for h in history[-6:]:
            # normalizzo il formato Anthropic → OpenAI (content può essere lista)
            c = h.get("content", "")
            if isinstance(c, list):
                c = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
            messages.append({"role": h.get("role", "user"), "content": c})
    messages.append({"role": "user", "content": prompt})
    try:
        data, _ = _openai_call("chat/completions", {
            "model": _MODEL_GPT_CHAT,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0
        })
        return (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip() or None
    except Exception as e:
        print(f"[GW] GPT chat fallito: {e}", flush=True)
        return None


def _serve_tool(prompt):
    """Decide se una domanda ha bisogno del tool-calling (grafo/calcolo) o è
    informativa semplice. Semplice → modello economico. Complessa → Sonnet+tool.
    Segnale: presenza di unità di misura, numeri, o verbi operativi di calcolo."""
    p = (prompt or "").lower()
    # unità di misura e simboli che indicano una domanda operativa/quantitativa
    segnali = ["°c", "°", "ph", "brix", "abv", "%", "grammi", " g ", "ml", " kg",
               "bar", "tds", "so2", "aw", "titolabil", "densità", "rapporto",
               "quanto", "calcola", "dose", "dosaggio", "resa", "percentuale",
               "temperatura", "quantità", "proporzion"]
    return any(s in p for s in segnali)


def route_chat(prompt, tools=None, history=None):
    """
    Route principale per la chat F&B.
    Provider: Claude Sonnet 4.6 con tool-calling → fallback Mistral.
    Gestisce automaticamente il ciclo tool_use → tool_result → risposta finale.

    Args:
        prompt: stringa del prompt completo (system + contesto + domanda)
        tools: lista tool definitions (per il motore deterministico)
        history: lista di dict {"role","content"} per mini-history

    Returns:
        str: testo della risposta, sanitizzato
    """
    import motore as Motore

    messages = []
    if history:
        messages.extend(history[-6:])  # max 3 scambi precedenti
    messages.append({"role": "user", "content": prompt})

    # ── ROUTING PER DIFFICOLTÀ ──────────────────────────────────────────────
    # Domanda semplice/informativa (nessuna unità di misura, nessun calcolo):
    # prova prima GPT-4o mini (30-50x più economico di Sonnet). Se fallisce o
    # torna vuoto, cade su Sonnet. Le domande operative saltano questo e vanno
    # direttamente a Sonnet con tool-calling (dove la qualità conta).
    if not _serve_tool(prompt):
        out = _gpt_chat(prompt, history=history, max_tokens=1500)
        if out:
            return _sanitize(out)
        print("[GW] GPT vuoto su domanda semplice → provo Sonnet", flush=True)

    # Tentativo 1: Sonnet con tool-calling (domande operative o fallback)
    try:
        data, _ = _anthropic_call(
            _MODEL_SONNET, messages,
            max_tokens=1500, temperature=0,
            tools=tools
        )

        # gestione tool_use
        testo = []
        tool_results = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                testo.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_id = block.get("id", "")
                tool_input = block.get("input", {})
                risultato = Motore.esegui(
                    tool_input.get("calcolo", ""),
                    tool_input.get("parametri", {})
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": json.dumps(risultato, ensure_ascii=False)
                })

        # secondo giro se c'era un tool call
        if tool_results:
            messages2 = messages + [
                {"role": "assistant", "content": data.get("content", [])},
                {"role": "user", "content": tool_results}
            ]
            data2, _ = _anthropic_call(
                _MODEL_SONNET, messages2,
                max_tokens=1500, temperature=0
            )
            out = "".join(
                b.get("text", "") for b in data2.get("content", [])
                if b.get("type") == "text"
            )
        else:
            out = "".join(testo)

        if out:
            return _sanitize(out)

    except Exception as e:
        import traceback
        print(f"[GW] Sonnet fallito: {e}", flush=True)
        print(f"[GW] Sonnet traceback: {traceback.format_exc()[-500:]}", flush=True)

    # Fallback 1: GPT-4o mini (economico, quasi sempre disponibile)
    try:
        out = _gpt_chat(prompt, history=history)
        if out:
            print("[GW] fallback GPT ok", flush=True)
            return _sanitize(out)
    except Exception as e:
        print(f"[GW] GPT fallback fallito: {e}", flush=True)

    # Fallback 2: Mistral
    try:
        out, _ = _mistral_call(prompt)
        if out:
            return _sanitize(out)
        print(f"[GW] Mistral returned empty", flush=True)
    except Exception as e:
        import traceback
        print(f"[GW] Mistral fallito: {e}", flush=True)
        print(f"[GW] Mistral traceback: {traceback.format_exc()[-300:]}", flush=True)
    return None


def route_fast(prompt, max_tokens=600, temperature=0):
    """
    Route per task rapidi e a basso costo.
    Provider: Haiku 4.5 con retry → fallback Mistral.
    Usa per: quiz, traduzioni, classificazioni, entity extraction.
    temperature: 0 per task deterministici, >0 per task creativi (naming).

    Returns:
        str: testo della risposta
    """
    # Tentativo Haiku con retry
    for attempt in range(2):
        try:
            messages = [{"role": "user", "content": prompt}]
            data, _ = _anthropic_call(
                _MODEL_HAIKU, messages,
                max_tokens=max_tokens, temperature=temperature
            )
            out = "".join(
                b.get("text", "") for b in data.get("content", [])
                if b.get("type") == "text"
            )
            if out:
                return _sanitize(out)
        except Exception as e:
            print(f"[GW] Haiku attempt {attempt+1} fallito: {e}", flush=True)
            if attempt == 0:
                time.sleep(2)

    # Fallback Mistral
    try:
        out, _ = _mistral_call(prompt, max_tokens=max_tokens)
        return _sanitize(out) if out else None
    except Exception as e:
        print(f"[GW] route_fast Mistral fallito: {e}", flush=True)
        return None


def route_embeddings(texts):
    """
    Route per embedding semantici.
    Provider: OpenAI text-embedding-3-small.
    Usa per: ricerca semantica flavor network, similarity search.

    Args:
        texts: str o list[str]

    Returns:
        list[list[float]]: vettori embedding, uno per testo
    """
    if isinstance(texts, str):
        texts = [texts]

    t0 = time.time()
    try:
        data, latency = _openai_call("embeddings", {
            "model": _MODEL_EMBED,
            "input": texts,
            "encoding_format": "float"
        })
        _log(
            "openai", _MODEL_EMBED, "embeddings",
            latency,
            tokens_in=data.get("usage", {}).get("total_tokens", 0)
        )
        return [item["embedding"] for item in sorted(
            data["data"], key=lambda x: x["index"]
        )]
    except Exception as e:
        _log("openai", _MODEL_EMBED, "embeddings",
             (time.time()-t0)*1000, error=str(e))
        raise


def route_stt(audio_bytes, filename="audio.webm", language="it"):
    """
    Route per Speech-to-Text.
    Provider: OpenAI Whisper.
    Usa per: voce al banco ("Chiedi con la voce").

    Args:
        audio_bytes: bytes dell'audio
        filename: nome file con estensione (webm, mp4, wav, m4a)
        language: codice lingua ISO 639-1

    Returns:
        str: trascrizione del testo
    """
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY non configurata")

    import io
    boundary = "----MatterLabBoundary"
    body_parts = []
    body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\nwhisper-1\r\n'.encode())
    body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="language"\r\n\r\n{language}\r\n'.encode())
    body_parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: audio/webm\r\n\r\n'.encode()
        + audio_bytes
        + b'\r\n'
    )
    body_parts.append(f'--{boundary}--\r\n'.encode())
    body = b''.join(body_parts)

    t0 = time.time()
    req = urllib.request.Request(
        f"{_OPENAI_URL}/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    latency = (time.time() - t0) * 1000
    _log("openai", _MODEL_WHISPER, "stt", latency)
    return data.get("text", "")


def route_vision(image_bytes, prompt, media_type="image/jpeg"):
    """
    Route per analisi immagini.
    Provider: OpenAI Vision gpt-4o-mini.
    Usa per: analisi foto schede tecniche, OCR etichette.

    Args:
        image_bytes: bytes dell'immagine
        prompt: cosa analizzare
        media_type: "image/jpeg" o "image/png" o "image/webp"

    Returns:
        str: testo della risposta
    """
    import base64
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    t0 = time.time()
    try:
        data, latency = _openai_call("chat/completions", {
            "model": _MODEL_VISION,
            "max_tokens": 800,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{b64}",
                            "detail": "low"
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        }, timeout=30)
        _log(
            "openai", _MODEL_VISION, "vision", latency,
            tokens_in=data.get("usage", {}).get("prompt_tokens", 0),
            tokens_out=data.get("usage", {}).get("completion_tokens", 0)
        )
        return _sanitize(data["choices"][0]["message"]["content"])
    except Exception as e:
        _log("openai", _MODEL_VISION, "vision", (time.time()-t0)*1000, error=str(e))
        raise


def route_moderation(text):
    """
    Route per content moderation.
    Provider: OpenAI Moderation (gratuita).
    Usa per: filtrare contenuti inappropriati nella chat libera.

    Returns:
        dict: {"flagged": bool, "categories": dict}
    """
    t0 = time.time()
    try:
        data, latency = _openai_call("moderations", {
            "model": _MODEL_MODERAT,
            "input": text
        })
        _log("openai", _MODEL_MODERAT, "moderation", latency)
        result = data["results"][0]
        return {
            "flagged": result.get("flagged", False),
            "categories": result.get("categories", {})
        }
    except Exception as e:
        _log("openai", _MODEL_MODERAT, "moderation",
             (time.time()-t0)*1000, error=str(e))
        # in caso di errore non bloccare — lascia passare
        return {"flagged": False, "categories": {}}


# ── Backward compatibility ────────────────────────────────────────────────────
# Questi alias mantengono la compatibilità con il codice esistente in app.py
# che chiama le vecchie funzioni. Si rimuovono gradualmente.

def compat_anthropic_raw(prompt, tools=None):
    """Alias per route_chat — compatibilità con _anthropic_raw()."""
    return route_chat(prompt, tools=tools)


def compat_haiku_raw(prompt, max_tokens=600):
    """Alias per route_fast — compatibilità con _haiku_raw()."""
    return route_fast(prompt, max_tokens=max_tokens)


def compat_mistral_raw(prompt, max_tokens=None):
    """Alias diretto a Mistral — compatibilità con _mistral_raw()."""
    try:
        out, _ = _mistral_call(prompt, max_tokens=max_tokens)
        return _sanitize(out) if out else None
    except Exception:
        return None
