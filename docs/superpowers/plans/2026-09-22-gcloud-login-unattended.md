# Unattended gcloud login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Claude (and the user) refresh gcloud CLI and Application Default Credentials for the ista Google accounts with one command and no manual clicks (admin: one security-key tap), and give Claude a skill that says which login fixes which failure.

**Architecture:** `gcloud-login` moves from a zsh function to a bash script in `~/.local/bin`. It runs `gcloud auth login` with `BROWSER` pointed at a hook that only records the OAuth URL, starts a plain Chromium (no Google API keys, so no enterprise profile interception) on a per-account profile with remote debugging, and a zero-dependency Node driver opens the URL there and walks the Google pages over the DevTools protocol until gcloud's callback fires. The admin account's Google password comes from 1Password through `op-agent`, a small daemon that keeps one 1Password CLI authorization alive in its own pseudo-terminal so later runs never prompt. Two skills in `~/.agents/skills` document when to call it and how it works.

**Tech Stack:** bash, Node 22 (global `WebSocket`, `node:test`, `node:util.parseArgs`), Chrome DevTools Protocol, Chromium snapshot via `@puppeteer/browsers`, 1Password CLI (`op`), gcloud, chezmoi.

**Spec:** [2026-09-22-gcloud-login-findings.md](2026-09-22-gcloud-login-findings.md) holds every observed page, selector and constraint; the "Design" section below is the distilled contract. Executors read both.

## Global Constraints

- Shell scripts: `#!/usr/bin/env bash`, no extension, executable, Google Shell Style header with Purpose and Usage, `set -euo pipefail`, named parameters, colors via `tput` only (see `~/.config/agents/rules/bash.md`).
- Never a `.tmpl` where a runtime check works. Context check: `[[ "${DOTFILES_CONTEXT:-}" == ista ]]`.
- `exact_bin/`, `exact_conf.d/` remove files deleted from the repo on apply; always edit source state under `home/`.
- No `Co-Authored-By` or AI attribution in commits. Never commit on `main`; the branch is `feat/gcloud-login-unattended`.
- Node code: CommonJS, no dependencies beyond the Node 22 standard library. Tests use `node:test`, follow `~/.config/agents/rules/testing.md` (subject named after the script, nesting by context, "on …" phrasing, result stored before assertion, helpers last).
- Passwords travel via bash variables, FIFOs with mode 0600 in a 0700 directory, and stdin only: never argv, never the clipboard, never a regular file.
- `BROWSER` must not contain whitespace (Python splits it); only the hook's bare name goes there.
- Identity policy: ADC is always the normal account; `--admin` only affects the CLI credential.
- The admin account requires a security-key tap on every login (Workspace policy); the script waits for it and says so. The Microsoft one-time code and key on the **first** run per browser profile are done by the user once.

---

## Design

### Accounts and secrets

| Role | Google email | Authenticates via | Password source |
|---|---|---|---|
| normal | `bjoern.kahlert@ista-express.de` | Microsoft Entra SAML (ista account), silent once "Stay signed in" was accepted | none needed in steady state |
| admin | `bjoern.kahlert.admin@ista-express.de` | Google password page + security key on every login | `op://Employee/p44thhnd5ylh6zrm6etwozs63a/password` ("Google (Admin)", referenced by ID because the title has parentheses) |

### Verified facts the design relies on (details in the findings file)

- gcloud waits for the `BROWSER` command; the hook records the URL and exits. `gcloud auth login <acct> --quiet` and `gcloud auth application-default login <acct> --quiet` exit without a browser when a valid credential exists.
- Managed Google Chrome and Chrome for Testing force a managed profile sign-in, after which remote debugging is disabled by policy. Plain Chromium has no API keys and is immune. Chromium build `1702741` (156.0.8070.0) was tested.
- `--remote-debugging-port=0` writes `<user-data-dir>/DevToolsActivePort`. `--no-startup-window` avoids a placeholder tab.
- Page states and selectors: see "Confirmed selectors" in the findings file. Visibility is `el.offsetParent !== null`.
- The callback lands on `docs.cloud.google.com/sdk/auth_success` within a second.
- 1Password CLI authorization is per process tree; a `setsid` daemon in its own pty keeps one authorization for up to 12 h with a keep-alive every 5 min.

### Files

| Path (source) | Target | Responsibility |
|---|---|---|
| `home/dot_local/exact_bin/executable_gcloud-login` | `~/.local/bin/gcloud-login` | Orchestrator: args, `--status`, Chromium install and lifecycle, gcloud, driver, admin password via op-agent, cleanup |
| `home/dot_local/exact_bin/executable_gcloud-login-browser` | `~/.local/bin/gcloud-login-browser` | `$BROWSER` hook: writes the URL to `$GCLOUD_LOGIN_URL_FILE` and exits |
| `home/dot_local/exact_bin/executable_gcloud-login-driver` | `~/.local/bin/gcloud-login-driver` | Node: opens the URL in the debug Chromium, drives identifier / chooser / password / confirm / consent, waits through Microsoft and security-key pages, closes its tab on the callback |
| `home/dot_local/exact_bin/executable_op-agent` | `~/.local/bin/op-agent` | 1Password read daemon + client (`start`, `stop`, `status`, `read <ref>`) |
| `tests/gcloud-login-driver.test.js` | not applied (ignored) | `node:test` suite against fixture pages in headless Chromium |
| `home/dot_agents/skills/gcloud-auth/SKILL.md` | `~/.agents/skills/gcloud-auth/SKILL.md` | Skill 1: which login fixes which failure, identity policy |
| `home/dot_agents/skills/gcloud-login-automation/SKILL.md` | `~/.agents/skills/gcloud-login-automation/SKILL.md` | Skill 2: internals, failure modes, how to debug |
| `home/private_dot_claude/skills/symlink_gcloud-auth` | `~/.claude/skills/gcloud-auth` | Symlink into `~/.agents/skills`, same as grill-me |
| `home/private_dot_claude/skills/symlink_gcloud-login-automation` | `~/.claude/skills/gcloud-login-automation` | Same |
| `home/.chezmoiignore` | — | Ignore `tests/`; skip the two skills outside the ista context |
| `home/private_dot_config/zsh/exact_conf.d/exact_ista/10-gcloud.zsh` | `~/.config/zsh/conf.d/ista/10-gcloud.zsh` | **Deleted** (held only the old function) |

### Paths on the machine

| Purpose | Path |
|---|---|
| Chromium download root | `~/.cache/gcloud-login` (`chromium/<platform>-<build>/chrome-mac/Chromium.app/Contents/MacOS/Chromium`) |
| Browser profiles | `~/Library/Application Support/gcloud-login/normal`, `…/admin` |
| op-agent state | `~/Library/Application Support/op-agent/` (0700): `req` FIFO, `pid`, `agent.log` |

### Process interfaces

```
gcloud-login-driver --port-file <path> --url-file <path> --email <email> [--timeout <seconds>]
  stdin: password (optional, may be empty or closed)
  exit 0: callback reached, tab closed
  exit 1: usage or connection error
  exit 2: timeout; stderr: "gcloud-login-driver: timed out in state <state> at <url> (<title>)"
  exit 3: Google password page reached but no password on stdin
  stderr hints (once each): "waiting for the security key", "Microsoft sign-in needs your input"

gcloud-login-browser <url>            writes <url> to $GCLOUD_LOGIN_URL_FILE, exit 0

op-agent start | stop | status        daemon control
op-agent read <op-ref>                prints the secret without trailing newline; starts the daemon if needed
  exit 0 ok · 1 error (message on stderr) · 2 timeout waiting for the daemon (1Password prompt not authorized)

gcloud-login [--admin | --adc] [--status] [--timeout <seconds>]
  exit 0: logged in, or with --status every credential valid
  exit 1: precondition or credential failure
  exit 2: browser flow did not complete within the timeout
```

