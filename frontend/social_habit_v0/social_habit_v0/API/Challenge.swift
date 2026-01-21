//
//  Challenge.swift
//  social_habit_v0
//
//  Created by Mauro Frehner on 11.10.2025.
//

import Foundation

final class api_challenge {
    private let Api: api
    init(Api: api) { self.Api = Api }

    
    
    // MARK: - Confirm (Challenge-Beitrag bestätigen)
    func confirm(
        _ challengeId: Int,
        imageDataURL: String,
        caption: String?,
        visibility: String,
        date: String? = nil,
        tzOffsetMinutes: Int? = nil,
        timestamp: Int64? = nil
    ) async throws {
        var query: [String: String] = [:]
        if let date { query["date"] = date }
        if let tzOffsetMinutes { query["tzOffsetMinutes"] = String(tzOffsetMinutes) }

        var body: [String: AnyEncodable] = [
            "imageUrl": AnyEncodable(imageDataURL),
            "visibility": AnyEncodable(visibility)
        ]

        if let caption { body["caption"] = AnyEncodable(caption) }
        if let timestamp { body["timestamp"] = AnyEncodable(timestamp) }

        // 📡 Request absenden
        let (data, http) = try await Api.request(
            "challenges/\(challengeId)/confirm",
            method: "POST",
            query: query,
            body: body
        )

        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }

