# Markdown

- When you reference a file, do so with a proper Markdown link
    - `[filename](path)`, or
    - `[path](path)`, or
    - `[title of the references file](path)`
- Code blocks tagged with a programming language are code samples: they parse as written ([documentation.md](documentation.md)).
- A shell code block (`shell`, `sh`, `bash`, `zsh`, `console`) holds only commands meant to run together, in order. An IDE can run a rendered
  block as a whole, so alternatives and independent commands never share one. Give each its own context instead — whatever form suits the case,
  such as a table row, or a heading or sentence before its own block.
- Trailing `# comments` are fine in such a block. Align them in one column within the block.
- Keep lines in shell blocks to 80 characters so they don't scroll horizontally. Break a long command with a trailing `\`.

```shell
git clone https://example.com/app.git   # fetch the source
cd app                                  # enter it
make install                            # build and install
```
