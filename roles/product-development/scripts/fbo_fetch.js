// Download Pentair's brochures and sell sheets that pentair.com embeds as FlippingBook publications.
//   node scripts/fbo_fetch.js        -> data/raw/pentair/docs/<sha>-fbo-<id>.pdf + data/work/pentair/web/fbo_files.json
// The viewer's own Download button hands out a short-lived signed link to the publisher's original PDF, so the
// file is Pentair's own (robots.txt on online.flippingbook.com allows everything; one publication at a time,
// a pause between them). Files already on disk are skipped.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = path.resolve(__dirname, '..');
const MEDIA = path.join(ROOT, 'data/work/pentair/web/media.json');
const DOCS = path.join(ROOT, 'data/raw/pentair/docs');
const OUT = path.join(ROOT, 'data/work/pentair/web/fbo_files.json');

function docPath(url) {  // mirrors web_media_fetch.doc_path
  const id = url.match(/view\/(\d+)/)[1];
  return path.join(DOCS, crypto.createHash('sha1').update(url).digest('hex').slice(0, 10) + '-fbo-' + id + '.pdf');
}

(async () => {
  const pages = JSON.parse(fs.readFileSync(MEDIA, 'utf8'));
  const urls = [...new Set(pages.flatMap(p => p.documents.filter(d => d.host === 'flippingbook').map(d => d.url)))].sort();
  const done = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : {};
  fs.mkdirSync(DOCS, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ acceptDownloads: true, viewport: { width: 1400, height: 900 } });
  let ok = 0, fail = 0;
  for (const url of urls) {
    const dest = docPath(url);
    if (fs.existsSync(dest)) { ok++; continue; }
    const page = await ctx.newPage();
    try {
      await page.goto(url, { waitUntil: 'load', timeout: 60000 });
      await page.waitForTimeout(8000);
      const title = await page.title();
      const btn = await page.$('[title="Download"], [aria-label="Download"]');
      if (!btn) throw new Error('no Download button (download disabled?)');
      const dlp = page.waitForEvent('download', { timeout: 60000 });
      await btn.click({ force: true });
      await page.waitForTimeout(2500);
      const clicked = await page.evaluate(() => {
        const el = [...document.querySelectorAll('.full-button-text-block, [class*="full-button"]')][0];
        if (el) { el.click(); return el.className; } return null;
      });
      if (!clicked) throw new Error('no Full Flipbook item');
      const d = await dlp;
      await d.saveAs(dest);
      const st = fs.statSync(dest);
      const head = fs.readFileSync(dest).subarray(0, 5).toString();
      if (head !== '%PDF-') { fs.unlinkSync(dest); throw new Error('not a PDF: ' + head); }
      done[url] = { file: path.relative(ROOT, dest), filename: d.suggestedFilename(), bytes: st.size, title: title.replace(/\s+/g, ' ').trim() };
      fs.writeFileSync(OUT, JSON.stringify(done, null, 1));
      console.log('ok', url, d.suggestedFilename(), st.size);
      ok++;
    } catch (e) {
      console.log('fail', url, e.message.split('\n')[0]);
      done[url] = { error: e.message.split('\n')[0] };
      fs.writeFileSync(OUT, JSON.stringify(done, null, 1));
      fail++;
    }
    await page.close();
    await new Promise(r => setTimeout(r, 2000));
  }
  await browser.close();
  console.log(`${ok} of ${urls.length} publications on disk, ${fail} failed`);
})();
