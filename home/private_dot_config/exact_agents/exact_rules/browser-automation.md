# Browser automation

- **Do not use the chrome-devtools MCP** to open or drive pages. The Chrome it spawns stalls on the profile picker and every call fails with
  "Target closed". Drive the user's already open browser with the peekaboo tools instead. There is no console access that way, so surface diagnostics in
  the DOM temporarily or write a Playwright spec.
- **peekaboo web clicks need the CLI in the foreground.** Web content is not in the accessibility tree, so click by coordinates. The MCP `click` in
  background mode never reaches the page and `foreground: true` is refused by policy. Use
  `peekaboo click --app "Google Chrome" --window-title "<title>" --at X,Y --foreground` with window-relative points read from a `see` or `image` capture
  of that window. Full-screen captures are downscaled to 1500 px wide, so scale coordinates first, and use `--global` for Chrome popups such as the
  serial-port picker. These clicks count as real user gestures for Web Serial and similar APIs.
