import SwiftUI

enum ThemeMode: String, CaseIterable, Identifiable {
    case auto
    case light
    case dark

    var id: String { rawValue }

    var label: String {
        switch self {
        case .auto: return "自动"
        case .light: return "白天"
        case .dark: return "夜晚"
        }
    }
}

@MainActor
final class ThemeStore: ObservableObject {
    private let key = "pulse_theme_mode"

    @Published var mode: ThemeMode {
        didSet {
            UserDefaults.standard.set(mode.rawValue, forKey: key)
        }
    }

    init() {
        let raw = UserDefaults.standard.string(forKey: key) ?? ThemeMode.auto.rawValue
        mode = ThemeMode(rawValue: raw) ?? .auto
    }

    var preferredColorScheme: ColorScheme? {
        switch mode {
        case .auto: return nil
        case .light: return .light
        case .dark: return .dark
        }
    }
}
