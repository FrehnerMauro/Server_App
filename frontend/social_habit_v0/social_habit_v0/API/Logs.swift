//
//  Logs.swift
//  social_habit_v0
//
//  Created by Mauro Frehner on 12.10.2025.
//
import Foundation




final class api_log
{
    private let Api: api
    init(Api: api) { self.Api = Api }
    
    func challengeStatsRecalc(_ challengeId: Int, tzOffsetMinutes: Int) async throws -> StatsRecalcResponse {
        let (data, http) = try await Api.request("challenges/\(challengeId)/stats/recalc",
                                             method: "POST",
                                             query: ["tzOffsetMinutes": String(tzOffsetMinutes)])
        guard (200...299).contains(http.statusCode) else { throw Api.decodeServerError(data, code: http.statusCode) }
        return try Api.decode(data)
    }
    
    func challengeBlocked(_ challengeId: Int, tzOffsetMinutes: Int) async throws -> BlockedListResponse {
        let (data, http) = try await Api.request("challenges/\(challengeId)/blocked",
                                             query: ["tzOffsetMinutes": String(tzOffsetMinutes)])
        guard (200...299).contains(http.statusCode) else { throw Api.decodeServerError(data, code: http.statusCode) }
        return try Api.decode(data)
    }
    
    func challengeFailLogs(_ challengeId: Int,
                           userId: Int? = nil,
                           from: String? = nil,
                           to: String? = nil,
                           tzOffsetMinutes: Int) async throws -> FailLogsResponse {
        var q: [String:String] = ["tzOffsetMinutes": String(tzOffsetMinutes)]
        if let userId { q["userId"] = String(userId) }
        if let from { q["from"] = from }
        if let to { q["to"] = to }
        let (data, http) = try await Api.request("challenges/\(challengeId)/logs/fails", query: q)
        guard (200...299).contains(http.statusCode) else { throw Api.decodeServerError(data, code: http.statusCode) }
        return try Api.decode(data)
    }
    
    // mit Checksum -------------------------------------------------------------------------------------------------------
    func challengeStatsUsers(
        _ challengeId: Int,
        tzOffsetMinutes: Int = TimeZone.current.secondsFromGMT() / 60
    ) async throws -> ChallengeStatsUserResponse {
        struct Cache {
            static var stats: [Int: ChallengeStatsUserResponse] = [:]
            static var sums: [Int: UInt64] = [:]
            static var refreshing: Set<Int> = []
        }

        func checksum(_ data: Data) -> UInt64 {
            var h: UInt64 = 1469598103934665603
            for b in data { h ^= UInt64(b); h &*= 1099511628211 }
            return h
        }

        // Sofort Cache liefern, falls vorhanden
        if let cached = Cache.stats[challengeId] {
            if !Cache.refreshing.contains(challengeId) {
                Cache.refreshing.insert(challengeId)
                let Api = self.Api
                Task.detached {
                    defer { Cache.refreshing.remove(challengeId) }
                    do {
                        let (data, http) = try await Api.request(
                            "challenges/\(challengeId)/stats",
                            query: ["tzOffsetMinutes": String(tzOffsetMinutes)]
                        )
                        guard (200...299).contains(http.statusCode) else { return }
                        let newSum = checksum(data)
                        if Cache.sums[challengeId] != newSum {
                            let fresh: ChallengeStatsUserResponse = try Api.decode(data)
                            Cache.stats[challengeId] = fresh
                            Cache.sums[challengeId] = newSum
                        }
                    } catch {
                        // still ignorieren
                    }
                }
            }
            return cached
        }

        // Erstaufruf – normal laden
        let (data, http) = try await Api.request(
            "challenges/\(challengeId)/stats",
            query: ["tzOffsetMinutes": String(tzOffsetMinutes)]
        )
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }
        let res: ChallengeStatsUserResponse = try Api.decode(data)
        Cache.stats[challengeId] = res
        Cache.sums[challengeId] = checksum(data)
        return res
    }
}