        // 🧩 Optional: Debug-Ausgabe für Rückmeldung
        if let jsonString = String(data: data, encoding: .utf8) {
            print("[DEBUG] confirm response JSON:\n\(jsonString)")
        }
    }

    /// Holt eine vollständige Challenge-Übersicht mit Mitgliedern & Stats
    func challengeOverview() async throws -> [ChallengeOverview] {
        let (data, http) = try await Api.request("challenges/user/overview")
        
        // 🧩 Debug-Ausgabe: zeige den rohen Server-Response als Text
        if let jsonString = String(data: data, encoding: .utf8) {
            print("[DEBUG] ChallengeOverview raw JSON:\n\(jsonString)")
        } else {
            print("[DEBUG] ChallengeOverview raw JSON not UTF-8 decodable")
        }

        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }

        // 🧩 Jetzt korrekt decodieren
        let decoded: [ChallengeOverview] = try Api.decode(data)
        print("[DEBUG] ChallengeOverview decoded count:", decoded.count)
        return decoded
    }
    // MARK: - Chat / Posten
    func challengeChatList(_ challengeId: Int) async throws -> ChallengeChatResponse {
        let (data, http) = try await Api.request("challenges/\(challengeId)/chat/full")
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Chat laden fehlgeschlagen (\(http.statusCode))")
        }

        let decoded: ChallengeChatResponse = try Api.decode(data)
        return decoded
    }
    
    func sendMessage(challengeId: Int, text: String) async throws {
        let body = ["message": text]
        _ = try await Api.request("challenges/\(challengeId)/chat/message", method: "POST", body: body)
    }
    

    func sendImage(challengeId: Int, base64: String) async throws {
        let body = ["image_url": base64]
        _ = try await Api.request("challenges/\(challengeId)/chat/image", method: "POST", body: body)
    }

    
    
    
    

    func postChat(_ challengeId: Int, text: String) async throws {
        let body = ChatBody(text: text)
        let (data, http) = try await Api.request(
            "challenges/\(challengeId)/chat",
            method: "POST",
            body: body
        )
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
        _ = data
    }



    // MARK: - Create Challenge
    func createChallenge(
        name: String,
        daysOfWeek: [Int],
        startAt: Int64,
        beschreibung: String?,
        friendsToAdd: [Int],
        dauerTage: Int,
        erlaubteFailsTage: Int
    ) async throws -> ChallengeResponse {
        // 📦 Verwende dein bestehendes Model
        let body = CreateChallengeBody(
            name: name,
            beschreibung: beschreibung,
            art: nil,
            startAt: startAt,
            faelligeWochentage: daysOfWeek,
            friendsToAdd: friendsToAdd,
            days: nil,
            dauerTage: dauerTage,
            erlaubteFailsTage: erlaubteFailsTage
        )

        // 📡 Request absenden
        let (data, http) = try await Api.request(
            "challenges",
            method: "POST",
            body: body
        )

        // 🔍 Statuscode prüfen
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Challenge konnte nicht erstellt werden (\(http.statusCode))")
        }

        // 🧩 Optional: Debug-Ausgabe (Server-Response)
        if let jsonString = String(data: data, encoding: .utf8) {
            print("[DEBUG] createChallenge Response JSON:\n\(jsonString)")
        }

        // 🧠 Decodieren in dein Response-Model
        return try Api.decode(data)
    }

    func leaveChallenge(_ id: Int) async throws {
        let (data, http) = try await Api.request("challenges/\(id)/leave", method: "POST")

        // Erfolgreich verlassen
        if (200...299).contains(http.statusCode) {
            return
        }

        // Fehlerantwort vom Server auslesen
        if let serverError = try? JSONDecoder().decode([String: String].self, from: data),
           let errorCode = serverError["error"] {
            switch errorCode {
            case "already_started":
                throw APIError(message: serverError["message"] ?? "Challenge hat bereits begonnen und kann nicht mehr verlassen werden.")
            case "not_found":
                throw APIError(message: "Challenge wurde nicht gefunden.")
            default:
                throw APIError(message: serverError["message"] ?? "Unbekannter Fehler beim Verlassen der Challenge.")
            }
        }

        // Fallback
        throw APIError(message: "Fehler beim Verlassen der Challenge (\(http.statusCode))")
    }

    // MARK: - Invites

    func listChallengeInvites(direction: String) async throws -> [ChallengeInvite] {
        let (data, http) = try await Api.request("challenges/invites", query: ["direction": direction])
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Einladungen laden fehlgeschlagen")
        }
        return try Api.decode(data)
    }

    func sendChallengeInvite(challengeId: Int, toUserId: Int, message: String?) async throws {
        let body = SendChallengeInviteBody(toUserId: toUserId, message: message)
        let (_, http) = try await Api.request(
            "challenges/\(challengeId)/invites",
            method: "POST",
            body: body
        )
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Invite senden fehlgeschlagen (\(http.statusCode))")
        }
    }

    func acceptChallengeInvite(_ rid: Int) async throws {
        let (data, http) = try await Api.request("challenges/invites/\(rid)/accept", method: "POST")
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
        _ = data
    }

    func declineChallengeInvite(_ rid: Int) async throws {
        let (data, http) = try await Api.request("challenges/invites/\(rid)/decline", method: "POST")
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
        _ = data
    }

    // MARK: - Challenges (Liste)
    func listChallenges(withToday: Bool, tzOffsetMinutes: Int) async throws -> [ChallengeWithToday] {
           var query: [String: String] = [:]
           if withToday {
               query["withToday"] = "true"
               query["tzOffsetMinutes"] = "\(tzOffsetMinutes)"
           }

           let (data, http) = try await Api.request("challenges/list", query: query)
           guard (200...299).contains(http.statusCode) else {
               throw APIError(message: "Challenges laden fehlgeschlagen (\(http.statusCode))")
           }

           // Erst englische Felder vom Server decoden …
           struct ServerChallenge: Codable {
               let id: Int
               let title: String
               let description: String?
               let creator_id: Int
               let due_weekdays: String?
               let duration_days: Int?
               let allowed_fails: Int?
               let created_at: Int?
           }

           let serverList = try JSONDecoder().decode([ServerChallenge].self, from: data)

           // … dann in dein Challenge-Model übersetzen
           let converted = serverList.map { s -> Challenge in
               let weekdays = s.due_weekdays?
                   .split(separator: ",")
                   .compactMap { Int($0.trimmingCharacters(in: .whitespaces)) }

               return Challenge(
                   id: s.id,
                   name: s.title,
                   beschreibung: s.description,
                   ownerId: s.creator_id,
                   faelligeWochentage: weekdays,
                   hinzugefuegtAt: s.created_at,
                   dauerTage: s.duration_days,
                   erlaubteFailsTage: s.allowed_fails
               )
           }

           // ChallengeWithToday bauen – gleiche Struktur
           return converted.map { ChallengeWithToday(from: $0) }
       }




    // MARK: - Challenge Detail (Actor-Cache + Hintergrund-Refresh)

    func challengeDetail(_ id: Int) async throws -> Challenge {
        struct Holder { static let cache = ChallengeDetailCache() }
        let cache = Holder.cache

        if let cached = await cache.cachedDetail(for: id) {
            if await cache.startRefreshIfNeeded(id: id) {
                let Api = self.Api
                Task(priority: .background) {
                    do {
                        let (data, http) = try await Api.request("challenges/\(id)")
                        guard (200...299).contains(http.statusCode) else {
                            await cache.finishRefresh(id: id, detail: nil, sum: nil)
                            return
                        }
                        let newSum = self.checksum(data)
                        let oldSum = await cache.sum(for: id)
                        if oldSum != newSum {
                            let fresh: Challenge = try Api.decode(data)
                            await cache.finishRefresh(id: id, detail: fresh, sum: newSum)
                        } else {
                            await cache.finishRefresh(id: id, detail: nil, sum: newSum)
                        }
                    } catch {
                        await cache.finishRefresh(id: id, detail: nil, sum: nil)
                    }
                }
            }
            return cached
        }

        let (data, http) = try await Api.request("challenges/\(id)")
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Challenge nicht gefunden")
        }
        let res: Challenge = try Api.decode(data)
        await cache.finishRefresh(id: id, detail: res, sum: checksum(data))
        return res
    }

    // MARK: - Mitglieder (Actor-Cache + Hintergrund-Refresh)

    func challengeMembers(_ id: Int) async throws -> [Member] {
        struct Holder { static let cache = MembersCache() }
        let cache = Holder.cache

        if let cached = await cache.cachedMembers(for: id) {
            if await cache.startRefreshIfNeeded(id: id) {
                let Api = self.Api
                Task(priority: .background) {
                    do {
                        let (data, http) = try await Api.request("challenges/\(id)/members")
                        guard (200...299).contains(http.statusCode) else {
                            await cache.finishRefresh(id: id, members: nil, sum: nil)
                            return
                        }
                        let newSum = self.checksum(data)
                        let oldSum = await cache.sum(for: id)
                        if oldSum != newSum {
                            let fresh: [Member] = try Api.decode(data)
                            await cache.finishRefresh(id: id, members: fresh, sum: newSum)
                        } else {
                            await cache.finishRefresh(id: id, members: nil, sum: newSum)
                        }
                    } catch {
                        await cache.finishRefresh(id: id, members: nil, sum: nil)
                    }
                }
            }
            return cached
        }

        let (data, http) = try await Api.request("challenges/\(id)/members")
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Mitglieder laden fehlgeschlagen")
        }
        let res: [Member] = try Api.decode(data)
        await cache.finishRefresh(id: id, members: res, sum: checksum(data))
        return res
    }

    // MARK: - Activity (Actor-Cache + Hintergrund-Refresh)

    func challengeActivity(_ id: Int) async throws -> [ActivityItem] {
        struct Holder { static let cache = ChallengeActivityCache() }
        let cache = Holder.cache

        if let cached = await cache.cachedActivity(for: id) {
            if await cache.startRefreshIfNeeded(id: id) {
                let Api = self.Api
                Task(priority: .background) {
                    do {
                        let (data, http) = try await Api.request("challenges/\(id)/activity")
                        guard (200...299).contains(http.statusCode) else {
                            await cache.finishRefresh(id: id, activity: nil, sum: nil)
                            return
                        }
                        let newSum = self.checksum(data)
                        let oldSum = await cache.sum(for: id)
                        if oldSum != newSum {
                            let fresh: [ActivityItem] = try Api.decode(data)
                            await cache.finishRefresh(id: id, activity: fresh, sum: newSum)
                        } else {
                            await cache.finishRefresh(id: id, activity: nil, sum: newSum)
                        }
                    } catch {
                        await cache.finishRefresh(id: id, activity: nil, sum: nil)
                    }
                }
            }
            return cached
        }

        let (data, http) = try await Api.request("challenges/\(id)/activity")
        guard (200...299).contains(http.statusCode) else {
            throw APIError(message: "Activity laden fehlgeschlagen")
        }
        let res: [ActivityItem] = try Api.decode(data)
        await cache.finishRefresh(id: id, activity: res, sum: checksum(data))
        return res
    }

    // MARK: - Hilfen

    private func checksum(_ data: Data) -> UInt64 {
        var h: UInt64 = 1469598103934665603 // FNV-1a 64
        for b in data {
            h ^= UInt64(b)
            h &*= 1099511628211
        }
        return h
    }
    
    
}