### Driver state machine

Polled every 500 ms via `Runtime.evaluate`; actions at most once per 5 s per state.

| state | detected by | action |
|---|---|---|
| `done` | URL matches `/sdk/auth_success` or `^http://(localhost\|127\.0\.0\.1):\d+/\?.*\bcode=` | `Target.closeTarget`, exit 0 |
| `identifier` | host `accounts.google.com`, visible `input[name="identifier"]` | focus, `Input.insertText` email, Enter |
| `chooser` | `[data-identifier="<email>"]` present | `.click()` |
| `password` | host `accounts.google.com`, visible `input[type="password"]` | exit 3 if no password; else focus, insertText, Enter |
| `confirm` | path `/speedbump/samlconfirmaccount`, visible button Continue / Weiter | `.click()` |
| `consent` | path `/signin/oauth/consent`, visible button Allow / Zulassen | `.click()` |
| `securitykey` | path contains `/challenge/sk/` | hint once, wait |
| `microsoft` | host `login.microsoftonline.com` with a visible `input` | hint once, wait (first run per profile only) |
| `unknown` | anything else | wait |

### Orchestrator sequence

1. Parse args, context check, tool check, `--status` short-circuit.
2. Start gcloud with `BROWSER=gcloud-login-browser` in the background; wait until the URL file appears **or gcloud exits**. If gcloud exits first, the stored credential was valid: report and stop (no browser, no 1Password).
3. Only now: admin → `op-agent read` for the password (first call of the day shows the 1Password prompt; the script says so); ensure Chromium is installed; start Chromium on the account's profile.
4. Run the driver with the password on stdin. On non-zero exit, focus the Chromium window, print the driver's last line and wait one more timeout window for gcloud.
5. `wait` gcloud, report, quit Chromium.

---

### Task 1: Empirical round ✅ (done 2026-09-22, see the findings file)

Remaining sub-steps, to be done during Task 8:

- [ ] Admin re-auth timing: ~15 min after an admin login run `gcloud config set account bjoern.kahlert.admin@ista-express.de && gcloud auth print-access-token --quiet; echo $?`. Expected: reauth error, non-zero, no browser. Record in the findings file. If a browser opens, `report_status` must set `CLOUDSDK_CORE_DISABLE_PROMPTS=1` instead of `--quiet`.
- [ ] Clean up obsolete profiles once the user has turned sync off in the dedicated Google Chrome profile: `rm -rf "$HOME/Library/Application Support/gcloud-login/"{normal,cft-normal,cft-probe}` (Google Chrome / Chrome for Testing profiles), `rm -rf ~/.cache/gcloud-login/chrome`, `defaults delete com.google.chrome.for.testing`. Then rename `chromium-normal` → `normal` and `chromium-admin` → `admin` so the already-trusted Chromium profiles are reused: `cd "$HOME/Library/Application Support/gcloud-login" && mv chromium-normal normal && mv chromium-admin admin`.

---

### Task 2: `gcloud-login-browser` hook

**Files:**
- Create: `home/dot_local/exact_bin/executable_gcloud-login-browser`

**Interfaces:**
- Consumes: `$GCLOUD_LOGIN_URL_FILE` set by the orchestrator (Task 6).
- Produces: the file's content is the auth URL, read by the driver (Task 3).

- [ ] **Step 1: Write the failing check**

```bash
f=$(mktemp); rm -f "$f"
GCLOUD_LOGIN_URL_FILE="$f" home/dot_local/exact_bin/executable_gcloud-login-browser 'https://example.test/?a=1&b=2'
[[ "$(cat "$f")" == 'https://example.test/?a=1&b=2' ]] && echo PASS || echo FAIL
```

Expected: `FAIL` (no such file).

- [ ] **Step 2: Write the script**

```bash
#!/usr/bin/env bash
# Purpose: Browser hook for gcloud-login. gcloud opens the OAuth URL through
#          $BROWSER and waits for that command to exit, so this hook only
#          records the URL for gcloud-login-driver and returns at once.
# Usage:   BROWSER=gcloud-login-browser gcloud auth login …
#          Requires GCLOUD_LOGIN_URL_FILE to point at the file to write.

set -euo pipefail

url=${1?url not set}
: "${GCLOUD_LOGIN_URL_FILE?GCLOUD_LOGIN_URL_FILE not set}"

printf '%s' "$url" >"$GCLOUD_LOGIN_URL_FILE"
```

```bash
chmod +x home/dot_local/exact_bin/executable_gcloud-login-browser
```

- [ ] **Step 3: Run the check** — rerun Step 1. Expected: `PASS`.

- [ ] **Step 4: Commit**

```bash
git add home/dot_local/exact_bin/executable_gcloud-login-browser
git commit -m "feat(gcloud-login): add the BROWSER hook that hands the auth URL to the driver"
```

---

### Task 3: `gcloud-login-driver` (Node, DevTools protocol)

**Files:**
- Create: `home/dot_local/exact_bin/executable_gcloud-login-driver`
- Create: `tests/gcloud-login-driver.test.js`
- Modify: `home/.chezmoiignore` (add `tests/`)

**Interfaces:**
- Consumes: `DevToolsActivePort` of a Chromium started with `--remote-debugging-port=0`; URL file written by Task 2; password on stdin.
- Produces: exit codes 0/1/2/3 as defined above.

- [ ] **Step 1: Ignore `tests/` in chezmoi** — append `tests/` to `home/.chezmoiignore` after the `docs/` line.

- [ ] **Step 2: Write the failing tests**

`tests/gcloud-login-driver.test.js`:

