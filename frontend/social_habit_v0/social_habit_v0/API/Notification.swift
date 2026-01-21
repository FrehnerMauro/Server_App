import Foundation

// ============================================================
// MARK: - Datentypen
// ============================================================

/// Repräsentiert eine einzelne Notification vom Server
struct NotificationItem: Codable, Identifiable {
    let id: Int
    let user_id: Int
    let message: String
    let type: NotificationType
    let target_type: NotificationTargetType?
    let target_id: Int?
    let created_at: Int
    let read: Int
    
    // Abgeleitete Hilfswerte
    var createdDate: Date {
        Date(timeIntervalSince1970: TimeInterval(created_at) / 1000.0)
    }
    
    var isRead: Bool { read != 0 }
}

/// Typ der Notification (Backend-Feld "type")
enum NotificationType: String, Codable {
    case challengeInvite = "challenge_invite"
    case challengeConfirm = "challenge_confirm"
    case challengeMessage = "challenge_message"
    case friendRequest = "friend_request"
    case info = "info"
    case unknown
    
    init(from decoder: Decoder) throws {
        let raw = try decoder.singleValueContainer().decode(String.self)
        self = NotificationType(rawValue: raw) ?? .unknown
    }
}

/// Typ des Ziels (Backend-Feld "target_type")
enum NotificationTargetType: String, Codable {
    case challenge
    case user
    case chat
    case unknown
    
    init(from decoder: Decoder) throws {
        let raw = try decoder.singleValueContainer().decode(String.self)
        self = NotificationTargetType(rawValue: raw) ?? .unknown
    }
}

// ============================================================
// MARK: - API-Klasse
// ============================================================

final class api_notifications {

    private let Api: api
    init(Api: api) { self.Api = Api }

    // ------------------------------------------------------------
    // 📩 Alle Notifications abrufen
    // ------------------------------------------------------------
    func notifications() async throws -> [NotificationItem] {
        let (data, http) = try await Api.request("notifications")
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Notifications laden fehlgeschlagen (\(http.statusCode))")
        }
        return try Api.decode(data)
    }

    // ------------------------------------------------------------
    // ✅ Notification als gelesen markieren
    // ------------------------------------------------------------
    func markAsRead(_ id: Int) async throws {
        let (data, http) = try await Api.request("notifications/mark_read/\(id)", method: "POST")
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
    }

    // ------------------------------------------------------------
    // 🧹 Alle Notifications löschen
    // ------------------------------------------------------------
    func clearAll() async throws {
        let (data, http) = try await Api.request("notifications/clear", method: "DELETE")
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
    }
}
