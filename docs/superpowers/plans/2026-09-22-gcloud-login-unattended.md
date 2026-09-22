# Unattended gcloud login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Claude (and the user) refresh gcloud CLI and Application Default Credentials for the ista Google accounts with one command and no manual clicks, and give Claude a skill that says which login fixes which failure.

**Architecture:** `gcloud-login` moves from a zsh function to a bash script in `~/.local/bin`. It reads the Google password from 1Password while peekaboo confirms the 1Password authorization window, launches Chrome on a dedicated profile with remote debugging, runs `gcloud auth login` with `BROWSER` pointed at a hook that only records the URL, and a zero-dependency Node driver opens that URL in the dedicated Chrome over the DevTools protocol and walks the Google pages until gcloud's localhost callback fires. Two skills in `~/.agents/skills` document when to call it and how it works.

**Tech Stack:** bash, Node 22 (global `WebSocket`, `node:test`), Chrome DevTools Protocol, 1Password CLI (`op`), peekaboo CLI, gcloud, chezmoi.

**Spec:** The design was settled in the grill-me session of 2026-09-22 and is recorded in the "Design" section below; there is no separate spec file.

## Global Constraints

- Shell scripts: `#!/usr/bin/env bash`, no extension, executable, Google Shell Style header with Purpose and Usage, `set -euo pipefail`, named parameters, colors via `tput` only (see `~/.config/agents/rules/bash.md`).
- Never a `.tmpl` where a runtime check works. Context check: `[[ "${DOTFILES_CONTEXT:-}" == ista ]]`.
- `exact_bin/`, `exact_conf.d/` remove files deleted from the repo on apply; always edit source state under `home/`.
- No `Co-Authored-By` or AI attribution in commits. Never commit on `main`; the branch is `feat/gcloud-login-unattended`.
- Node code: CommonJS, no dependencies beyond the Node 22 standard library. Test files use `node:test` and follow the naming rules in `~/.config/agents/rules/testing.md` (subject `Test`, nesting by context, "on …" phrasing, result stored before assertion).
- Passwords travel via bash variables and stdin only: never argv, never the clipboard, never a file.
- Identity policy: ADC is always the normal account; `--admin` only affects the CLI credential.
- Hardware-key challenges are out of scope: the script fails clearly and hands back.

---

## Design

### Accounts and secrets

| Role | Email | 1Password reference |
|---|---|---|
| normal | `bjoern.kahlert@ista-express.de` | `op://Employee/gzcxoxeug2wr2bq6moqkozamlq/password` |
| admin | `bjoern.kahlert.admin@ista-express.de` | `op://Employee/p44thhnd5ylh6zrm6etwozs63a/password` |

Items are referenced by ID because the admin item's title contains parentheses, which `op://` references reject.

### Verified facts the design relies on

- gcloud opens the browser with Python's `webbrowser.open`, which honors `$BROWSER`; a value containing `%s` becomes a `GenericBrowser` whose command is run and **waited for**. The hook must therefore exit immediately, or gcloud never serves its callback.
- `gcloud auth login [ACCOUNT]` and `gcloud auth application-default login [ACCOUNT]` both accept the account as a login hint. `--quiet` suppresses the "already authenticated, proceed?" prompt.
- gcloud's redirect URI is `http://localhost:<port>/?state=…&code=…`.
- Chrome 136+ refuses `--remote-debugging-port` on the default user-data-dir, so a dedicated `--user-data-dir` is required. With `--remote-debugging-port=0` Chrome writes `<user-data-dir>/DevToolsActivePort` (line 1: port, line 2: browser websocket path).
- The 1Password CLI "Access Requested" window on this Mac is confirmed by a plain click, not Touch ID. peekaboo has Screen Recording, Accessibility and event synthesis granted.
- The admin account re-authenticates every 10–15 minutes and Google asks for the password on re-auth, so the password path is the common path, not the fallback.
- Claude's Bash tool does not source `conf.d`, so a zsh function is invisible to it; `~/.local/bin` is on PATH and has `node` via nvm.

### Files

| Path (source) | Target | Responsibility |
|---|---|---|
| `home/dot_local/exact_bin/executable_gcloud-login` | `~/.local/bin/gcloud-login` | Orchestrator: args, `--status`, 1Password + peekaboo, Chrome lifecycle, gcloud, driver, cleanup |
| `home/dot_local/exact_bin/executable_gcloud-login-browser` | `~/.local/bin/gcloud-login-browser` | `$BROWSER` hook: writes the URL to `$GCLOUD_LOGIN_URL_FILE` and exits |
| `home/dot_local/exact_bin/executable_gcloud-login-driver` | `~/.local/bin/gcloud-login-driver` | Node: opens the URL in the debug Chrome, drives chooser / password / consent, exits on callback |
| `tests/gcloud-login-driver.test.js` | not applied (ignored) | `node:test` suite against fixture pages in headless Chrome |
| `home/dot_agents/skills/gcloud-auth/SKILL.md` | `~/.agents/skills/gcloud-auth/SKILL.md` | Skill 1: which login fixes which failure, identity policy |
| `home/dot_agents/skills/gcloud-login-automation/SKILL.md` | `~/.agents/skills/gcloud-login-automation/SKILL.md` | Skill 2: internals, failure modes, how to debug |
| `home/private_dot_claude/skills/symlink_gcloud-auth` | `~/.claude/skills/gcloud-auth` | Symlink into `~/.agents/skills`, same as grill-me |
| `home/private_dot_claude/skills/symlink_gcloud-login-automation` | `~/.claude/skills/gcloud-login-automation` | Same |
| `home/.chezmoiignore` | — | Ignore `tests/`; skip the two skills outside the ista context |
| `home/private_dot_config/zsh/exact_conf.d/exact_ista/10-gcloud.zsh` | `~/.config/zsh/conf.d/ista/10-gcloud.zsh` | **Deleted** (held only the old function) |
| `docs/superpowers/plans/2026-09-22-gcloud-login-findings.md` | — | Empirical findings from Task 1 |

