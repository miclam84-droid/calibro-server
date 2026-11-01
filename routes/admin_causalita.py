# -*- coding: utf-8 -*-
# ADMIN — causalità SPECIFICA sui protocolli (bonifica del fossato).
#
# Problema (audit 2026-10-31): la causalità dei protocolli è generica. Ogni
# protocollo salva solo il nome del fenomeno ed EREDITA la causalità dal nodo-
# Fenomeno (routes/api.py leggi_protocollo ~4929-4936). Risultato: tutti i
# protocolli con lo stesso fenomeno mostrano la STESSA identica causalità.
#
# Rimedio: scrivere la causalità PROPRIA nel protocollo, in
# data.fenomeni[i].causalita. leggi_protocollo la preferisce già a quella
# ereditata (eredita solo se None). Così diventa specifica di QUELLA
# preparazione, senza toccare né il nodo-Fenomeno né altri protocolli.
#
# Contenuto INLINE qui sotto (rivedibile nella PR). Da FONTI / tecnica nota,
# NON inventato; "fonte" tracciata dentro la causalità. Da validare al banco.
# causalita=None su un fenomeno REVERTE quel fenomeno al generico ereditato.
#
# Sicurezza: gate ADMIN_SECRET; DRY-RUN di default, scrive SOLO con &esegui=1;
# tocca SOLO gli id nell'allowlist; idempotente; funzione pura testata offline.
from flask import Blueprint, request, jsonify
import json
from db import connessione
from routes.admin import _admin_ok

bp_causalita = Blueprint("admin_causalita", __name__)

