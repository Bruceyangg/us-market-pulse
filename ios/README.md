# Pulse Desk · iPhone

## 立刻安装（推荐，无需电脑）

Apple **不允许**像安卓 APK 那样直接分发未签名 `.ipa` 给任意 iPhone 安装。当前最稳妥的方式是 **Safari 添加到主屏幕**（PWA，全屏独立图标）：

1. 用 **Safari** 打开：  
   https://us-market-pulse-6sqa.onrender.com/install  
2. 点底部分享 → **添加到主屏幕** → 添加  
3. 主屏幕点「Pulse Desk」即可全屏使用（与网站数据、登录态同步）

本地离线说明页也可打开仓库里的 `dist/PulseDesk-iOS-安装说明.html`。

---

## 原生工程（需 Mac + Xcode）

`ios/PulseDesk/` 为 SwiftUI + WKWebView 壳，内嵌线上站点，体验接近独立 App。

1. 安装 [Xcode](https://developer.apple.com/xcode/)（App Store）
2. 打开 Xcode → **File → New → Project → App**  
   - Product Name: `PulseDesk`  
   - Interface: **SwiftUI**  
   - Language: **Swift**  
   - Bundle ID 自定（如 `com.yourname.pulsedesk`）
3. 删掉自动生成的 `ContentView.swift` / `*App.swift`，把本目录下全部 `.swift` 拖进工程  
4. 把 `Info.plist` 按需合并（或使用工程生成的 Launch Screen）  
5. 选你的 iPhone（需登录 Apple ID，开发者免费账号可装到自己的手机，有效期约 7 天）  
6. Run ▶

上架 App Store / TestFlight 需要 [Apple Developer Program](https://developer.apple.com/programs/)（年费）。

## 与安卓对比

| | 安卓 `dist/PulseDesk-debug.apk` | iPhone |
|---|---|---|
| 直接安装包 | ✅ debug APK | ❌ 需签名 / TestFlight / 主屏幕 PWA |
| 本机无 Xcode 时 | 已提供 APK | 请用 Safari「添加到主屏幕」 |
| 数据源 | 同一 Render API | 同一站点 / API |
