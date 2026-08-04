import SwiftUI
import WebKit

struct RootView: View {
    @EnvironmentObject private var themeStore: ThemeStore
    @State private var path = "/"

    private let tabs: [(title: String, path: String)] = [
        ("持仓", "/"),
        ("市场", "/markets"),
        ("板块", "/sectors"),
        ("财报", "/earnings"),
        ("情报", "/intel"),
        ("设置", "/settings"),
        ("安装说明", "/install"),
    ]

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Pulse Desk")
                    .font(.headline)
                Spacer()
                Picker("主题", selection: $themeStore.mode) {
                    ForEach(ThemeMode.allCases) { mode in
                        Text(mode.label).tag(mode)
                    }
                }
                .pickerStyle(.segmented)
                .frame(maxWidth: 220)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)

            WebShell(url: Self.deskURL(path))
                .id(path)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(tabs, id: \.path) { tab in
                        Button(tab.title) { path = tab.path }
                            .buttonStyle(.bordered)
                            .tint(path == tab.path ? Color(red: 0.85, green: 0.17, blue: 0.17) : .secondary)
                    }
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
            }
        }
    }

    private static func deskURL(_ path: String) -> URL {
        if path == "/" { return APIConfig.baseURL }
        return URL(string: path, relativeTo: APIConfig.baseURL)!.absoluteURL
    }
}

struct WebShell: UIViewRepresentable {
    let url: URL

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.allowsBackForwardNavigationGestures = true
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        if webView.url?.path != url.path {
            webView.load(URLRequest(url: url))
        }
    }
}
