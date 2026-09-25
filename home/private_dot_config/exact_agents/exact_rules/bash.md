# Scripting

## Log messages

If the context implies prefixing log messages with an informative icon/symbol, use the following (if supported, apply color/format):

| Event       | Icon | Color               | Format |
|-------------|------|---------------------|--------|
| created     | `✱`  | Yellow              |        |
| added       | `✚`  | Green               |        |
| item        | `▪`  | Gray (Bright black) |        |
| link / file | `↗`  | Blue                |        |
| task        | `⚙`  | Yellow              |        |
| nested      | `❱`  | Yellow              |        |
| exit        | `↩`  | Red                 | Bold   |
| success     | `✔`  | Green               |        |
| info        | `ℹ`  | White               |        |
| warning     | `!`  | Yellow              | Bold   |
| error       | `✘`  | Red                 |        |
| failure     | `ϟ`  | Red                 | Bold   |

Apply color and format to the **icon only**, then reset.
Use whatever coloring mechanism is idiomatic for the runtime.
Avoid adding dependencies and avoid shell expansion pitfalls (e.g. use `printf` with single-quoted format strings in Bash).

## Shell/Bash scripts

### Files

- must follow the [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html), i.e. file header with purpose and usage
- must not contain hard coded escape sequences but use tput or a similar semantic approach
- shell script libraries must have a .bash extension
- shell scripts must
    - not have a file extension
    - be executable
    - use shebang `#!/usr/bin/env bash`

### Parameter handling

- prefer named parameters over positional arguments (unless those are actual files)
- parse with a `while`/`case` loop. Not `getopts` (short options only), not GNU `getopt` (macOS ships the BSD one without long options), not an
  argument-parsing library (a dependency for a dotfile script)
- `-h`/`--help` prints the file header. The comment block right after the shebang is the single source of truth for usage, so keep it complete
  and end it with a blank line
- unknown options exit with code 2, one line and a hint to `--help`. Do not dump the whole header on every typo
- accept both `--name value` and `--name=value`

```bash
usage() { awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}"; }
die()   { printf '%s: %s\nTry %s --help\n' "${0##*/}" "$1" "${0##*/}" >&2; exit 2; }

verbose=false; code=1; args=()
while (( $# )); do
  case $1 in
    -h|--help) usage; exit 0 ;;
    --verbose) verbose=true; shift ;;
    --code)    code=${2?--code: missing value}; shift 2 ;;
    --code=*)  code=${1#*=}; shift ;;
    --)        shift; args+=("$@"); break ;;
    -?*)       die "unknown option: $1" ;;
    *)         args+=("$1"); shift ;;
  esac
done
```

- the `*)` branch depends on who owns the positional arguments:
    - the script itself (files, names, ids): collect them as above, so options may follow positionals and a typo is caught wherever it appears
    - a command the script wraps: `*) break ;;` at the first positional, because everything from there on belongs to the wrapped command
- `-?*` rather than `-*`, so that `-` (stdin) and negative numbers stay positional
- shell functions have no header file to read: put their help in a heredoc instead
