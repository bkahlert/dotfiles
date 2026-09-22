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
const EMAIL = 'someone@example.test';

function findChromium() {
  const root = path.join(os.homedir(), '.cache', 'gcloud-login', 'chromium');
  if (!fs.existsSync(root)) return null;
  for (const dir of fs.readdirSync(root)) {
    const bin = path.join(root, dir, 'chrome-mac', 'Chromium.app', 'Contents', 'MacOS', 'Chromium');
    if (fs.existsSync(bin)) return bin;
  }
  return null;
}

const CHROMIUM = findChromium();

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
  // chooser (click) -> password form (Enter) -> oauth/id interstitial
  // (click Continue) -> consent (click) -> callback.
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
          return page(`<form action="/signin/oauth/id" method="get"><input type="password" name="Passwd"></form>`);
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