```js
// Tests for gcloud-login-driver against fixture pages that mimic the Google
// login sequence, served locally and opened in a headless Chromium.
const { test, describe, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');

const DRIVER = path.join(__dirname, '..', 'home', 'dot_local', 'exact_bin', 'executable_gcloud-login-driver');
const CHROMIUM = findChromium();
const EMAIL = 'someone@example.test';

describe('gcloud-login-driver', { skip: CHROMIUM ? false : 'Chromium not installed (run gcloud-login once)' }, () => {
  let chromium, fixture;

  before(async () => {
    chromium = await launchChromium();
    fixture = await startFixture();
  });

  after(() => {
    chromium.kill();
    fixture.server.close();
  });

  describe('on identifier, chooser, password and consent pages', () => {
    test('reaches the callback, closes its tab and exits 0', async () => {
      const result = await runDriver({ url: `${fixture.origin}/identifier`, password: 'hunter2' });
      assert.equal(result.code, 0, result.stderr);
      assert.deepEqual(fixture.seen(), { identifier: EMAIL, password: 'hunter2', callback: true });
      const pages = await chromium.pages();
      assert.equal(pages.filter(p => p.url.startsWith(fixture.origin)).length, 0);
    });
  });

  describe('on a password page without a password', () => {
    test('exits 3 and names the missing password', async () => {
      const result = await runDriver({ url: `${fixture.origin}/password`, password: '' });
      assert.equal(result.code, 3);
      assert.match(result.stderr, /password/);
    });
  });

  describe('on an unknown page', () => {
    test('exits 2 and reports state and url', async () => {
      const result = await runDriver({ url: `${fixture.origin}/unknown`, password: 'x', timeout: 2 });
      assert.equal(result.code, 2);
      assert.match(result.stderr, /timed out in state unknown at http:\/\/127\.0\.0\.1:\d+\/unknown/);
    });
  });

  describe('on a security-key page', () => {
    test('prints the key hint once and keeps waiting until timeout', async () => {
      const result = await runDriver({ url: `${fixture.origin}/v3/signin/challenge/sk/webauthn`, password: 'x', timeout: 2 });
      assert.equal(result.code, 2);
      assert.equal((result.stderr.match(/security key/g) || []).length, 1);
    });
  });

  // --- helpers -------------------------------------------------------------

  function findChromium() {
    const root = path.join(os.homedir(), '.cache', 'gcloud-login', 'chromium');
    if (!fs.existsSync(root)) return null;
    for (const dir of fs.readdirSync(root)) {
      const bin = path.join(root, dir, 'chrome-mac', 'Chromium.app', 'Contents', 'MacOS', 'Chromium');
      if (fs.existsSync(bin)) return bin;
    }
    return null;
  }

  async function launchChromium() {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gcloud-login-driver-test-'));
    const proc = spawn(CHROMIUM, [
      `--user-data-dir=${dir}`, '--remote-debugging-port=0', '--headless=new',
      '--no-first-run', '--no-default-browser-check', 'about:blank',
    ], { stdio: 'ignore' });
    const portFile = path.join(dir, 'DevToolsActivePort');
    for (let i = 0; i < 100 && !fs.existsSync(portFile); i++) await sleep(100);
    assert.ok(fs.existsSync(portFile), 'Chromium did not write DevToolsActivePort');
    const port = fs.readFileSync(portFile, 'utf8').split('\n')[0];
    return {
      portFile,
      kill: () => proc.kill(),
      pages: async () => (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).filter(t => t.type === 'page'),
    };
  }

  // Fixture pages mirror the real navigation: identifier form (Enter) ->
  // chooser (click) -> password form (Enter) -> consent (click) -> callback.
  async function startFixture() {
    const seen = { identifier: null, password: null, callback: false };
    const server = http.createServer((req, res) => {
      const url = new URL(req.url, 'http://127.0.0.1');
      const page = body => { res.setHeader('Content-Type', 'text/html'); res.end(`<!doctype html><title>${url.pathname}</title>${body}`); };
      switch (url.pathname) {
        case '/identifier':
          return page(`<form action="/chooser" method="get"><input type="text" name="identifier"></form>`);
        case '/chooser':
          seen.identifier = url.searchParams.get('identifier') ?? seen.identifier;
          return page(`<div role="link" data-identifier="${EMAIL}" onclick="location='/password'">${EMAIL}</div>`);
        case '/password':
          return page(`<form action="/signin/oauth/consent" method="get"><input type="password" name="Passwd"></form>`);
        case '/signin/oauth/consent':
          seen.password = url.searchParams.get('Passwd') ?? seen.password;
          return page(`<button onclick="location='/?state=s&code=c'">Allow</button>`);
        case '/':
          seen.callback = url.searchParams.get('code') === 'c';
          return page('<p>You are now authenticated.</p>');
        case '/v3/signin/challenge/sk/webauthn':
          return page('<p>Complete sign-in using your security key</p><button>Try another way</button>');
        default:
          return page('<p>Something else</p>');
      }
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    return { server, origin: `http://127.0.0.1:${server.address().port}`, seen: () => ({ ...seen }) };
  }

  function runDriver({ url, password, timeout = 20 }) {
    const urlFile = path.join(os.tmpdir(), `gcloud-login-driver-test-${process.pid}-${Date.now()}.url`);
    const proc = spawn(process.execPath, [
      DRIVER, '--port-file', chromium.portFile, '--url-file', urlFile,
      '--email', EMAIL, '--timeout', String(timeout),
    ], { stdio: ['pipe', 'pipe', 'pipe'] });
    proc.stdin.end(password);
    setTimeout(() => fs.writeFileSync(urlFile, url), 300);
    let stderr = '';
    proc.stderr.on('data', d => { stderr += d; });
    return new Promise(resolve => proc.on('close', code => {
      fs.rmSync(urlFile, { force: true });
      resolve({ code, stderr });
    }));
  }

  function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
});
```

Note on the fixture: the driver classifies `password`, `identifier`, `confirm` and `consent` by path and element only, not by host, so the fixture on 127.0.0.1 exercises the same code paths as accounts.google.com. Host checks are used only for `microsoft`.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `node --test tests/gcloud-login-driver.test.js`
Expected: four failures (driver file missing → exit code null).

- [ ] **Step 4: Write the driver**

`home/dot_local/exact_bin/executable_gcloud-login-driver`:

```js
#!/usr/bin/env node
// Purpose: Drive the Google OAuth pages that `gcloud auth login` opens, inside
//          the Chromium identified by a DevToolsActivePort file, until Google
//          redirects to gcloud's callback. No dependencies beyond Node 22.
// Usage:   gcloud-login-driver --port-file <path> --url-file <path> --email <email>
//                              [--timeout <seconds>]
//          The Google password, if needed, is read from stdin.
// Exit:    0 callback reached · 1 usage or connection error
//          2 timed out (stderr names state, url, title) · 3 password page, no password
//
// Pages and selectors were recorded in
// docs/superpowers/plans/2026-09-22-gcloud-login-findings.md.

const fs = require('node:fs');
const { parseArgs } = require('node:util');

const SELECTORS = {
  identifier: 'input[name="identifier"]',
  password: 'input[type="password"]',
  chooser: email => `[data-identifier="${email}"]`,
  confirmPath: '/speedbump/samlconfirmaccount',
  confirmLabels: ['Continue', 'Weiter'],
  consentPath: '/signin/oauth/consent',
  consentLabels: ['Allow', 'Zulassen'],
  securityKeyPath: '/challenge/sk/',
  microsoftHost: 'login.microsoftonline.com',
  done: [/\/sdk\/auth_success/, /^http:\/\/(localhost|127\.0\.0\.1):\d+\/\?.*\bcode=/],
};
const POLL_MS = 500;
const ACTION_COOLDOWN_MS = 5000;

class Cdp {
  constructor(ws) {
    this.ws = ws;
    this.nextId = 0;
    this.pending = new Map();
    ws.onmessage = ev => {
      const msg = JSON.parse(ev.data);
      const p = this.pending.get(msg.id);
      if (!p) return;
      this.pending.delete(msg.id);
      msg.error ? p.reject(new Error(msg.error.message)) : p.resolve(msg.result);
    };
  }

  static connect(portFile) {
    const [port, wsPath] = fs.readFileSync(portFile, 'utf8').trim().split('\n');
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(`ws://127.0.0.1:${port}${wsPath}`);
      ws.onopen = () => resolve(new Cdp(ws));
      ws.onerror = () => reject(new Error(`cannot connect to Chromium on port ${port}`));
    });
  }

  send(method, params = {}, sessionId) {
    const id = ++this.nextId;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params, sessionId }));
    });
  }

  close() { this.ws.close(); }
}

// Runs inside the page. Returns { url, title, state }.
const STATE_SCRIPT = email => `(() => {
  const S = ${JSON.stringify({ ...SELECTORS, chooser: SELECTORS.chooser(email), done: undefined })};
  const visible = el => !!el && el.offsetParent !== null;
  const url = location.href, title = document.title, host = location.host, path = location.pathname;
  const buttons = [...document.querySelectorAll('button, [role="button"]')].filter(visible).map(b => b.textContent.trim());
  const has = labels => buttons.some(b => labels.includes(b));
  let state = 'unknown';
  if (${SELECTORS.done.map(String).join('.test(url) || ')}.test(url)) state = 'done';
  else if (host === S.microsoftHost && [...document.querySelectorAll('input')].some(visible)) state = 'microsoft';
  else if (path.includes(S.securityKeyPath)) state = 'securitykey';
  else if (visible(document.querySelector(S.password))) state = 'password';
  else if (visible(document.querySelector(S.identifier))) state = 'identifier';
  else if (document.querySelector(S.chooser)) state = 'chooser';
  else if (path.startsWith(S.confirmPath) && has(S.confirmLabels)) state = 'confirm';
  else if (path.startsWith(S.consentPath) && has(S.consentLabels)) state = 'consent';
  return { url, title, state };
})()`;