### Process interfaces

`gcloud-login-driver` CLI:

```
gcloud-login-driver --port-file <path> --url-file <path> --email <email> [--timeout <seconds>]
  stdin: password (optional, may be empty or closed)
  exit 0: callback reached
  exit 1: usage or connection error
  exit 2: timeout; stderr: "gcloud-login-driver: timed out in state <state> at <url> (<title>)"
  exit 3: password page reached but no password on stdin
```

`gcloud-login-browser <url>`: writes `<url>` to `$GCLOUD_LOGIN_URL_FILE`, exit 0.

`gcloud-login`:

```
gcloud-login [--admin | --adc] [--status] [--timeout <seconds>]
  exit 0: logged in (or, with --status, every checked credential is valid)
  exit 1: precondition or credential failure (message on stderr)
  exit 2: browser flow did not complete within the timeout
```

### Page state machine (driver)

Polled every 500 ms through `Runtime.evaluate` on the login tab:

| state | detected by | action |
|---|---|---|
| `done` | URL matches `^http://(localhost\|127\.0\.0\.1):\d+/\?.*\bcode=` | exit 0 |
| `chooser` | element matching `[data-identifier="<email>"], [data-email="<email>"]` | click it |
| `password` | visible `input[type="password"]` | focus it, `Input.insertText`, press Enter; at most once per 5 s |
| `consent` | visible `button`/`[role=button]` whose trimmed text is one of Allow, Zulassen, Continue, Weiter | click it; at most once per 5 s |
| `unknown` | anything else | keep waiting |

Selectors and labels live in one `SELECTORS` constant at the top of the driver; Task 1 confirms or corrects them before Task 3 uses them.

---

### Task 1: Empirical round — record what the flow actually looks like

The user must be present for this task: the dedicated Chrome profile starts empty, so the first sign-in per account is a full Google login and may show a second factor.

**Files:**
- Create: `docs/superpowers/plans/2026-09-22-gcloud-login-findings.md`
- Scratch (not committed): `$SCRATCHPAD/probe.js`

**Interfaces:**
- Produces: confirmed values for `SELECTORS` (Task 3), the 1Password button label and window title (Task 4), and the list of failure modes (Task 5).

- [ ] **Step 1: Create the dedicated profile and launch Chrome with remote debugging**

```bash
PROFILE_DIR="$HOME/Library/Application Support/gcloud-login/chrome"
CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
mkdir -p "$PROFILE_DIR"
"$CHROME_BIN" --user-data-dir="$PROFILE_DIR" --remote-debugging-port=0 \
  --no-first-run --no-default-browser-check about:blank >/dev/null 2>&1 &
sleep 2; cat "$PROFILE_DIR/DevToolsActivePort"
```

Expected: two lines, a port number and `/devtools/browser/<uuid>`. A separate Chrome window appears next to the daily one.

- [ ] **Step 2: Write the probe that prints page state every second**

Save to `$SCRATCHPAD/probe.js`:

```js
// Prints url, title and candidate elements of every accounts.google.com /
// localhost tab once a second, so the page sequence can be recorded.
const fs = require('node:fs');
const [port, path] = fs.readFileSync(process.argv[2], 'utf8').trim().split('\n');
const ws = new WebSocket(`ws://127.0.0.1:${port}${path}`);
let id = 0; const pending = new Map();
const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
  const msgId = ++id; pending.set(msgId, { resolve, reject });
  ws.send(JSON.stringify({ id: msgId, method, params, sessionId }));
});
ws.onmessage = ev => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id).resolve(msg.result); pending.delete(msg.id); }
};
const PROBE = `(() => {
  const vis = el => !!el && el.getClientRects().length > 0;
  const buttons = [...document.querySelectorAll('button,[role="button"]')].filter(vis).map(b => b.textContent.trim()).filter(Boolean);
  const inputs = [...document.querySelectorAll('input')].filter(vis).map(i => i.type + ':' + (i.name || i.id || ''));
  const ids = [...document.querySelectorAll('[data-identifier],[data-email]')].map(e => e.dataset.identifier || e.dataset.email);
  return JSON.stringify({ url: location.href, title: document.title, buttons, inputs, ids });
})()`;
ws.onopen = async () => {
  setInterval(async () => {
    const { targetInfos } = await send('Target.getTargets');
    for (const t of targetInfos.filter(t => t.type === 'page' && /google\.com|localhost/.test(t.url))) {
      const { sessionId } = await send('Target.attachToTarget', { targetId: t.targetId, flatten: true });
      const { result } = await send('Runtime.evaluate', { expression: PROBE, returnByValue: true }, sessionId);
      console.log(new Date().toISOString(), result.value);
      await send('Target.detachFromTarget', { sessionId });
    }
  }, 1000);
};
```

Run in a second terminal: `node "$SCRATCHPAD/probe.js" "$PROFILE_DIR/DevToolsActivePort"`.

- [ ] **Step 3: Run the normal-account CLI login through the dedicated Chrome**

A second Chrome invocation with the same user-data-dir hands the URL to the running instance and exits at once, which is exactly what gcloud's `GenericBrowser` needs:

```bash
BROWSER="$CHROME_BIN --user-data-dir=$PROFILE_DIR %s" \
  gcloud auth login bjoern.kahlert@ista-express.de --quiet
