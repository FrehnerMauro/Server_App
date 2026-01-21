import SwiftUI
import UIKit

private func applyCustomTabBarTheme(_ theme: Theme) {
    let appearance = UITabBarAppearance()
    appearance.configureWithOpaqueBackground()
    appearance.backgroundColor = UIColor(theme.background)

    let normalColor = UIColor(theme.textSecondary)
    let selectedColor = UIColor(theme.accent)

    let normal = appearance.stackedLayoutAppearance.normal
    normal.iconColor = normalColor
    normal.titleTextAttributes = [.foregroundColor: normalColor]

    let selected = appearance.stackedLayoutAppearance.selected
    selected.iconColor = selectedColor
    selected.titleTextAttributes = [.foregroundColor: selectedColor]

    appearance.inlineLayoutAppearance = appearance.stackedLayoutAppearance
    appearance.compactInlineLayoutAppearance = appearance.stackedLayoutAppearance

    let tabBar = UITabBar.appearance()
    tabBar.standardAppearance = appearance
    if #available(iOS 15.0, *) {
        tabBar.scrollEdgeAppearance = appearance
    }

    tabBar.tintColor = selectedColor
    tabBar.unselectedItemTintColor = normalColor
}

struct ContentView: View {
    @EnvironmentObject private var app: AppState
    @EnvironmentObject private var theme: ThemeManager

    @State private var selectedTab = 0
    @State private var refreshTrigger = UUID()

    var body: some View {
        ZStack {
            theme.theme.backgroundGradient.ignoresSafeArea()

            Group {
                if app.token != nil {
                    TabView(selection: $selectedTab) {
                        FeedView()
                            .tabItem { Label("Feed", systemImage: "photo.on.rectangle") }
                            .tag(0)

                        ChallengesOverviewView()
                            .tabItem { Label("Challenges", systemImage: "flame") }
                            .tag(1)

                        FriendsView()
                            .tabItem { Label("Freunde", systemImage: "person.2") }
                            .tag(2)

                        ProfileView()
                            .tabItem { Label("Profil", systemImage: "person.crop.circle") }
                            .tag(3)
                    }
                    .tint(theme.theme.accent)
                    .id(refreshTrigger)
                } else {
                    LoginView()
                }
            }
        }
        .animation(.default, value: app.token != nil)
        .onAppear { applyCustomTabBarTheme(theme.theme) }
        .onChange(of: theme.currentPreset) { _ in 
            applyCustomTabBarTheme(theme.theme)
            // Force TabView to rebuild
            refreshTrigger = UUID()
        }
    }
}