// MARK: - Actor Caches

private actor ChallengeDetailCache {
    private var details: [Int: Challenge] = [:]
    private var sums: [Int: UInt64] = [:]
    private var refreshing: Set<Int> = []

    func cachedDetail(for id: Int) -> Challenge? { details[id] }
    func sum(for id: Int) -> UInt64? { sums[id] }

    func startRefreshIfNeeded(id: Int) -> Bool {
        if refreshing.contains(id) { return false }
        refreshing.insert(id)
        return true
    }

    func finishRefresh(id: Int, detail new: Challenge?, sum: UInt64?) {
        if let new { details[id] = new }
        if let sum { sums[id] = sum }
        refreshing.remove(id)
    }
}

private actor ChallengeChatCache {
    private var chats: [Int: [ChatMessage]] = [:]
    private var sums: [Int: UInt64] = [:]
    private var refreshing: Set<Int> = []

    func cachedChat(for id: Int) -> [ChatMessage]? { chats[id] }
    func sum(for id: Int) -> UInt64? { sums[id] }

    func startRefreshIfNeeded(id: Int) -> Bool {
        if refreshing.contains(id) { return false }
        refreshing.insert(id)
        return true
    }

    func finishRefresh(id: Int, chat new: [ChatMessage]?, sum: UInt64?) {
        if let new { chats[id] = new }
        if let sum { sums[id] = sum }
        refreshing.remove(id)
    }
}