const clickScript = selector => `document.querySelector(${JSON.stringify(selector)}).click()`;
const clickButtonScript = labels => `(() => {
  const b = [...document.querySelectorAll('button, [role="button"]')]
    .filter(e => e.offsetParent !== null).find(b => ${JSON.stringify(labels)}.includes(b.textContent.trim()));
  b.click();
})()`;

const HINTS = {
  securitykey: 'gcloud-login-driver: waiting for the security key — tap it now',
  microsoft: 'gcloud-login-driver: Microsoft sign-in needs your input (first run in this browser profile)',
};

function readStdin() {
  try { return fs.readFileSync(0, 'utf8').replace(/\n$/, ''); } catch { return ''; }
}

function waitForFile(file, deadline) {
  return new Promise((resolve, reject) => {
    const tick = () => {
      if (fs.existsSync(file) && fs.statSync(file).size > 0) return resolve(fs.readFileSync(file, 'utf8').trim());
      if (Date.now() > deadline) return reject(new Error(`no auth url appeared in ${file}`));
      setTimeout(tick, 100);
    };
    tick();
  });
}

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function typeInto(cdp, sessionId, selector, text) {
  await cdp.send('Runtime.evaluate', { expression: `document.querySelector(${JSON.stringify(selector)}).focus()` }, sessionId);
  await cdp.send('Input.insertText', { text }, sessionId);
  const key = { key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 };
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', ...key }, sessionId);
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', ...key }, sessionId);
}

async function drive({ portFile, urlFile, email, timeoutMs, password }) {
  const deadline = Date.now() + timeoutMs;
  const url = await waitForFile(urlFile, deadline);
  const cdp = await Cdp.connect(portFile);
  let targetId;
  try {
    ({ targetId } = await cdp.send('Target.createTarget', { url }));
    const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
    await cdp.send('Page.enable', {}, sessionId);
    await cdp.send('Runtime.enable', {}, sessionId);
    await cdp.send('Page.bringToFront', {}, sessionId);

    const hinted = new Set();
    let lastAction = 0;
    let last = { state: 'unknown', url, title: '' };
    while (Date.now() < deadline) {
      let result;
      try {
        ({ result } = await cdp.send('Runtime.evaluate', { expression: STATE_SCRIPT(email), returnByValue: true }, sessionId));
      } catch {
        await sleep(POLL_MS); // navigating between pages
        continue;
      }
      last = result.value;
      if (last.state === 'done') {
        await cdp.send('Target.closeTarget', { targetId });
        return 0;
      }
      if (HINTS[last.state] && !hinted.has(last.state)) {
        hinted.add(last.state);
        process.stderr.write(HINTS[last.state] + '\n');
      }
      if (Date.now() - lastAction > ACTION_COOLDOWN_MS) {
        switch (last.state) {
          case 'identifier':
            await typeInto(cdp, sessionId, SELECTORS.identifier, email); lastAction = Date.now(); break;
          case 'chooser':
            await cdp.send('Runtime.evaluate', { expression: clickScript(SELECTORS.chooser(email)) }, sessionId); lastAction = Date.now(); break;
          case 'password':
            if (!password) {
              process.stderr.write(`gcloud-login-driver: password page reached but no password on stdin (${last.url})\n`);
              return 3;
            }
            await typeInto(cdp, sessionId, SELECTORS.password, password); lastAction = Date.now(); break;
          case 'confirm':
            await cdp.send('Runtime.evaluate', { expression: clickButtonScript(SELECTORS.confirmLabels) }, sessionId); lastAction = Date.now(); break;
          case 'consent':
            await cdp.send('Runtime.evaluate', { expression: clickButtonScript(SELECTORS.consentLabels) }, sessionId); lastAction = Date.now(); break;
        }
      }
      await sleep(POLL_MS);
    }
    process.stderr.write(`gcloud-login-driver: timed out in state ${last.state} at ${last.url} (${last.title})\n`);
    return 2;
  } finally {
    cdp.close();
  }
}

async function main() {
  const { values } = parseArgs({
    options: {
      'port-file': { type: 'string' },
      'url-file': { type: 'string' },
      email: { type: 'string' },
      timeout: { type: 'string', default: '120' },
    },
  });
  for (const name of ['port-file', 'url-file', 'email']) {
    if (!values[name]) {
      process.stderr.write(`gcloud-login-driver: --${name} not set\n`);
      return 1;
    }
  }
  return drive({
    portFile: values['port-file'],
    urlFile: values['url-file'],
    email: values.email,
    timeoutMs: Number(values.timeout) * 1000,
    password: readStdin(),
  });
}

if (require.main === module) {
  main().then(code => process.exit(code), err => {
    process.stderr.write(`gcloud-login-driver: ${err.message}\n`);
    process.exit(1);
  });
}
```

```bash
chmod +x home/dot_local/exact_bin/executable_gcloud-login-driver
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `node --test tests/gcloud-login-driver.test.js`
Expected: 4 passing. Chromium is already present from the empirical round (`~/.cache/gcloud-login/chromium/mac_arm-1702741`).

- [ ] **Step 6: Commit**

```bash
git add home/.chezmoiignore home/dot_local/exact_bin/executable_gcloud-login-driver tests/gcloud-login-driver.test.js
git commit -m "feat(gcloud-login): add the DevTools-protocol driver for the Google login pages"
```

---

### Task 4: `op-agent` — one 1Password authorization for the whole day

**Files:**
- Create: `home/dot_local/exact_bin/executable_op-agent`

**Interfaces:**
- Consumes: `op` CLI with the desktop-app integration.
- Produces: `op-agent read <ref>` used by Task 6 for the admin password.

Protocol: the daemon holds the `req` FIFO open read-write and reads lines `<op-ref>\t<response-fifo>`. The client creates a private response FIFO (0600) in a private temp directory (0700), writes its request, and reads the answer with a timeout. Answers are `OK\t<secret>` or `ERR\t<message>`. Between requests the daemon runs `op whoami` every 5 min so the desktop app's 10-minute inactivity window never closes; the 12-hour hard limit still forces one Authorize click per day.

- [ ] **Step 1: Write the failing checks**

```bash
s=home/dot_local/exact_bin/executable_op-agent
"$s" status; echo "exit=$? (want 1: not running)"
"$s" start && "$s" status; echo "exit=$? (want 0: running, pid printed)"
v=$("$s" read "op://Employee/p44thhnd5ylh6zrm6etwozs63a/password"); echo "read#1 exit=$? len=${#v}"   # 1Password prompt appears once
v=$("$s" read "op://Employee/p44thhnd5ylh6zrm6etwozs63a/password"); echo "read#2 exit=$? len=${#v}"   # no prompt
"$s" read "op://Employee/does-not-exist/password"; echo "exit=$? (want 1 with op's message)"
"$s" stop; "$s" status; echo "exit=$? (want 1)"
```

Expected now: `no such file`.

- [ ] **Step 2: Write the script**