```

Complete the login by hand in the dedicated window. Record in the findings file, per page: URL pattern, title, the `buttons`, `inputs`, `ids` the probe printed, UI language, and whether a second factor appeared.

- [ ] **Step 4: Repeat for the admin account**

```bash
BROWSER="$CHROME_BIN --user-data-dir=$PROFILE_DIR %s" \
  gcloud auth login bjoern.kahlert.admin@ista-express.de --quiet
```

Record the same. Then wait 15 minutes and run it again to capture the **re-auth** page sequence, which is the common case for admin.

- [ ] **Step 5: Repeat for ADC**

```bash
BROWSER="$CHROME_BIN --user-data-dir=$PROFILE_DIR %s" \
  gcloud auth application-default login bjoern.kahlert@ista-express.de --quiet
```

Record whether the account chooser appears despite the hint, and the exact consent button label (ADC requests more scopes than the CLI login).

- [ ] **Step 6: Capture the 1Password authorization window**

In one terminal start a read that will prompt (open a fresh terminal window so the per-tty authorization is not cached):

```bash
op read --no-newline "op://Employee/gzcxoxeug2wr2bq6moqkozamlq/password" >/dev/null
```

While the window is up, in another terminal:

```bash
peekaboo window list --app 1Password --json
peekaboo see --app 1Password --tree --no-screenshot
```

Record the window title and the exact button label (expected "Authorize"; may be localized). Then confirm a click works: start another `op read` from yet another fresh terminal and run

```bash
peekaboo click "<label>" --app 1Password --wait-for 15s
```

Expected: the `op read` returns with the password.

- [ ] **Step 7: Confirm `--status` cannot itself open a browser**

With the admin credential expired (15 minutes after Step 4), run:

```bash
gcloud config set account bjoern.kahlert.admin@ista-express.de
gcloud auth print-access-token --quiet; echo "exit=$?"
```

Expected: an error mentioning reauthentication and a non-zero exit, **no browser window**. If a browser opens, record it: `report_status` in Task 4 must then use `CLOUDSDK_CORE_DISABLE_PROMPTS=1` or `--no-user-output-enabled` instead of `--quiet`.

- [ ] **Step 8: Verify the session survives a Chrome restart**

Quit the dedicated Chrome (`pkill -f "user-data-dir=$PROFILE_DIR"`), relaunch it as in Step 1, and rerun Step 3. Record whether Google asked for the password again. Expected for the normal account: no password, consent only.

- [ ] **Step 9: Write the findings file**

`docs/superpowers/plans/2026-09-22-gcloud-login-findings.md` with sections: "Page sequences" (one table per flow: normal, admin fresh, admin re-auth, ADC), "Confirmed selectors" (the values to put into `SELECTORS`), "1Password window" (title, button label), "Unexpected pages" (anything the state machine would classify as `unknown`).

- [ ] **Step 10: Commit**

```bash
git add docs/superpowers/plans/2026-09-22-gcloud-login-findings.md
git commit -m "docs(gcloud-login): record the observed Google and 1Password page sequences"
```

---

### Task 2: `gcloud-login-browser` hook

**Files:**
- Create: `home/dot_local/exact_bin/executable_gcloud-login-browser`

**Interfaces:**
- Consumes: `$GCLOUD_LOGIN_URL_FILE` set by the orchestrator (Task 4).
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
# Usage:   BROWSER="gcloud-login-browser %s" gcloud auth login …
#          Requires GCLOUD_LOGIN_URL_FILE to point at the file to write.

set -euo pipefail

url=${1?url not set}
: "${GCLOUD_LOGIN_URL_FILE?GCLOUD_LOGIN_URL_FILE not set}"

printf '%s' "$url" >"$GCLOUD_LOGIN_URL_FILE"
```

```bash
chmod +x home/dot_local/exact_bin/executable_gcloud-login-browser
```

- [ ] **Step 3: Run the check**

Rerun Step 1. Expected: `PASS`.

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
- Consumes: `DevToolsActivePort` file of a Chrome started with `--remote-debugging-port=0`; URL file written by Task 2; password on stdin.
- Produces: exit codes 0/1/2/3 as defined in "Process interfaces"; `SELECTORS` constant adjusted to Task 1 findings.

- [ ] **Step 1: Ignore `tests/` in chezmoi**

Append to `home/.chezmoiignore` after the `docs/` line:

```
tests/
```

