# Calibro — server. Come avviarlo.

## In locale (sul tuo PC, per provarlo)

Dentro la cartella `calibro-server`, da PowerShell:

```
pip install flask
python app.py
```

Poi apri il browser su **http://localhost:5001** — c'è la chat.
Scrivi una domanda ("perché la mia confettura non prende?") e vedi:
- i nodi che il grafo ha trovato,
- il contesto che ha costruito navigando le connessioni.

La risposta finale di Mistral NON parte in locale (la chiave sta su Railway).
In locale vedi il CONTESTO che il grafo costruisce — il cuore del lavoro.

## Su Railway (per il prodotto vero, dopo Cruscotto)

Stessa identica procedura di Cruscotto:
1. Carica la cartella su un repo / Railway.
2. Aggiungi la variabile `MISTRAL_API_KEY` (la stessa di Cruscotto).
3. Railway legge il `Procfile` e avvia `gunicorn app:app`.
4. Da lì Mistral risponde davvero, perché la chiave c'è.

Per ora il grafo è in SQLite (costruito dai .sql ad ogni avvio).
Quando vorrai, si sposta su Postgres — la funzione `carica_grafo()` è il
solo punto da cambiare. Tutto il resto resta uguale.

## Cosa c'è nella cartella
- `app.py` — il server: riceve domanda, naviga il grafo, costruisce il prompt, chiama Mistral.
- `templates/index.html` — la chat.
- `grafo/` — lo schema e i seed (il grafo vero).
- `requirements.txt`, `Procfile` — per Railway.