```bash
#!/usr/bin/env bash
# Purpose: Keep one 1Password CLI authorization alive and serve `op read`
#          requests from other processes. The desktop app authorizes op per
#          process tree, so every new shell (e.g. each Claude Code Bash call)
#          would otherwise show the "Access Requested" prompt again. The
#          daemon runs in its own session and pseudo-terminal, pings op every
#          5 minutes to stay inside the 10-minute inactivity window, and lives
#          at most 12 hours (1Password's hard limit).
# Usage:   op-agent start | stop | status
#          op-agent read <op-ref>      # prints the secret, no trailing newline;
#                                      # starts the daemon if needed
# Exit:    0 ok · 1 error · 2 timeout waiting for the daemon (prompt not authorized)
#
# Security: anyone able to write to the request FIFO (mode 0600, directory
# 0700 — i.e. this user) can read any secret this account can. That equals
# what an authorized terminal already allows.

set -euo pipefail

readonly STATE_DIR="$HOME/Library/Application Support/op-agent"
readonly REQ="$STATE_DIR/req"
readonly PID_FILE="$STATE_DIR/pid"
readonly LOG="$STATE_DIR/agent.log"
readonly KEEPALIVE_SECONDS=300
readonly READ_TIMEOUT=90   # op's own prompt times out after 60 s

err() { printf 'op-agent: %s\n' "$1" >&2; }
die() { err "$1"; exit "${2:-1}"; }

running() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(<"$PID_FILE")" 2>/dev/null
}

# --- daemon -------------------------------------------------------------------

serve() {
  exec 3<>"$REQ"  # read-write keeps the FIFO open even with no client
  local line ref resp value
  while :; do
    if read -r -t "$KEEPALIVE_SECONDS" -u 3 line; then
      ref=${line%%$'\t'*}
      resp=${line#*$'\t'}
      [[ -p "$resp" ]] || continue
      if value=$(op read --no-newline "$ref" 2>&1); then
        printf 'OK\t%s\n' "$value" >"$resp"
      else
        printf 'ERR\t%s\n' "$value" >"$resp"
      fi
    else
      op whoami >/dev/null 2>&1 || true
    fi
  done
}

start() {
  running && return 0
  mkdir -p "$STATE_DIR"
  chmod 700 "$STATE_DIR"
  [[ -p "$REQ" ]] || mkfifo -m 600 "$REQ"
  # setsid + pty: 1Password identifies the terminal by tty and session, so the
  # daemon must not share Claude's or the user's shell.
  nohup python3 - "$0" "$PID_FILE" <<'PY' >>"$LOG" 2>&1 &
import os, pty, sys
script, pid_file = sys.argv[1], sys.argv[2]
os.setsid()
with open(pid_file, 'w') as f:
    f.write(str(os.getpid()))
pty.spawn([script, '__serve'])
PY
  local i
  for ((i = 0; i < 50; i++)); do
    running && return 0
    sleep 0.1
  done
  die "daemon did not start (see $LOG)"
}

stop() {
  running || return 0
  pkill -TERM -s "$(<"$PID_FILE")" 2>/dev/null || kill "$(<"$PID_FILE")" 2>/dev/null || true
  rm -f "$PID_FILE"
}

status() {
  if running; then
    printf 'op-agent: running (pid %s)\n' "$(<"$PID_FILE")"
  else
    printf 'op-agent: not running\n'
    return 1
  fi
}

# --- client -------------------------------------------------------------------

read_secret() {
  local ref=$1 tmp resp line
  start
  tmp=$(mktemp -d)
  chmod 700 "$tmp"
  resp="$tmp/resp"
  mkfifo -m 600 "$resp"
  trap 'rm -rf "$tmp"' RETURN
  printf '%s\t%s\n' "$ref" "$resp" >"$REQ"
  if ! read -r -t "$READ_TIMEOUT" line <"$resp"; then
    die "no answer within ${READ_TIMEOUT}s — authorize the 1Password prompt and retry" 2
  fi
  case $line in
    OK$'\t'*) printf '%s' "${line#OK$'\t'}" ;;
    ERR$'\t'*) die "${line#ERR$'\t'}" ;;
    *) die "unexpected answer" ;;
  esac
}

case ${1:-} in
  __serve) serve ;;
  start) start ;;
  stop) stop ;;
  status) status ;;
  read) read_secret "${2?op-agent read: reference not set}" ;;
  *) die "usage: op-agent start | stop | status | read <op-ref>" ;;
esac
```

```bash
chmod +x home/dot_local/exact_bin/executable_op-agent
```

Notes for the implementer: `read -t … <"$resp"` opens the FIFO for reading, which blocks until the daemon opens it for writing; the daemon does so right after `op read`, so the timeout covers the whole round trip. `trap … RETURN` needs `set -o functrace`? No: `RETURN` traps fire for functions without it. `pkill -s <sid>` kills the whole daemon session (python, bash, op).

- [ ] **Step 3: Run the checks** — rerun Step 1 from a new shell each time for `read#2` (e.g. `bash -c '…'`). Expected: `status` exits 1 then 0; `read#1` shows exactly one 1Password prompt and returns `len=64`; `read#2` returns in ≤1 s with no prompt; the bogus reference exits 1 with op's "could not read secret" message; `stop` leaves no `op-agent` processes (`pgrep -fl op-agent`).

- [ ] **Step 4: Commit**

```bash
git add home/dot_local/exact_bin/executable_op-agent
git commit -m "feat(op-agent): keep one 1Password CLI authorization alive for other processes"
```

---

### Task 5: Chromium installation helper inside `gcloud-login` (design note, implemented in Task 6)

The Homebrew `chromium` cask is disabled (Gatekeeper). `gcloud-login` therefore installs the pinned snapshot itself when the binary is missing:

```bash
readonly CHROMIUM_BUILD=1702741   # Chromium 156.0.8070.0, tested 2026-09-22
readonly CACHE_DIR="$HOME/.cache/gcloud-login"
chromium_bin() { ls -d "$CACHE_DIR"/chromium/*-"$CHROMIUM_BUILD"/chrome-mac/Chromium.app/Contents/MacOS/Chromium 2>/dev/null | head -1; }
ensure_chromium() {
  [[ -n "$(chromium_bin)" ]] && return 0
  info "Installing Chromium $CHROMIUM_BUILD (plain build, immune to the managed-profile interception)"
  npx --yes @puppeteer/browsers install "chromium@$CHROMIUM_BUILD" --path "$CACHE_DIR" >/dev/null
  [[ -n "$(chromium_bin)" ]] || die "gcloud-login: Chromium install failed"
}
```

No separate task; listed here so the build pin has one home.

---

### Task 6: `gcloud-login` orchestrator, replacing the zsh function

**Files:**
- Create: `home/dot_local/exact_bin/executable_gcloud-login`
- Delete: `home/private_dot_config/zsh/exact_conf.d/exact_ista/10-gcloud.zsh`

**Interfaces:**
- Consumes: `gcloud-login-browser` (Task 2), `gcloud-login-driver` (Task 3), `op-agent` (Task 4), `gcloud`, `jq`, `curl`, `node`, `npx`.
- Produces: the command the skills (Task 7) tell Claude to run; exit codes per "Process interfaces".

- [ ] **Step 1: Write the failing checks**

```bash
s=home/dot_local/exact_bin/executable_gcloud-login
DOTFILES_CONTEXT=bkahlert "$s" --status; echo "exit=$? (want 1, context message)"
"$s" --admin --adc; echo "exit=$? (want 1, mutually exclusive)"
"$s" --bogus; echo "exit=$? (want 1, unknown option)"
"$s" --status; echo "exit=$? (want 0 or 1 with two report lines)"
```

Expected now: `no such file` for all four.

- [ ] **Step 2: Write the script**