- [ ] **Step 2: Write the failing tests**

`tests/gcloud-login-driver.test.js`:

```js
// Tests for gcloud-login-driver against fixture pages that mimic the Google
// login sequence, served locally and opened in a headless Chrome.
const { test, describe, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');

const DRIVER = path.join(__dirname, '..', 'home', 'dot_local', 'exact_bin', 'executable_gcloud-login-driver');
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const EMAIL = 'someone@example.test';

describe('gcloud-login-driver', { skip: fs.existsSync(CHROME) ? false : 'Chrome not installed' }, () => {
  let chrome, fixture;

  before(async () => {
    chrome = await launchChrome();
    fixture = await startFixture();
  });

  after(() => {
    chrome.kill();
    fixture.server.close();
  });

  describe('on chooser, password and consent pages', () => {
    test('reaches the callback and exits 0', async () => {
      const result = await runDriver({ url: `${fixture.origin}/chooser`, password: 'hunter2' });
      assert.equal(result.code, 0, result.stderr);
      assert.deepEqual(fixture.seen(), { password: 'hunter2', callback: true });
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

  // --- helpers -------------------------------------------------------------

  async function launchChrome() {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gcloud-login-driver-test-'));
    const proc = spawn(CHROME, [
      `--user-data-dir=${dir}`, '--remote-debugging-port=0', '--headless=new',
      '--no-first-run', '--no-default-browser-check', 'about:blank',
    ], { stdio: 'ignore' });
    const portFile = path.join(dir, 'DevToolsActivePort');
    for (let i = 0; i < 100 && !fs.existsSync(portFile); i++) await sleep(100);
    assert.ok(fs.existsSync(portFile), 'Chrome did not write DevToolsActivePort');
    return { portFile, kill: () => proc.kill() };
  }

  // Fixture pages: /chooser -> /password -> /consent -> /?code=… (callback).
  // Navigation between them mirrors the real flow: chooser click, password
  // form submit on Enter, consent button click.
  async function startFixture() {
    const seen = { password: null, callback: false };
    const server = http.createServer((req, res) => {
      const url = new URL(req.url, 'http://127.0.0.1');
      const page = body => { res.setHeader('Content-Type', 'text/html'); res.end(`<!doctype html><title>${url.pathname}</title>${body}`); };
      switch (url.pathname) {
        case '/chooser':
          return page(`<div data-identifier="${EMAIL}" onclick="location='/password'">${EMAIL}</div>`);
        case '/password':
          return page(`<form action="/consent" method="get"><input type="password" name="Passwd"></form>`);
        case '/consent':
          seen.password = url.searchParams.get('Passwd');
          return page(`<button onclick="location='/?state=s&code=c'">Allow</button>`);
        case '/':
          seen.callback = url.searchParams.get('code') === 'c';
          return page('<p>You are now authenticated.</p>');
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
      DRIVER, '--port-file', chrome.portFile, '--url-file', urlFile,
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

- [ ] **Step 3: Run the tests to verify they fail**

Run: `node --test tests/gcloud-login-driver.test.js`
Expected: three failures, the driver file does not exist (`spawn` error / exit code null).

- [ ] **Step 4: Write the driver**

`home/dot_local/exact_bin/executable_gcloud-login-driver`. Replace the values in `SELECTORS` with the confirmed ones from the findings file if they differ.

```js
#!/usr/bin/env node
// Purpose: Drive the Google OAuth pages that `gcloud auth login` opens, inside
//          the Chrome instance identified by a DevToolsActivePort file, until
//          Google redirects to gcloud's localhost callback. No dependencies
//          beyond Node 22 (global WebSocket).
// Usage:   gcloud-login-driver --port-file <path> --url-file <path> --email <email>
//                              [--timeout <seconds>]
//          The password, if needed, is read from stdin.
// Exit:    0 callback reached · 1 usage or connection error
//          2 timed out (stderr names state, url, title) · 3 password page, no password

const fs = require('node:fs');
const { parseArgs } = require('node:util');

