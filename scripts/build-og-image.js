#!/usr/bin/env node
/**
 * Builds landing/public/og.png, the 1200x630 card that every link unfurl of
 * acecollege.app shows: iMessage, Slack, Discord, X, LinkedIn, WhatsApp.
 *
 *     node scripts/build-og-image.js
 *
 * WHY A SCRIPT AND NOT A PNG IN THE REPO
 * The card is the brand at its smallest useful size, and the brand moves. A
 * checked-in PNG drifts silently: the mark changes, the accent changes, the
 * proof numbers change, and the card keeps showing the old ones for months
 * because nobody opens a binary to check. Regenerating from this file is a
 * one-line diff that shows what changed and why.
 *
 * WHY 1200x630 AND NOT THE HERO POSTER
 * poster.jpg is 1920x1080 (16:9). Unfurlers crop to roughly 1.91:1, so 16:9
 * loses about 7% off the top and bottom, which is exactly where a centred
 * composition keeps its subject. 1200x630 IS 1.91:1, so nothing is cropped.
 *
 * BRAND CONSTRAINTS THIS FILE IS BOUND BY (brand/BRAND.md)
 *  - The mark is the locked one: lowercase `a` leaning -11deg, LEVEL period.
 *    The rotate() wraps only the `a`, never the dot.
 *  - Emerald #00875A appears exactly once, and it is the period. There is one
 *    emerald element in the markup below. Adding a second breaks the whole
 *    conditioning argument in brand/playbook.html section 07.
 *  - No em dashes. House rule, and it applies to card copy too.
 *
 * The fonts are loaded from landing/public/type/fonts over file://, so this
 * has to run from a checkout, not from a published build.
 */

const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

const REPO = path.resolve(__dirname, '..');
const FONTS = path.join(REPO, 'landing', 'public', 'type', 'fonts');
const OUT = path.join(REPO, 'landing', 'public', 'og.png');

/* Playwright's bundled Chromium, which is what the container has. A local
 * machine will more likely have a system Chrome, so try a list and report
 * the whole list if none of them exist rather than a bare ENOENT. */
const CANDIDATES = [
  process.env.CHROME_PATH,
  '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
].filter(Boolean);

function findChrome() {
  const hit = CANDIDATES.find((p) => fs.existsSync(p));
  if (hit) return hit;
  /* The glob is for a Playwright install whose build number has moved on
   * from the pin above; the pin is only a fast path. */
  const pw = '/opt/pw-browsers';
  if (fs.existsSync(pw)) {
    for (const d of fs.readdirSync(pw)) {
      const p = path.join(pw, d, 'chrome-linux', 'chrome');
      if (d.startsWith('chromium-') && fs.existsSync(p)) return p;
    }
  }
  throw new Error(
    'No Chrome or Chromium found. Set CHROME_PATH, or install one of:\n  ' +
      CANDIDATES.join('\n  ')
  );
}

const font = (f) => `url('file://${path.join(FONTS, f)}') format('woff2')`;

