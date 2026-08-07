import Foundation

enum AppConfig {
    /// Same live site as the Android APK.
    static let baseURL = URL(string: "https://us-market-pulse-6sqa.onrender.com")!
    static let appVersion = "1.2.4"
    /// Site detects this UA and applies `pulse-native-app` styles.
    static let userAgentSuffix = " PulseDeskApp/\(appVersion) iOS"
}