// Confirmed against the real pages in the empirical round; see
// docs/superpowers/plans/2026-09-22-gcloud-login-findings.md.
const SELECTORS = {
  password: 'input[type="password"]',
  chooser: email => `[data-identifier="${email}"], [data-email="${email}"]`,
  consentLabels: ['Allow', 'Zulassen', 'Continue', 'Weiter'],
  callback: /^http:\/\/(localhost|127\.0\.0\.1):\d+\/\?.*\bcode=/,
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
      ws.onerror = () => reject(new Error(`cannot connect to Chrome on port ${port}`));
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

const STATE_SCRIPT = (email) => `(() => {
  const visible = el => !!el && el.getClientRects().length > 0;
  const url = location.href, title = document.title;
  if (${SELECTORS.callback}.test(url)) return { url, title, state: 'done' };
  if (visible(document.querySelector(${JSON.stringify(SELECTORS.password)}))) return { url, title, state: 'password' };
  if (document.querySelector(${JSON.stringify(SELECTORS.chooser(email))})) return { url, title, state: 'chooser' };
  const labels = ${JSON.stringify(SELECTORS.consentLabels)};
  const buttons = [...document.querySelectorAll('button, [role="button"]')].filter(visible);
  if (buttons.some(b => labels.includes(b.textContent.trim()))) return { url, title, state: 'consent' };
  return { url, title, state: 'unknown' };
})()`;

const CLICK_CHOOSER = (email) =>
  `document.querySelector(${JSON.stringify(SELECTORS.chooser(email))}).click()`;

const FOCUS_PASSWORD = `document.querySelector(${JSON.stringify(SELECTORS.password)}).focus()`;

const CLICK_CONSENT = `(() => {
  const visible = el => !!el && el.getClientRects().length > 0;
  const labels = ${JSON.stringify(SELECTORS.consentLabels)};
  [...document.querySelectorAll('button, [role="button"]')]
    .filter(visible).find(b => labels.includes(b.textContent.trim())).click();
})()`;

function readStdin() {
  try {
    return fs.readFileSync(0, 'utf8').replace(/\n$/, '');
  } catch {
    return '';
  }
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

async function pressEnter(cdp, sessionId) {
  const key = { key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 };
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', ...key }, sessionId);
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', ...key }, sessionId);
}

async function drive({ portFile, urlFile, email, timeoutMs, password }) {
  const deadline = Date.now() + timeoutMs;
  const url = await waitForFile(urlFile, deadline);
  const cdp = await Cdp.connect(portFile);
  try {
    const { targetId } = await cdp.send('Target.createTarget', { url });
    const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
    await cdp.send('Page.enable', {}, sessionId);
    await cdp.send('Runtime.enable', {}, sessionId);
    await cdp.send('Page.bringToFront', {}, sessionId); // Input.insertText needs a focused tab

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
      if (last.state === 'done') return 0;
      if (Date.now() - lastAction > ACTION_COOLDOWN_MS) {
        if (last.state === 'chooser') {
          await cdp.send('Runtime.evaluate', { expression: CLICK_CHOOSER(email) }, sessionId);
          lastAction = Date.now();
        } else if (last.state === 'password') {
          if (!password) {
            process.stderr.write(`gcloud-login-driver: password page reached but no password on stdin (${last.url})\n`);
            return 3;
          }
          await cdp.send('Runtime.evaluate', { expression: FOCUS_PASSWORD }, sessionId);
          await cdp.send('Input.insertText', { text: password }, sessionId);
          await pressEnter(cdp, sessionId);
          lastAction = Date.now();
        } else if (last.state === 'consent') {
          await cdp.send('Runtime.evaluate', { expression: CLICK_CONSENT }, sessionId);
          lastAction = Date.now();
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
      timeout: { type: 'string', default: '90' },
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
Expected: 3 passing. If the consent test times out, check that headless Chrome delivered the synthetic click; `Runtime.evaluate` `.click()` on a `<button>` works in headless=new.

- [ ] **Step 6: Commit**

```bash
git add home/.chezmoiignore home/dot_local/exact_bin/executable_gcloud-login-driver tests/gcloud-login-driver.test.js
git commit -m "feat(gcloud-login): add the DevTools-protocol driver for the Google login pages"
```

---

### Task 4: `gcloud-login` orchestrator, replacing the zsh function

**Files:**
- Create: `home/dot_local/exact_bin/executable_gcloud-login`
- Delete: `home/private_dot_config/zsh/exact_conf.d/exact_ista/10-gcloud.zsh`

**Interfaces:**
- Consumes: `gcloud-login-browser` (Task 2), `gcloud-login-driver` (Task 3), `op`, `peekaboo`, `gcloud`, `jq`, `curl`.
- Produces: the command the skills (Task 5) tell Claude to run; exit codes per "Process interfaces".

- [ ] **Step 1: Write the failing checks**

Argument handling and `--status` can be checked without a browser:

```bash
s=home/dot_local/exact_bin/executable_gcloud-login
DOTFILES_CONTEXT=bkahlert "$s" --status; echo "exit=$? (want 1, context message)"
"$s" --admin --adc; echo "exit=$? (want 1, mutually exclusive)"
"$s" --bogus; echo "exit=$? (want 1, unknown option)"
"$s" --status; echo "exit=$? (want 0 or 1 with two report lines)"
```

Expected now: `no such file` for all four.

- [ ] **Step 2: Write the script**

Replace `ONEPASSWORD_BUTTON` with the label recorded in the findings file if it is not "Authorize".

```bash
#!/usr/bin/env bash
# Purpose: Log the gcloud CLI, or Application Default Credentials, into one of
#          the ista Google accounts without manual interaction. The Google
#          password comes from 1Password (the authorization window is confirmed
#          with peekaboo), Google's pages are driven in a dedicated Chrome
#          profile over the DevTools protocol by gcloud-login-driver.
# Usage:   gcloud-login [--admin | --adc] [--status] [--timeout <seconds>]
#          --admin    log the CLI into the admin account
#          --adc      refresh Application Default Credentials (always the normal account)
#          --status   report CLI account, ADC identity and token validity; exit 0 if all valid
#          --timeout  seconds to wait for the browser flow (default 90)
# Exit:    0 success · 1 precondition or credential failure · 2 browser flow timed out

set -euo pipefail

readonly NORMAL_EMAIL="bjoern.kahlert@ista-express.de"
readonly ADMIN_EMAIL="bjoern.kahlert.admin@ista-express.de"
# Items by ID: the admin item's title, "Google (Admin)", has parentheses,
# which op:// references reject.
readonly NORMAL_OP_REF="op://Employee/gzcxoxeug2wr2bq6moqkozamlq/password"
readonly ADMIN_OP_REF="op://Employee/p44thhnd5ylh6zrm6etwozs63a/password"
readonly ONEPASSWORD_BUTTON="Authorize"
readonly CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
readonly PROFILE_DIR="$HOME/Library/Application Support/gcloud-login/chrome"
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
timeout=90
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
for tool in gcloud op peekaboo jq curl node gcloud-login-driver gcloud-login-browser; do
  command -v "$tool" >/dev/null || die "gcloud-login: $tool not found"
done
[[ -x "$CHROME_BIN" ]] || die "gcloud-login: Chrome not found at $CHROME_BIN"

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

# --- 1Password ----------------------------------------------------------------

# op read blocks until the desktop app's "Access Requested" window is
# confirmed; peekaboo presses the button from a second process. When the
# terminal is still authorized no window appears, op returns at once and the
# waiting click is cancelled.
read_password() {
  local op_ref=$1 click_pid
  peekaboo click "$ONEPASSWORD_BUTTON" --app 1Password --wait-for 20s >/dev/null 2>&1 &
  click_pid=$!
  password=$(op read --no-newline "$op_ref") || {
    kill "$click_pid" 2>/dev/null || true
    return 1
  }
  kill "$click_pid" 2>/dev/null || true
  wait "$click_pid" 2>/dev/null || true
  [[ -n "$password" ]]
}

# --- Chrome -------------------------------------------------------------------

chrome_pid=""
start_chrome() {
  mkdir -p "$PROFILE_DIR"
  # A leftover instance from an aborted run would swallow the new launch.
  pkill -f -- "--user-data-dir=${PROFILE_DIR}" 2>/dev/null || true
  rm -f "$PROFILE_DIR/DevToolsActivePort"
  "$CHROME_BIN" --user-data-dir="$PROFILE_DIR" --remote-debugging-port=0 \
    --no-first-run --no-default-browser-check about:blank >/dev/null 2>&1 &
  chrome_pid=$!
  local i
  for ((i = 0; i < 50; i++)); do
    [[ -s "$PROFILE_DIR/DevToolsActivePort" ]] && return 0
    sleep 0.2
  done
  die "gcloud-login: Chrome did not expose its DevTools port"
}

url_file=""
gcloud_pid=""
cleanup() {
  [[ -n "$gcloud_pid" ]] && kill "$gcloud_pid" 2>/dev/null || true
  [[ -n "$chrome_pid" ]] && kill "$chrome_pid" 2>/dev/null || true
  [[ -n "$url_file" ]] && rm -f "$url_file"
}
trap cleanup EXIT

# --- login --------------------------------------------------------------------

case $mode in
  admin) email=$ADMIN_EMAIL; op_ref=$ADMIN_OP_REF; gcloud_cmd=(gcloud auth login "$email" --quiet) ;;
  adc)   email=$NORMAL_EMAIL; op_ref=$NORMAL_OP_REF; gcloud_cmd=(gcloud auth application-default login "$email" --quiet) ;;
  cli)   email=$NORMAL_EMAIL; op_ref=$NORMAL_OP_REF; gcloud_cmd=(gcloud auth login "$email" --quiet) ;;
esac

info "Reading the password for $email from 1Password"
password=""
read_password "$op_ref" || die "gcloud-login: could not read the password from 1Password ($op_ref)"

info "Starting Chrome on the dedicated profile"
start_chrome

url_file=$(mktemp)
rm -f "$url_file"
export GCLOUD_LOGIN_URL_FILE="$url_file"
gcloud_log=$(mktemp)

info "Running: ${gcloud_cmd[*]}"
BROWSER="gcloud-login-browser %s" "${gcloud_cmd[@]}" >"$gcloud_log" 2>&1 &
gcloud_pid=$!

driver_status=0
printf '%s' "$password" | gcloud-login-driver \
  --port-file "$PROFILE_DIR/DevToolsActivePort" --url-file "$url_file" \
  --email "$email" --timeout "$timeout" || driver_status=$?
unset password

if (( driver_status != 0 )); then
  # Leave the page visible so the user can finish a challenge the driver does
  # not handle (hardware key, new consent screen), and give gcloud one more
  # timeout window to receive the callback.
  peekaboo window focus --pid "$chrome_pid" >/dev/null 2>&1 || true
  warn "gcloud-login: automation stopped (driver exit $driver_status); finish the login in the Chrome window or press Ctrl-C"
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
rm -f "$gcloud_log"
if (( driver_status == 2 )); then
  die "gcloud-login: browser flow timed out" 2
fi
die "gcloud-login: gcloud did not complete the login"
```

```bash
chmod +x home/dot_local/exact_bin/executable_gcloud-login
```

- [ ] **Step 3: Run the checks**

Rerun Step 1. Expected:

```
✘ gcloud-login: only available in the ista context      exit=1
✘ gcloud-login: --admin and --adc are mutually exclusive exit=1
✘ gcloud-login: unknown option --bogus …                exit=1
CLI account:  bjoern.kahlert.admin@ista-express.de (valid|needs login)
ADC identity: <email> (valid|needs login)               exit=0 or 1
```

- [ ] **Step 4: Remove the zsh function**

```bash
git rm home/private_dot_config/zsh/exact_conf.d/exact_ista/10-gcloud.zsh
```

The file contained only the `gcloud-login` function; `exact_conf.d/exact_ista/` removes the target on the next apply.

- [ ] **Step 5: Commit**

```bash
git add home/dot_local/exact_bin/executable_gcloud-login
git commit -m "feat(gcloud-login): move to ~/.local/bin and drive the login unattended"
```

---

### Task 5: The two skills, their symlinks, and the context ignore

**Files:**
- Create: `home/dot_agents/skills/gcloud-auth/SKILL.md`
- Create: `home/dot_agents/skills/gcloud-login-automation/SKILL.md`
- Create: `home/private_dot_claude/skills/symlink_gcloud-auth`
- Create: `home/private_dot_claude/skills/symlink_gcloud-login-automation`
- Modify: `home/.chezmoiignore`

**Interfaces:**
- Consumes: the `gcloud-login` CLI (Task 4) and the findings file (Task 1) for the failure-mode section.

- [ ] **Step 1: Write the failing check**

```bash
chezmoi managed | grep -E '\.(agents|claude)/skills/gcloud-' ; echo "exit=$? (want 0 with four entries)"
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

## Identity policy

- **ADC is always the normal account.** `gcloud-login --adc` cannot be combined with `--admin`. If `--status` shows the admin email as ADC identity, run `gcloud-login --adc` to correct it.
- **CLI defaults to the normal account.** Switch to admin only for a concrete `PERMISSION_DENIED` on IAM, organization or project-level resources:
  - both accounts are usually credentialed, so first try `gcloud config set account bjoern.kahlert.admin@ista-express.de` and re-run;
  - if that fails with a reauthentication error, run `gcloud-login --admin`;
  - when the admin operation is done, run `gcloud config set account bjoern.kahlert@ista-express.de`. Never leave admin active at the end of a task.
- The admin credential expires every 10–15 minutes. Expect `gcloud-login --admin` more than once in a long admin session; that is normal.

## What not to do

- Do not tell the user to run `gcloud auth login`; `gcloud-login` does it without interaction.
- Do not run `gcloud auth login` or `gcloud auth application-default login` directly: they open the user's daily browser and wait for clicks.
- Do not use admin for ADC, for deployments, or "just in case".

## Exit codes of gcloud-login

0 logged in · 1 precondition or credential failure (message on stderr) · 2 browser flow timed out, the Chrome window is left open for the user.
```

- [ ] **Step 3: Write skill 2**

`home/dot_agents/skills/gcloud-login-automation/SKILL.md`. Fill the "Failure modes" table from the findings file; keep the rows below that apply.

```markdown
---
name: gcloud-login-automation
description: Use when `gcloud-login` fails, hangs, or needs a change (new Google page, new consent button label, 1Password window changed, Chrome update), or when asked how the unattended gcloud login works. Explains the components (1Password + peekaboo, dedicated Chrome profile, DevTools driver), where each lives, how to debug a run and how to extend the selectors.
---

# gcloud-login automation

`gcloud-login` (`~/.local/bin`, source `home/dot_local/exact_bin/executable_gcloud-login` in the dotfiles repo) logs the gcloud CLI or ADC into an ista Google account with no manual step.

## Flow

1. `op read` fetches the Google password from the Employee vault. The 1Password desktop app shows its "Access Requested" window once per terminal; a background `peekaboo click "Authorize" --app 1Password --wait-for 20s` confirms it. If the terminal is still authorized the window never appears and the click is cancelled.
2. Chrome starts on the dedicated profile `~/Library/Application Support/gcloud-login/chrome` with `--remote-debugging-port=0`; the port is read from `DevToolsActivePort` in that directory. Google sessions live in this profile, so the normal account usually needs no password after the first run.
3. `gcloud auth login <email> --quiet` (or `application-default login`) runs with `BROWSER="gcloud-login-browser %s"`. gcloud waits for the browser command, so the hook only writes the URL to `$GCLOUD_LOGIN_URL_FILE` and exits.
4. `gcloud-login-driver` (Node, no dependencies) opens that URL in the debug Chrome and polls the page every 500 ms: account chooser → click the entry for the email; password field → insert the password from stdin and press Enter; consent button (Allow / Zulassen / Continue / Weiter) → click; URL `http://localhost:<port>/?…code=` → done.
5. gcloud receives the callback and exits; Chrome is quit; the password variable is unset.

## Debugging a failed run

- Driver exit 2 prints `timed out in state <state> at <url> (<title>)`. State `unknown` means a page the state machine does not know; the Chrome window is left open and focused, so look at it.
- Driver exit 3 means Google asked for a password although none was read; the 1Password step failed silently. Run `op read --no-newline "op://Employee/gzcxoxeug2wr2bq6moqkozamlq/password" | wc -c` in the same terminal to check.
- No `DevToolsActivePort`: a stale Chrome on the same profile (the script kills it via `pkill -f -- "--user-data-dir=…"`) or Chrome moved; check `CHROME_BIN` in the script.
- The 1Password click does nothing: the button label or window changed. Start `op read` in a fresh terminal and run `peekaboo see --app 1Password --tree --no-screenshot`; update `ONEPASSWORD_BUTTON`.
- Tests for the driver: `node --test tests/gcloud-login-driver.test.js` in the dotfiles repo (headless Chrome against fixture pages).

## Extending the selectors

All page knowledge sits in the `SELECTORS` constant at the top of `gcloud-login-driver`. To learn what a new page looks like, run the probe from the findings file (`docs/superpowers/plans/2026-09-22-gcloud-login-findings.md`) against the debug Chrome while logging in by hand.

## Failure modes seen

| Situation | Symptom | Handling |
|---|---|---|
| Admin session expired (every 10–15 min) | Google shows the password page on re-auth | Normal path: password from 1Password |
| Hardware-key challenge | state `unknown`, security-key page | Out of scope; finish in the open Chrome window |
| First run on a fresh profile | full sign-in incl. second factor | Complete once by hand; sessions persist afterwards |
```

- [ ] **Step 4: Create the symlink sources**

```bash
printf '../../.agents/skills/gcloud-auth' > home/private_dot_claude/skills/symlink_gcloud-auth
printf '../../.agents/skills/gcloud-login-automation' > home/private_dot_claude/skills/symlink_gcloud-login-automation
```

(Same relative form as the existing `~/.claude/skills/grill-me` link.)

- [ ] **Step 5: Ignore the skills outside the ista context**

`.chezmoiignore` is always rendered as a template. Append to `home/.chezmoiignore`:

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
chezmoi execute-template --init --promptString company=bkahlert --promptString name=x --promptString email=x < home/.chezmoiignore | grep -c 'skills/gcloud-'
```

Expected: four managed paths; the second command prints `0` (this machine is ista, the block is not rendered); the third prints `4` (rendered for a non-ista company). If `--init` rejects the prompt flags on this chezmoi version, drop the third command and rely on `make build && make validate`, whose container has an empty company.

- [ ] **Step 7: Commit**

```bash
git add home/dot_agents home/private_dot_claude/skills home/.chezmoiignore
git commit -m "feat(skills): add gcloud-auth and gcloud-login-automation skills"
```

---

### Task 6: Apply and verify end to end

**Files:** none new.

- [ ] **Step 1: Preview and apply**

```bash
chezmoi diff
chezmoi apply -n
chezmoi apply
```

Expected in the diff: three new executables in `~/.local/bin`, two SKILL.md files, two symlinks, removal of `~/.config/zsh/conf.d/ista/10-gcloud.zsh`. Any unrelated drift is handled per the CLAUDE.md "Offer 1" rules.

- [ ] **Step 2: Verify the shell sees the command and Claude's shell too**

From an interactive zsh:

```bash
whence -v gcloud-login            # → file ~/.local/bin/gcloud-login
gcloud-login --status
```

From Claude's Bash tool: `command -v gcloud-login && gcloud-login --status`. Expected: same two report lines.

- [ ] **Step 3: Unattended runs, hands off the keyboard**

```bash
gcloud-login            # normal CLI
gcloud-login --adc      # ADC, normal account
gcloud-login --admin    # admin CLI (password path)
gcloud-login --status   # → both valid, ADC identity is the normal email, exit 0
```

Expected: each ends with `✔ Logged in (…) as …` and no click by the user. Record any `timed out in state` message in the findings file and adjust `SELECTORS` / `ONEPASSWORD_BUTTON`, then rerun `node --test tests/gcloud-login-driver.test.js`.

- [ ] **Step 4: Verify the skills load**

In a new Claude Code session type `/gcloud-auth`; expected: the skill text appears. Ask "my gcloud command fails with Reauthentication required"; expected: Claude runs `gcloud-login --status` then `gcloud-login`, not `gcloud auth login`.

- [ ] **Step 5: Commit any corrections and record findings**

```bash
git add -A home docs/superpowers/plans/2026-09-22-gcloud-login-findings.md
git commit -m "fix(gcloud-login): adjust selectors to the observed pages"
```

Only if something changed. Then offer the ship flow (push, PR, squash-merge) per CLAUDE.md.

---

## Self-review

- **Spec coverage:** identity policy (Task 5 skill 1, `--adc` forced to normal in Task 4), `--status` (Task 4), 1Password click (Task 4, label confirmed in Task 1), dedicated Chrome + DevTools driver (Tasks 3–4), BROWSER hook (Task 2), zsh function moved to bin (Task 4), two skills ista-only and linked like grill-me (Task 5), empirical round first (Task 1), hand-off on unexpected pages (Task 3 exit 2, Task 4 focus + grace wait), password never in argv/clipboard/file (Task 4 uses a variable and stdin). Not covered on purpose: Gemini/Copilot skill links (Claude only), the one-time manual sign-in is not scripted.
- **Placeholders:** none; `ONEPASSWORD_BUTTON` and `SELECTORS` have defaults and an explicit correction step.
- **Consistency:** driver flags `--port-file/--url-file/--email/--timeout` match between Task 3 code, Task 3 tests and Task 4 invocation; exit codes 0/1/2/3 match the interface table; `GCLOUD_LOGIN_URL_FILE` name matches Tasks 2 and 4.
