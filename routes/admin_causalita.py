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