# ── Allowlist: id-protocollo -> {"fenomeni": [{"nome", "causalita"}]} ──
# causalita=None  -> reverte quel fenomeno al generico ereditato (fallback onesto).
CAUSALITA_SPECIFICA = {
    # Focaccia barese (Bucolico). Ricetta protocollo VERIFICATA (live): grano
    # tenero 1kg + acqua 650ml (~65%) + lievito madre 200g + olio EVO, pomodorini,
    # olive — NON semola/patata. Bersaglio 70-80% idratazione, mollica morbida.
    # Causalità scritta su QUESTA ricetta (grano tenero + pasta madre, alta idratazione).
    "prot-focaccia-barese": {
        "fenomeni": [
            {
                "nome": "idratazione dell'impasto",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Idratazione alta (~65-70% contando l'acqua del lievito madre) — vapore in cottura, alveolatura aperta, mollica morbida"},
                        {"fattore": "Lievito madre maturo — fermentazione lunga: estensibilità e ritenzione d'acqua, focaccia soffice e morbida più a lungo"},
                        {"fattore": "Pieghe e riposi invece dell'impasto aggressivo — sviluppano la maglia glutinica in un impasto molle senza scaldarlo"},
                        {"fattore": "Olio EVO nell'impasto e in superficie — mollica tenera e crosta che non si asciuga"},
                        {"fattore": "Grano tenero (più debole del duro) — impasto estensibile, mollica più soffice della semola"},
                    ],
                    "rallentanti": [
                        {"fattore": "Poca acqua — mollica densa, chiusa e asciutta: non è la barese morbida"},
                        {"fattore": "Troppa acqua per la forza del grano tenero — impasto che non tiene, si spande, mollica gommosa senza struttura"},
                        {"fattore": "Troppa farina sul banco in formatura — abbassa l'idratazione reale e indurisce"},
                        {"fattore": "Cottura corta — centro gommoso e umido scambiato per 'ben idratato'"},
                        {"fattore": "Pomodorini non scolati o troppo bagnati — rilasciano acqua in cottura: zone slavate sotto"},
                    ],
                    "fonte": "panificazione della focaccia barese a lievito madre e grano tenero, alta idratazione — tecnica di panificazione stabilita; da validare al banco",
                },
            },
        ],
    },
    # Bloody Mary (Bucopertuso). Tecnica classica DOCUMENTATA: si costruisce e
    # si ROLLA (travaso tra due tin) o si mescola gentilmente, NON si shakera —
    # shakerare aera e fa schiumare il succo di pomodoro. Fonte dentro.
    "prot-bloody-mary-rivisitato": {
        "fenomeni": [
            {
                "nome": "shakerare vs mescolare",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Roll (travaso tra due tin) o mescolata gentile — raffredda e integra senza inglobare aria"},
                        {"fattore": "Succo di pomodoro denso — ha già corpo, non serve l'aria dello shake"},
                        {"fattore": "Ghiaccio grande e solido — raffredda con diluizione lenta e controllabile"},
                    ],
                    "rallentanti": [
                        {"fattore": "Shakerare — aera e schiuma il pomodoro: colore pallido, testa spumosa, diluizione troppo rapida"},
                        {"fattore": "Ghiaccio tritato o piccolo — scioglie in fretta: drink acquoso, pomodoro slavato"},
                    ],
                    "fonte": "tecnica classica del Bloody Mary (build/roll, non shake) — Difford's / Liquid Intelligence; da validare al banco",
                },
            },
            {
                "nome": "diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Roll/mescolata misurata sul ghiaccio — porta acqua quanto basta a smussare vodka e acidità"},
                        {"fattore": "Ghiaccio più 'bagnato' (vicino a 0°C) — cede acqua prima, utile se il drink è troppo aggressivo"},
                    ],
                    "rallentanti": [
                        {"fattore": "Troppa diluizione — il corpo del pomodoro si appiattisce, sale e acidità si spengono: watery"},
                        {"fattore": "Mescolata troppo breve — vodka e limone restano taglienti, non integrati"},
                    ],
                    "fonte": "equilibrio e diluizione del Bloody Mary — Liquid Intelligence; da validare al banco",
                },
            },
        ],
    },
    # Boulevardier (Bucopertuso). Ricetta protocollo: bourbon 30 / vermouth rosso
    # 30 / bitter Campari 30 — equal-parts, spirit-forward, SENZA agrumi. Tecnica
    # classica: si MESCOLA nel mixing glass, non si shakera (texture setosa).
    "prot-boulevardier-classico": {
        "fenomeni": [
            {
                "nome": "Diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Mescolare 20-30s nel mixing glass con ghiaccio grande — porta ~20-25% d'acqua che smussa l'alcol del bourbon"},
                        {"fattore": "Vermouth rosso e Campari (già bassa gradazione e zuccherini) abbassano la gradazione media — serve meno acqua che per un drink di solo distillato"},
                        {"fattore": "Ghiaccio asciutto da freezer — raffredda cedendo poca acqua: diluizione fine e controllabile"},
                    ],
                    "rallentanti": [
                        {"fattore": "Shakerare — qui dà microbolle e velo: il Boulevardier equal-parts va mescolato, non agitato"},
                        {"fattore": "Ghiaccio piccolo/bagnato o mescolata troppo lunga — troppa acqua: amaro del Campari e corpo del vermouth si appiattiscono"},
                    ],
                    "fonte": "tecnica classica degli stirred spirit-forward equal-parts (Boulevardier) — Difford's Guide / Regan; da validare al banco",
                },
            },
        ],
    },
    # Americano (Bucopertuso). Ricetta protocollo: vermouth rosso 30 / bitter 30 /
    # acqua frizzante 60 — long drink COSTRUITO nel bicchiere e allungato con soda.
    "prot-americano-rivisitato": {
        "fenomeni": [
            {
                "nome": "diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Build diretto sul ghiaccio con mescolata breve — basta a integrare vermouth e bitter: la soda fa già da allungo"},
                        {"fattore": "Ghiaccio grande e abbondante — raffredda cedendo poca acqua: la diluizione la porta la soda, non lo scioglimento"},
                    ],
                    "rallentanti": [
                        {"fattore": "Mescolata lunga o ghiaccio piccolo — aggiunge acqua di troppo sopra ai 60 ml di soda: drink slavato, bitter spento"},
                        {"fattore": "Ghiaccio scarso in un drink lungo — scioglie in fretta e si scalda: diluizione incontrollata"},
                    ],
                    "fonte": "tecnica classica dell'Americano (build sul ghiaccio, allungato con soda) — Difford's Guide; da validare al banco",
                },
            },
            {
                "nome": "carbonatazione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Soda fredda versata per ultima e piano sul ghiaccio — trattiene più CO2: perlage fine e persistente"},
                        {"fattore": "Soda e bicchiere ben freddi — a bassa temperatura la CO2 resta più disciolta"},
                        {"fattore": "Una sola mescolata minima dal basso dopo la soda — integra senza sbattere fuori le bolle"},
                    ],
                    "rallentanti": [
                        {"fattore": "Versare la soda di getto o mescolare con energia — sbatte fuori la CO2: drink piatto in pochi minuti"},
                        {"fattore": "Soda a temperatura ambiente — perde gas subito al contatto col ghiaccio"},
                    ],
                    "fonte": "comportamento della CO2 nei long drink allungati con soda — tecnica di bar documentata; da validare al banco",
                },
            },
        ],
    },
    # Old Fashioned (Bucopertuso). Ricetta protocollo: bourbon/rye 60 / sciroppo di
    # zucchero 10 / Angostura 3 dash / scorza d'arancia — stirred, servito su rock.
    "prot-old-fashioned": {
        "fenomeni": [
            {
                "nome": "diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Mescolare a lungo (30-40s) su ghiaccio grande — un drink quasi di solo distillato (60 ml) chiede più acqua per aprirsi"},
                        {"fattore": "Servire su un cubo grande singolo — continua a diluire lentamente nel bicchiere, tenendo l'equilibrio nel tempo"},
                        {"fattore": "Ghiaccio molto freddo e asciutto — consente mescolate lunghe senza annacquare di colpo"},
                    ],
                    "rallentanti": [
                        {"fattore": "Servire quasi senza diluizione (mescolata breve) — il bourbon resta spigoloso e alcolico, lo zucchero non si lega"},
                        {"fattore": "Ghiaccio tritato — scioglie troppo: perde subito corpo e diventa acquoso"},
                    ],
                    "fonte": "tecnica classica dell'Old Fashioned (stir, big rock, ~25-30% diluizione) — Liquid Intelligence (Arnold) / Difford's; da validare al banco",
                },
            },
            {
                "nome": "equilibrio del cocktail",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "~10 ml di sciroppo contro 60 di distillato — zucchero appena sufficiente ad arrotondare senza dolcificare"},
                        {"fattore": "3 dash di Angostura — amaro e spezia che legano zucchero e whiskey"},
                        {"fattore": "Olio della scorza d'arancia espresso sopra — profuma e bilancia la dolcezza senza aggiungere acidità"},
                    ],
                    "rallentanti": [
                        {"fattore": "Troppo sciroppo — drink stucchevole, perde il carattere del whiskey"},
                        {"fattore": "Spremere la parte bianca (albedo) della scorza — note amare/verdi fuori posto"},
                    ],
                    "fonte": "equilibrio classico dell'Old Fashioned (distillato-zucchero-bitter) — Regan / Difford's; da validare al banco",
                },
            },
        ],
    },
    # Whiskey Sour (Bucopertuso). Ricetta protocollo: bourbon 60 / succo di limone
    # 30 / sciroppo 1:1 20 / albume 20 — sour CON albume, SHAKERATO (serve aria).
    "prot-whiskey-sour": {
        "fenomeni": [
            {
                "nome": "shakerare vs mescolare",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Shakerare con forza — emulsiona l'albume e integra il limone: senza aria non c'è la schiuma setosa del sour"},
                        {"fattore": "Dry shake (prima senza ghiaccio, poi con) — monta l'albume e dà la testa cremosa e stabile"},
                        {"fattore": "Ghiaccio solido nello shake — raffredda e diluisce al punto giusto mentre si aera"},
                    ],
                    "rallentanti": [
                        {"fattore": "Mescolare invece di shakerare — niente emulsione: albume slegato, drink piatto e sbilanciato sull'acido"},
                        {"fattore": "Shake troppo breve — schiuma scarsa e instabile, collassa nel bicchiere"},
                    ],
                    "fonte": "tecnica classica del sour con albume (shake / dry shake per l'emulsione) — Difford's / Liquid Intelligence; da validare al banco",
                },
            },
            {
                "nome": "diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Shake energico ~10-15s con ghiaccio grande — porta l'acqua che bilancia l'acidità del limone e la gradazione del bourbon"},
                        {"fattore": "Ghiaccio abbondante e duro — raffredda in fretta diluendo il giusto durante lo shake"},
                    ],
                    "rallentanti": [
                        {"fattore": "Shake troppo lungo o ghiaccio già bagnato — troppa acqua: il sour diventa debole e slavato"},
                        {"fattore": "Ghiaccio tritato — eccesso di diluizione in pochi secondi"},
                    ],
                    "fonte": "diluizione nello shake dei sour — Liquid Intelligence (Arnold); da validare al banco",
                },
            },
            {
                "nome": "equilibrio del cocktail",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Rapporto ~60/30/20 (bourbon/limone/sciroppo) — struttura classica del sour: acido e zucchero in tensione sul distillato"},
                        {"fattore": "Succo di limone fresco — acidità viva che taglia dolcezza e gradazione"},
                        {"fattore": "Albume — non cambia il gusto ma arrotonda e lega acido e zucchero in bocca"},
                    ],
                    "rallentanti": [
                        {"fattore": "Troppo sciroppo o poco limone — drink dolce e piatto, perde la spinta 'sour'"},
                        {"fattore": "Succo di limone vecchio/ossidato — acidità spenta e amara, squilibrio"},
                    ],
                    "fonte": "equilibrio acido-zucchero-distillato del Whiskey Sour — Regan / Difford's; da validare al banco",
                },
            },
        ],
    },
    # French 75 (Bucopertuso). Ricetta protocollo: gin 30 / succo di limone 15 /
    # sciroppo 15 / champagne 60 — base shakerata, top di champagne, servito in flute.
    "prot-french-75-classico": {
        "fenomeni": [
            {
                "nome": "diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Shakerare brevemente la base gin-limone-zucchero con ghiaccio — raffredda e diluisce la parte alcolica prima dello champagne"},
                        {"fattore": "Champagne ben freddo versato per ultimo — allunga e raffredda senza bisogno d'altra acqua o ghiaccio nel flute"},
                    ],
                    "rallentanti": [
                        {"fattore": "Shake troppo lungo della base — troppa acqua: con l'aggiunta dello champagne il drink è già slavato"},
                        {"fattore": "Ghiaccio nel flute con lo champagne — diluisce e scalda inutilmente, smorza le bolle"},
                    ],
                    "fonte": "tecnica classica del French 75 (base shakerata, top di champagne, flute senza ghiaccio) — Difford's Guide; da validare al banco",
                },
            },
            {
                "nome": "carbonatazione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Champagne freddissimo aggiunto alla fine e versato piano sulla base già fredda — trattiene la CO2: bollicine fini e durature"},
                        {"fattore": "Base gin-limone pre-raffreddata — meno shock termico allo champagne, meno gas perso"},
                        {"fattore": "Flute stretto — riduce la superficie e rallenta la perdita di bolle"},
                    ],
                    "rallentanti": [
                        {"fattore": "Versare lo champagne di getto o mescolare dopo — sbatte fuori la CO2: drink piatto"},
                        {"fattore": "Base calda o champagne poco freddo — la CO2 esce subito in schiuma"},
                    ],
                    "fonte": "ritenzione della CO2 nei cocktail con top di spumante (French 75) — tecnica di bar documentata; da validare al banco",
                },
            },
        ],
    },

    # ── ONDA 2 ────────────────────────────────────────────────────────────
    # Nuove preparazioni (bar Bucopertuso + forno Bucolico). Ogni causalità è
    # scritta SOLO sui fenomeni che il protocollo ha DAVVERO (verificati live) e
    # da tecnica stabilita, non inventata. "fonte" chiude con "; da validare al banco".

    # Daiquiri Floridita (Bucopertuso). Ricetta: rum bianco + succo di lime +
    # sciroppo di zucchero. Sour agrumato: si SHAKERA forte. Unico fenomeno: 'shaken'.
    "prot-daiquiri-floridita": {
        "fenomeni": [
            {
                "nome": "shaken",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Shake forte e breve (8-12s) con ghiaccio solido — il sour agrumato va aerato e raffreddato in fretta: texture serica, schiumetta fine, servizio ghiacciato in coppetta"},
                        {"fattore": "Ghiaccio grande e freddo nello shaker — raffredda dando diluizione misurata mentre si monta"},
                        {"fattore": "Doppio-strain in coppetta pre-raffreddata — trattiene le schegge di ghiaccio e serve il drink limpido e freddo"},
                    ],
                    "rallentanti": [
                        {"fattore": "Mescolare invece di shakerare — un sour con lime resta piatto, caldo e non integrato: sbagliato per il daiquiri"},
                        {"fattore": "Shake troppo lungo o ghiaccio piccolo/tritato — sovra-diluizione: daiquiri acquoso e slavato"},
                    ],
                    "fonte": "tecnica classica del daiquiri (hard shake dei sour agrumati) — Difford's / Liquid Intelligence; da validare al banco",
                },
            },
        ],
    },

    # Mint Julep (Bucopertuso). Ricetta: bourbon + zucchero + acqua + menta fresca
    # + ghiaccio tritato. Fenomeni: 'infusione' (menta) e 'diluizione' (tritato).
    "prot-mint-julep-rivisitato": {
        "fenomeni": [
            {
                "nome": "infusione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Menta schiaffeggiata (spanking) o premuta gentilmente nello sciroppo — libera gli oli essenziali dalla superficie senza rompere le foglie: aroma pulito"},
                        {"fattore": "Breve contatto menta-sciroppo-bourbon prima del ghiaccio — estrae l'aroma volatile al punto giusto"},
                    ],
                    "rallentanti": [
                        {"fattore": "Pestare/triturare la menta (muddling aggressivo) — rilascia clorofilla e note amare/erbacee: aroma 'verde' sporco"},
                        {"fattore": "Contatto troppo prolungato con l'alcol — estrae l'amaro dalle nervature"},
                    ],
                    "fonte": "gestione della menta nel julep (espressione, non pestatura) — bartending classico; da validare al banco",
                },
            },
            {
                "nome": "diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Ghiaccio tritato abbondante che scioglie lentamente nel tempo — la diluizione progressiva è il cuore del julep: ammorbidisce il bourbon e crea la brina sul metallo"},
                        {"fattore": "Mug di metallo ghiacciato — favorisce brina e raffreddamento continuo"},
                        {"fattore": "Churn (rimescolo col cucchiaio nel tritato) — raffredda e diluisce in modo uniforme"},
                    ],
                    "rallentanti": [
                        {"fattore": "Cubi grandi al posto del tritato — poca superficie: non diluisce né ghiaccia come deve, niente brina"},
                        {"fattore": "Troppa acqua aggiunta a monte — con il tritato che scioglie il drink diventa acquoso"},
                    ],
                    "fonte": "ruolo del ghiaccio tritato nel mint julep (diluizione progressiva e brina) — bartending classico; da validare al banco",
                },
            },
        ],
    },

    # Negroni in batch (Bucopertuso). Ricetta: gin + Campari + vermut rosso +
    # ACQUA pre-calcolata. Fenomeno unico: 'Batch cocktail (diluizione pre-calcolata)'.
    "prot-negroni-batch": {
        "fenomeni": [
            {
                "nome": "Batch cocktail (diluizione pre-calcolata)",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Acqua pre-calcolata (~20-25% del volume degli alcolici) aggiunta al batch — simula la diluizione dello stir: ogni drink esce bilanciato come un Negroni mescolato al momento"},
                        {"fattore": "Batch raffreddato in frigo/freezer prima del servizio — serve meno ghiaccio nel bicchiere, meno diluizione extra incontrollata"},
                        {"fattore": "Volumi misurati sulla gradazione reale (gin 40-47%, Campari 25%, vermut 16-18%) — la gradazione media determina quanta acqua aggiungere"},
                    ],
                    "rallentanti": [
                        {"fattore": "Zero acqua nel batch e servizio su ghiaccio come fosse mescolato al momento — troppo forte e 'caldo', oppure incoerente da un drink all'altro"},
                        {"fattore": "Acqua di troppo — Negroni piatto e slavato, amaro del Campari spento"},
                        {"fattore": "Ghiaccio piccolo nel bicchiere dopo un batch già diluito — doppia diluizione: drink acquoso"},
                    ],
                    "fonte": "tecnica di batching dei cocktail mescolati (diluizione pre-calcolata) — Morgenthaler / Liquid Intelligence; da validare al banco",
                },
            },
        ],
    },

    # Penicillin (Bucopertuso). Ricetta: whisky torbato + succo di limone + miele
    # + scotch affumicato (float) + ghiaccio. Sour con float: si SHAKERA la base,
    # il float affumicato NON si shakera. Fenomeni: 'Diluizione', 'Shakerare vs mescolare'.
    "prot-penicillin-rivisitata": {
        "fenomeni": [
            {
                "nome": "Shakerare vs mescolare",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Shakerare la base con ghiaccio — limone + miele (sour) richiedono aerazione e raffreddamento rapido per integrare il miele denso e dare texture"},
                        {"fattore": "Ghiaccio solido e freddo nello shaker — raffredda e monta in 8-12s"},
                        {"fattore": "Float di scotch affumicato aggiunto DOPO, non shakerato — preserva il naso torbato/di fumo in superficie"},
                    ],
                    "rallentanti": [
                        {"fattore": "Mescolare invece di shakerare — il miele resta stratificato e il sour non si integra: drink squilibrato e poco freddo"},
                        {"fattore": "Shakerare anche il float affumicato — disperde l'aroma di fumo che deve colpire al naso"},
                    ],
                    "fonte": "costruzione del Penicillin (sour shakerato + float affumicato non shakerato) — ricetta classica Sam Ross; da validare al banco",
                },
            },
            {
                "nome": "Diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Servizio su un ghiaccio grande fresco dopo lo shake — diluizione lenta che tiene il drink freddo senza annacquarlo"},
                        {"fattore": "Shake breve e deciso — porta la diluizione giusta a smussare limone e torba"},
                    ],
                    "rallentanti": [
                        {"fattore": "Ghiaccio tritato o molti cubetti piccoli nel bicchiere — sciolgono in fretta: miele e limone si slavano"},
                        {"fattore": "Shake troppo lungo — sovra-diluizione: la torba del whisky si spegne"},
                    ],
                    "fonte": "equilibrio e diluizione del Penicillin — bartending contemporaneo; da validare al banco",
                },
            },
        ],
    },

    # Sazerac (Bucopertuso). Ricetta: rye + zucchero + Peychaud's bitters + assenzio
    # (rinse) + scorza di limone. Drink tutto-alcolico: si MESCOLA e si serve liscio.
    # Fenomeni: 'diluizione', 'amaro e bitter'.
    "prot-sazerac-rivisitato": {
        "fenomeni": [
            {
                "nome": "diluizione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Mescolare (stir) con ghiaccio, non shakerare — drink interamente alcolico (rye + zucchero + bitter): lo stir raffredda e diluisce senza aerare, texture setosa e limpida"},
                        {"fattore": "Ghiaccio grande e freddo mescolato 20-30s — porta la diluizione che ammorbidisce il rye ad alta gradazione"},
                        {"fattore": "Servizio liscio nel tumbler freddo senza ghiaccio — la diluizione è tutta nello stir, calibrata a monte"},
                    ],
                    "rallentanti": [
                        {"fattore": "Shakerare — aera e intorbida un drink che deve essere cristallino: sbagliato per il Sazerac"},
                        {"fattore": "Stir troppo breve o ghiaccio bagnato/piccolo — rye tagliente e alcolico, oppure acquoso"},
                    ],
                    "fonte": "tecnica classica del Sazerac (build mescolato, servito liscio) — Difford's; da validare al banco",
                },
            },
            {
                "nome": "amaro e bitter",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Peychaud's bitters in dose decisa — è la firma aromatica del Sazerac (anice/floreale), definisce il drink"},
                        {"fattore": "Rinse del bicchiere con assenzio e scarto dell'eccesso — vela di anice al naso senza coprire"},
                        {"fattore": "Scorza di limone espressa sugli oli e scartata — agrumi in superficie che sollevano il bitter"},
                    ],
                    "rallentanti": [
                        {"fattore": "Troppo assenzio lasciato nel bicchiere — l'anice domina e copre il Peychaud's"},
                        {"fattore": "Poco bitter — Sazerac anonimo, manca la spina dorsale aromatica"},
                        {"fattore": "Scorza strofinata sul bordo o lasciata dentro — amaro bianco dell'albedo"},
                    ],
                    "fonte": "ruolo di Peychaud's e assenzio nel Sazerac — ricetta classica New Orleans; da validare al banco",
                },
            },
        ],
    },

    # Pane di Altamura con lievito madre (Bucolico). Ricetta VERIFICATA (live):
    # semola di grano duro rimacinata 1000g + lievito madre 200g + acqua 600g (~60%)
    # + sale. Fenomeni: 'idratazione dell'impasto', 'lievito madre'.
    "prot-pane-di-altamura-con-lievito-madre": {
        "fenomeni": [
            {
                "nome": "idratazione dell'impasto",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Idratazione ~60% adatta alla semola rimacinata di grano duro — assorbe più acqua del tenero: mollica gialla fitta ma non secca"},
                        {"fattore": "Assorbimento lento della semola con riposo/autolisi — l'acqua entra nei granuli: impasto più lavorabile e mollica uniforme"},
                    ],
                    "rallentanti": [
                        {"fattore": "Troppa poca acqua — mollica compatta e asciutta, crosta troppo dura"},
                        {"fattore": "Troppa acqua per la semola — impasto colloso, alveolatura irregolare e appiattita"},
                    ],
                    "fonte": "idratazione del pane di Altamura (semola di grano duro rimacinata) — tecnica di panificazione stabilita; da validare al banco",
                },
            },
            {
                "nome": "lievito madre",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Lievito madre maturo al picco (raddoppiato, profumo lattico-dolce) — spinta e aroma tipici, acidità che conserva"},
                        {"fattore": "Fermentazione lunga con pasta madre — sviluppo aromatico e durata (il pane di Altamura si conserva giorni)"},
                    ],
                    "rallentanti": [
                        {"fattore": "Lievito madre troppo maturo/acido — eccesso acetico: mollica gommosa e sapore pungente"},
                        {"fattore": "Lievito madre debole o fuori picco — poca spinta: pane basso e denso"},
                    ],
                    "fonte": "gestione del lievito madre nel pane di Altamura — tecnica di panificazione stabilita; da validare al banco",
                },
            },
        ],
    },

    # Pizza napoletana (Bucolico). Ricetta VERIFICATA (live): farina W300-340 1000g
    # + acqua 650g (~65%) + sale 25g + lievito fresco 3g, DDT target ~28°C. Fenomeni:
    # 'fermentazione', 'idratazione'.
    "prot-pizza-napoletana": {
        "fenomeni": [
            {
                "nome": "fermentazione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Poco lievito (3g su 1kg) + fermentazione lunga — maglia matura, cornicione leggero e digeribile"},
                        {"fattore": "Temperatura impasto a fine lavorazione ~28°C (DDT) — cinetica di lievitazione corretta e costante"},
                        {"fattore": "Appretto/staglio con tempi adeguati — alveolatura del cornicione"},
                    ],
                    "rallentanti": [
                        {"fattore": "Troppo lievito o fermentazione troppo corta — cornicione pesante, poco sviluppo, meno digeribile"},
                        {"fattore": "Impasto troppo caldo o troppo freddo rispetto al DDT — lievitazione fuori controllo (troppo veloce o bloccata)"},
                    ],
                    "fonte": "fermentazione della pizza napoletana (basso lievito, lunga maturazione, DDT) — tecnica STG stabilita; da validare al banco",
                },
            },
            {
                "nome": "idratazione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Idratazione ~65% su farina forte (W300-340) — la farina regge l'acqua: impasto estensibile, cornicione alveolato"},
                        {"fattore": "Farina di forza adeguata alla lunga fermentazione — trattiene i gas senza smagliarsi"},
                    ],
                    "rallentanti": [
                        {"fattore": "Idratazione alta su farina debole — l'impasto non tiene i tempi lunghi, si smaglia"},
                        {"fattore": "Idratazione troppo bassa — disco rigido, cornicione secco e poco sviluppato"},
                    ],
                    "fonte": "idratazione/forza farina nella pizza napoletana ad alta temperatura — tecnica di panificazione stabilita; da validare al banco",
                },
            },
        ],
    },

    # ── ONDA 3 ────────────────────────────────────────────────────────────
    # Cucina napoletana/italiana (dominio del fondatore). Ogni causalità è
    # scritta SOLO sui fenomeni che il protocollo ha DAVVERO (verificati live su
    # /v1/protocollo/<id>) e sui reagenti REALI della ricetta; tecnica di cucina
    # stabilita, non inventata. "fonte" chiude con "; da validare al banco".

    # Cacio e pepe (cucina). Reagenti live: tonnarelli, pecorino romano, pepe nero,
    # sale, acqua. Bersaglio ~65°C. Fenomeni: 'emulsione', "gelatinizzazione dell'amido".
    "prot-cacio-e-pepe": {
        "fenomeni": [
            {
                "nome": "emulsione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Crema di pecorino sciolta con acqua di cottura TIEPIDA (non bollente) — l'amido disciolto nell'acqua fa da legante e stabilizza l'emulsione formaggio-grasso-acqua"},
                        {"fattore": "Acqua di cottura ben amidacea (poca acqua, poco sale) — più amido = emulsione più stabile e cremosa"},
                        {"fattore": "Mantecatura energica fuori o a fuoco spento, aggiungendo liquido poco per volta — monta la crema senza spezzarla"},
                        {"fattore": "Pepe tostato a secco e macinato al momento — rilascia oli aromatici che profumano senza interferire con la legatura"},
                    ],
                    "rallentanti": [
                        {"fattore": "Pecorino unito ad acqua o padella troppo calde (>65°C) — la caseina coagula: grumi filanti e separazione del grasso invece della crema"},
                        {"fattore": "Acqua troppo salata o troppo abbondante — poco amido e sale in eccesso: emulsione slegata e piatto sapido"},
                        {"fattore": "Aggiungere tutto il formaggio in un colpo sul caldo — shock termico: palla di cacio appiccicata"},
                    ],
                    "fonte": "emulsione della cacio e pepe (crema di pecorino + acqua amidacea sotto i 65°C) — tecnica di cucina romana stabilita; da validare al banco",
                },
            },
            {
                "nome": "gelatinizzazione dell'amido",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Cottura della pasta in poca acqua (risottata o quasi) — l'acqua si carica di amido che serve poi all'emulsione"},
                        {"fattore": "Tonnarello ruvido e poroso — rilascia e trattiene più amido superficiale, lega meglio la crema"},
                        {"fattore": "Scolare al dente tenendo da parte l'acqua amidacea — l'amido gelatinizzato è il legante del piatto"},
                    ],
                    "rallentanti": [
                        {"fattore": "Troppa acqua di cottura — amido diluito: acqua inefficace come legante, crema che non tiene"},
                        {"fattore": "Pasta scotta — amido sfaldato in eccesso: collosità e perdita di struttura, non cremosità"},
                    ],
                    "fonte": "ruolo dell'amido della pasta nella cacio e pepe (acqua amidacea come legante) — tecnica di cucina stabilita; da validare al banco",
                },
            },
        ],
    },

    # Risotto (cucina). Reagenti live: riso Carnaroli/Arborio, brodo caldo, burro
    # freddo, parmigiano, vino bianco. Fenomeni: 'Gelatinizzazione amido', 'Mantecatura'.
    "prot-risotto": {
        "fenomeni": [
            {
                "nome": "Gelatinizzazione amido",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Riso ad alto tenore di amilopectina (Carnaroli/Arborio) — rilascia amido in cottura: è ciò che rende cremoso il risotto senza panna"},
                        {"fattore": "Brodo caldo aggiunto poco per volta, mescolando — lo sfregamento dei chicchi libera amido in modo graduale e uniforme"},
                        {"fattore": "Tostatura iniziale del riso — sigilla il chicco così l'amido esce regolato e il cuore resta al dente"},
                    ],
                    "rallentanti": [
                        {"fattore": "Brodo freddo versato tutto insieme — abbassa la temperatura, cottura disomogenea, amido rilasciato male: riso slegato o impastato"},
                        {"fattore": "Non mescolare — l'amido resta nel chicco: risotto che non lega, acquoso"},
                        {"fattore": "Lavare il riso prima — via l'amido superficiale: addio cremosità"},
                    ],
                    "fonte": "gelatinizzazione dell'amido nel risotto (varietà, tostatura, brodo caldo a mestoli) — tecnica di cucina italiana stabilita; da validare al banco",
                },
            },
            {
                "nome": "Mantecatura",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Burro FREDDO e parmigiano a fuoco SPENTO, mescolando con energia — emulsiona grasso e amido: onda cremosa e lucida (all'onda)"},
                        {"fattore": "Riposo di un minuto e mantecatura vigorosa — l'emulsione si monta e il risotto 'si allarga'"},
                        {"fattore": "Giusta umidità residua prima di mantecare — serve un velo di fondo liquido per legare burro e formaggio"},
                    ],
                    "rallentanti": [
                        {"fattore": "Mantecare a fuoco acceso o con burro a temperatura ambiente — il grasso si separa: risotto unto, non cremoso"},
                        {"fattore": "Risotto troppo asciutto prima della mantecatura — niente da emulsionare: resta compatto e colloso"},
                        {"fattore": "Troppo parmigiano — sapore squilibrato e tendenza al collant/filante"},
                    ],
                    "fonte": "mantecatura all'onda del risotto (burro freddo + formaggio fuori fuoco) — tecnica di cucina italiana stabilita; da validare al banco",
                },
            },
        ],
    },

    # Polpette al sugo (cucina napoletana). Reagenti live: carne macinata, pane
    # grattugiato, latte, uova, parmigiano, sale, pepe, olio d'oliva, passata di
    # pomodoro, cipolla. Fenomeni: 'Reazione di Strecker', 'Il riposo della carne', 'Il soffritto'.
    "prot-polpette-al-sugo": {
        "fenomeni": [
            {
                "nome": "Reazione di Strecker",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Rosolare le polpette in olio ben caldo prima del sugo — crosta dorata: la degradazione di Strecker sviluppa gli aromi tostati della carne"},
                        {"fattore": "Superficie delle polpette asciutta e non sovraffollata in padella — la temperatura resta alta e la doratura parte subito"},
                        {"fattore": "Fondo di cottura recuperato nel sugo — i composti aromatici della rosolatura passano alla salsa"},
                    ],
                    "rallentanti": [
                        {"fattore": "Padella fredda o affollata — le polpette bollono nei loro liquidi: niente crosta, niente aroma di Strecker, carne grigia"},
                        {"fattore": "Cuocere le polpette solo nel sugo senza rosolarle — saltano i composti tostati, risultato piatto"},
                        {"fattore": "Rosolatura spinta fino al bruciato — note amare al posto di quelle tostate"},
                    ],
                    "fonte": "doratura delle polpette (Maillard/Strecker in rosolatura prima del sugo) — tecnica di cucina stabilita; da validare al banco",
                },
            },
            {
                "nome": "Il riposo della carne",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Impasto fatto riposare in frigo prima di formare le polpette — pane e latte idratano e legano, la carne si compatta: polpette che tengono la forma"},
                        {"fattore": "Panatura (pane + latte) ammollata e strizzata bene — distribuisce umidità uniforme: morbidezza senza sfaldarsi"},
                        {"fattore": "Riposo a crudo che lascia ridistribuire i succhi — cottura più uniforme e polpetta più succosa"},
                    ],
                    "rallentanti": [
                        {"fattore": "Formare e cuocere subito l'impasto appena fatto — poco legato: le polpette si aprono in cottura"},
                        {"fattore": "Impasto troppo lavorato e scaldato dalle mani — grasso spalmato: polpette gommose e asciutte"},
                    ],
                    "fonte": "riposo dell'impasto delle polpette (idratazione panatura, legatura, succosità) — tecnica di cucina stabilita; da validare al banco",
                },
            },
            {
                "nome": "Il soffritto",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Cipolla a fuoco dolce in olio fino a trasparenza e dolcezza — base aromatica del sugo di accompagnamento, senza nota pungente di crudo"},
                        {"fattore": "Soffritto non bruciato, appena biondo — zuccheri della cipolla che addolciscono la passata"},
                    ],
                    "rallentanti": [
                        {"fattore": "Cipolla a fuoco alto che brucia — amaro che rovina tutto il sugo"},
                        {"fattore": "Passata aggiunta sulla cipolla ancora cruda/pungente — sugo sbilanciato e aggressivo"},
                    ],
                    "fonte": "soffritto di cipolla per il sugo delle polpette — tecnica di cucina stabilita; da validare al banco",
                },
            },
        ],
    },

    # Genovese di melanzane (cucina napoletana). Reagenti live: cipolle, manzo,
    # pasta ziti, olio EVO, sale, melanzane. Bersaglio 40 min. Fenomeni: 'il soffritto', 'la rosolatura'.
    "prot-genovese-di-melanzane": {
        "fenomeni": [
            {
                "nome": "il soffritto",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Grande quantità di cipolle a fuoco bassissimo e lungo — è il cuore della genovese: le cipolle si sfaldano e caramellano negli zuccheri propri, dolcezza bruna"},
                        {"fattore": "Coperchio nelle prime fasi e poca acqua — le cipolle sudano e stufano senza bruciare, poi si asciugano in crema"},
                        {"fattore": "Tempo lungo (ben oltre i 40 min di base per la versione classica) — la cipolla passa da pungente a dolce e ambrata"},
                    ],
                    "rallentanti": [
                        {"fattore": "Fuoco alto per accorciare i tempi — cipolle bruciate fuori e crude dentro: amaro, niente dolcezza genovese"},
                        {"fattore": "Poche cipolle — manca la massa che fa la salsa, genovese magra e slavata"},
                    ],
                    "fonte": "soffritto/stufatura delle cipolle nella genovese napoletana (massa di cipolle, fuoco lento e lungo) — tecnica di cucina napoletana stabilita; da validare al banco",
                },
            },
            {
                "nome": "la rosolatura",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Manzo rosolato bene in olio caldo prima di unirlo alle cipolle — crosta Maillard che dà fondo e profondità alla genovese"},
                        {"fattore": "Carne asciutta e padella non affollata — doratura vera invece di bollitura nei succhi"},
                    ],
                    "rallentanti": [
                        {"fattore": "Carne messa fredda e bagnata in padella non abbastanza calda — rilascia acqua, lessa invece di rosolare: genovese piatta"},
                        {"fattore": "Rosolatura bruciata — amaro che sporca il dolce delle cipolle"},
                    ],
                    "fonte": "rosolatura del manzo nella genovese (Maillard per il fondo di sapore) — tecnica di cucina napoletana stabilita; da validare al banco",
                },
            },
        ],
    },

    # Tagliatelle al ragù (cucina italiana). Reagenti live: tagliatelle fresche,
    # carne macinata di manzo, carota, cipolla, sedano, pomodori pelati, vino rosso,
    # olio EVO, sale, pepe. Bersaglio 150-180°C. Fenomeni: 'Soffritto', 'Rosolatura'.
    "prot-tagliatelle-al-ragu": {
        "fenomeni": [
            {
                "nome": "Soffritto",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Trito di carota, cipolla e sedano (battuto) a fuoco dolce in olio — base aromatica del ragù: dolcezza e profondità prima della carne"},
                        {"fattore": "Soffritto appassito lentamente fino a morbido e dorato chiaro — zuccheri delle verdure che bilanciano l'acidità del pomodoro"},
                    ],
                    "rallentanti": [
                        {"fattore": "Soffritto bruciato o a fuoco troppo alto — amaro che resta nel ragù fino alla fine"},
                        {"fattore": "Verdure tagliate grosse e poco cotte — base aromatica debole e pezzi crudi nel sugo"},
                    ],
                    "fonte": "battuto/soffritto del ragù (carota-cipolla-sedano a fuoco dolce) — tecnica di cucina italiana stabilita; da validare al banco",
                },
            },
            {
                "nome": "Rosolatura",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Carne rosolata a fuoco vivo (~150-180°C in padella) fino a doratura — Maillard che costruisce il fondo di sapore del ragù"},
                        {"fattore": "Carne asciutta, aggiunta in più riprese senza affollare — resta la temperatura alta e la carne dora invece di lessare"},
                        {"fattore": "Sfumatura col vino rosso DOPO la rosolatura — deglassa il fondo bruno e lega i composti aromatici"},
                    ],
                    "rallentanti": [
                        {"fattore": "Troppa carne tutta insieme in padella — crolla la temperatura: la carne rilascia acqua e bolle, grigia e insapore"},
                        {"fattore": "Pomodoro aggiunto prima di aver rosolato — l'acidità e l'acqua bloccano la Maillard"},
                    ],
                    "fonte": "rosolatura della carne del ragù (Maillard a 150-180°C, poi sfumatura col vino) — tecnica di cucina italiana stabilita; da validare al banco",
                },
            },
        ],
    },

    # Pasta al pomodoro (cucina). Reagenti live: pasta, pomodori pelati, aglio, olio
    # EVO, basilico, sale. Fenomeni: 'Amido gelatinizza da fuori a dentro', 'Emulsione della salsa'.
    "prot-pasta-al-pomodoro-rivisitata": {
        "fenomeni": [
            {
                "nome": "Amido gelatinizza da fuori a dentro",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Acqua in abbondante ebollizione e pasta al dente — l'amido gelatinizza dall'esterno mentre il cuore resta sodo: tenuta e rilascio di amido per legare"},
                        {"fattore": "Ultima parte di cottura della pasta direttamente nel sugo con un po' d'acqua di cottura — l'amido che esce lega pasta e salsa (risottatura)"},
                    ],
                    "rallentanti": [
                        {"fattore": "Pasta scotta — amido completamente gelatinizzato e sfaldato: collosa, non lega, si spappola"},
                        {"fattore": "Poca acqua o acqua non bollente all'immissione — cottura irregolare e pasta appiccicata"},
                    ],
                    "fonte": "gelatinizzazione dell'amido della pasta (al dente, risottatura nel sugo) — tecnica di cucina stabilita; da validare al banco",
                },
            },
            {
                "nome": "Emulsione della salsa",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Olio EVO + acqua di cottura amidacea mantecati col pomodoro a fuoco vivace — l'amido emulsiona grasso e acqua: salsa lucida che vela la pasta"},
                        {"fattore": "Mantecatura in padella saltando la pasta — il movimento monta l'emulsione e fa aderire il sugo"},
                        {"fattore": "Aglio in olio a freddo/dolce — aromatizza l'olio che è la fase grassa dell'emulsione"},
                    ],
                    "rallentanti": [
                        {"fattore": "Olio e acqua senza amido e senza mantecatura — si separano: pasta 'asciutta' con sugo che cola sotto"},
                        {"fattore": "Troppo olio rispetto all'acqua amidacea — emulsione che si rompe, piatto unto"},
                    ],
                    "fonte": "emulsione della salsa al pomodoro (olio + acqua amidacea mantecati) — tecnica di cucina stabilita; da validare al banco",
                },
            },
        ],
    },

    # Pasta alla Norma (cucina). Reagenti live: pasta, melanzane, pomodori pelati,
    # ricotta salata, basilico, olio EVO, sale. Fenomeni: 'amido gelatinizza da fuori
    # a dentro', 'acqua amidacea emulsionante'.
    "prot-pasta-alla-norma": {
        "fenomeni": [
            {
                "nome": "amido gelatinizza da fuori a dentro",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Pasta scolata al dente — l'amido gelatinizza in superficie mentre il cuore tiene: struttura che regge la mantecatura col sugo di melanzane"},
                        {"fattore": "Breve saltatura finale nel sugo con acqua di cottura — l'amido rilasciato lega pasta, pomodoro e olio delle melanzane"},
                    ],
                    "rallentanti": [
                        {"fattore": "Pasta scotta — amido sfaldato: si impasta col sugo e perde mordente"},
                        {"fattore": "Scolare troppo asciutto senza tenere acqua di cottura — niente amido per legare, sugo che scivola"},
                    ],
                    "fonte": "gelatinizzazione dell'amido nella pasta alla Norma (al dente, saltata nel sugo) — tecnica di cucina siciliana stabilita; da validare al banco",
                },
            },
            {
                "nome": "acqua amidacea emulsionante",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Acqua di cottura ricca di amido aggiunta al sugo con l'olio delle melanzane — emulsiona grasso e acqua: salsa cremosa che avvolge la pasta"},
                        {"fattore": "Mantecatura saltando in padella — monta l'emulsione e fa aderire pomodoro e olio alla pasta"},
                        {"fattore": "Ricotta salata grattugiata a fine piatto — sapidità e corpo senza spezzare l'emulsione (fuori dal fuoco vivace)"},
                    ],
                    "rallentanti": [
                        {"fattore": "Acqua povera di amido o niente mantecatura — olio e pomodoro restano separati, pasta slegata"},
                        {"fattore": "Melanzane troppo cariche d'olio senza acqua amidacea a bilanciare — piatto unto e salsa che non lega"},
                    ],
                    "fonte": "acqua amidacea come emulsionante nella pasta alla Norma — tecnica di cucina siciliana stabilita; da validare al banco",
                },
            },
        ],
    },
    # ── ONDA 4 — pasticceria, gelateria, caffetteria (+ cucina) ──
    # Panna cotta (pasticceria). Ricetta protocollo (live): panna fresca, zucchero,
    # gelatina in fogli, vaniglia. Fenomeno reale: "gelificazione". Causalità scritta
    # sulla gelatina (collagene idrolizzato, gel termoreversibile) in base grassa.
    "prot-panna-cotta": {
        "fenomeni": [
            {
                "nome": "gelificazione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Gelatina in fogli idratata in acqua fredda prima dell'uso — assorbe acqua e si scioglie uniforme nella panna calda senza grumi"},
                        {"fattore": "Sciogliere la gelatina in panna calda ma NON bollente (sotto ~80°C) — il collagene idrolizzato gelifica; l'ebollizione prolungata degrada le catene e indebolisce la presa"},
                        {"fattore": "Dose calibrata sul volume (tipico ~8-10 g di gelatina per litro) — presa che sta in piedi ma trema: cremosa al cucchiaio, non gommosa"},
                        {"fattore": "Riposo in frigo alcune ore — la rete di gelatina si forma a freddo (gel termoreversibile)"},
                        {"fattore": "Grasso della panna — ammorbidisce la rete proteica e dà la texture vellutata"},
                    ],
                    "rallentanti": [
                        {"fattore": "Troppa gelatina — rete fitta: consistenza gommosa da caramella, non da cucchiaio"},
                        {"fattore": "Far bollire la panna con la gelatina dentro — degrada il collagene: presa debole o assente"},
                        {"fattore": "Frutta fresca con enzimi proteolitici (ananas, kiwi) o ingredienti molto acidi — idrolizzano le proteine della gelatina e impediscono la presa"},
                        {"fattore": "Gelatina versata tutta insieme in un liquido freddo — si rapprende a filamenti (grumi) invece di distribuirsi"},
                        {"fattore": "Troppa poca gelatina per i liquidi e lo zucchero — non prende, resta colante"},
                    ],
                    "fonte": "gelificazione con gelatina (collagene idrolizzato, gel termoreversibile) nella panna cotta — tecnica di pasticceria stabilita; da validare al banco",
                },
            },
        ],
    },
    # Ganache fondente per tartufi 1:1 (pasticceria). Ricetta (live): cioccolato
    # fondente 70%, panna 35%, burro opzionale, glucosio. Fenomeno reale: "Ganache".
    # Causalità sull'emulsione grasso-in-acqua e sul seizing.
    "prot-ganache-fondente": {
        "fenomeni": [
            {
                "nome": "Ganache",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Rapporto cioccolato:panna ~1:1 — burro di cacao sufficiente a rapprendere in una massa modellabile ma cremosa, giusto per i tartufi"},
                        {"fattore": "Panna calda versata sul cioccolato e lasciata riposare prima di mescolare — scioglie uniforme senza shock termico"},
                        {"fattore": "Emulsione mescolando dal centro verso l'esterno — i globuli di grasso si disperdono fini nella fase acquosa della panna: ganache lucida e liscia"},
                        {"fattore": "Glucosio — trattiene acqua e morbidezza e stabilizza l'emulsione contro la ricristallizzazione dello zucchero"},
                        {"fattore": "Burro a ~35°C a fine lavorazione — aggiunge lucentezza e scioglievolezza senza spaccare l'emulsione"},
                    ],
                    "rallentanti": [
                        {"fattore": "Surriscaldare il cioccolato (oltre ~50°C) o panna troppo bollente — il grasso si separa: ganache oleosa e spaccata"},
                        {"fattore": "Qualche goccia d'acqua o vapore nel cioccolato fuso — seizing: la massa si irrigidisce a grumi"},
                        {"fattore": "Mescolare troppo presto o troppo violento incorporando aria — emulsione instabile e opaca"},
                        {"fattore": "Troppa panna per il cacao del fondente — non rapprende: resta una crema molle non modellabile"},
                        {"fattore": "Raffreddamento troppo rapido — cristallizzazione irregolare del burro di cacao: superficie opaca e granulosa"},
                    ],
                    "fonte": "emulsione grasso-in-acqua della ganache (burro di cacao disperso nella fase acquosa della panna), rapporto 1:1 per tartufi — tecnica di pasticceria stabilita; da validare al banco",
                },
            },
        ],
    },
    # Gelato al caramello e nocciola (gelateria). Ricetta (live): latte, panna,
    # zucchero, nocciole, caramello, sale. Fenomeni reali: "Cristalli di ghiaccio
    # (cremosita)" e "Bilanciamento del mix gelato". Causalità su crioscopia e mix.
    "prot-gelato-al-caramello-e-nocciola": {
        "fenomeni": [
            {
                "nome": "Cristalli di ghiaccio (cremosita)",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Mantecazione con agitazione continua durante il congelamento — rompe i cristalli di ghiaccio sul nascere e incorpora aria fine: massa cremosa"},
                        {"fattore": "Congelamento rapido — meno tempo perché i cristalli crescano: struttura fine"},
                        {"fattore": "Zuccheri disciolti (saccarosio + quelli del caramello) — abbassano il punto di congelamento: più acqua resta liquida, cristalli più piccoli"},
                        {"fattore": "Grassi di latte e panna + pasta di nocciole — rivestono cristalli e bolle d'aria: percezione vellutata in bocca"},
                    ],
                    "rallentanti": [
                        {"fattore": "Congelamento lento senza agitazione — i cristalli crescono grandi: gelato granuloso e ghiacciato"},
                        {"fattore": "Ri-congelare dopo scioglimento parziale — i cristalli si saldano e ingrossano (ricristallizzazione)"},
                        {"fattore": "Troppa acqua libera (mix poco bilanciato) — più ghiaccio e meno cremosità"},
                    ],
                    "fonte": "controllo della dimensione dei cristalli di ghiaccio (mantecazione, congelamento rapido, abbassamento crioscopico degli zuccheri) nel gelato — tecnica di gelateria stabilita; da validare al banco",
                },
            },
            {
                "nome": "Bilanciamento del mix gelato",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Zuccheri nella giusta quota (saccarosio + caramello) — abbassano il punto di congelamento quanto basta per spatolabilità a -12/-14°C"},
                        {"fattore": "Solidi del latte (proteine, lattosio) — legano l'acqua e stabilizzano la schiuma: meno acqua libera da congelare"},
                        {"fattore": "Grassi ~6-10% — corpo, scioglievolezza e trasporto degli aromi di nocciola e caramello"},
                        {"fattore": "Equilibrio fra zuccheri, grassi e solidi — struttura cremosa che non ghiaccia e non resta molle"},
                    ],
                    "rallentanti": [
                        {"fattore": "Troppo zucchero (caramello compreso) — punto di congelamento troppo basso: gelato molle e appiccicoso che non indurisce"},
                        {"fattore": "Troppi pochi zuccheri o solidi — troppa acqua libera: duro e cristallino appena uscito dal freezer"},
                        {"fattore": "Eccesso di grasso — sensazione untuosa e congelamento ostacolato"},
                    ],
                    "fonte": "bilanciamento del mix gelato (zuccheri per il punto di congelamento, solidi del latte per l'acqua legata, grassi per il corpo) — tecnica di gelateria stabilita; da validare al banco",
                },
            },
        ],
    },
    # Crème pâtissière al cioccolato (pasticceria). Ricetta (live): panna, tuorli,
    # zucchero, cioccolato fondente, vaniglia. Fenomeno reale: "coagulazione
    # controllata". Causalità sull'amido che protegge i tuorli (gelatinizzazione).
    "prot-cr-me-p-tissi-re-al-cioccolato": {
        "fenomeni": [
            {
                "nome": "coagulazione controllata",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Amido (farina o amido di mais) nei tuorli — interferisce col legame fra le proteine dell'uovo e alza la temperatura di coagulazione: si può portare a bollore senza impazzire"},
                        {"fattore": "Frusta continua durante la cottura — distribuisce il calore ed evita che i tuorli coagulino a grumi sul fondo"},
                        {"fattore": "Temperare i tuorli versando il liquido caldo a filo — innalza la temperatura gradualmente, niente shock che rapprende l'uovo"},
                        {"fattore": "Portare a ~85°C (o a bollore grazie all'amido) — gelatinizza l'amido e addensa: crema liscia e stabile"},
                        {"fattore": "Cioccolato fondente incorporato fuori dal fuoco — il grasso rende setoso senza rischio di bruciare"},
                    ],
                    "rallentanti": [
                        {"fattore": "Calore troppo alto senza mescolare — i tuorli coagulano a frittata: crema granulosa"},
                        {"fattore": "Poco amido rispetto ai tuorli — coagulano a temperatura più bassa: margine stretto, rischio di stracciare"},
                        {"fattore": "Liquido bollente versato tutto insieme sui tuorli freddi — shock termico: grumi"},
                        {"fattore": "Sovracottura prolungata — la rete proteica si contrae ed espelle acqua (sineresi): crema che 'piange'"},
                    ],
                    "fonte": "coagulazione controllata dei tuorli protetta dall'amido (gelatinizzazione) nella crema pasticcera — tecnica di pasticceria stabilita; da validare al banco",
                },
            },
        ],
    },
    # Caffè con la moka (caffetteria). Ricetta (live): caffè macinato medio-fine,
    # acqua. Fenomeni reali: "Estrazione caffè" e "Macinatura e estrazione del caffè".
    "prot-moka": {
        "fenomeni": [
            {
                "nome": "Estrazione caffè",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Fuoco medio-basso — l'acqua risale piano e attraversa il caffè senza surriscaldarsi: aromi senza amaro bruciato"},
                        {"fattore": "Togliere dal fuoco appena il caffè sale e inizia a gorgogliare — evita l'ultima acqua surriscaldata e la sovra-estrazione"},
                        {"fattore": "Acqua già calda nella caldaia — riduce il tempo sul fuoco e lo stress termico del macinato"},
                        {"fattore": "Caffè raso nel filtro senza pressare — l'acqua passa in modo uniforme, estrazione pari"},
                    ],
                    "rallentanti": [
                        {"fattore": "Fuoco alto — acqua troppo calda e risalita violenta: sovra-estrazione, amaro e note bruciate"},
                        {"fattore": "Lasciare la moka sul fuoco a fine risalita — l'ultima acqua surriscaldata porta amaro e odore di bruciato"},
                        {"fattore": "Caffè pressato nel filtro — sovrapressione e canalizzazione: estrazione irregolare"},
                    ],
                    "fonte": "estrazione a pressione moderata nella moka (controllo del fuoco, stop a fine risalita) — tecnica di caffetteria stabilita; da validare al banco",
                },
            },
            {
                "nome": "Macinatura e estrazione del caffè",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Macinatura medio-fine (da moka, non da espresso) — superficie di contatto giusta: estrae aroma senza intasare il filtro"},
                        {"fattore": "Macinatura uniforme — l'acqua attraversa il letto in modo omogeneo: estrazione pari"},
                        {"fattore": "Caffè macinato fresco — gli aromi volatili sono ancora presenti, non ancora ossidati"},
                    ],
                    "rallentanti": [
                        {"fattore": "Macinatura troppo fine — intasa il filtro, l'acqua fatica a passare: sovrapressione e amaro"},
                        {"fattore": "Macinatura troppo grossa — l'acqua passa veloce: caffè acquoso e sotto-estratto"},
                        {"fattore": "Macinato vecchio e stantio — ossidato: aromi persi, tazza piatta"},
                    ],
                    "fonte": "rapporto fra granulometria ed estrazione nella moka (medio-fine, uniforme, fresco) — tecnica di caffetteria stabilita; da validare al banco",
                },
            },
        ],
    },
    # Cappuccino latte art (caffetteria). Ricetta (live): espresso, latte intero
    # fresco; bersaglio 70°C. Fenomeno reale: "Temperatura e vaporizzazione del latte".
    "prot-cappuccino": {
        "fenomeni": [
            {
                "nome": "Temperatura e vaporizzazione del latte",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Fase di 'stretch' iniziale (punta della lancia appena sotto la superficie) — incorpora aria fine: microschiuma lucida"},
                        {"fattore": "Poi affondare la lancia per creare il vortice — le bolle grandi si rompono in microbolle: texture setosa da latte art"},
                        {"fattore": "Fermarsi a ~60-65°C (massimo ~70°C) — in questa finestra le proteine del latte stabilizzano la schiuma e il lattosio esprime dolcezza"},
                        {"fattore": "Latte intero fresco e freddo di partenza — più proteine e grassi a stabilizzare, più tempo utile per lavorare la schiuma"},
                    ],
                    "rallentanti": [
                        {"fattore": "Superare ~70°C — le sieroproteine denaturano oltre il punto utile: schiuma che collassa e gusto di latte cotto/bruciato"},
                        {"fattore": "Incorporare aria tardi (stretch dopo i ~40°C) — bolle grandi che non si richiudono: schiuma a 'bolloni', niente microschiuma"},
                        {"fattore": "Latte scremato o già caldo — meno proteine/grassi utili: schiuma instabile che si separa dal liquido"},
                        {"fattore": "Latte vecchio o ri-scaldato — proteine già stressate: schiuma che non tiene"},
                    ],
                    "fonte": "montatura del latte a microschiuma (stretch + vortice, finestra termica ~60-70°C, stabilizzazione proteica) per il cappuccino — tecnica di caffetteria stabilita; da validare al banco",
                },
            },
        ],
    },
    # Caffè filtro V60 (caffetteria). Ricetta (live): caffè macinato, acqua.
    # Fenomeni reali: "Estrazione" e "Capillarita".
    "prot-caffe-filtro-v60": {
        "fenomeni": [
            {
                "nome": "Estrazione",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Acqua ~92-96°C — estrae acidi e aromi desiderati senza amaro"},
                        {"fattore": "Pre-infusione (bloom): bagnare il macinato e attendere ~30s — libera la CO2 della tostatura che altrimenti respinge l'acqua e rende irregolare l'estrazione"},
                        {"fattore": "Versate lente e circolari — bagnano tutto il letto in modo uniforme: estrazione pari"},
                        {"fattore": "Rapporto acqua:caffè costante (~15-16:1) — concentrazione equilibrata e ripetibile"},
                    ],
                    "rallentanti": [
                        {"fattore": "Acqua bollente (100°C) — sovra-estrae: amaro e astringenza"},
                        {"fattore": "Acqua troppo fredda (sotto ~88°C) — sotto-estrae: acido, acquoso, piatto"},
                        {"fattore": "Versata unica e veloce al centro — scava un canale: parte del caffè non estratto, parte sovra-estratta"},
                        {"fattore": "Letto non livellato — canalizzazione: estrazione irregolare"},
                    ],
                    "fonte": "estrazione per infusione filtrata nel V60 (temperatura, bloom, versate uniformi, rapporto costante) — tecnica di caffetteria stabilita; da validare al banco",
                },
            },
            {
                "nome": "Capillarita",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Filtro di carta bagnato e fatto aderire prima dell'uso — toglie il gusto di carta e crea il contatto per un drenaggio uniforme"},
                        {"fattore": "Macinatura media (da filtro) — i pori fra le particelle fanno scendere l'acqua a velocità giusta per gravità"},
                        {"fattore": "Cono V60 con nervature e grande foro — l'acqua drena senza ristagnare: è la capillarità del letto a governare il flusso, non il fondo del cono"},
                    ],
                    "rallentanti": [
                        {"fattore": "Macinatura troppo fine — il letto si compatta, l'acqua ristagna e drena a fatica: sovra-estrazione"},
                        {"fattore": "Macinatura troppo grossa — l'acqua scende troppo in fretta: sotto-estrazione"},
                        {"fattore": "Filtro non bagnato o mal aderente — drenaggio irregolare e by-pass d'acqua lungo le pareti"},
                    ],
                    "fonte": "drenaggio per capillarità e gravità nel letto del V60 (granulometria, filtro bagnato, geometria del cono) — tecnica di caffetteria stabilita; da validare al banco",
                },
            },
        ],
    },
    # Sugo di pomodoro classico (cucina). Ricetta (live): pomodori pelati, cipolla,
    # olio EVO, basilico, sale. Fenomeno reale: "Umami e esaltazione dei sapori".
    "prot-sugo-di-pomodoro-classico": {
        "fenomeni": [
            {
                "nome": "Umami e esaltazione dei sapori",
                "causalita": {
                    "acceleranti": [
                        {"fattore": "Glutammato naturale del pomodoro (soprattutto nei pelati maturi) — è la base umami del sugo"},
                        {"fattore": "Sale nella giusta misura — non aggiunge umami ma lo rende percepibile e amplifica la rotondità: senza sale l'umami resta muto"},
                        {"fattore": "Cottura lenta che concentra — l'acqua evapora e glutammati e zuccheri si concentrano: sapore più pieno"},
                        {"fattore": "Cipolla/soffritto e un filo di dolcezza — bilanciano l'acidità e allungano il gusto"},
                        {"fattore": "Basilico a fine cottura — aromi freschi che non si volatilizzano"},
                    ],
                    "rallentanti": [
                        {"fattore": "Poco sale — l'umami del pomodoro resta impercepibile: sugo piatto nonostante gli ingredienti giusti"},
                        {"fattore": "Troppa acqua o cottura corta — diluisce glutammati e zuccheri: acquoso e acido"},
                        {"fattore": "Pomodori acerbi o conserva povera — poco glutammato di partenza: manca la base umami"},
                        {"fattore": "Cottura troppo lunga e violenta — caramellizza o brucia e vira all'amaro, coprendo l'umami"},
                        {"fattore": "Basilico bollito a lungo — perde gli aromi e può virare all'amaro"},
                    ],
                    "fonte": "umami da glutammato del pomodoro, esaltato dal sale e concentrato in cottura, nel sugo classico — principio gastronomico stabilito; da validare al banco",
                },
            },
        ],
    },
}


