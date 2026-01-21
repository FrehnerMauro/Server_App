//
//  SocialAppV0App.swift
//  social_habit_v0
//

import SwiftUI

@main
struct SocialAppV0App: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    @StateObject private var app = AppState()
    @StateObject private var theme = ThemeManager()

    var body: some Scene {
        WindowGroup {
            RootBootView()
                .environmentObject(app)
                .environmentObject(theme)
                .tint(theme.theme.accent)
        }
    }
}




private struct RootBootView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager

    var body: some View {
        ContentView()
            .onAppear {
                // Base-URL default setzen
                if app.Api.baseURL.host == nil {
                    app.Api.baseURL = URL(string: "https://api.socialhabit.org")!
                }

                // Token aus Defaults
                if let token = UserDefaults.standard.string(forKey: "jwt"), !token.isEmpty {
                    app.Api.setToken(token)
                    // oder: app.setToken(token) falls du UI-States koppeln willst
                }
            }
    }
}