```bash
#!/usr/bin/env bash
# Purpose: Log the gcloud CLI, or Application Default Credentials, into one of
#          the ista Google accounts without manual interaction. gcloud's OAuth
#          URL is opened in a plain Chromium (per-account profile, DevTools
#          enabled) and gcloud-login-driver walks the Google pages. The admin
#          account's password comes from 1Password via op-agent; its security
#          key must be tapped once per login (Workspace policy).
# Usage:   gcloud-login [--admin | --adc] [--status] [--timeout <seconds>]
#          --admin    log the CLI into the admin account
#          --adc      refresh Application Default Credentials (always the normal account)
#          --status   report CLI account, ADC identity and token validity; exit 0 if all valid
#          --timeout  seconds to wait for the browser flow (default 120; use 300 on a
#                     fresh browser profile, where the Microsoft sign-in is manual)
# Exit:    0 success · 1 precondition or credential failure · 2 browser flow timed out
#
# First run per account: the browser profile is empty, so the normal account
# goes through the Microsoft sign-in (ista account, Authenticator code, "Stay
# signed in" = Yes) and the security key by hand; afterwards it is silent.
# See docs/superpowers/plans/2026-09-22-gcloud-login-findings.md in the
# dotfiles repo for every observed page.

set -euo pipefail

readonly NORMAL_EMAIL="bjoern.kahlert@ista-express.de"
readonly ADMIN_EMAIL="bjoern.kahlert.admin@ista-express.de"
# Referenced by ID: the item title "Google (Admin)" has parentheses, which
# op:// references reject.
readonly ADMIN_OP_REF="op://Employee/p44thhnd5ylh6zrm6etwozs63a/password"
readonly CHROMIUM_BUILD=1702741   # Chromium 156.0.8070.0, tested 2026-09-22
readonly CACHE_DIR="$HOME/.cache/gcloud-login"
readonly PROFILE_ROOT="$HOME/Library/Application Support/gcloud-login"
readonly TOKENINFO_URL="https://oauth2.googleapis.com/tokeninfo"

if [ -t 2 ]; then
  c_reset=$(tput sgr0); c_red=$(tput setaf 1); c_green=$(tput setaf 2)
  c_yellow=$(tput setaf 3); c_blue=$(tput setaf 4)
else
  c_reset=''; c_red=''; c_green=''; c_yellow=''; c_blue=''
fi
info() { printf '%sℹ%s %s\n' "$c_blue" "$c_reset" "$1" >&2; }
ok()   { printf '%s✔%s %s\n' "$c_green" "$c_reset" "$1" >&2; }
warn() { printf '%s!%s %s\n' "$c_yellow" "$c_reset" "$1" >&2; }
err()  { printf '%s✘%s %s\n' "$c_red" "$c_reset" "$1" >&2; }
die()  { err "$1"; exit "${2:-1}"; }

mode=cli
status=false
timeout=120
while [ $# -gt 0 ]; do
  case $1 in
    --admin) [[ $mode == adc ]] && die "gcloud-login: --admin and --adc are mutually exclusive"; mode=admin && shift ;;
    --adc) [[ $mode == admin ]] && die "gcloud-login: --admin and --adc are mutually exclusive"; mode=adc && shift ;;
    --status) status=true && shift ;;
    --timeout) timeout=${2?$1: parameter value not set} && shift 2 ;;
    --timeout=*) timeout=${1#*=} && shift ;;
    *) die "gcloud-login: unknown option $1 (usage: gcloud-login [--admin | --adc] [--status] [--timeout <seconds>])" ;;
  esac
done

[[ "${DOTFILES_CONTEXT:-}" == ista ]] || die "gcloud-login: only available in the ista context"
for tool in gcloud jq curl node npx gcloud-login-driver gcloud-login-browser op-agent; do
  command -v "$tool" >/dev/null || die "gcloud-login: $tool not found"
done

# --- status -------------------------------------------------------------------

report_status() {
  local all_valid=true cli_account cli_state adc_token adc_email adc_state
  cli_account=$(gcloud config get-value account 2>/dev/null || true)
  if gcloud auth print-access-token --quiet >/dev/null 2>&1; then
    cli_state=valid
  else
    cli_state="needs login"; all_valid=false
  fi
  if adc_token=$(gcloud auth application-default print-access-token 2>/dev/null); then
    adc_email=$(curl -fsS "${TOKENINFO_URL}?access_token=${adc_token}" | jq -r '.email // empty')
    adc_state=valid
  else
    adc_email=""; adc_state="needs login"; all_valid=false
  fi
  printf 'CLI account:  %s (%s)\n' "${cli_account:-none}" "$cli_state"
  printf 'ADC identity: %s (%s)\n' "${adc_email:-unknown}" "$adc_state"
  [[ $all_valid == true ]]
}

if [[ $status == true ]]; then
  report_status
  exit
fi

# --- Chromium -----------------------------------------------------------------

chromium_bin() {
  ls -d "$CACHE_DIR"/chromium/*-"$CHROMIUM_BUILD"/chrome-mac/Chromium.app/Contents/MacOS/Chromium 2>/dev/null | head -1
}

ensure_chromium() {
  [[ -n "$(chromium_bin)" ]] && return 0
  info "Installing Chromium $CHROMIUM_BUILD (plain build, immune to the managed-profile interception)"
  npx --yes @puppeteer/browsers install "chromium@$CHROMIUM_BUILD" --path "$CACHE_DIR" >/dev/null
  [[ -n "$(chromium_bin)" ]] || die "gcloud-login: Chromium install failed"
}

chromium_pid=""
start_chromium() {
  local profile_dir=$1 port_file="$1/DevToolsActivePort" i
  mkdir -p "$profile_dir"
  # A leftover instance from an aborted run would swallow the new launch.
  pkill -f -- "--user-data-dir=${profile_dir}" 2>/dev/null || true
  for ((i = 0; i < 50; i++)); do
    pgrep -f -- "--user-data-dir=${profile_dir}" >/dev/null || break
    sleep 0.2
  done
  rm -f "$port_file"
  "$(chromium_bin)" --user-data-dir="$profile_dir" --remote-debugging-port=0 \
    --no-first-run --no-default-browser-check --no-startup-window >/dev/null 2>&1 &
  chromium_pid=$!
  for ((i = 0; i < 100; i++)); do
    [[ -s "$port_file" ]] && return 0
    sleep 0.2
  done
  die "gcloud-login: Chromium did not expose its DevTools port"
}

# --- lifecycle ----------------------------------------------------------------

url_file=""
gcloud_pid=""
gcloud_log=""
cleanup() {
  [[ -n "$gcloud_pid" ]] && kill "$gcloud_pid" 2>/dev/null || true
  [[ -n "$chromium_pid" ]] && kill "$chromium_pid" 2>/dev/null || true
  [[ -n "$url_file" ]] && rm -f "$url_file"
  [[ -n "$gcloud_log" ]] && rm -f "$gcloud_log"
}
trap cleanup EXIT

case $mode in
  admin) email=$ADMIN_EMAIL; profile=admin;  gcloud_cmd=(gcloud auth login "$email" --quiet) ;;
  adc)   email=$NORMAL_EMAIL; profile=normal; gcloud_cmd=(gcloud auth application-default login "$email" --quiet) ;;
  cli)   email=$NORMAL_EMAIL; profile=normal; gcloud_cmd=(gcloud auth login "$email" --quiet) ;;
esac

# 1. Start gcloud. With a valid stored credential it exits at once and never
#    calls the browser hook; then there is nothing else to do.
url_file=$(mktemp); rm -f "$url_file"
gcloud_log=$(mktemp)
export GCLOUD_LOGIN_URL_FILE="$url_file"
info "Running: ${gcloud_cmd[*]}"
BROWSER=gcloud-login-browser "${gcloud_cmd[@]}" >"$gcloud_log" 2>&1 &
gcloud_pid=$!
while [[ ! -s "$url_file" ]] && kill -0 "$gcloud_pid" 2>/dev/null; do sleep 0.2; done
if [[ ! -s "$url_file" ]]; then
  if wait "$gcloud_pid"; then
    gcloud_pid=""
    ok "Credentials for $email are still valid ($mode); nothing to do"
    exit 0
  fi
  gcloud_pid=""
  cat "$gcloud_log" >&2
  die "gcloud-login: gcloud failed before opening a browser"
fi

# 2. Everything the browser flow needs, fetched only now that we know we need it.
password=""
if [[ $mode == admin ]]; then
  op-agent status >/dev/null 2>&1 || info "First 1Password read of the day: authorize the prompt"
  password=$(op-agent read "$ADMIN_OP_REF") || die "gcloud-login: could not read the admin password from 1Password"
fi
ensure_chromium
start_chromium "$PROFILE_ROOT/$profile"

# 3. Drive the pages.
driver_status=0
printf '%s' "$password" | gcloud-login-driver \
  --port-file "$PROFILE_ROOT/$profile/DevToolsActivePort" --url-file "$url_file" \
  --email "$email" --timeout "$timeout" || driver_status=$?
unset password

if (( driver_status != 0 )); then
  # Leave the page visible so the user can finish what the driver does not
  # handle, and give gcloud one more timeout window to receive the callback.
  warn "gcloud-login: automation stopped (driver exit $driver_status); finish the login in the Chromium window or press Ctrl-C"
  for ((i = 0; i < timeout; i++)); do
    kill -0 "$gcloud_pid" 2>/dev/null || break
    sleep 1
  done
fi

if wait "$gcloud_pid"; then
  gcloud_pid=""
  ok "Logged in ($mode) as $email"
  exit 0
fi
gcloud_pid=""
cat "$gcloud_log" >&2
if (( driver_status == 2 )); then
  die "gcloud-login: browser flow timed out" 2
fi
die "gcloud-login: gcloud did not complete the login"
```

