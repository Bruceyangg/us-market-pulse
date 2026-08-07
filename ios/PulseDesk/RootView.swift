import SwiftUI
import WebKit

private struct TabItem: Identifiable, Hashable {
    let id: String
    let title: String
    let shortTitle: String
    let path: String
    let systemImage: String
}

/// Same modules as Android APK bottom bar / tablet rail.
private let allTabs: [TabItem] = [
    .init(id: "desk", title: "持仓", shortTitle: "持仓", path: "/", systemImage: "building.columns"),
    .init(id: "sectors", title: "板块", shortTitle: "板块", path: "/sectors", systemImage: "square.grid.2x2"),
    .init(id: "markets", title: "市场", shortTitle: "市场", path: "/markets", systemImage: "chart.line.uptrend.xyaxis"),
    .init(id: "earnings", title: "财报", shortTitle: "财报", path: "/earnings", systemImage: "calendar"),
    .init(id: "intel", title: "情报", shortTitle: "情报", path: "/intel", systemImage: "newspaper"),
    .init(id: "chains", title: "产业链", shortTitle: "产业", path: "/chains", systemImage: "arrow.triangle.branch"),
    .init(id: "settings", title: "设置", shortTitle: "设置", path: "/settings", systemImage: "gearshape"),
]

struct RootView: View {
    @Environment(\.horizontalSizeClass) private var sizeClass
    @State private var selectedID = "desk"
    @State private var currentPath = "/"
    @StateObject private var bridge = WebBridge()

    private var selectedTab: TabItem {
        allTabs.first(where: { $0.id == selectedID }) ?? allTabs[0]
    }

    private var isRegularWidth: Bool {
        sizeClass == .regular
    }

    /// Match Android: hide native chrome on login/register so the form is not interrupted.
    private var hideNativeTabs: Bool {
        isAuthPath(currentPath)
    }

    var body: some View {
        Group {
            if isRegularWidth {
                // iPad / large width ≈ Android tablet NavigationRail
                HStack(spacing: 0) {
                    if !hideNativeTabs {
                        tabletRail
                    }
                    webPane
                }
            } else {
                // iPhone ≈ Android phone bottom tabs
                VStack(spacing: 0) {
                    webPane
                    if !hideNativeTabs {
                        phoneTabBar
                    }
                }
            }
        }
        .background(Color(.systemBackground))
    }

    private func isAuthPath(_ path: String) -> Bool {
        let clean = path.split(separator: "?").first.map(String.init) ?? path
        return clean.hasPrefix("/login") || clean.hasPrefix("/register")
    }

    private var webPane: some View {
        ZStack(alignment: .top) {
            WebShell(
                path: selectedTab.path,
                isTablet: isRegularWidth,
                bridge: bridge,
                onPathChanged: { path in
                    currentPath = path
                    if let match = allTabs.first(where: { tabMatches(path, tab: $0) }) {
                        selectedID = match.id
                    }
                },
            )
            .ignoresSafeArea(edges: isRegularWidth ? [] : [.bottom])

            if bridge.isLoading {
                ProgressView(value: bridge.progress)
                    .progressViewStyle(.linear)
                    .tint(Color(red: 0.18, green: 0.45, blue: 0.72))
            }
        }
    }