const html = `<!doctype html>
<html><head><meta charset="utf-8"><style>
@font-face{font-family:Recia;src:${font('recia-700.woff2')};font-weight:700}
@font-face{font-family:Switzer;src:${font('switzer-400.woff2')};font-weight:400}
@font-face{font-family:Switzer;src:${font('switzer-500.woff2')};font-weight:500}
/* Both Tabular weights, and every consumer names one of them explicitly.
 * Headless Chromium here has no system monospace to fall back on, so a rule
 * that asks for a weight with no @font-face renders as nothing at all: the
 * first cut of this card silently lost its whole bottom row that way. */
@font-face{font-family:Tabular;src:${font('tabular-400.woff2')};font-weight:400}
@font-face{font-family:Tabular;src:${font('tabular-600.woff2')};font-weight:600}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1200px;height:630px}
body{
  background:#FBF6EC; color:#14120E;
  font-family:Switzer,system-ui,sans-serif;
  display:flex; flex-direction:column; justify-content:space-between;
  padding:76px 88px 64px;
  -webkit-font-smoothing:antialiased;
}

/* The card is a fixed 630px column: mark row, message, footer rule.
 *
 * A NOTE ON THE FOOTER ROW, because it went missing for four rebuilds and
 * the symptom pointed everywhere except the cause. It rendered its
 * border-top and no text: spans laid out at the correct widths, zero glyphs.
 * It was not flex-shrink, not a missing @font-face, not font-display, and
 * not this CSS at all. Chrome's --screenshot flag captures at a viewport
 * ~75px SHORTER than --window-size, and text below that line is never
 * painted while backgrounds and borders still are. Anything in the bottom
 * ~12% of the card silently disappeared.
 *
 * The renderer below now sets an exact 1200x630 viewport over the DevTools
 * protocol, so the whole card is really in frame and this layout is free to
 * be the obvious one. Do not go back to the --screenshot flag. */
body>*{flex:0 0 auto}

/* The hairline is the landing page's own rule weight and colour. */
.top{display:flex;align-items:center;gap:26px}
.mark{height:52px;width:auto;color:#14120E}
.kicker{
  font-family:Tabular,ui-monospace,monospace;font-weight:600;font-size:15px;
  letter-spacing:.15em;text-transform:uppercase;color:#7C766C;
  padding-left:26px;border-left:1.5px solid #DED7C6;
}
h1{
  font-family:Recia,Georgia,serif;font-weight:700;
  font-size:86px;line-height:1.04;letter-spacing:-.022em;
  max-width:15ch;
}
.sub{font-size:26px;line-height:1.45;color:#4E4940;max-width:34ch;margin-top:24px}
.base{
  display:flex;justify-content:space-between;align-items:baseline;
  padding-top:26px;border-top:1.5px solid #DED7C6;
  font-family:Tabular,ui-monospace,monospace;font-weight:400;font-size:16px;
  letter-spacing:.11em;text-transform:uppercase;line-height:1.2;color:#7C766C;
}
</style></head><body>

  <div class="top">
    <!-- The locked mark. rotate() wraps the lowercase a only; the period stays level. -->
    <svg class="mark" viewBox="-54 -44 332.93 112" fill="none">
      <g transform="rotate(-11 5 12)">
        <circle cx="0" cy="12" r="31" stroke="currentColor" stroke-width="22"/>
        <rect x="30" y="-32" width="22" height="88" rx="11" fill="currentColor"/>
        <path d="M 123.93 -11.75 A 31 31 0 1 0 123.93 35.75" stroke="currentColor" stroke-width="22" stroke-linecap="round"/>
        <path d="M 211.93 12 A 31 31 0 1 0 186.31 42.53" stroke="currentColor" stroke-width="22" stroke-linecap="round"/>
        <rect x="150.93" y="1" width="72" height="22" rx="11" fill="currentColor"/>
      </g>
      <!-- the one emerald element on the card -->
      <circle cx="248.93" cy="38" r="18" fill="#00875A"/>
    </svg>
    <span class="kicker">for students at Penn State</span>
  </div>

  <div>
    <h1>Ask your college anything.</h1>
    <p class="sub">Courses, deadlines, money, the offices nobody explains.
      Cited to the page, and awake at 2am.</p>
  </div>

  <div class="base">
    <span>749 majors · 9,439 courses</span>
    <span>acecollege.app</span>
  </div>

</body></html>`;

const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'ace-og-')), 'og.html');
fs.writeFileSync(tmp, html);

/* ── Rendering ───────────────────────────────────────────────────────────
 * Chrome is driven over the DevTools protocol rather than with the
 * --screenshot flag, for the reason recorded in the CSS above: that flag
 * captures at a viewport meaningfully shorter than --window-size and drops
 * any text below the fold without saying so.
 *
 * Emulation.setDeviceMetricsOverride sets the frame to exactly 1200x630, so
 * what is captured is the whole card and nothing else. Node 22 ships a
 * global WebSocket, which is why this needs no dependency.
 * ──────────────────────────────────────────────────────────────────────── */

const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ace-og-profile-'));

const chrome = spawn(findChrome(), [
  '--headless',
  '--no-sandbox',
  '--disable-gpu',
  '--hide-scrollbars',
  '--remote-debugging-port=0',
  `--user-data-dir=${userDataDir}`,
  'about:blank',
]);

