//
//  Friends.swift
//  social_habit_v0
//
//  Created by Mauro Frehner on 11.10.2025.
//
import Foundation

final class api_friends {
    private let Api: api
    init(Api: api) { self.Api = Api }
    
    func listFriendRequests(direction: String) async throws -> [FriendRequest] {
        let (data, http) = try await Api.request("friends/requests", query: ["direction": direction])
        guard (200...299).contains(http.statusCode) else { throw APIError(message: "Friend-Requests laden fehlgeschlagen") }
        return try Api.decode(data)
    }
    
    func sendFriendRequest(toUserId: Int, message: String?) async throws {
        let (data, http) = try await Api.request("friends/request/\(toUserId)", method: "POST")
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
    }
    func acceptFriendRequest(_ id: Int) async throws -> Bool {
        let (data, http) = try await Api.request("friends/requests/\(id)/accept", method: "POST")
        
        // Prüfe HTTP-Status
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
        
        // Versuche, Antwort zu decodieren
        struct FriendAcceptResponse: Codable {
            let ok: Bool
            let message: String?
        }
        
        if let decoded = try? JSONDecoder().decode(FriendAcceptResponse.self, from: data) {
            print("✅ Freundschaft akzeptiert:", decoded.message ?? "")
            return decoded.ok
        } else {
            print("⚠️ Antwort konnte nicht decodiert werden.")
            return true // Fallback, falls API zwar 200 liefert, aber kein JSON-Body
        }
    }
    
    func declineFriendRequest(_ id: Int) async throws {
        let (data, http) = try await Api.request("friends/requests/\(id)/decline", method: "POST")
        guard (200...299).contains(http.statusCode) else { throw Api.decodeServerError(data, code: http.statusCode) }
        _ = data
    }
    
    
    // mit Checksum ------------------------------------------------------------------------------------------------------------
    func listUsers() async throws -> [User] {
        struct Cache {
            static var users: [User]? = nil
            static var sum: UInt64? = nil
            static var refreshing = false
        }
        func checksum(_ data: Data) -> UInt64 {
            var h: UInt64 = 1469598103934665603
            for b in data { h ^= UInt64(b); h &*= 1099511628211 }
            return h
        }

        if let cached = Cache.users {
            if !Cache.refreshing {
                Cache.refreshing = true
                let Api = self.Api
                Task.detached {
                    defer { Cache.refreshing = false }
                    do {
                        let (data, http) = try await Api.request("users")
                        guard (200...299).contains(http.statusCode) else { return }
                        let newSum = checksum(data)
                        if Cache.sum != newSum {
                            let fresh: [User] = try Api.decode(data)
                            Cache.users = fresh
                            Cache.sum = newSum
                        }
                    } catch { /* still ignorieren */ }
                }
            }
            return cached
        }

        let (data, http) = try await Api.request("users")
        guard (200...299).contains(http.statusCode) else { throw APIError(message: "Users laden fehlgeschlagen") }
        let res: [User] = try Api.decode(data)
        Cache.users = res
        Cache.sum = checksum(data)
        return res
    }
    
    func listFriends() async throws -> [User] {
        struct Cache {
            static var friends: [User]? = nil
            static var sum: UInt64? = nil
            static var refreshing = false
        }

        func checksum(_ data: Data) -> UInt64 {
            var h: UInt64 = 1469598103934665603
            for b in data { h ^= UInt64(b); h &*= 1099511628211 }
            return h
        }

        if let cached = Cache.friends {
            if !Cache.refreshing {
                Cache.refreshing = true
                let Api = self.Api
                Task.detached {
                    defer { Cache.refreshing = false }
                    do {
                        let (data, http) = try await Api.request("friends/list")
                        guard (200...299).contains(http.statusCode) else { return }
                        let newSum = checksum(data)
                        if Cache.sum != newSum {
                            let fresh: [User] = try Api.decode(data)
                            Cache.friends = fresh
                            Cache.sum = newSum
                        }
                    } catch { /* ignorieren */ }
                }
            }
            return cached
        }

        let (data, http) = try await Api.request("friends/list")
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Freunde laden fehlgeschlagen")
        }

        let res: [User] = try Api.decode(data)
        Cache.friends = res
        Cache.sum = checksum(data)
        return res
    }
    
    
    func removeFriend(userId: Int) async throws {
        let (data, http) = try await Api.request("friends/remove/\(userId)", method: "DELETE")
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
    }


}

public struct FriendBlock: Codable, Identifiable, Equatable {
    public var id: Int { userId }
    public var userId: Int
    public var displayName: String
    public var avatarUrl: String?
    public var createdAt: Int

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case displayName = "display_name"
        case avatarUrl = "avatar_url"
        case createdAt = "created_at"
    }
}
extension api_friends {
    
    // ============================================================
    // MARK: - BLOCK USER
    // ============================================================
    func blockUser(_ userId: Int) async throws {
        let (data, http) = try await Api.request("friends/block/\(userId)", method: "POST")
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
    }

    // ============================================================
    // MARK: - UNBLOCK USER
    // ============================================================
    func unblockUser(_ userId: Int) async throws {
        let (data, http) = try await Api.request("friends/block/\(userId)", method: "DELETE")
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
    }

    // ============================================================
    // MARK: - LIST BLOCKED USERS
    // ============================================================
    func listBlockedUsers() async throws -> [FriendBlock] {
        struct Cache {
            static var blocks: [FriendBlock]? = nil
            static var sum: UInt64? = nil
            static var refreshing = false
        }

        func checksum(_ data: Data) -> UInt64 {
            var h: UInt64 = 1469598103934665603
            for b in data { h ^= UInt64(b); h &*= 1099511628211 }
            return h
        }

        if let cached = Cache.blocks {
            if !Cache.refreshing {
                Cache.refreshing = true
                let Api = self.Api
                Task.detached {
                    defer { Cache.refreshing = false }
                    do {
                        let (data, http) = try await Api.request("friends/blocks")
                        guard (200...299).contains(http.statusCode) else { return }
                        let newSum = checksum(data)
                        if Cache.sum != newSum {
                            let fresh: [FriendBlock] = try Api.decode(data)
                            Cache.blocks = fresh
                            Cache.sum = newSum
                        }
                    } catch { /* ignorieren */ }
                }
            }
            return cached
        }

        let (data, http) = try await Api.request("friends/blocks")
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Blockierte Benutzer laden fehlgeschlagen")
        }

        let res: [FriendBlock] = try Api.decode(data)
        Cache.blocks = res
        Cache.sum = checksum(data)
        return res
    }
}

struct FriendSearchResult: Codable, Identifiable {
    var id: Int
    var display_name: String
    var avatar_url: String?
    var relation_status: String?
}

extension api_friends {
    func searchUsers(query: String) async throws -> [FriendSearchResult] {
        let (data, http) = try await Api.request("friends/search", query: ["query": query])
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Suche fehlgeschlagen")
        }
        return try Api.decode(data)
    }
}


