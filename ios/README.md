# Pulse Desk · iPhone（免费个人签名）

与安卓 APK **同一套线上站**（WebView 壳），底栏 7 模块：持仓 / 板块 / 市场 / 财报 / 情报 / 产业 / 设置。

版本：**1.2.4**

---

## 你需要准备

1.一台 **Mac**
2. App Store 安装免费 **[Xcode](https://apps.apple.com/app/xcode/id497799835)**
3. 一个普通 **Apple ID**（不用付费加入 Developer Program）
4. 一根线，把 **iPhone** 连到 Mac（首次信任此电脑）

> 免费签名限制（苹果规定，无法绕过）：  
> - 只能装到**你自己登录的那台 iPhone**  
> - 大约 **7 天**后图标会打不开，需再用 Xcode 点一次 Run 续签  
> - 同一 Apple ID 同时最多约 3 个免费签名 App

---

## 安装步骤（约 10 分钟）

### 1. 打开工程

```bash
open /Users/你的用户名/Projects/us-market-pulse/ios/PulseDesk.xcodeproj
```

或在 Finder 中双击：`us-market-pulse/ios/PulseDesk.xcodeproj`

### 2. 登录 Apple ID

Xcode 菜单：**Xcode → Settings… → Accounts → + → Apple ID**  
登录你的 Apple ID。

### 3. 选签名团队

左侧点项目 **PulseDesk** → 目标 **PulseDesk** → **Signing & Capabilities**：

- 勾选 **Automatically manage signing**
- **Team** 选你的个人团队（一般显示为「你的名字 (Personal Team)」）
- 若 Bundle ID 冲突，改成唯一值，例如：`com.你的名字.pulsedesk`

### 4. 信任开发者（手机上，首次）

1. iPhone：**设置 → 通用 → VPN 与设备管理**（或「描述文件与设备管理」）
2. 点你的 Apple ID 开发者描述文件 → **信任**

### 5. 运行到手机

1. 用线连接 iPhone，解锁手机
2. Xcode 顶部设备列表选你的 **iPhone**（不要选 Simulator）
3. 点 ▶ **Run**
4. 若提示「未受信任的开发者」，回到第 4 步完成信任后再 Run 一次

装好后主屏幕会出现 **Pulse Desk**，用法与安卓 APK 一致（数据来自同一网址）。

---

## 7 天后打不开怎么办

用线连接 iPhone → 再打开本工程 → 再点一次 ▶ Run 即可续签。  
（这是免费个人签名的固有限制；若以后要免续签，需加入付费 Apple Developer Program。）

---

## 工程说明

| 项 | 说明 |
|----|------|
| 线上地址 | `https://us-market-pulse-6sqa.onrender.com` |
| 壳 | SwiftUI + WKWebView，`?app=1` + UA `PulseDeskApp` |
| 手机 | 底部 7 栏 |
| iPad | 左侧导航轨（宽屏） |
| 源码 | `ios/PulseDesk/*.swift` |

旧文件 `APIClient.swift` / `Models.swift` / `ThemeStore.swift` 已不再参与编译，可忽略。
