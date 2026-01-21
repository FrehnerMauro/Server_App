import Foundation

final class api_settings {
    private let Api: api
    init(Api: api) { self.Api = Api }

    // MARK: - Benutzer aktualisieren (Name + Passwort)
    func updateMe(displayName: String?, password: String?) async throws -> SettingsUser {
        struct Body: Codable {
            let display_name: String?
            let password: String?
        }

        let body = Body(display_name: displayName, password: password)
        let (data, http) = try await Api.request("settings/me", method: "PATCH", body: body)
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }

        // ❗ FIX: kein „as:“ Parameter mehr
        let response: SettingsUpdateResponse = try Api.decode(data)
        return response.user
    }

    // MARK: - Logout
    func logout() async throws {
        let (_, http) = try await Api.request("settings/logout", method: "POST")
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Logout fehlgeschlagen (\(http.statusCode))")
        }
    }

    // MARK: - Profil löschen
    func deleteProfile() async throws {
        let (_, http) = try await Api.request("settings/me", method: "DELETE")
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Profil löschen fehlgeschlagen (\(http.statusCode))")
        }
    }

    // MARK: - Blockierte Benutzer
    func listBlocked() async throws -> [SettingsBlockedUser] {
        let (data, http) = try await Api.request("settings/blocked")
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }

        // ❗ FIX
        return try Api.decode(data)
    }

    func blockUser(id: Int) async throws {
        let (_, http) = try await Api.request("settings/block/\(id)", method: "POST")
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Blockieren fehlgeschlagen (\(http.statusCode))")
        }
    }

    func unblockUser(id: Int) async throws {
        let (_, http) = try await Api.request("settings/block/\(id)", method: "DELETE")
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Entblocken fehlgeschlagen (\(http.statusCode))")
        }
    }

    // MARK: - Dummy Endpoints
    func getNotificationSettings() async throws -> SettingsNotificationResponse {
        let (data, http) = try await Api.request("settings/notifications")
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
        return try Api.decode(data)
    }

    func getPrivacySettings() async throws -> SettingsPrivacyResponse {
        let (data, http) = try await Api.request("settings/privacy")
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
        return try Api.decode(data)
    }

    func getTermsInfo() async throws -> SettingsTermsResponse {
        let (data, http) = try await Api.request("settings/terms")
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
        return try Api.decode(data)
    }
}

// MARK: - Datenmodelle

struct SettingsUser: Codable, Identifiable {
    let id: Int
    let display_name: String?
    let avatar_url: String?
    let email: String?
}

struct SettingsUpdateResponse: Codable {
    let ok: Bool
    let user: SettingsUser
}

struct SettingsBlockedUser: Codable, Identifiable {
    let user_id: Int
    let display_name: String?
    let avatar_url: String?
    var id: Int { user_id }
}

struct SettingsNotificationResponse: Codable {
    let push_enabled: Bool
    let challenge_reminders: Bool
    let email_notifications: Bool
}

struct SettingsPrivacyResponse: Codable {
    let privacy_policy: String
    let is_private: Bool
    let default_visibility: String
}

struct SettingsTermsResponse: Codable {
    let terms_url: String
    let version: String
    let last_updated: String
}
