# Pulse Desk · Android

Kotlin + Jetpack Compose **自适应壳** + 全站 WebView，与线上站内容一致：

`https://us-market-pulse-6sqa.onrender.com`

版本：**1.2.3**（versionCode 13）

## 手机 / 平板操作设计

| 形态 | 导航 | 页面布局 |
|------|------|----------|
| **手机**（smallestWidth &lt;600dp） | 底栏 7 栏等宽（持仓/板块/市场/财报/情报/产业/设置） | 单列；美市条横滑；期货图/涨跌图可折叠 |
| **平板**（smallestWidth ≥600dp） | 左侧可滚动 NavigationRail | 列表+图表并排；顶栏只留主题/登录 |

其他：

- 单一 WebView 实例，旋转时不销毁页面
- 隐藏网页主导航与底栏，避免双导航
- UA 带 `PulseDeskApp/1.2.3`；站点 `pulse-native-app` + `phone|tablet`
- 下拉刷新、系统返回、外链系统浏览器；Cookie 持久化

## 环境要求

1. [Android Studio](https://developer.android.com/studio)（Ladybug / 2024.2+）或本仓库 `.tools` JDK/SDK
2. SDK 35 + JDK 17
3. 真机 USB 调试或模拟器

## 运行 / 打包

```bash
cd android
./gradlew :app:assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
# 同步拷贝：../dist/PulseDesk-debug.apk
```

## 配置 API 地址

默认 Render 线上。连本机时改 `app/build.gradle.kts` 的 `API_BASE_URL`。

## 说明

- Render 免费档冷启动首次可能需 20–40 秒唤醒
- 旧版纯 Compose 页面文件仍保留在工程中，当前入口为 WebView 壳
