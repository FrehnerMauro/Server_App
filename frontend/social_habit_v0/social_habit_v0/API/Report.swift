//
//  Report.swift
//  social_habit_v0
//
//  Created by Mauro Frehner on 27.10.2025.
//

import Foundation

final class api_report {
    private let Api: api

    init(Api: api) {
        self.Api = Api
    }

    // MARK: - Etwas melden
    func createReport(
        userId: Int? = nil,
        postId: Int? = nil,
        challengeId: Int? = nil,
        messageId: Int? = nil,
        commentId: Int? = nil,
        reason: String
    ) async throws -> Bool {
        guard let token = Api.token, !token.isEmpty else {
            throw NSError(domain: "auth", code: 401, userInfo: [NSLocalizedDescriptionKey: "Kein Token vorhanden"])
        }

        let url = Api.baseURL.appendingPathComponent("report")
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Nur vorhandene IDs mitsenden
        var body: [String: Any] = ["reason": reason]
        if let userId { body["user_id"] = userId }
        if let challengeId { body["challenge_id"] = challengeId }
        if let postId { body["post_id"] = postId }

        if let messageId { body["message_id"] = messageId }
        if let commentId { body["comment_id"] = commentId }

        req.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse else { throw URLError(.badServerResponse) }

        if http.statusCode == 200 {
            return true
        } else {
            let errText = String(data: data, encoding: .utf8) ?? "Unbekannter Fehler"
            print("⚠️ Report Error:", errText)
            return false
        }
    }
}