/* Chrome keeps writing into its profile for a moment after kill(), so the
 * removal races it and ENOTEMPTYs. Retries cover the race, and a leftover
 * temp directory is never worth failing a build over. */
const cleanup = () => {
  try { chrome.kill(); } catch {}
  for (const dir of [path.dirname(tmp), userDataDir]) {
    try {
      fs.rmSync(dir, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
    } catch {}
  }
};

/* Chrome prints "DevTools listening on ws://..." to stderr once, and the
 * port is 0 above so it is only knowable by reading it back. */
function devtoolsUrl() {
  return new Promise((resolve, reject) => {
    let buf = '';
    const timer = setTimeout(
      () => reject(new Error('Chrome never announced a DevTools endpoint.\n' + buf)),
      20000
    );
    chrome.stderr.on('data', (d) => {
      buf += d;
      const m = buf.match(/ws:\/\/[^\s]+/);
      if (m) { clearTimeout(timer); resolve(m[0]); }
    });
    chrome.on('exit', (code) => {
      clearTimeout(timer);
      reject(new Error(`Chrome exited with ${code} before starting.\n` + buf));
    });
  });
}

/* A minimal CDP client: send({method, params}) resolves with the result for
 * that id, and `on` dispatches the events we wait for. */
function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    let id = 0;
    const pending = new Map();
    const events = new Map();

    ws.addEventListener('message', (e) => {
      const msg = JSON.parse(e.data);
      if (msg.id !== undefined) {
        const p = pending.get(msg.id);
        pending.delete(msg.id);
        if (!p) return;
        msg.error ? p.reject(new Error(msg.error.message)) : p.resolve(msg.result);
      } else if (events.has(msg.method)) {
        events.get(msg.method)();
        events.delete(msg.method);
      }
    });
    ws.addEventListener('error', () => reject(new Error('DevTools socket failed')));
    ws.addEventListener('open', () =>
      resolve({
        send: (method, params = {}, sessionId) =>
          new Promise((res, rej) => {
            const n = ++id;
            pending.set(n, { resolve: res, reject: rej });
            ws.send(JSON.stringify({ id: n, method, params, sessionId }));
          }),
        once: (method) => new Promise((res) => events.set(method, res)),
        close: () => ws.close(),
      })
    );
  });
}

(async () => {
  const cdp = await connect(await devtoolsUrl());

  /* Attach to a fresh tab. flatten:true multiplexes the page session down
   * the same socket, so there is only ever one connection to manage. */
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  const page = (method, params) => cdp.send(method, params, sessionId);

  await page('Page.enable');
  await page('Emulation.setDeviceMetricsOverride', {
    width: 1200,
    height: 630,
    deviceScaleFactor: 1,
    mobile: false,
  });

  const loaded = cdp.once('Page.loadEventFired');
  await page('Page.navigate', { url: `file://${tmp}` });
  await loaded;

  /* The faces are local files, but "local" is not "already decoded". Waiting
   * on document.fonts.ready is what makes the output byte-stable instead of
   * dependent on how warm the disk cache happened to be. */
  await page('Runtime.evaluate', {
    expression: 'document.fonts.ready.then(() => true)',
    awaitPromise: true,
  });

  const { data } = await page('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: false,
  });

  fs.writeFileSync(OUT, Buffer.from(data, 'base64'));
  cdp.close();
  cleanup();

  const { size } = fs.statSync(OUT);
  console.log(`wrote ${path.relative(REPO, OUT)} (${(size / 1024).toFixed(1)} kB)`);
  /* X drops a card over 5 MB and Slack gets slow well before that. Nothing
   * this flat should come close, so a breach means the design grew a photo. */
  if (size > 1_000_000) {
    console.warn('WARNING: over 1 MB. Unfurlers are unhappy above ~5 MB; check the design.');
  }
  /* And the failure this file exists to prevent: a card whose bottom third
   * did not paint compresses far smaller than a complete one. */
  if (size < 20_000) {
    console.warn('WARNING: suspiciously small. Open the PNG and check the footer row is there.');
  }
})().catch((err) => {
  cleanup();
  console.error(err.message);
  process.exit(1);
});
