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
- **Admin needs the user.** Every admin login requires a security-key tap (Workspace policy); the script prints "tap it now". Tell the user before running `gcloud-login --admin`, and expect it again whenever gcloud reports a reauthentication error; the admin credential expires well before the normal one. The first admin run of the day also shows one 1Password "Access Requested" prompt the user must authorize. The first admin run in a shell session may also wait on `op-agent`; if it exits 2, the 1Password prompt was not authorized.

## What not to do

- Do not tell the user to run `gcloud auth login`; `gcloud-login` does it.
- Do not run `gcloud auth login` or `gcloud auth application-default login` directly: they open the user's daily browser and wait for clicks.
- Do not use admin for ADC, for deployments, or "just in case".

## Exit codes of gcloud-login

0 logged in · 1 precondition or credential failure (message on stderr) · 2 browser flow timed out, the Chromium window is left open for the user.
