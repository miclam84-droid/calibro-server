# Fusione culturale — cosa serve per la V1 vera

**Data verifica:** 18 ottobre 2026 · **Ondata 3** · endpoint `routes/fusione_culturale.py`

## Verdetto onesto sulla fattibilità

La visione del 16 ottobre è: *«fusione culturale» = trovare ponti aromatici **tra
cucine diverse** — un ingrediente di una tradizione che si lega a uno di un'altra
tramite composti condivisi (rete Ahn)*.

**Nel grafo NON esiste oggi un dato di cucina / cultura / tradizione per
ingrediente.** Verificato su `db.py`, `grafo/schema.sql`, `grafo/schema-ricette.sql`,
`routes/criteri.py`, `routes/api.py`, `routes/misc.py` e su tutti i seed `grafo/*.sql`.

Quello che c'è davvero:

| Campo | Dove | Cosa è | È una cucina? |
|---|---|---|---|
| `nodes.domain` (ingredienti Ahn) | `seed-ahn-ingredienti.sql` | categoria alimentare Ahn: `flower`, `meat`, `spice`, `fruit`, `vegetable`, `herb`, `dairy`, `nut/seed/pulse`… | **No** — è una categoria merceologica |
| `nodes.data->>'categoria'` | stessi nodi | copia della categoria Ahn | **No** |
| `ricette.disciplina` | `schema-ricette.sql` | `bar` \| `cucina` \| `bakery` — il mestiere | **No** — è la disciplina, non una cucina nazionale |
| `nodes.data->>'regione'` | solo un sottoinsieme di varietà italiane (Atlante biodiversità, DOP/IGP) | provenienza **intra-italiana**: Campania, Sicilia… | **No** — è territorio italiano, non una cucina del mondo; e sta su nodi-varietà che di norma **non** portano la chimica aromatica (i composti stanno sul padre Ahn canonico) |

In più, `routes/api.py` dichiara esplicitamente, per il «filo territorio» delle carte:

> «Il filo per territorio non è ancora disponibile: la regione dei piatti non è un
> dato verificato nel corpus.»

**Conclusione:** la «fusione culturale» intesa come *ponte TRA cucine* non è
fattibile oggi senza **inventare** l'origine culturale degli ingredienti. Non è
stato fatto.

## Cosa è stato consegnato invece (V1 onesta)

`GET /v1/fusione/<ingrediente>` — sola lettura. Fa il ponte **onesto** via composti
aromatici realmente condivisi (archi `contiene_composto`, rete Ahn 2011), con lo
stesso motore di `criteri._base_aromatica` (peso IDF per rarità: i composti comuni
pesano ~0, i caratterizzanti pesano tanto; normalizzazione per profilo).

Per ogni ponte restituisce **solo dati veri**:

```json
{
  "ingrediente": "...",
  "categoria": "spice",          // categoria alimentare Ahn — NON una cucina
  "regione": null,                // provenienza italiana SE presente, altrimenti null
  "composti_condivisi": ["eugenol", "..."],
  "n_condivisi": 7,
  "robustezza": "Alta|Media|Esplorativa",
  "perche": "condivide composti caratterizzanti — eugenol, ..."
}
```

Parametro `?solo_altra_categoria=1`: tiene solo i partner di **categoria alimentare
Ahn diversa** — il ponte più «trasversale» ottenibile coi dati veri. Resta una
categoria merceologica, **non** una cucina.

Il campo `cucina_disponibile` nella risposta è **sempre `false`**: è il verdetto reso
esplicito all'API, non un placeholder.

## Cosa servirebbe per la V1 vera (ponte tra cucine)

Serve un **tag di cucina/cultura per ingrediente** (o per ricetta), verificato e
con fonte. In ordine di preferenza:

1. **Dato cucina→ingrediente dal paper Ahn 2011.** Il dataset originale
   *«Flavor network and the principles of food pairing»* (Ahn et al., 2011) contiene
   le ricette raggruppate per **cucina regionale** (NorthAmerican, SouthernEuropean,
   EastAsian, LatinAmerican, WesternEuropean, African, MiddleEastern, SoutheastAsian…)
   e quali ingredienti compaiono in ciascuna. Quelle tabelle **non sono state
   importate**: nel repo è entrato solo ingredienti + composti + connessioni
   (`seed-ahn-ingredienti.sql`, `seed-ahn-composti.sql`, `seed-ahn-connessioni.sql`,
   `seed-ahn-backbone.sql`). Importare la matrice `cuisine × ingredient` darebbe, per
   ogni ingrediente Ahn (che ha già `ahn_id` nel campo `data`), l'insieme delle cucine
   in cui è usato. Join diretto sull'`ahn_id` → nessuna invenzione.

   Forma minima suggerita, additiva e non distruttiva:
   ```sql
   -- su nodi Prodotto/Ingrediente Ahn:
   UPDATE nodes SET data = jsonb_set(data, '{cucine}', '["EastAsian","SoutheastAsian"]')
   WHERE data->>'ahn_id' = '<id>';
   ```
   dove `cucine` è un **array** (un ingrediente sta in più cucine: è questo che rende
   possibile il ponte «sta in A e in B»).

2. **In assenza del dato Ahn:** una tabella curata `ingrediente → cucine[]` con fonte
   esplicita per riga (come già si fa per `fonte` sugli altri nodi). Richiede lavoro
   editoriale e una fonte verificabile; senza fonte, non entra.

Con una delle due, l'endpoint diventa la V1 vera: filtrare i ponti aromatici per
**cucina del base ≠ cucina del partner**, restituendo `{ingrediente, cucina,
composti_condivisi, perche}`. Il motore dei composti condivisi è già pronto e testato
(`ponti_aromatici`, `tests/test_fusione_culturale.py`): mancano **solo** le etichette
di cucina.

## Nota di onestà

Niente cucine o abbinamenti inventati. Ogni ponte prodotto oggi si basa su composti
realmente condivisi nel grafo. Il pezzo «cultura» è dichiarato **pendente**, non
simulato.