    private var phoneTabBar: some View {
        HStack(spacing: 0) {
            ForEach(allTabs) { tab in
                Button {
                    selectedID = tab.id
                } label: {
                    VStack(spacing: 3) {
                        Image(systemName: tab.systemImage)
                            .font(.system(size: 17, weight: selectedID == tab.id ? .semibold : .regular))
                        Text(tab.shortTitle)
                            .font(.system(size: 10, weight: selectedID == tab.id ? .bold : .medium))
                            .lineLimit(1)
                            .minimumScaleFactor(0.8)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 6)
                    .foregroundStyle(selectedID == tab.id ? Color.accentColor : Color.secondary)
                    .background(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .fill(selectedID == tab.id ? Color.accentColor.opacity(0.12) : Color.clear),
                    )
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 2)
        .padding(.top, 4)
        .padding(.bottom, 2)
        .background(.bar)
    }

    private var tabletRail: some View {
        VStack(spacing: 4) {
            Text("Pulse")
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(Color.accentColor)
                .padding(.top, 16)
                .padding(.bottom, 8)

            ForEach(allTabs) { tab in
                Button {
                    selectedID = tab.id
                } label: {
                    VStack(spacing: 4) {
                        Image(systemName: tab.systemImage)
                            .font(.system(size: 18))
                        Text(tab.shortTitle)
                            .font(.system(size: 11, weight: selectedID == tab.id ? .bold : .medium))
                    }
                    .frame(width: 64)
                    .padding(.vertical, 10)
                    .foregroundStyle(selectedID == tab.id ? Color.accentColor : Color.secondary)
                    .background(
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .fill(selectedID == tab.id ? Color.accentColor.opacity(0.14) : Color.clear),
                    )
                }
                .buttonStyle(.plain)
            }
            Spacer()
        }
        .frame(width: 76)
        .background(Color(.secondarySystemBackground))
    }

    private func tabMatches(_ path: String, tab: TabItem) -> Bool {
        let clean = path.split(separator: "?").first.map(String.init) ?? path
        if tab.path == "/" {
            return clean == "/" || clean == "/desk" || clean.isEmpty
        }
        return clean.hasPrefix(tab.path)
    }
}

@MainActor
final class WebBridge: ObservableObject {
    @Published var isLoading = false
    @Published var progress: Double = 0
}

// MARK: - WKWebView

struct WebShell: UIViewRepresentable {
    let path: String
    let isTablet: Bool
    @ObservedObject var bridge: WebBridge
    var onPathChanged: (String) -> Void

    func makeCoordinator() -> Coordinator {
        Coordinator(bridge: bridge, isTablet: isTablet, onPathChanged: onPathChanged)
    }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        // Persistent store keeps pulse_session cookie after login / app relaunch.
        config.websiteDataStore = .default()
        config.allowsInlineMediaPlayback = true
        config.defaultWebpagePreferences.allowsContentJavaScript = true

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        webView.scrollView.contentInsetAdjustmentBehavior = .automatic
        webView.customUserAgent = (webView.value(forKey: "userAgent") as? String ?? "")
            + AppConfig.userAgentSuffix

        context.coordinator.webView = webView
        context.coordinator.observeProgress(webView)
        context.coordinator.load(path: path, in: webView)
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        context.coordinator.isTablet = isTablet
        context.coordinator.onPathChanged = onPathChanged
        // Only navigate when the *native tab* changed. Comparing against the
        // live WebView URL used to yank users off /login back to "/" on every
        // SwiftUI refresh — which made login appear broken.
        let want = Self.normalizedPath(path)
        if want != context.coordinator.lastNativePath {
            context.coordinator.load(path: path, in: webView)
        } else {
            context.coordinator.injectNativeClass(into: webView)
        }
    }

    static func normalizedPath(_ path: String) -> String {
        let p = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        return p.isEmpty ? "/" : "/\(p)"
    }

    static func siteURL(path: String) -> URL {
        var components = URLComponents(url: AppConfig.baseURL, resolvingAgainstBaseURL: false)!
        let clean = path.hasPrefix("/") ? path : "/\(path)"
        components.path = clean == "/" ? "/" : clean
        components.queryItems = [URLQueryItem(name: "app", value: "1")]
        return components.url ?? AppConfig.baseURL
    }

    @MainActor
    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        var bridge: WebBridge
        var isTablet: Bool
        var onPathChanged: (String) -> Void
        /// Last path loaded because the user tapped a native tab (not web nav).
        var lastNativePath: String = ""
        weak var webView: WKWebView?
        private var progressObs: NSKeyValueObservation?

        init(bridge: WebBridge, isTablet: Bool, onPathChanged: @escaping (String) -> Void) {
            self.bridge = bridge
            self.isTablet = isTablet
            self.onPathChanged = onPathChanged
        }

        func observeProgress(_ webView: WKWebView) {
            progressObs = webView.observe(\.estimatedProgress, options: [.new]) { [weak self] wv, _ in
                Task { @MainActor in
                    self?.bridge.progress = wv.estimatedProgress
                    self?.bridge.isLoading = wv.estimatedProgress < 1
                }
            }
        }

        func load(path: String, in webView: WKWebView) {
            lastNativePath = WebShell.normalizedPath(path)
            bridge.isLoading = true
            webView.load(URLRequest(url: WebShell.siteURL(path: path)))
        }

        func injectNativeClass(into webView: WKWebView) {
            let mode = isTablet ? "pulse-native-tablet" : "pulse-native-phone"
            let other = isTablet ? "pulse-native-phone" : "pulse-native-tablet"
            let js = """
            (function(){
              try {
                var r = document.documentElement;
                r.classList.add('pulse-native-app', '\(mode)');
                r.classList.remove('\(other)');
                r.setAttribute('data-pulse-app', '\(isTablet ? "tablet" : "phone")');
              } catch (e) {}
            })();
            """
            webView.evaluateJavaScript(js, completionHandler: nil)
        }

        func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
            bridge.isLoading = true
            injectNativeClass(into: webView)
            if let path = webView.url?.path {
                onPathChanged(path)
            }
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            bridge.isLoading = false
            injectNativeClass(into: webView)
            if let path = webView.url?.path {
                onPathChanged(path)
            }
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void,
        ) {
            guard let url = navigationAction.request.url else {
                decisionHandler(.allow)
                return
            }
            let host = url.host?.lowercased() ?? ""
            let appHost = AppConfig.baseURL.host?.lowercased() ?? ""
            if !host.isEmpty, !appHost.isEmpty, host != appHost {
                UIApplication.shared.open(url)
                decisionHandler(.cancel)
                return
            }
            decisionHandler(.allow)
        }
    }
}
