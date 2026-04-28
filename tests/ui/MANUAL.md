# Manual e2e checklist for aidb-locator UI

Run these against a real Android device (or emulator) with CodeLocator SDK
integrated into a debug build. Tick each before considering a release ready.

Prereqs:
- `adb devices` shows your device as `device`
- A debug app built with CodeLocator SDK is foreground

## Smoke
- [ ] `aidb-ui` opens browser to `http://127.0.0.1:<port>`
- [ ] Top-right device dropdown shows the connected serial
- [ ] Activity / Fragment names render in top bar
- [ ] Screenshot renders in center panel
- [ ] Left tree renders with `DecorView` at top

## Core: click → layout
- [ ] Click any visible widget on the screenshot → blue box appears around it
- [ ] Left tree expands and highlights the same node
- [ ] Right panel shows class / id / bounds / text / mem_addr

## Hover (A1)
- [ ] Move mouse over screenshot → red dashed box follows the deepest view
- [ ] Move mouse off screenshot → red box disappears

## Search (A3)
- [ ] Type partial id / class / text in left search box → tree filters
- [ ] Parent chain auto-expands to reveal matches
- [ ] Clear search → full tree returns

## Refresh (A4)
- [ ] After app changes screen, click 🔄 → screenshot + tree update

## Edit (B1)
- [ ] Select a TextView → change 文字 → 应用 → screenshot reflects new text
- [ ] Change 透明度 slider to 0.5 → 应用 → view becomes translucent
- [ ] Change 可见性 to G → 应用 → view disappears
- [ ] Set 可见性 back to V → 应用 → view returns

## Activity (B2)
- [ ] Switch app to a different Activity → 🔄 → top bar updates

## Schema (B3)
- [ ] Type a known deep link → 🚀 跳转 → app navigates and snapshot refreshes

## Copy (B4)
- [ ] 📋 复制 id → paste somewhere → matches selected view's id

## Export
- [ ] 📥 导出 JSON → file downloads, contains the layout tree
- [ ] 📥 导出该 view 截图 (C3) → PNG downloads, shows just that view

## Multi-device (D1)
- [ ] With two devices connected, dropdown shows both
- [ ] Switching dropdown auto-refreshes the snapshot for the other device

## Error states
- [ ] Disconnect device → 🔄 → red banner: "未检测到设备"
- [ ] Reconnect → 🔄 → recovers
- [ ] Foreground a non-SDK app → 🔄 → red banner about SDK
