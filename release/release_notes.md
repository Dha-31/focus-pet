## Focus Pet v4.0.4

A desktop companion pet that keeps you focused — and keeps an eye on you.

### Highlights
- **Electron HTML desktop pet** — transparent, always-on-top, click-through, with speech bubbles
- **Supervision** — browser-extension blacklist/whitelist + on-device screenshot analysis (OCR)
- **Emotion thermometer** — gets visibly annoyed, staged blocking (remind → overlay → prompt to close)
- **Raising** — focus-coin economy, daily/weekly/monthly medals, achievements, study report
- **My Space** — Cozy Room / Star Field / Seaside / Forest with placeable furniture + camping series
- **All windows are HTML** — Settings / Rules / Help / Achievements / Report / Shop / My Space

### Install
Download **FocusPet-Setup-4.0.4.exe** (~166 MB) and run it.
- Windows 10/11 (64-bit), no Python required
- Per-user install (no admin); Start Menu + optional desktop shortcut; built-in uninstaller
- Your study data is kept on uninstall (`%LOCALAPPDATA%\FocusPet`)

### v4.0.4 revised build (2026-08-23)
- Fix: the user-facing Settings no longer shows or allows editing developer-only parameters (shop prices, focus-coin rate, blocking tiers, XP table, keywords)
- New app icon: real rendered cat (multi-size .ico, incl. tray icon)
- Checksum updated to the revised build below

### Checksum
SHA256 (FocusPet-Setup-4.0.4.exe): `150BB4B810E683234D56CD0F21EF09A762E5DFDF44B7AE4DEBBEFAC3B13639FB`

### Notes
- Light build: on-device OCR screen analysis is included; face auto-adaptation for custom pet images is degraded (mediapipe/cv2 not bundled)
- Unsigned build — SmartScreen may warn; click **More info → Run anyway**
