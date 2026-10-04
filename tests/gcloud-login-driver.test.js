// Tests for gcloud-login-driver against fixture pages that mimic the Google
// login sequence, served locally and opened in a headless Chromium.
const { test, describe, before, beforeEach, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const https = require('node:https');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, execFileSync } = require('node:child_process');

const DRIVER = path.join(__dirname, '..', 'home', 'dot_local', 'exact_bin', 'executable_gcloud-login-driver');
const EMAIL = 'someone@example.test';
const GOOGLE_HOST = 'accounts.google.com';
const LOOKALIKE_HOST = 'accounts.google.com.evil.test';

function findChromium() {
  const root = path.join(os.homedir(), '.cache', 'gcloud-login', 'chromium');
  if (!fs.existsSync(root)) return null;
  for (const dir of fs.readdirSync(root)) {
    const bin = path.join(root, dir, 'chrome-mac', 'Chromium.app', 'Contents', 'MacOS', 'Chromium');
    if (fs.existsSync(bin)) return bin;
  }
  return null;
}

const CHROMIUM = process.env.CHROMIUM_BIN || findChromium();
if (!CHROMIUM && process.env.CI) {
  throw new Error('no Chromium found; set CHROMIUM_BIN (the driver test must not skip on CI)');
}

describe('gcloud-login-driver', { skip: CHROMIUM ? false : 'Chromium not installed (run gcloud-login once, or set CHROMIUM_BIN)' }, () => {
  let chromium, fixture;

  before(async () => {
    fixture = await startFixture();
    chromium = await launchChromium({ hostRules: fixture.hostRules });
  });

  after(async () => {
    // The server must close even if Chromium cleanup fails: an open listener keeps node alive forever.
    // Either may be unset when `before` failed halfway.
    try { await chromium?.kill(); } finally { fixture?.close(); }
  }, { timeout: 20_000 });

  describe('on identifier, chooser, password, oauth-signin-interstitial and consent pages', () => {
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
      const result = await runDriver({ url: `${fixture.googleOrigin}/password`, password: '' });
      assert.equal(result.code, 3);
      assert.match(result.stderr, /password/);
    });
  });

  describe('on a password page of a host that is not Google', () => {
    beforeEach(() => fixture.reset());

    for (const [name, origin] of [
      ['an unrelated host', () => fixture.origin],
      ['a host that merely starts with the Google login host', () => fixture.lookalikeOrigin],
      // Plain http://accounts.google.com cannot be tested: Chromium upgrades
      // it to https (preloaded HSTS) before any page loads. The port is the
      // part of the origin that can still differ on the real host.
      ['the Google login host on another port', () => fixture.googleOtherPortOrigin],
    ]) {
      test(`exits 4, names the host and does not type the password on ${name}`, async () => {
        const result = await runDriver({ url: `${origin()}/password`, password: 'hunter2' });
        assert.equal(result.code, 4, result.stderr);
        assert.match(result.stderr, new RegExp(`password page on unexpected host ${new URL(origin()).host.replaceAll('.', '\\.')}\\b`));
        assert.equal(fixture.seen().password, null);
      });
    }

    test('exits 4 even when no password was supplied', async () => {
      const result = await runDriver({ url: `${fixture.origin}/password`, password: '' });
      assert.equal(result.code, 4, result.stderr);
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

  describe('on a Chromium that exited on its own', () => {
    test('kill() resolves instead of waiting for an exit that already happened', async () => {
      const extra = await launchChromium();
      process.kill(extra.pid);
      await extra.exited;
      const outcome = await Promise.race([extra.kill().then(() => 'resolved'), sleep(3000).then(() => 'hung')]);
      assert.equal(outcome, 'resolved');
    });
  });

  describe('on a browser that never writes its DevTools port', () => {
    test('fails with its stderr and leaves no process behind', async () => {
      const silent = fakeBrowser('echo oops >&2\nexec sleep 60');
      const failure = await launchChromium({ bin: silent, timeoutMs: 500 }).then(() => null, e => e);
      assert.match(failure?.message, /did not write DevToolsActivePort after \d+ ms/);
      assert.match(failure.message, /oops/);
      assert.equal(await isAlive(failure.pid), false);
    });
  });

  describe('on a browser that exits at startup', () => {
    test('fails at once with its exit code and stderr', async () => {
      const crashing = fakeBrowser('echo boom >&2\nexit 7');
      const started = Date.now();
      const failure = await launchChromium({ bin: crashing, timeoutMs: 20_000 }).then(() => null, e => e);
      assert.match(failure?.message, /exitCode 7/);
      assert.match(failure.message, /boom/);
      assert.ok(Date.now() - started < 5000, 'waited for the full timeout');
    });
  });

  // --- helpers -------------------------------------------------------------

  function fakeBrowser(body) {
    const bin = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gcloud-login-driver-test-')), 'browser');
    fs.writeFileSync(bin, `#!/bin/sh\n${body}\n`, { mode: 0o755 });
    return bin;
  }

  async function isAlive(pid) {
    for (let i = 0; i < 20; i++) {
      try { process.kill(pid, 0); } catch { return false; }
      await sleep(100);
    }
    return true;
  }

  async function launchChromium({ bin = CHROMIUM, timeoutMs = 30_000, hostRules = '' } = {}) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gcloud-login-driver-test-'));
    const proc = spawn(bin, [
      `--user-data-dir=${dir}`, '--remote-debugging-port=0', '--headless=new',
      '--no-first-run', '--no-default-browser-check',
      // The fixture answers for the real Google login host and a lookalike,
      // so the driver's origin check sees the names it will see in
      // production. Both are served over TLS with a throwaway certificate:
      // Chromium upgrades google.com to https (preloaded HSTS).
      '--ignore-certificate-errors',
      `--host-resolver-rules=${hostRules}`,
      // This throwaway profile stores nothing worth encrypting, and without
      // these macOS pops a "Keychain Not Found" dialog on the user's screen.
      // gcloud-login's real launch must NOT use them: the normal and admin
      // profiles' cookies are tied to the existing Chromium Safe Storage
      // keychain item.
      '--use-mock-keychain', '--password-store=basic',
      'about:blank',
    ], { stdio: ['ignore', 'ignore', 'pipe'], detached: true });
    let stderr = '';
    proc.stderr.on('data', d => { stderr += d; });
    // Remove the throwaway profile only after Chromium exited; it writes to
    // the profile while shutting down and would recreate parts of it. On
    // Linux Chromium may already be gone, and SIGTERM is not always enough.
    // Its helper processes (zygote, GPU, network) can outlive the main
    // process and keep writing into the profile, so the whole process group
    // is killed before the profile goes; rm retries while the last of them
    // dies, instead of failing with ENOTEMPTY.
    const kill = async () => {
      if (proc.exitCode === null && proc.signalCode === null) {
        const exit = new Promise(resolve => proc.once('exit', resolve));
        const hammer = setTimeout(() => proc.kill('SIGKILL'), 5000);
        proc.kill();
        await exit;
        clearTimeout(hammer);
      }
      try { process.kill(-proc.pid, 'SIGKILL'); } catch { /* group already gone */ }
      await fs.promises.rm(dir, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
    };
    const portFile = path.join(dir, 'DevToolsActivePort');
    const started = Date.now();
    while (!fs.existsSync(portFile)) {
      const exited = proc.exitCode !== null || proc.signalCode !== null;
      if (exited || Date.now() - started > timeoutMs) {
        // A browser that stays behind keeps node, and so the CI job, alive.
        await kill();
        throw Object.assign(new Error(
          `Chromium did not write DevToolsActivePort after ${Date.now() - started} ms `
          + `(exitCode ${proc.exitCode}, signal ${proc.signalCode})\n${stderr.trim()}`,
        ), { pid: proc.pid });
      }
      await sleep(100);
    }
    const port = fs.readFileSync(portFile, 'utf8').split('\n')[0];
    return {
      portFile,
      pid: proc.pid,
      exited: new Promise(resolve => proc.once('exit', resolve)),
      kill,
      pages: async () => (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).filter(t => t.type === 'page'),
    };
  }

  // Fixture pages mirror the real navigation: identifier form (Enter) ->
  // chooser (click) -> password form (Enter) -> oauth/id interstitial
  // (click Continue) -> consent (click) -> callback. The password page is
  // reached under the Google login host, the callback under 127.0.0.1 as
  // gcloud's local server is.
  async function startFixture() {
    const seen = { identifier: null, password: null, callback: false };
    let origin, googleOrigin;
    const handler = (req, res) => {
      const url = new URL(req.url, 'http://127.0.0.1');
      const page = body => { res.setHeader('Content-Type', 'text/html'); res.end(`<!doctype html><title>${url.pathname}</title>${body}`); };
      switch (url.pathname) {
        case '/identifier':
          return page(`<form action="/chooser" method="get"><input type="text" name="identifier"></form>`);
        case '/chooser':
          seen.identifier = url.searchParams.get('identifier') ?? seen.identifier;
          return page(`<div role="link" data-identifier="${EMAIL}" onclick="location='${googleOrigin}/password'">${EMAIL}</div>`);
        case '/password':
          return page(`<form action="${origin}/signin/oauth/id" method="get"><input type="password" name="Passwd"></form>`);
        case '/signin/oauth/id':
          seen.password = url.searchParams.get('Passwd') ?? seen.password;
          return page(`<button>Cancel</button><button onclick="location='/signin/oauth/consent'">Continue</button>`);
        case '/signin/oauth/consent':
          return page(`<button onclick="location='/?state=s&code=c'">Allow</button>`);
        case '/':
          seen.callback = url.searchParams.get('code') === 'c';
          return page('<p>You are now authenticated.</p>');
        case '/v3/signin/challenge/sk/webauthn':
          return page('<p>Complete sign-in using your security key</p><button>Try another way</button>');
        default:
          return page('<p>Something else</p>');
      }
    };
    const server = http.createServer(handler);
    const tlsServer = https.createServer(selfSignedCertificate(), handler);
    await Promise.all([server, tlsServer].map(s => new Promise(resolve => s.listen(0, '127.0.0.1', resolve))));
    origin = `http://127.0.0.1:${server.address().port}`;
    googleOrigin = `https://${GOOGLE_HOST}`;
    const tlsTarget = `127.0.0.1:${tlsServer.address().port}`;
    return {
      origin,
      googleOrigin,
      lookalikeOrigin: `https://${LOOKALIKE_HOST}`,
      googleOtherPortOrigin: `https://${GOOGLE_HOST}:${tlsServer.address().port}`,
      hostRules: `MAP ${GOOGLE_HOST} ${tlsTarget}, MAP ${LOOKALIKE_HOST} ${tlsTarget}`,
      close: () => { server.close(); tlsServer.close(); },
      seen: () => ({ ...seen }),
      reset: () => Object.assign(seen, { identifier: null, password: null, callback: false }),
    };
  }

  function selfSignedCertificate() {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gcloud-login-driver-test-'));
    try {
      execFileSync('openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1', '-subj', `/CN=${GOOGLE_HOST}`,
        '-keyout', path.join(dir, 'key.pem'), '-out', path.join(dir, 'cert.pem')], { stdio: 'ignore' });
      return { key: fs.readFileSync(path.join(dir, 'key.pem')), cert: fs.readFileSync(path.join(dir, 'cert.pem')) };
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
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