private actor MembersCache {
    private var members: [Int: [Member]] = [:]
    private var sums: [Int: UInt64] = [:]
    private var refreshing: Set<Int> = []

    func cachedMembers(for id: Int) -> [Member]? { members[id] }
    func sum(for id: Int) -> UInt64? { sums[id] }

    func startRefreshIfNeeded(id: Int) -> Bool {
        if refreshing.contains(id) { return false }
        refreshing.insert(id)
        return true
    }

    func finishRefresh(id: Int, members new: [Member]?, sum: UInt64?) {
        if let new { members[id] = new }
        if let sum { sums[id] = sum }
        refreshing.remove(id)
    }
}

private actor ChallengeActivityCache {
    private var acts: [Int: [ActivityItem]] = [:]
    private var sums: [Int: UInt64] = [:]
    private var refreshing: Set<Int> = []

    func cachedActivity(for id: Int) -> [ActivityItem]? { acts[id] }
    func sum(for id: Int) -> UInt64? { sums[id] }

    func startRefreshIfNeeded(id: Int) -> Bool {
        if refreshing.contains(id) { return false }
        refreshing.insert(id)
        return true
    }

    func finishRefresh(id: Int, activity new: [ActivityItem]?, sum: UInt64?) {
        if let new { acts[id] = new }
        if let sum { sums[id] = sum }
        refreshing.remove(id)
    }
}



// MARK: - Challenge Info (inkl. Mitglieder)
struct ChallengeInfoResponse: Codable {
    struct ChallengeInfo: Codable {
        let id: Int
        let title: String?
        let description: String?
        let creator_id: Int
        let start_at: Int?
        let duration_days: Int?
        let allowed_fails: Int?
        let due_weekdays: String?
        let created_at: Int?
        let updated_at: Int?
    }

    struct ChallengeMemberInfo: Codable, Identifiable {
        var id: Int { user_id }
        let user_id: Int
        let display_name: String
        let avatar_url: String?
        let joined_at: Int?
        let blocked: String?  // "not_started", "pending", "run", "completed"
        let today_pending: Int?  // 1 = heute fällig, 0 = nicht fällig
        let today_done: Int?  // 1 = heute erledigt, 0 = nicht erledigt
        let conf_count: Int?
        let fail_count: Int?
        let status: String?  // "creator", "accepted", "pending"
    }

    let challenge: ChallengeInfo
    let members: [ChallengeMemberInfo]
}

extension api_challenge {
    /// Holt Detailinfos zu einer Challenge inkl. Mitgliederliste.
    func getChallengeInfo(_ id: Int) async throws -> ChallengeInfoResponse {
        let (data, http) = try await Api.request("challenges/\(id)/info")
        
        // Debug-Ausgabe
        if let raw = String(data: data, encoding: .utf8) {
            print("[DEBUG] Challenge Info Response für ID \(id):\n\(raw)")
        }

        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }

        let decoded: ChallengeInfoResponse = try Api.decode(data)
        return decoded
    }
}
