# Pulse Desk · Android（原生）

Kotlin + Jetpack Compose 原生安卓客户端，直连线上 API：

`https://us-market-pulse-6sqa.onrender.com`

## 已实现

- 底部五栏：**行情 / 板块 / 财报 / 情报 / 持仓**
- **全板块涨跌图**（可点击下钻）
- K 线 + 均线，支持 **双指捏合缩放 / 拖动平移**
- 红涨绿跌配色，暗色交易台风格

## 环境要求

1. 安装 [Android Studio](https://developer.android.com/studio)（Ladybug / 2024.2+ 推荐）
2. 安装 SDK 35 与 JDK 17（Studio 自带即可）
3. 真机打开「开发者选项 → USB 调试」，或使用模拟器

## 运行

```bash
# 用 Android Studio 打开本目录（android/）
# File → Open → 选择 us-market-pulse/android

# 或命令行（需本机已配置 Android SDK + 生成过 Gradle Wrapper）:
./gradlew :app:installDebug
```

首次打开 Android Studio 会自动下载 Gradle / 依赖；点 **Run ▶** 安装到手机。

## 配置 API 地址

默认指向 Render 线上服务。若要连本机：

1. 电脑与手机同一 Wi-Fi
2. 编辑 `app/build.gradle.kts` 里 `API_BASE_URL`，例如：

```kotlin
buildConfigField("String", "API_BASE_URL", "\"http://192.168.1.20:8765/\"")
```

3. 同时在 `res/xml/network_security_config.xml` 允许 cleartext（仅调试用）

## 打包正式版

```bash
./gradlew :app:assembleRelease
```

生成的 APK / AAB 在 `app/build/outputs/`。上架 Google Play 需要开发者账号，并用正式签名密钥。

## 说明

- 持仓页依赖网页端登录态；当前原生端为访客读取，未接 Cookie 登录时可能为空
- Render 免费档冷启动首次请求可能较慢（10–30 秒）
