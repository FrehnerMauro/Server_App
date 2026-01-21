//
//  API_LoginRegister.swift
//  social_habit_v0
//

import Foundation
import UIKit

final class api_login_register {
    private let Api: api
    init(Api: api) { self.Api = Api }

    // ------------------------------------------------------------
    // Envelope: Server-Antwort kann verschieden heißen
    // ------------------------------------------------------------
    struct LooseLoginEnvelope: Decodable {
        let token: String?
        let accessToken: String?
        let authToken: String?
        let jwt: String?
        let user: User?
    }

    // ------------------------------------------------------------
    // Token-Erkennung aus JSON oder Header
    // ------------------------------------------------------------
    private func extractToken(from data: Data, http: HTTPURLResponse) -> (token: String?, user: User?) {
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            if let tok = json["token"] as? String ??
                         json["accessToken"] as? String ??
                         json["authToken"] as? String ??
                         json["jwt"] as? String {
                if let userDict = json["user"] as? [String: Any],
                   let userData = try? JSONSerialization.data(withJSONObject: userDict),
                   let user = try? JSONDecoder().decode(User.self, from: userData) {
                    return (tok, user)
                }
                return (tok, nil)
            }
        }

        let headers = http.allHeaderFields
        let possibleKeys = [
            "token", "authorization",
            "X-Auth-Token", "x-auth-token",
            "X-Access-Token", "x-access-token"
        ]
        for key in possibleKeys {
            if let raw = headers[key] as? String, !raw.isEmpty {
                if raw.lowercased().hasPrefix("bearer ") {
                    return (String(raw.dropFirst(7)), nil)
                }
                return (raw, nil)
            }
        }

        if let s = String(data: data, encoding: .utf8),
           s.count > 10,
           !s.contains("{") {
            return (s.trimmingCharacters(in: .whitespacesAndNewlines), nil)
        }

        return (nil, nil)
    }

    // ------------------------------------------------------------
    // Registrierung
    // ------------------------------------------------------------
    func register(vorname: String, name: String, email: String, passwort: String, nb_state: String) async throws -> LoginResponse {
        let body: [String: String] = [
            "vorname": vorname,
            "name": name,
            "email": email,
            "password": passwort,
            "nb_state": nb_state
        ]

        let (data, http) = try await Api.request("register", method: "POST", body: body)
        guard (200...299).contains(http.statusCode) else {
            throw Api.decodeServerError(data, code: http.statusCode)
        }

        let (tok, user) = extractToken(from: data, http: http)
        guard let token = tok else {
            throw APIError(message: "Register OK, aber kein Token erhalten")
        }

        return LoginResponse(token: token, user: user)
    }

    // ------------------------------------------------------------
    // Login mit automatischer Device-Token-Erfassung (APNs)
    // ------------------------------------------------------------
    func login(email: String, passwort: String) async throws -> LoginResponse {
        // 1️⃣ Versuche, das Apple-Device-Token aus UserDefaults zu holen
        var deviceToken: String? = UserDefaults.standard.string(forKey: "apns_device_token")

        // 2️⃣ Falls es noch nicht vorhanden ist, kurz warten, bis es registriert wurde
        if deviceToken == nil {
            print("⏳ Warte auf APNs Device Token …")
            for _ in 0..<10 { // bis zu 3 Sekunden warten
                try await Task.sleep(nanoseconds: 300_000_000)
                deviceToken = UserDefaults.standard.string(forKey: "apns_device_token")
                if deviceToken != nil { break }
            }
        }

        // 3️⃣ Fallback falls gar nichts da ist
        let finalToken = deviceToken ?? UIDevice.current.identifierForVendor?.uuidString ?? "unknown"
        print("📱 Verwende Device-Token für Login:", finalToken)

        // ✅ body als [String: String], kein Any mehr!
        let body: [String: String] = [
            "email": email,
            "password": passwort,
            "device_token": finalToken
        ]

        // 4️⃣ Haupt-Login
        do {
            let (data, http) = try await Api.request("login", method: "POST", body: body)
            guard (200...299).contains(http.statusCode) else {
                throw APIError(message: "Login fehlgeschlagen (\(http.statusCode))")
            }
            let (tok, user) = extractToken(from: data, http: http)
            if let token = tok {
                return LoginResponse(token: token, user: user)
            }
        } catch {
            print("⚠️ /login fehlgeschlagen, versuche /auth/login …")
        }

        // 5️⃣ Fallback /auth/login
        let (data2, http2) = try await Api.request("auth/login", method: "POST", body: body)
        guard (200...299).contains(http2.statusCode) else {
            throw APIError(message: "Login fehlgeschlagen (\(http2.statusCode))")
        }

        let (tok2, user2) = extractToken(from: data2, http: http2)
        guard let token2 = tok2 else {
            throw APIError(message: "Login OK, aber kein Token erhalten")
        }

        return LoginResponse(token: token2, user: user2)
    }
}
