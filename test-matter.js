// ============================================================
// TEST AUTOMATICO MATTER BENCH — versione completa
// Uso: node test-matter.js
// Prima volta: npm install playwright && npx playwright install chromium
// Testa: performance, ogni sezione, errori, sovrapposizioni, testi illeggibili,
//        elementi che escono dai bordi, asterischi residui, immagini rotte.
// ============================================================

const { chromium } = require('playwright');

const URL = 'https://web-production-79457.up.railway.app/app';
const SOGLIA_LENTO = 2000;   // ms
const SOGLIA_DOM = 5000;     // px

const problemi = [];
const ok = [];

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2
  });
  const page = await ctx.newPage();

  const erroriConsole = [];
  const erroriRete = [];
  page.on('console', m => { if (m.type() === 'error') erroriConsole.push(m.text().slice(0, 80)); });
  page.on('response', r => {
    if (r.status() >= 400) {
      const u = r.url();
      if (u.includes('/static/') || u.includes('.jpg') || u.includes('.png') || u.includes('pexels')) {
        erroriRete.push(`${r.status()} ${u.split('/').pop().slice(0,40)}`);
      }
    }
  });

  // ---- helper: controlla testi illeggibili (contrasto basso) ----
  async function testiIlleggibili() {
    return await page.evaluate(() => {
      const out = [];
      const els = document.querySelectorAll('p, span, div, a, h1, h2, h3, label, button, li');
      for (const el of els) {
        if (el.children.length > 0 || !el.innerText || !el.innerText.trim()) continue;
        const s = getComputedStyle(el);
        const fg = s.color.match(/\d+/g), bgc = s.backgroundColor.match(/\d+/g);
        if (!fg) continue;
        // sfondo effettivo: risalgo i parent se trasparente
        let bg = bgc; let p = el;
        while ((!bg || bg[3] === '0') && p.parentElement) { p = p.parentElement; const ps = getComputedStyle(p).backgroundColor.match(/\d+/g); if (ps && ps[3] !== '0') bg = ps; }
        if (!bg) continue;
        const lum = c => (0.299*c[0] + 0.587*c[1] + 0.114*c[2]);
        const diff = Math.abs(lum(fg) - lum(bg));
        if (diff < 60 && el.innerText.length > 2) out.push(el.innerText.slice(0, 25));
      }
      return [...new Set(out)].slice(0, 8);
    });
  }

  // ---- helper: elementi che escono dai bordi (overflow orizzontale) ----
  async function elementiFuoriBordo() {
    return await page.evaluate(() => {
      const out = [];
      const vw = window.innerWidth;
      const els = document.querySelectorAll('*');
      for (const el of els) {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.right > vw + 5 && r.left >= 0 && el.innerText && el.innerText.trim()) {
          out.push((el.className || el.tagName).toString().slice(0, 30) + ' ("' + el.innerText.slice(0,15) + '")');
        }
      }
      return [...new Set(out)].slice(0, 6);
    });
  }

  // ---- helper: asterischi/markdown residui a schermo ----
  async function asterischiVisibili() {
    const txt = await page.evaluate(() => document.body.innerText);
    const n = (txt.match(/\*\*/g) || []).length + (txt.match(/^#{1,6}\s/gm) || []).length;
    return n;
  }

  async function apriBanner() {
    for (const t of ['Accetto', 'Accetta', 'Salta']) { try { await page.click(`text=${t}`, { timeout: 1200 }); await page.waitForTimeout(300); } catch {} }
  }

  // ========== 1. BOOT ==========
  let t0 = Date.now();
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 40000 });
  const boot = ((Date.now() - t0) / 1000).toFixed(1);
  if (boot > 3) problemi.push(`Boot lento: ${boot}s (dovrebbe <3s)`); else ok.push(`Boot ${boot}s`);
  await page.waitForTimeout(3000);

  // ========== 2. SOVRAPPOSIZIONE COOKIE (prima di accettare) ==========
  const sovrap = await page.evaluate(() => {
    const cookie = document.querySelector('#cookie-banner, [class*=cookie]');
    if (!cookie) return null;
    const cb = cookie.getBoundingClientRect();
    for (const b of document.querySelectorAll('button, .safe-bottom, [class*=action]')) {
      const bb = b.getBoundingClientRect();
      if (bb.width && cb.width && bb.height && !(bb.right < cb.left || bb.left > cb.right || bb.bottom < cb.top || bb.top > cb.bottom))
        return b.innerText.slice(0, 20) || b.className.slice(0,20);
    }
    return null;
  });
  if (sovrap) problemi.push(`Cookie banner copre: "${sovrap}"`); else ok.push('Cookie banner non copre nulla');
  await apriBanner();

  // ========== 3. HOME ==========
  let ill = await testiIlleggibili();
  if (ill.length) problemi.push(`HOME testi illeggibili: ${ill.join(', ')}`);
  let fb = await elementiFuoriBordo();
  if (fb.length) problemi.push(`HOME elementi fuori bordo: ${fb.join('; ')}`);
  let ast = await asterischiVisibili();
  if (ast > 0) problemi.push(`HOME asterischi/markdown visibili: ${ast}`);

  // ========== 4. ATLANTE + FENOMENO ==========
  try {
    await page.evaluate(() => switchTab('mappa')); await page.waitForTimeout(2000);
    t0 = Date.now();
    await page.tap('text=Fermentazione'); await page.waitForTimeout(2500);
    const latF = ((Date.now() - t0) / 1000).toFixed(1);
    if (latF > SOGLIA_LENTO/1000) problemi.push(`Apertura fenomeno lenta: ${latF}s`); else ok.push(`Apertura fenomeno ${latF}s`);
    const domH = await page.evaluate(() => document.body.scrollHeight);
    if (domH > SOGLIA_DOM) problemi.push(`Scheda fenomeno troppo lunga: ${domH}px`); else ok.push(`Scheda fenomeno ${domH}px`);
    ill = await testiIlleggibili();
    if (ill.length) problemi.push(`FENOMENO testi illeggibili: ${ill.join(', ')}`);
    fb = await elementiFuoriBordo();
    if (fb.length) problemi.push(`FENOMENO fuori bordo: ${fb.join('; ')}`);
  } catch (e) { problemi.push('ATLANTE/fenomeno: errore apertura'); }

  // ========== 5. CHAT ==========
  try {
    await page.evaluate(() => switchTab('chiedi')); await page.waitForTimeout(2500);
    ill = await testiIlleggibili();
    if (ill.length) problemi.push(`CHAT testi illeggibili: ${ill.join(', ')}`);
    fb = await elementiFuoriBordo();
    if (fb.length) problemi.push(`CHAT fuori bordo: ${fb.join('; ')}`);
  } catch (e) { problemi.push('CHAT: errore apertura'); }

  // ========== 6. QUADERNO (le pill) ==========
  try {
    await page.evaluate(() => switchTab('quaderno')); await page.waitForTimeout(2000);
    fb = await elementiFuoriBordo();
    if (fb.length) problemi.push(`QUADERNO fuori bordo (pill?): ${fb.join('; ')}`);
    // scroll orizzontale presente?
    const scrollH = await page.evaluate(() => {
      const t = document.querySelector('[class*=tab], [class*=pill], [class*=sub]');
      return t ? (t.scrollWidth > t.clientWidth + 10) : false;
    });
    if (scrollH) problemi.push('QUADERNO: le pill hanno scroll orizzontale (escono da schermo)');
    ill = await testiIlleggibili();
    if (ill.length) problemi.push(`QUADERNO testi illeggibili: ${ill.join(', ')}`);
  } catch (e) { problemi.push('QUADERNO: errore apertura'); }

  // ========== 7. RICETTARIO (immagini rotte) ==========
  try {
    await page.evaluate(() => switchTab('vetrina')).catch(()=>{});
    await page.waitForTimeout(2000);
    const imgRotte = await page.evaluate(() => {
      let rotte = 0;
      for (const img of document.querySelectorAll('img')) {
        if (img.complete && img.naturalWidth === 0) rotte++;
      }
      return rotte;
    });
    if (imgRotte > 0) problemi.push(`RICETTARIO: ${imgRotte} immagini rotte`);
  } catch (e) {}

  // ========== REPORT ==========
  console.log('\n╔════════════════════════════════════════════╗');
  console.log('║   MATTER BENCH — REPORT TEST COMPLETO       ║');
  console.log('╠════════════════════════════════════════════╣');
  console.log(`║ Errori console JS: ${erroriConsole.length || 'Zero'}`.padEnd(45) + '║');
  console.log(`║ Errori rete/asset: ${erroriRete.length || 'Zero'}`.padEnd(45) + '║');
  console.log('╠════════════════════════════════════════════╣');
  if (problemi.length === 0) {
    console.log('║ ✓ NESSUN PROBLEMA TROVATO                   ║');
  } else {
    console.log(`║ ⚠ ${problemi.length} PROBLEMI TROVATI:`.padEnd(45) + '║');
    console.log('╚════════════════════════════════════════════╝');
    problemi.forEach((p, i) => console.log(`  ${i+1}. ${p}`));
    console.log('');
  }
  if (problemi.length === 0) console.log('╚════════════════════════════════════════════╝');
  if (ok.length) { console.log('\n✓ OK: ' + ok.join(' · ')); }
  if (erroriConsole.length) { console.log('\nErrori console:'); erroriConsole.forEach(e => console.log('  - ' + e)); }
  if (erroriRete.length) { console.log('\nErrori rete:'); erroriRete.slice(0,10).forEach(e => console.log('  - ' + e)); }

  await browser.close();
})();
