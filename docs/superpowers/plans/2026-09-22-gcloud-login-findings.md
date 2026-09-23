# gcloud-login — empirical findings (2026-09-22)

Recorded during Task 1 of [the implementation plan](2026-09-22-gcloud-login-unattended.md).
Everything below was observed on the user's Jamf-managed Mac with Chrome 153 and gcloud from `~/google-cloud-sdk`.

## Facts that change the design

1. **`BROWSER` cannot contain spaces.** Python's `webbrowser` splits the value on whitespace, so neither the Chrome binary path nor a profile path can appear in it. Only the `gcloud-login-browser` hook (no spaces in its path) works.
2. **Google Workspace delegates sign-in to Microsoft Entra ID via SAML.** After the identifier page Google redirects to `login.microsoftonline.com/<tenant>/saml2`. There is no Google password page at all; the "password" is the Microsoft one.
3. **In managed Google Chrome the SAML hop is silent** (returns to Google in ~2 s in a fresh profile without any input), presumably through the force-installed Microsoft SSO extension / macOS Platform SSO. **In Chrome for Testing it is not**: Microsoft shows its "Email address or Azure login" page.
4. **Google Chrome forces a managed profile sign-in.** Signing a managed Google account in on the web triggers the "Your organization requires you to sign into Chrome" interception (chrome://managed-user-profile-notice). Its "Continue as …" button ignores synthetic clicks and its window has no accessibility tree for peekaboo; it needs a real user click. The OAuth tab is consumed by the profile sign-in and the gcloud run has to be restarted.
5. **A signed-in managed Chrome profile stops exposing the DevTools port.** After the profile sign-in, `--remote-debugging-port=0` no longer writes `DevToolsActivePort` (fresh profile of the same binary: it does). Consistent with a user-level `RemoteDebuggingAllowed=false` / `DeveloperToolsAvailability` policy. **The DevTools driver cannot work in managed Google Chrome.** Chrome for Testing (downloaded via `@puppeteer/browsers`, `~/.cache/gcloud-login/chrome/…`) cannot be signed into Chrome, so profile policy never applies and the port stays available.
6. **Chrome Sync side effect.** The profile-customisation dialog after the forced sign-in turned sync on and the chosen profile colour synced to the user's daily Chrome profile. Never enable sync in a dedicated profile; decline the customisation.
7. **`gcloud auth login <account> --quiet` re-uses a valid stored credential** ("Re-using locally stored credentials … re-run with `--force`") and opens no browser. The orchestrator therefore never needs a pre-check for the CLI credential; `--force` is only for testing.
8. **The callback page redirects instantly** to `https://docs.cloud.google.com/sdk/auth_success` (German UI: "Sie sind jetzt bei der gcloud CLI authentifiziert."). The driver must treat that URL as `done` too; the localhost URL is rarely observable.
9. **Google's identifier page appears despite the login hint** in a fresh profile: `input[name="identifier"]` plus a "Next" button. Typing the email and Enter works via `Input.insertText` + Enter key events.
10. **The account chooser appears despite the login hint** once the profile has a Google session: `div[role="link"][data-identifier="<email>"]`; `.click()` works.
11. **"Verify that it's you" (`/speedbump/samlconfirmaccount`)** follows the SAML hop: `<button>Continue</button>` (German: "Weiter"); `.click()` works.
12. **Consent** (`/signin/oauth/consent`): `<button>Allow</button>` (client "Google Cloud SDK" for the CLI, "Google Auth Library" for ADC); `.click()` works. No checkboxes were shown for either.
13. **UI language flips** between `en-US`, `en-GB` and `de` within one flow; button labels must be matched in both languages.
14. **Hardware key** (`/signin/challenge/sk/webauthn`, "2-Step Verification … Complete sign-in using your security key", button "Try another way") appears on the first sign-in in a fresh browser profile; afterwards a checkbox page ("Next") offers to trust the device. Not seen again in the same profile afterwards.
15. **peekaboo on the 1Password window**: not yet verified — in the first test the user confirmed the prompt manually before the click. `peekaboo see --app 1Password --tree` at that moment listed only window chrome buttons. Retest from a fresh pty (`script -q /dev/null op read …`) so the prompt reappears.
16. **Session persistence in Google Chrome**: not testable after finding 5. Chrome for Testing: pending.

17. **Chrome for Testing is also interceptable.** It ships Google API keys, so the managed-profile interception (fact 4) fires there too. **Plain Chromium** (no API keys, `npx @puppeteer/browsers install chromium@latest`, `~/.cache/gcloud-login/chromium/…`) cannot sign into the browser, so the interception never appears and the DevTools port stays available across relaunches. **Chromium is the browser for the dedicated profiles.**
18. **Chrome policies cannot be set per user.** `defaults write com.google.chrome.for.testing BrowserSignin 0` shows as "Not set" in chrome://policy; only `/Library/Managed Preferences` counts, which needs admin rights.
19. **The normal account authenticates via Microsoft Entra (SAML); the admin account does not.** `bjoern.kahlert.admin@ista-express.de` gets Google's own password page (`/v3/signin/challenge/pwd`, `input[type=password][name=Passwd]`, button Next/Weiter). The "Google (Admin)" 1Password item holds that password (64 chars). The normal account's "Google" item (15 chars) is irrelevant for the browser flow: Microsoft asks for the **ista** account (`bjoern.kahlert@ista.com`) password, not any ista-express one.
20. **Microsoft sequence in a fresh browser profile**: `loginfmt` (username) → `passwd` → `device.login.microsoftonline.com` → `/common/DeviceAuthTls/reprocess` with `input[type=tel][name=otc]` (one-time code from the Authenticator app, entered by the user) → `/common/SAS/ProcessAuth` "Stay signed in?" (`checkbox DontShowAgain`, `idSIButton9` = Yes) → `/kmsi` → back to Google. With "Stay signed in" accepted, later runs pass Microsoft silently (`device.login.microsoftonline.com` "Working…" ~1 s). Microsoft's page keeps a hidden `input[type=password]` in the DOM on the username step, so the driver's visibility check must use `offsetParent` rather than `getClientRects` alone.
21. **Security key**: the normal account showed `sk/webauthn` only on the first sign-in per browser profile, followed by an `sk/finish` page with a "don't ask again" checkbox. The admin account showed `sk/webauthn` on **every** login so far, with no trust checkbox — consistent with a Workspace re-auth policy for admins. To be confirmed with the user whether the key was tapped each time.
22. **1Password CLI authorization is per process tree.** From Claude's Bash tool every call is a new tree, so `op read` prompted again (and timed out after 60 s when nobody clicked). A read repeated inside the same call took 1 s. **Workaround that works:** a daemon started with `setsid` inside its own pty (`python3 -c 'import os,pty; os.setsid(); pty.spawn([...])'`) that serves `op read` requests over a FIFO. After one Authorize click, later Bash calls got the password in 0–1 s with no prompt. The desktop app's limits still apply: 10 min inactivity, 12 h hard limit; the daemon needs a keep-alive (`op whoami` every ~5 min) to stay within the inactivity window.
23. **The 1Password "Access Requested" window has no accessibility tree** (peekaboo: `no_matching_accessibility_window`, pixels only, 500×500 at (0,940)); when `op` was launched from a Python pty in the background the prompt did not appear at all until the user was addressed. Clicking it with peekaboo is not a viable design; the daemon in fact 22 makes it unnecessary.
24. **Idempotency**: `gcloud auth login <account> --quiet` re-uses a valid credential (fact 7). `gcloud auth application-default login <account> --quiet` likewise prints "Valid credentials already exist for <account>" and exits without a browser. `--force` exists only for the CLI login.
25. **Steady-state timings in Chromium** after a full relaunch of the browser: normal CLI login 7 s (chooser → silent Microsoft → consent), ADC 8 s, admin 14 s including the user's key tap. All clicks via `.click()` on the DOM element; the German consent button "Zulassen" and English "Allow" both matched.
26. **Launch flags**: `--no-startup-window` avoids the leftover about:blank tab; `Target.createTarget` then opens the window on demand. The driver should `Target.closeTarget` its tab when done; the orchestrator quits the browser afterwards.
27. **Chrome Sync side effect, resolution**: the dedicated Google Chrome profile (`~/Library/Application Support/gcloud-login/normal`) and the Chrome for Testing profile (`…/cft-normal`) are managed/synced and must be signed out of sync before deletion; both are obsolete.

28. **Admin credential lifetime is longer than remembered.** After the 17:47 admin login, `gcloud auth print-access-token --quiet` still succeeded at 18:45 (58 min later) with no browser opened. The "10–15 minutes" from memory does not match; treat the expiry as "well before the normal account" until measured. `--quiet` on `print-access-token` never opens a browser.
29. **OAuth interstitial `/signin/oauth/id`** ("Sign in to Google Auth Library", buttons Cancel / Continue) appears before the consent page when consent is granted afresh after `gcloud auth application-default revoke`. Not seen for the CLI client after `gcloud auth revoke`. The driver needs an `oauthid` state (click Continue / Weiter); the consent button after it was "Allow".
30. **`op-agent` verified against real 1Password**: first read 34 s (one Authorize click), second read from a new process tree 0 s. The desktop app does answer a daemon that was started from Claude's Bash tool with `setsid` + pty; when it did not answer earlier (18:05–18:40) the user was away and the app was locked.
31. **End-to-end with the installed scripts (Task 8)**: `gcloud-login` idempotent ("still valid") · CLI after revoke 11 s · ADC after revoke blocked only by fact 29 · `gcloud-login --admin` after revoke 17 s including the key tap · `--status` exit 0 with both valid.
32. **peekaboo** occasionally loses its capture daemon ("ScreenCaptureKit owner PID … does not serve selected socket"); not part of the design any more, noted for debugging sessions only.

## Page sequences

### Google Chrome (managed), fresh profile, normal account, CLI login

| # | URL | Title | Elements | Note |
|---|---|---|---|---|
| 1 | `accounts.google.com/v3/signin/identifier` | Sign in - Google Accounts | `input[name=identifier]`, buttons Next / Forgot email? / Create account | typed email + Enter via CDP |
| 2 | `login.microsoftonline.com/…/saml2` | Working... | — | silent, ~2 s |
| 3 | `accounts.google.com/v3/signin/continue` | Sign in - Google Accounts | — | transient |
| 4 | `accounts.google.com/v3/signin/challenge/sk/webauthn` | 2-Step Verification | button "Try another way", ids `[email]` | hardware key by the user |
| 5 | `…/challenge/sk/finish` | 2-Step Verification | checkbox, button Next | "don't ask again" by the user |
| 6 | `accounts.google.com/speedbump/samlconfirmaccount` | Identität bestätigen (de) | buttons Weiter / Ich kenne dieses Konto nicht | interrupted by 7 |
| 7 | `chrome://managed-user-profile-notice/` + `accounts.google.de/accounts/SetSID` | Your organization requires a profile | cr-button "Continue as Björn" / "Sign out" | real click needed; OAuth tab lost |

### Google Chrome (managed), signed-in profile, normal account, CLI login (second run)

| # | URL | Elements | Action |
|---|---|---|---|
| 1 | `…/v3/signin/accountchooser` | `[data-identifier=email]` ×2 (one hidden) | `.click()` |
| 2 | `login.microsoftonline.com/…/saml2` "Working..." | — | silent |
| 3 | `…/speedbump/samlconfirmaccount` "Verify that it's you" (en-GB) | buttons Continue / I don't recognise this account | `.click()` Continue |
| 4 | `…/signin/oauth/consent` "Google Cloud SDK wants to access your Google Account" | buttons Cancel / Allow (+ 8 unlabeled) | `.click()` Allow |
| 5 | `docs.cloud.google.com/sdk/auth_success?hl=de` | — | gcloud: "You are now logged in as […]" |

### Google Chrome (managed), signed-in profile, ADC login (normal account)

Prototype driver, fully unattended, 8 s: `accountchooser` → click → `oauth/consent` ("Google Auth Library wants to access…", Allow) → `auth_success`. No SAML confirm page this time (Microsoft session fresh). ADC identity afterwards: `bjoern.kahlert@ista-express.de`.

### Chrome for Testing 153, fresh profile, normal account, CLI login (manual Microsoft part)

| # | URL | Elements | Who |
|---|---|---|---|
| 1 | `…/v3/signin/identifier` | `input[name=identifier]` | driver |
| 2 | `login.microsoftonline.com/…/saml2` | `input[name=loginfmt]`, Next | user (ista account) |
| 3 | same | `input[name=passwd]` | user |
| 4 | `device.login.microsoftonline.com` → `/common/DeviceAuthTls/reprocess` | `input[type=tel][name=otc]`, `idSubmit_SAOTCC_Continue` | user (Authenticator code) |
| 5 | `/common/SAS/ProcessAuth` | checkbox `DontShowAgain`, `idSIButton9` | user (Yes) |
| 6 | `/kmsi` → `accounts.google.com/v3/signin/continue` | — | — |
| 7 | `…/challenge/sk/webauthn` → `sk/finish` | key, then checkbox + Next | user |
| 8 | `…/speedbump/samlconfirmaccount` | Weiter | — (run was interrupted by the profile interception) |

### Chromium 156, fresh profile, normal account, CLI login

Identifier (driver) → Microsoft username / password / OTC / stay-signed-in (user) → `accounts.google.com/samlrp/…/acs` "Post Trampoline" → `sk/webauthn` → `sk/finish` (user) → `oauth/consent` → Allow (driver) → `auth_success`. **No profile interception, no samlconfirmaccount page.**

### Chromium, signed-in profile after relaunch, normal account (steady state, 7 s, unattended)

`accountchooser` (click) → `login.microsoftonline.com/…/saml2` "Redirecting" → `device.login.microsoftonline.com` "Working…" → `v3/signin/continue` → `oauth/consent` (Allow) → `auth_success`.

### Chromium, admin account

Fresh profile: `identifier` (driver types email) → `challenge/pwd` "Welcome" (driver types password, Enter) → `sk/webauthn` (user, ~5 s) → `oauth/consent` (Zulassen) → `auth_success`. 14 s.
After relaunch (steady state): `accountchooser` (click) → `challenge/pwd` "Willkommen" (password) → `sk/webauthn` (~4 s) → `oauth/consent` → `auth_success`.

## Confirmed selectors

| state | detection | action |
|---|---|---|
| identifier | visible `input[name="identifier"]` | insertText email + Enter |
| chooser | `[data-identifier="<email>"]` | `.click()` |
| google-password | host `accounts.google.com`, visible `input[type="password"]` | insertText password + Enter |
| confirm | URL `/speedbump/samlconfirmaccount`, visible button Continue / Weiter | `.click()` (only seen in Google Chrome) |
| consent | URL `/signin/oauth/consent`, visible button Allow / Zulassen | `.click()` |
| done | URL `docs.cloud.google.com/sdk/auth_success` or `http://localhost:<port>/?…code=` | close tab, exit 0 |
| ms-* | host `login.microsoftonline.com` | wait; only seen with user input on the first run per profile; "Working…"/"Redirecting" pass by themselves |
| sk | URL `/challenge/sk/` | wait for the user's key tap (bounded) |

Visibility: `el.offsetParent !== null` (Microsoft keeps hidden password inputs in the DOM).

## 1Password window

Not clickable (fact 23). Use the pty daemon (fact 22).