```bash
chmod +x home/dot_local/exact_bin/executable_gcloud-login
```

- [ ] **Step 3: Run the checks** — rerun Step 1. Expected:

```
✘ gcloud-login: only available in the ista context      exit=1
✘ gcloud-login: --admin and --adc are mutually exclusive exit=1
✘ gcloud-login: unknown option --bogus …                exit=1
CLI account:  <email> (valid|needs login)
ADC identity: <email> (valid|needs login)               exit=0 or 1
```

- [ ] **Step 4: Remove the zsh function**

```bash
git rm home/private_dot_config/zsh/exact_conf.d/exact_ista/10-gcloud.zsh
```

- [ ] **Step 5: Commit**

```bash
git add home/dot_local/exact_bin/executable_gcloud-login
git commit -m "feat(gcloud-login): move to ~/.local/bin and drive the login unattended"
```

---

### Task 7: The two skills, their symlinks, and the context ignore

**Files:**
- Create: `home/dot_agents/skills/gcloud-auth/SKILL.md`
- Create: `home/dot_agents/skills/gcloud-login-automation/SKILL.md`
- Create: `home/private_dot_claude/skills/symlink_gcloud-auth`
- Create: `home/private_dot_claude/skills/symlink_gcloud-login-automation`
- Modify: `home/.chezmoiignore`

- [ ] **Step 1: Write the failing check**

```bash
chezmoi managed | grep -E '\.(agents|claude)/skills/gcloud-'; echo "exit=$? (want 0 with four entries)"
```

Expected now: no output, `exit=1`.

- [ ] **Step 2: Write skill 1**

`home/dot_agents/skills/gcloud-auth/SKILL.md`:

```markdown
---
name: gcloud-auth
description: Use before any gcloud, Cloud Run, Firestore, Pub/Sub or other GCP work, and whenever a gcloud or Google client call fails with a credential, reauthentication, "Reauthentication required", "invalid_grant", UNAUTHENTICATED or PERMISSION_DENIED error. Decides which gcloud login is missing (CLI vs Application Default Credentials, normal vs admin account) and runs `gcloud-login` to fix it unattended instead of telling the user to log in.
---

# gcloud auth

Two credential stores exist and fail independently:

| Store | Used by | Check | Fix |
|---|---|---|---|
| CLI credential | `gcloud …` commands, `gcloud auth print-access-token` | `gcloud-login --status`, line "CLI account" | `gcloud-login` (normal) or `gcloud-login --admin` |
| Application Default Credentials (ADC) | Google client libraries, local services, MCP servers, Terraform, `gcloud auth application-default print-access-token` | `gcloud-login --status`, line "ADC identity" | `gcloud-login --adc` |

## Procedure

1. Run `gcloud-login --status` first. It prints both stores and exits 0 only if both are valid.
2. Fix only the store that failed. A failing `gcloud` command needs the CLI credential; a failing application, library or MCP server needs ADC. Both can be stale at once after a long break.
3. Re-run the original command. Do not retry the login in a loop: if `gcloud-login` exits non-zero, report its last stderr line and stop.

`gcloud-login` is idempotent: with a valid credential it exits immediately without a browser, so calling it before GCP work is cheap.

## Identity policy

- **ADC is always the normal account.** `gcloud-login --adc` cannot be combined with `--admin`. If `--status` shows the admin email as ADC identity, run `gcloud-login --adc` to correct it.
- **CLI defaults to the normal account.** Switch to admin only for a concrete `PERMISSION_DENIED` on IAM, organization or project-level resources:
  - both accounts are usually credentialed, so first try `gcloud config set account bjoern.kahlert.admin@ista-express.de` and re-run;
  - if that fails with a reauthentication error, run `gcloud-login --admin`;
  - when the admin operation is done, run `gcloud config set account bjoern.kahlert@ista-express.de`. Never leave admin active at the end of a task.
- **Admin needs the user.** Every admin login requires a security-key tap (Workspace policy); the script prints "tap it now". Tell the user before running `gcloud-login --admin`, and expect it again after 10–15 minutes, because the admin credential expires that fast. The first admin run of the day also shows one 1Password "Access Requested" prompt the user must authorize.

## What not to do

- Do not tell the user to run `gcloud auth login`; `gcloud-login` does it.
- Do not run `gcloud auth login` or `gcloud auth application-default login` directly: they open the user's daily browser and wait for clicks.
- Do not use admin for ADC, for deployments, or "just in case".

## Exit codes of gcloud-login

0 logged in · 1 precondition or credential failure (message on stderr) · 2 browser flow timed out, the Chromium window is left open for the user.
```

- [ ] **Step 3: Write skill 2**

`home/dot_agents/skills/gcloud-login-automation/SKILL.md`:

```markdown
---
name: gcloud-login-automation
description: Use when `gcloud-login` or `op-agent` fails, hangs, or needs a change (new Google or Microsoft page, new button label, Chromium update, 1Password prompt behaviour), or when asked how the unattended gcloud login works. Explains the components (BROWSER hook, plain Chromium per account, DevTools driver, op-agent), where each lives, how to debug a run and how to extend the selectors.
---

# gcloud-login automation

`gcloud-login` (`~/.local/bin`; source `home/dot_local/exact_bin/executable_gcloud-login` in the dotfiles repo) logs the gcloud CLI or ADC into an ista Google account without manual steps, except the admin security key. The recorded page sequences and every constraint discovered live in `docs/superpowers/plans/2026-09-22-gcloud-login-findings.md` in the dotfiles repo; read it before changing anything.

## Flow

1. `gcloud auth login <email> --quiet` (or `application-default login`) runs with `BROWSER=gcloud-login-browser`. With a valid credential gcloud exits at once and nothing else happens. Otherwise gcloud calls the hook, which writes the OAuth URL to `$GCLOUD_LOGIN_URL_FILE` and returns immediately (gcloud waits for the browser command).
2. For `--admin` only: the Google password is read through `op-agent read op://Employee/<id>/password`.
3. A plain Chromium (`~/.cache/gcloud-login/chromium/…`, installed on first use via `npx @puppeteer/browsers`) starts on `~/Library/Application Support/gcloud-login/<normal|admin>` with `--remote-debugging-port=0 --no-startup-window`. Plain Chromium has no Google API keys, so the enterprise "your organization requires you to sign into Chrome" interception cannot fire and remote debugging stays available. Google Chrome and Chrome for Testing both fail here.
4. `gcloud-login-driver` opens the URL over the DevTools protocol and polls the page every 500 ms: identifier → types the email; account chooser → clicks the account; Google password page → types the password (admin); "Verify that it's you" → Continue/Weiter; consent → Allow/Zulassen; `docs.cloud.google.com/sdk/auth_success` → closes the tab, exit 0. Microsoft pages and the security-key page are waited through with a stderr hint.
5. gcloud receives the callback and exits; Chromium is quit; the password variable is unset.

