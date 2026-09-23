# iOS Simulator

On a Jamf-managed Mac the Simulator fails in ways that look like Xcode or CoreSimulator bugs. Check the machine before blaming the app:

- **"Failed to start launchd_sim: could not bind to session" on every runtime** has two known causes. Run `ls -ld /private/tmp /private/var/tmp`: an
  MDM policy resets them from mode 1777, and launchd_sim cannot create its state directory. The user must run `sudo chmod 1777` on both; if it reverts,
  escalate to IT. Otherwise run `systemextensionsctl list`: a Jamf Protect Endpoint Security extension in `waiting to uninstall on reboot` state gates
  process spawning, and only a reboot fixes it. Cache clearing and service restarts cannot.
- **Synthetic input does not reach the Simulator** from this sandbox. peekaboo capture and foreground clicks are refused, and System Events clicks report
  success without effect, so do not spend turns on them. Use `xcrun simctl io <device> screenshot <path>` for screenshots,
  `xcrun simctl launch --console-pty --terminate-running-process <device> <bundle-id>` for live stdout, crash reports in
  `~/Library/Logs/DiagnosticReports/*.ips` symbolicated with `atos`, a throwaway test run on `iosSimulatorArm64Test` to exercise native code without any
  UI, or an XCUITest target when real taps and screenshots are needed.
