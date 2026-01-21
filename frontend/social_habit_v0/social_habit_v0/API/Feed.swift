import Foundation



struct FeedItemDTO: Codable, Identifiable {
    let id: Int
    let display_name: String
    let challenge_title: String?
    let progress: Int?
    let avatar_url: String?
    let image_url: String?
    let content: String
    let created_at: Double
    let updated_at: Double?
    var likedByMe: Bool?
    var likesCount: Int?
    var commentsCount: Int?
    let user_id: Int?

    // Fallbacks für optionale Werte
    var safeLikedByMe: Bool { likedByMe ?? false }
    var safeLikesCount: Int { likesCount ?? 0 }
    var safeCommentsCount: Int { commentsCount ?? 0 }

    enum CodingKeys: String, CodingKey {
        case id, display_name,challenge_title, progress, avatar_url, image_url, content, created_at, updated_at
        case likedByMe, likesCount, commentsCount, user_id
    }
}



struct FeedCommentDTO: Codable, Identifiable {
    let id: Int
    let text: String
    let createdAt: Double
    let userId: Int?
    let displayName: String?
    let avatarUrl: String?

    enum CodingKeys: String, CodingKey {
        case id
        case text = "content"
        case createdAt = "created_at"
        case userId = "user_id"
        case displayName = "display_name"
        case avatarUrl = "avatar_url"
    }
}

final class api_feed {
    private let Api: api
    private let decoder = JSONDecoder()

    init(Api: api) {
        self.Api = Api
    }

    // MARK: - Helper: Request mit Token
    private func makeRequest(path: String, method: String = "GET", body: Data? = nil) throws -> URLRequest {
        guard let token = Api.token, !token.isEmpty else {
            print("❌ FEED ERROR: Kein Token gefunden!")
            throw NSError(domain: "auth", code: 401, userInfo: [NSLocalizedDescriptionKey: "Kein Token vorhanden"])
        }

        let url = Api.baseURL.appendingPathComponent(path)
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let body { req.httpBody = body }

        return req
    }

    // MARK: - Feed abrufen
    func feed() async throws -> [FeedItemDTO] {
        let req = try makeRequest(path: "feed/")
        let (data, response) = try await URLSession.shared.data(for: req)

        guard let http = response as? HTTPURLResponse,
              (200..<300).contains(http.statusCode) else {
            let text = String(data: data, encoding: .utf8) ?? "Unbekannter Fehler"
            throw NSError(domain: "FeedAPI", code: (response as? HTTPURLResponse)?.statusCode ?? -1,
                          userInfo: [NSLocalizedDescriptionKey: text])
        }

        do {
            return try decoder.decode([FeedItemDTO].self, from: data)
        } catch {
            print("❌ Feed Decoding Error:", error)
            if let jsonString = String(data: data, encoding: .utf8) {
                print("🔍 JSON String:", jsonString)
            }
            throw error
        }
    }

    // MARK: - Like / Unlike
    func feedLike(postId: Int) async throws -> Bool {
        let req = try makeRequest(path: "feed/\(postId)/like", method: "POST")
        let (_, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse,
              (200..<300).contains(http.statusCode) else { return false }
        return true
    }

    func feedUnlike(postId: Int) async throws -> Bool {
        let req = try makeRequest(path: "feed/\(postId)/unlike", method: "POST")
        let (_, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse,
              (200..<300).contains(http.statusCode) else { return false }
        return true
    }

    // MARK: - Kommentare abrufen
    func feedComments(postId: Int) async throws -> [FeedCommentDTO] {
        let req = try makeRequest(path: "feed/\(postId)/comments")
        let (data, response) = try await URLSession.shared.data(for: req)

        guard let http = response as? HTTPURLResponse,
              (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }

        return try decoder.decode([FeedCommentDTO].self, from: data)
    }

    // MARK: - Kommentar hinzufügen
    func feedAddComment(postId: Int, text: String) async throws -> Bool {
        let body = try JSONEncoder().encode(["text": text])
        let req = try makeRequest(path: "feed/\(postId)/comments", method: "POST", body: body)
        let (_, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse, http.statusCode == 201 else { return false }
        return true
    }
    
    // MARK: - Post löschen
    func feedDelete(postId: Int) async throws -> Bool {
        let req = try makeRequest(path: "feed/\(postId)", method: "DELETE")
        let (_, response) = try await URLSession.shared.data(for: req)

        guard let http = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }

        if (200..<300).contains(http.statusCode) {
            return true
        } else {
            // optional: Server-Fehlerinhalt anzeigen
            print("❌ Feed Delete fehlgeschlagen, Status:", http.statusCode)
            return false
        }
    }
}
