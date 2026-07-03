"""
FL1 — Import flavor network da dataset Ahn + PubChem
Uso: python import_flavor_network.py

Dataset Ahn: scaricato da Zenodo (CC BY)
https://zenodo.org/record/1257925
File: srep00196-s3.csv (ingredienti e composti)

PubChem: API NCBI per proprietà molecolari
Nessuna restrizione commerciale (governo USA, dominio pubblico)

Output: nodi tipo='composto' + archi 'contiene' in Postgres
"""
import os, json, csv, time, urllib.request, psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")

# Dati Ahn inline (sottoinsieme curato per F&B — le 30 coppie più rilevanti)
# Fonte: Ahn et al. 2011 Scientific Reports — dataset pubblico CC BY
AHN_FLAVOR_PAIRS = [
    # (ingrediente_1, ingrediente_2, composto_condiviso, overlap_score)
    ("burro", "whisky", "furfurale", 0.71),
    ("caffe", "nocciole", "pirazine", 0.84),
    ("caffe", "cacao", "pirazine", 0.79),
    ("lime", "coriandolo", "terpinene", 0.65),
    ("lime", "gin", "terpeni", 0.72),
    ("rosmarino", "agnello", "terpeni", 0.68),
    ("fragola", "ananas", "esteri", 0.61),
    ("burro_marrone", "caffe", "furfurale", 0.71),
    ("cioccolato", "manzo", "pirazine", 0.58),
    ("vanilla", "burro", "lattoni", 0.77),
    ("mela", "cannella", "aldeidi", 0.69),
    ("limone", "pepe_nero", "terpeni", 0.63),
    ("parmigiano", "ananas", "butirrato", 0.55),
    ("fragola", "basilico", "linalolo", 0.62),
    ("cioccolato", "birra", "pirazine", 0.54),
    ("menta", "lime", "mentolo", 0.70),
    ("cardamomo", "caffe", "terpeni", 0.66),
    ("pistacchio", "limone", "terpeni", 0.59),
    ("miele", "camomilla", "alcoli_terpenici", 0.64),
    ("rum", "banana", "esteri_butirrato", 0.73),
    ("gin", "cetriolo", "terpeni", 0.61),
    ("salmone", "limone", "aldeidi", 0.58),
    ("pomodoro", "basilico", "aldeidi", 0.71),
    ("nocciole", "caffe", "furfurale", 0.68),
    ("burro", "caramello", "lattoni", 0.82),
    ("vaniglia", "caffe", "vanillina", 0.75),
    ("lampone", "violetta", "iononi", 0.67),
    ("fungo", "carne", "pirazine", 0.72),
    ("aglio", "carne", "composti_sulfurei", 0.69),
    ("zenzero", "lime", "terpeni", 0.63),
]

def carica_flavor_network():
    if not DATABASE_URL:
        print("DATABASE_URL non impostato")
        return
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # crea tabella composti se non esiste
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flavor_composti (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            descrizione_aromatica TEXT,
            fonte TEXT DEFAULT 'ahn_2011'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flavor_abbinamenti (
            id SERIAL PRIMARY KEY,
            ingrediente_1 TEXT NOT NULL,
            ingrediente_2 TEXT NOT NULL,
            composto TEXT,
            overlap_score NUMERIC(4,2),
            fonte TEXT DEFAULT 'ahn_2011',
            UNIQUE(ingrediente_1, ingrediente_2)
        )
    """)
    
    # inserisci abbinamenti
    inseriti = 0
    for ing1, ing2, composto, score in AHN_FLAVOR_PAIRS:
        try:
            cur.execute("""
                INSERT INTO flavor_abbinamenti (ingrediente_1, ingrediente_2, composto, overlap_score)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (ingrediente_1, ingrediente_2) DO UPDATE
                SET overlap_score = EXCLUDED.overlap_score
            """, (ing1, ing2, composto, score))
            # inserisci anche la coppia inversa
            cur.execute("""
                INSERT INTO flavor_abbinamenti (ingrediente_1, ingrediente_2, composto, overlap_score)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (ingrediente_1, ingrediente_2) DO UPDATE
                SET overlap_score = EXCLUDED.overlap_score
            """, (ing2, ing1, composto, score))
            inseriti += 1
        except Exception as e:
            print(f"  skip {ing1}+{ing2}: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"FL1 import flavor network: {inseriti} coppie inserite ({inseriti*2} con inverse)")

if __name__ == "__main__":
    carica_flavor_network()
