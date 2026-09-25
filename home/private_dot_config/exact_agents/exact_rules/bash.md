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
  and end it with a blank line. It starts with `Purpose:` and `Usage:` lines, followed by these sections as far as they add something:
    - `Options:` — one indented entry per option. Only when the script has options besides `-h`/`--help`; every script accepts those
      anyway, and a section that repeats just that line is noise
    - `Arguments:` — when a positional needs more than its name in the usage line
    - `Examples:` — real invocations, one per line, each copy-pasteable and actually tried, with a trailing `# comment` where the effect
      isn't obvious. When the output is the point, show a trimmed sample under the invocation. Skip it when the usage line already says
      everything (a script without arguments)
- unknown options exit with code 2, one line and a hint to `--help`. Do not dump the whole header on every typo
- a script that needs arguments and gets none prints the help to stderr and exits 2 — the one case where the whole header is the right
  answer. A wrong or missing value next to other arguments still gets the one-line `die`
- accept both `--name value` and `--name=value`

```bash
#!/usr/bin/env bash
# Purpose: Frobnicate files.
# Usage:   frob [--verbose] [--code <n>] [--] <file>...
#
# Options:
#   --verbose    Print every step.
#   --code <n>   Exit code on failure (default: 1).
#   -h, --help   Show this help.
#
# Examples:
#   frob *.txt
#   frob --verbose --code 3 -- -weird-name.txt

set -euo pipefail

usage() { awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}"; }
die()   { printf '%s: %s\nSee '\''%s --help'\''\n' "${0##*/}" "$1" "${0##*/}" >&2; exit 2; }

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
(( ${#args[@]} )) || { usage >&2; exit 2; }
```

- the `*)` branch depends on who owns the positional arguments:
    - the script itself (files, names, ids): collect them as above, so options may follow positionals and a typo is caught wherever it appears
    - a command the script wraps: `*) break ;;` at the first positional, because everything from there on belongs to the wrapped command
- `-?*` rather than `-*`, so that `-` (stdin) and negative numbers stay positional
- shell functions have no header file to read: put their help in a heredoc instead
