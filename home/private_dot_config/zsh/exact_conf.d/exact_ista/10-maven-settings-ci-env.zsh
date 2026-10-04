#!/usr/bin/env zsh
# Purpose: Export CI environment variables from the active Maven profile in
#          ~/.m2/settings.xml. Exports CAS_ARTIFACTORY_BASE_URL,
#          CAS_ARTIFACTORY_CI_USER, and CAS_ARTIFACTORY_CI_TOKEN — but only
#          when not already set (e.g. skips when running in CI). Stays silent
#          when the file declares no active profile.
#          The Python parse runs once per settings.xml change: its result is
#          cached under $XDG_CACHE_HOME/zsh, keyed on the file's mtime and size.
# Usage:   Sourced automatically from ~/.config/zsh/conf.d/

[[ -f "${HOME}/.m2/settings.xml" ]] || return 0

# Skip if all vars are already set (e.g. in CI)
if [[ -n "${CAS_ARTIFACTORY_BASE_URL}" && -n "${CAS_ARTIFACTORY_CI_USER}" && -n "${CAS_ARTIFACTORY_CI_TOKEN}" ]]; then
  return 0
fi

zmodload -F zsh/stat b:zstat
# Prefixed builtins only: plain mkdir/mv must stay the external commands in the user's session.
zmodload -Fm zsh/files 'b:zf_*'

_artifactory_settings="${HOME}/.m2/settings.xml"
_artifactory_cache="${XDG_CACHE_HOME:-${HOME}/.cache}/zsh/maven-settings-ci-env"
zstat -H _artifactory_key -- "${_artifactory_settings}"
_artifactory_stamp="# mtime ${_artifactory_key[mtime]} size ${_artifactory_key[size]}"

if [[ -f "${_artifactory_cache}" ]]; then
  _artifactory_exports=$(<"${_artifactory_cache}")
  if [[ "${_artifactory_exports%%$'\n'*}" == "${_artifactory_stamp}" ]]; then
    eval "${_artifactory_exports}"
    unset _artifactory_settings _artifactory_cache _artifactory_key _artifactory_stamp _artifactory_exports
    return 0
  fi
fi

_artifactory_exports=$(python3 - "${_artifactory_settings}" <<'PYEOF'
import sys, re, shlex
import xml.etree.ElementTree as ET

settings_file = sys.argv[1]

try:
    tree = ET.parse(settings_file)
except Exception as e:
    print(f'artifactory: failed to parse {settings_file}: {e}', file=sys.stderr)
    sys.exit(1)

root = tree.getroot()

ns = ''
if '{' in root.tag:
    ns = '{' + root.tag.split('{')[1].split('}')[0] + '}'

def t(name):
    return f'{ns}{name}'

active_profiles = [el.text for el in root.findall(f'{t("activeProfiles")}/{t("activeProfile")}')]
if not active_profiles:
    sys.exit(0)

active_id = active_profiles[0]

profile = next(
    (p for p in root.findall(f'{t("profiles")}/{t("profile")}')
     if (p.find(t('id')) is not None and p.find(t('id')).text == active_id)),
    None
)
if profile is None:
    print(f'artifactory: profile "{active_id}" not found in settings.xml', file=sys.stderr)
    sys.exit(1)

repo = profile.find(f'{t("repositories")}/{t("repository")}')
if repo is None:
    print(f'artifactory: no repositories in profile "{active_id}"', file=sys.stderr)
    sys.exit(1)

repo_url = repo.find(t('url')).text
repo_id  = repo.find(t('id')).text

m = re.match(r'(https?://[^/]+/artifactory)', repo_url)
base_url = m.group(1) if m else repo_url.rsplit('/', 1)[0]

server = next(
    (s for s in root.findall(f'{t("servers")}/{t("server")}')
     if (s.find(t('id')) is not None and s.find(t('id')).text == repo_id)),
    None
)
if server is None:
    print(f'artifactory: no server with id "{repo_id}" found in settings.xml', file=sys.stderr)
    sys.exit(1)

username = server.find(t('username'))
password = server.find(t('password'))

if username is None or password is None:
    print(f'artifactory: server "{repo_id}" is missing username or password', file=sys.stderr)
    sys.exit(1)

# The output is eval'd by the shell, so quote the values: a password may contain " $ ` or \.
print(f'export CAS_ARTIFACTORY_BASE_URL={shlex.quote(base_url)}')
print(f'export CAS_ARTIFACTORY_CI_USER={shlex.quote(username.text)}')
print(f'export CAS_ARTIFACTORY_CI_TOKEN={shlex.quote(password.text)}')
PYEOF
)

if [[ $? -eq 0 ]]; then
  eval "${_artifactory_exports}"
  # Only a clean parse is cached (an empty result included), so a broken settings.xml keeps warning.
  # The cache holds the token: owner-only, and renamed into place so a concurrent shell never reads half a file.
  (
    umask 077
    zf_mkdir -p "${_artifactory_cache:h}" &&
      {
        print -r -- "${_artifactory_stamp}"$'\n'"${_artifactory_exports}" >| "${_artifactory_cache}.$$" &&
          zf_mv -f "${_artifactory_cache}.$$" "${_artifactory_cache}"
      } || zf_rm -f "${_artifactory_cache}.$$"
  ) 2>/dev/null
fi

unset _artifactory_settings _artifactory_cache _artifactory_key _artifactory_stamp _artifactory_exports
