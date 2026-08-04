import Foundation

enum APIConfig {
    static let baseURL = URL(string: "https://us-market-pulse-6sqa.onrender.com")!
}

enum APIError: Error, LocalizedError {
    case badStatus(Int)
    case decode

    var errorDescription: String? {
        switch self {
        case .badStatus(let code): return "请求失败 (\(code))"
        case .decode: return "数据解析失败"
        }
    }
}

actor APIClient {
    static let shared = APIClient()

    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 60
        config.httpAdditionalHeaders = [
            "Accept": "application/json",
            "User-Agent": "PulseDesk-iOS/1.0",
        ]
        return URLSession(configuration: config)
    }()

    func getJSON<T: Decodable>(_ path: String, as type: T.Type = T.self) async throws -> T {
        var components = URLComponents(
            url: APIConfig.baseURL.appendingPathComponent(path),
            resolvingAgainstBaseURL: false,
        )!
        // appendingPathComponent drops leading slash handling for "api/..."
        if path.hasPrefix("/") {
            components = URLComponents(string: APIConfig.baseURL.absoluteString + path)!
        }
        let (data, response) = try await session.data(from: components.url!)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.badStatus(status) }
        do {
            let decoder = JSONDecoder()
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decode
        }
    }
}
