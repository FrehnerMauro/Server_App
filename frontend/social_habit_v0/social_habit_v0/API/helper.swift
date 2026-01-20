import Foundation

final class api {
    var baseURL: URL
    var token: String?

    let session: URLSession

    /// Haupt-Initializer mit Defaults
    init(
        baseURL: URL = URL(string: "https://api.socialhabit.org")!,
        session: URLSession = {
            let cfg = URLSessionConfiguration.default
            cfg.timeoutIntervalForRequest = 25
            cfg.timeoutIntervalForResource = 50
            return URLSession(configuration: cfg)
        }()
    ) {
        self.baseURL = baseURL
        self.session = session
    }

    func setToken(_ t: String?) { self.token = t }
    var isAuthed: Bool { token != nil }

    // MARK: - Core request
    func request(_ path: String,
                 method: String = "GET",
                 query: [String:String]? = nil,
                 body: Encodable? = nil) async throws -> (Data, HTTPURLResponse) {

        var url = baseURL.appendingPathComponent(path)
        if let q = query, !q.isEmpty, var comps = URLComponents(url: url, resolvingAgainstBaseURL: false) {
            comps.queryItems = q.map { URLQueryItem(name: $0.key, value: $0.value) }
            url = comps.url ?? url
        }

        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Accept")

        if let token {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body {
            let enc = JSONEncoder()
            req.httpBody = try enc.encode(AnyEncodable(body))
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let (data, resp) = try await session.data(for: req)
        guard let http = resp as? HTTPURLResponse else {
            throw APIError(message: "Kein HTTP Response")
        }
        return (data, http)
    }

    func decode<T: Decodable>(_ data: Data) throws -> T {
        let dec = JSONDecoder()
        return try dec.decode(T.self, from: data)
    }

    func decodeServerError(_ data: Data, code: Int) -> APIError {
        if let obj = try? JSONSerialization.jsonObject(with: data) as? [String:Any] {
            if let details = obj["details"] { return APIError(message: "\(code): \(details)") }
            if let msg = obj["error"] as? String { return APIError(message: "\(code): \(msg)") }
        }
        return APIError(message: "Serverfehler \(code)")
    }

    func makeMultipartBody(boundary: String,
                           fileField: String,
                           filename: String,
                           mime: String,
                           data: Data) -> Data {
        var body = Data()
        let prefix = "--\(boundary)\r\n"
        body.append(prefix.data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"\(fileField)\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: \(mime)\r\n\r\n".data(using: .utf8)!)
        body.append(data)
        body.append("\r\n".data(using: .utf8)!)
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        return body
    }
}