def applica_causalita(dd, spec, esegui):
    """Funzione PURA (testabile senza DB). Per ogni fenomeno in spec['fenomeni'],
    trova il fenomeno di 'dd' che combacia per nome e vi scrive la causalità
    (o la RIMUOVE se causalita è None -> torna al generico ereditato).
    Normalizza un fenomeno-stringa in dict. Ritorna (dd_nuovo, info)."""
    fen_specs = spec.get("fenomeni") or []
    fen_list = list(dd.get("fenomeni") or [])
    dettagli = []
    cambiato = False
    for fs in fen_specs:
        target = (fs.get("nome") or "").strip().lower()
        nuova_caus = fs.get("causalita")  # può essere None = revert
        trovato = False
        for i, f in enumerate(fen_list):
            nome_f = (f if isinstance(f, str) else f.get("nome", "")).strip().lower()
            if nome_f != target:
                continue
            trovato = True
            if isinstance(f, str):
                f = {"nome": f}
            else:
                f = dict(f)
            prima = bool(f.get("causalita"))
            if esegui:
                if nuova_caus is None:
                    f.pop("causalita", None)           # revert al generico ereditato
                else:
                    f["causalita"] = nuova_caus
                cambiato = True
            fen_list[i] = f
            dettagli.append({"fenomeno": fs.get("nome"),
                             "azione": ("revert" if nuova_caus is None else "scrittura") + ("" if esegui else " (dry-run)"),
                             "aveva_causalita_propria_prima": prima})
            break
        if not trovato:
            dettagli.append({"fenomeno": fs.get("nome"), "azione": "fenomeno-assente",
                             "fenomeni_presenti": [(x.get("nome") if isinstance(x, dict) else x) for x in fen_list]})
    if cambiato:
        dd = dict(dd)
        dd["fenomeni"] = fen_list
    return dd, {"dettagli": dettagli, "modificato": cambiato}


@bp_causalita.route("/admin/causalita-specifica", methods=["GET"])
def causalita_specifica():
    """Scrive/reverte la causalità sui protocolli dell'allowlist.
    DRY-RUN di default; scrive con &esegui=1. Auth: header X-Admin-Secret o ?s=."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    esegui = request.args.get("esegui") == "1"
    report = []
    with connessione() as conn:
        cur = conn.cursor()
        for pid, spec in CAUSALITA_SPECIFICA.items():
            cur.execute("SELECT data FROM nodes WHERE id=%s", (pid,))
            row = cur.fetchone()
            if not row:
                report.append({"id": pid, "stato": "non trovato"})
                continue
            dd = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            nuovo, info = applica_causalita(dd, spec, esegui)
            info["id"] = pid
            if esegui and info.get("modificato"):
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(nuovo, ensure_ascii=False), pid))
            report.append(info)
        # IMPORTANTE: db.connessione() fa ROLLBACK in uscita — il commit è
        # responsabilità del chiamante, va fatto QUI o la scrittura si perde.
        if esegui:
            conn.commit()
        cur.close()
    return jsonify({"esegui": esegui, "n_protocolli": len(CAUSALITA_SPECIFICA), "report": report})
