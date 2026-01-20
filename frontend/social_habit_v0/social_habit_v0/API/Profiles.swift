//
//  Profiles.swift
//  social_habit_v0
//
//  Created by Mauro Frehner on 11.10.2025.
//

import Foundation

final class api_profiles {
    private let Api: api
    init(Api: api) { self.Api = Api }

    // ============================================================
    // MARK: - Eigenes Profil abrufen (inkl. Posts, Likes, Kommentare)
    // ============================================================

    func getMyProfileFull() async throws -> ProfileMeResponse {
        let (data, http) = try await Api.request("users/me")
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Profil konnte nicht geladen werden (\(http.statusCode))")
        }
        return try Api.decode(data)
    }

    // ============================================================
    // MARK: - Profil eines anderen Benutzers abrufen (ohne private Posts)
    // ============================================================

    func getUserProfile(userId: Int) async throws -> ProfileMeResponse {
        let (data, http) = try await Api.request("users/\(userId)")
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
        return try Api.decode(data)
    }
}

// ============================================================
// MARK: - Datenmodelle für /users/me und /users/{id}
// ============================================================

/// Antwortstruktur für GET /users/me oder /users/{id}
struct ProfileMeResponse: Codable, Identifiable {
    let id: Int
    let display_name: String?
    let avatar_url: String?
    let anzahl_freunde: Int
    let anzahl_posts: Int
    let meine_posts: ProfilePostsContainer
}

/// Container für getrennte Post-Listen (freunde & privat / public)
struct ProfilePostsContainer: Codable {
    let freunde: [ProfilePost]
    let privat: [ProfilePost]?
    let public_: [ProfilePost]?  // wird nur bei fremden Profilen genutzt

    enum CodingKeys: String, CodingKey {
        case freunde
        case privat
        case public_ = "public"
    }
}

/// Einzelner Post mit Likes & Kommentaren
struct ProfilePost: Codable, Identifiable {
    let id: Int
    let content: String
    let image_url: String?
    let visibility: String?
    let created_at: Int
    let like_count: Int
    let comment_count: Int
    let likes: [ProfileLike]
    let comments: [ProfileComment]
}

/// Like eines Benutzers (vereinfachte User-Infos)
struct ProfileLike: Codable, Identifiable {
    var id: Int { user_id }
    let user_id: Int
    let display_name: String?
    let avatar_url: String?
}

/// Kommentar eines Benutzers unter einem Post
struct ProfileComment: Codable, Identifiable {
    let id: Int
    let comment: String
    let created_at: Int
    let display_name: String?
    let avatar_url: String?
}
