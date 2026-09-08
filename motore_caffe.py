# motore_caffe.py - MOTORE OPERATIVO Caffè Pro (espresso + filtro).
# Parte dall'obiettivo (tipo estrazione), calcola ratio + parametri. SCA standard.

def progetta_caffe(metodo="espresso", dose_g=18):
    """Progetta l'estrazione. Espresso: ratio 1:2. Filtro: ratio 1:16."""
    if metodo == "espresso":
        return {
            "obiettivo": f"Espresso da {dose_g}g",
            "ratio": "1:2 (ratio espresso classico)",
            "resa": f"{dose_g}g caffè → {dose_g*2}g in tazza",
            "tempo": "25-30 secondi",
            "temperatura": "90-94°C",
            "macinatura": "fine (regola per centrare i 25-30s)",
            "note": "Se esce in <20s: macina più fine. Se >35s: più grossa. L'amaro viene da sovra-estrazione "
                    "(tempo lungo/macinatura fine), l'acido da sotto-estrazione.",
            "punto_critico": "Il tempo di estrazione (25-30s) è la variabile che decide il gusto, si regola con la macinatura.",
        }
    else:  # filtro
        return {
            "obiettivo": f"Caffè filtro da {dose_g}g",
            "ratio": "1:16 (60g caffè per litro d'acqua)",
            "resa": f"{dose_g}g caffè → {dose_g*16}g acqua",
            "tempo": "2:30-3:30 (V60), 4min (French press)",
            "temperatura": "92-96°C",
            "macinatura": "media (sabbia grossa)",
            "note": "Estrazione target 18-22% (extraction yield). Sotto 18% acido/erbaceo, sopra 22% amaro.",
            "punto_critico": "Il ratio caffè/acqua (1:16) e la temperatura decidono forza ed estrazione.",
        }