## Accounts

| Account | Identity provider | Steady state |
|---|---|---|
| normal | Microsoft Entra SAML with the **ista** account; "Stay signed in" keeps it silent | 7 s, no input |
| admin | Google password + security key on **every** login | 14 s incl. the key tap; password from 1Password |

## op-agent

`op-agent` keeps one 1Password CLI authorization alive: the desktop app authorizes `op` per process tree, so each new shell (every Claude Code Bash call) would prompt again. The daemon runs `setsid` in its own pty, serves `op read` over a FIFO in `~/Library/Application Support/op-agent/`, pings `op whoami` every 5 min (10-min inactivity limit) and dies with 1Password's 12-h hard limit. Commands: `start | stop | status | read <ref>`. First read of the day shows the "Access Requested" prompt once. The prompt window has no accessibility tree; do not try to click it with peekaboo.

## Debugging a failed run

- Driver exit 2 prints `timed out in state <state> at <url> (<title>)`. State `unknown` means a page the state machine does not know; the Chromium window is left open, look at it. `securitykey` means nobody tapped the key. `microsoft` means the Microsoft session expired: run `gcloud-login --timeout 300` and let the user sign in once (ista account, Authenticator code, Stay signed in = Yes).
- Driver exit 3: Google asked for a password although none was supplied — only expected for admin; check `op-agent read op://Employee/p44thhnd5ylh6zrm6etwozs63a/password | wc -c` (64).
- `op-agent read` exit 2: the 1Password prompt was not authorized within 90 s; `op-agent stop`, retry and click Authorize.
- No `DevToolsActivePort`: a stale Chromium on the same profile (the script kills it) or the profile was signed into a browser account (never happens with plain Chromium; if a Google Chrome profile was reused by mistake, delete the profile directory).
- Tests for the driver: `node --test tests/gcloud-login-driver.test.js` in the dotfiles repo (headless Chromium against fixture pages).
- Recording a new page: run the probe from the findings file against the running Chromium (`DevToolsActivePort` in the profile directory) and add the state to `SELECTORS` in `gcloud-login-driver`.

## Failure modes seen

| Situation | Symptom | Handling |
|---|---|---|
| Admin credential expired (every 10–15 min) | reauth error from gcloud | `gcloud-login --admin`, user taps the key |
| Microsoft session expired (normal) | state `microsoft` | user signs in once with `--timeout 300` |
| Fresh browser profile | Microsoft sign-in, security key, trust-device checkbox | user, once per profile |
| Chromium updated / build missing | `Chromium install failed` | check `CHROMIUM_BUILD` and `npx @puppeteer/browsers list` |
| 1Password locked or prompt ignored | `op-agent read` exit 2 | unlock 1Password, authorize, retry |
```

- [ ] **Step 4: Create the symlink sources**

```bash
mkdir -p home/private_dot_claude/skills
printf '../../.agents/skills/gcloud-auth' > home/private_dot_claude/skills/symlink_gcloud-auth
printf '../../.agents/skills/gcloud-login-automation' > home/private_dot_claude/skills/symlink_gcloud-login-automation
```

- [ ] **Step 5: Ignore the skills outside the ista context** — append to `home/.chezmoiignore` (it is always rendered as a template):

```
{{- if ne .company "ista" }}
# gcloud-login skills describe the ista Google accounts only.
.agents/skills/gcloud-auth
.agents/skills/gcloud-login-automation
.claude/skills/gcloud-auth
.claude/skills/gcloud-login-automation
{{- end }}
```

- [ ] **Step 6: Run the check**

```bash
chezmoi managed | grep -E '\.(agents|claude)/skills/gcloud-'
chezmoi execute-template < home/.chezmoiignore | grep -c 'skills/gcloud-'
```

Expected: four managed paths; the second prints `0` on this ista machine. The non-ista rendering is covered by `make build && make validate` (empty company in the container).

- [ ] **Step 7: Commit**

```bash
git add home/dot_agents home/private_dot_claude/skills home/.chezmoiignore
git commit -m "feat(skills): add gcloud-auth and gcloud-login-automation skills"
```

---

### Task 8: Apply and verify end to end

- [ ] **Step 1: Finish Task 1's leftovers** (admin re-auth timing, profile cleanup and rename) and commit any findings-file changes.

- [ ] **Step 2: Preview and apply**

```bash
chezmoi diff
chezmoi apply -n
chezmoi apply
```

Expected in the diff: four new executables in `~/.local/bin`, two SKILL.md files, two symlinks, removal of `~/.config/zsh/conf.d/ista/10-gcloud.zsh`.

- [ ] **Step 3: Verify the shell sees the command and Claude's shell too**

Interactive zsh: `whence -v gcloud-login` → file; `gcloud-login --status`. Claude's Bash tool: `command -v gcloud-login && gcloud-login --status`.

- [ ] **Step 4: Unattended runs**

```bash
gcloud-login            # normal CLI: "still valid" or 7 s browser flow, no input
gcloud-login --adc      # same for ADC
gcloud-login --admin    # 1Password prompt once per day, key tap, ~15 s
gcloud-login --status   # both valid, ADC identity is the normal email, exit 0
gcloud config set account bjoern.kahlert@ista-express.de
```

Record any `timed out in state` message in the findings file, adjust `SELECTORS`, rerun `node --test tests/gcloud-login-driver.test.js`.

- [ ] **Step 5: Verify the skills load** — new Claude Code session, `/gcloud-auth` shows the skill; "my gcloud command fails with Reauthentication required" makes Claude run `gcloud-login --status` then `gcloud-login`, not `gcloud auth login`.

- [ ] **Step 6: Commit corrections, then offer the ship flow** per CLAUDE.md.

---

## Self-review

- **Spec coverage:** every fact in the findings file maps to a design element: no-space `BROWSER` (Task 2, Global Constraints), Chromium instead of Chrome (Tasks 5–6), per-account profiles (Task 6), identifier/chooser/password/confirm/consent/securitykey/microsoft states and `offsetParent` visibility (Task 3), `auth_success` as done and tab close (Task 3), idempotent gcloud short-circuit before any browser or 1Password work (Task 6 step 1), op-agent for the per-process-tree prompt (Task 4), admin key tap as an accepted manual step (skills, driver hint), `--no-startup-window` (Task 6), cleanup of the synced Google Chrome profile (Task 1 leftovers).
- **Placeholders:** none. `CHROMIUM_BUILD`, the op reference and all labels are literal.
- **Consistency:** driver flags and exit codes match between Task 3 code, Task 3 tests and Task 6 invocation; `GCLOUD_LOGIN_URL_FILE` matches Tasks 2 and 6; `op-agent read` semantics match Tasks 4, 6 and the skills; profile directory names `normal`/`admin` match Task 1 leftovers and Task 6.
