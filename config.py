# ============================================================
# config.py — costanti condivise (ambiente, percorsi).
# Estratto da app.py senza modifiche di comportamento.
# HERE/GRAFO restano identici: config.py sta nella stessa cartella di app.py.
# ============================================================
import os
import pathlib

HERE = pathlib.Path(__file__).parent
GRAFO = HERE / "grafo"

DATABASE_URL = os.environ.get("DATABASE_URL")
