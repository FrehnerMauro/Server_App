//
//  AppDelegate.swift
//  social_habit_v0
//
//  Created by Mauro Frehner on 06.11.2025.
//

import UIKit
import UserNotifications

class AppDelegate: NSObject, UIApplicationDelegate {
    
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey : Any]? = nil
    ) -> Bool {
        // 🔔 Push-Berechtigung anfragen
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { granted, _ in
            if granted {
                print("✅ Push-Berechtigung erteilt. Registriere für Remote Notifications …")
                DispatchQueue.main.async {
                    UIApplication.shared.registerForRemoteNotifications()
                }
            } else {
                print("⚠️ Push-Berechtigung verweigert.")
            }
        }
        return true
    }

    // 📲 Wird aufgerufen, wenn Apple das Device-Token übergibt
    func application(_ application: UIApplication,
                     didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        
        // 1️⃣ Token in reinen Hex-String umwandeln (ohne Leerzeichen, ohne < >)
        let tokenString = deviceToken.map { String(format: "%02x", $0) }.joined()
        
        // 2️⃣ Ausgabe mit Debug-Infos
        print("📱 APNs Device Token (HEX): \(tokenString)")
        print("🔢 Länge: \(tokenString.count) Zeichen")
        
        // 3️⃣ Prüfen, ob es ein gültiger Hex-String ist
        let isHex = tokenString.range(of: "^[0-9a-f]+$", options: .regularExpression) != nil
        print("🧩 Token ist gültiges Hex:", isHex ? "✅" : "❌")
        
        // 4️⃣ (Optional) Token speichern, damit er an deinen Server gesendet werden kann
        UserDefaults.standard.set(tokenString, forKey: "apns_device_token")
        print("💾 Token in UserDefaults gespeichert.")
    }

    // ❌ Wird aufgerufen, wenn die Registrierung bei APNs fehlschlägt
    func application(_ application: UIApplication,
                     didFailToRegisterForRemoteNotificationsWithError error: Error) {
        print("❌ APNs Registrierung fehlgeschlagen:", error.localizedDescription)
    }
}
