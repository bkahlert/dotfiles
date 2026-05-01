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
- adopt the following pattern for parse named parameters:

```
    local code=1
    while [ $# -gt 0 ]; do
        case $1 in
        --code) code=${2?$1: parameter value not set} && shift 2 ;;
        --code=*) code=${1#*=} && shift ;;
        *) break ;;
        esac
    done
```

- for boolean parameters you can use

```
  # Boolean flags
  local verbose=false
  case $1 in
      --verbose) verbose=true && shift ;;
```
