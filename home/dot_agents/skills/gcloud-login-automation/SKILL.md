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
| Admin credential expired (re-auth policy) | reauth error from gcloud | `gcloud-login --admin`, user taps the key |
| Microsoft session expired (normal) | state `microsoft` | user signs in once with `--timeout 300` |
| Fresh browser profile | Microsoft sign-in, security key, trust-device checkbox | user, once per profile |
| Chromium updated / build missing | `Chromium install failed` | check `CHROMIUM_BUILD` and `npx @puppeteer/browsers list` |
| 1Password locked or prompt ignored | `op-agent read` exit 2 | unlock 1Password, authorize, retry |
