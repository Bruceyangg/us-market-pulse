import Foundation

struct MarketsResponse: Decodable {
    let indexes: [IndexQuote]?
    let asOf: String?

    enum CodingKeys: String, CodingKey {
        case indexes
        case asOf = "as_of"
    }
}

struct IndexQuote: Decodable, Identifiable {
    var id: String { symbol }
    let symbol: String
    let name: String?
    let price: Double?
    let changePct: Double?

    enum CodingKeys: String, CodingKey {
        case symbol, name, price
        case changePct = "change_pct"
    }
}

struct IntelResponse: Decodable {
    let items: [IntelItem]?
}

struct IntelItem: Decodable, Identifiable {
    var id: String { url ?? title }
    let title: String
    let source: String?
    let url: String?
    let published: String?
    let sentiment: String?
    let summaryZh: String?

    enum CodingKeys: String, CodingKey {
        case title, source, url, published, sentiment
        case summaryZh = "summary_zh"
    }
}

struct EarningsResponse: Decodable {
    let items: [EarningsItem]?
}

struct EarningsItem: Decodable, Identifiable {
    var id: String { "\(symbol)-\(date ?? "")" }
    let symbol: String
    let name: String?
    let date: String?
    let time: String?
}

struct SectorMapResponse: Decodable {
    let sectors: [SectorNode]?
}

struct SectorNode: Decodable, Identifiable {
    var id: String { key ?? name }
    let key: String?
    let name: String
    let changePct: Double?
    let weight: Double?
    let stocks: [StockNode]?

    enum CodingKeys: String, CodingKey {
        case key, name, weight, stocks
        case changePct = "change_pct"
    }
}

struct StockNode: Decodable, Identifiable {
    var id: String { symbol }
    let symbol: String
    let name: String?
    let changePct: Double?
    let weight: Double?

    enum CodingKeys: String, CodingKey {
        case symbol, name, weight
        case changePct = "change_pct"
    }
}
