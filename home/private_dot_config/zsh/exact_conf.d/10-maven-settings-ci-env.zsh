#!/usr/bin/env zsh
# Purpose: Export CI environment variables from the active Maven profile in
#          ~/.m2/settings.xml. Exports CAS_ARTIFACTORY_BASE_URL,
#          CAS_ARTIFACTORY_CI_USER, and CAS_ARTIFACTORY_CI_TOKEN — but only
#          when not already set (e.g. skips when running in CI).
# Usage:   Sourced automatically from ~/.config/zsh/conf.d/

[ "${DOTFILES_CONTEXT}" = ista ] || return 0

[[ -f "${HOME}/.m2/settings.xml" ]] || return 0

# Skip if all vars are already set (e.g. in CI)
if [[ -n "${CAS_ARTIFACTORY_BASE_URL}" && -n "${CAS_ARTIFACTORY_CI_USER}" && -n "${CAS_ARTIFACTORY_CI_TOKEN}" ]]; then
  return 0
fi

_artifactory_exports=$(python3 - "${HOME}/.m2/settings.xml" <<'PYEOF'
import sys, re
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
    print('artifactory: no activeProfile found in settings.xml', file=sys.stderr)
    sys.exit(1)

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

print(f'export CAS_ARTIFACTORY_BASE_URL="{base_url}"')
print(f'export CAS_ARTIFACTORY_CI_USER="{username.text}"')
print(f'export CAS_ARTIFACTORY_CI_TOKEN="{password.text}"')
PYEOF
)

if [[ $? -eq 0 ]]; then
  eval "${_artifactory_exports}"
fi

unset _artifactory_exports
