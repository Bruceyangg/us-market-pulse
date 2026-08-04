import SwiftUI

@main
struct PulseDeskApp: App {
    @StateObject private var themeStore = ThemeStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(themeStore)
                .preferredColorScheme(themeStore.preferredColorScheme)
        }
    }
}
