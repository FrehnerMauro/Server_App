import SwiftUI

struct NotificationsView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager
    @State private var loading = false
    @State private var error: String?

    private var palette: Theme { theme.theme }

    var body: some View {
        NavigationStack {
            ZStack {
                // 🔹 Vollflächiger Hintergrund
                palette.backgroundGradient
                    .ignoresSafeArea()

                VStack {
                    if loading {
                        ProgressView("Lade Benachrichtigungen…")
                            .tint(palette.accent)
                            .foregroundColor(palette.textPrimary)
                            .padding(.top, 40)
                    } else if let err = error {
                        VStack(spacing: 10) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .font(.system(size: 36))
                                .foregroundColor(.yellow)
                            Text("Fehler beim Laden")
                                .font(.headline)
                                .foregroundColor(palette.textPrimary)
                            Text(err)
                                .font(.caption)
                                .foregroundColor(palette.danger)
                        }
                        .padding(.top, 60)
                    } else if app.notifications.isEmpty {
                        VStack(spacing: 12) {
                            Image(systemName: "bell.slash.fill")
                                .font(.system(size: 46))
                                .foregroundColor(.gray)
                            Text("Keine Benachrichtigungen 📭")
                                .font(.headline)
                                .foregroundColor(palette.textSecondary)
                            Text("Hier erscheinen neue Nachrichten, Einladungen und Anfragen.")
                                .font(.caption)
                                .foregroundColor(palette.textSecondary)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 40)
                        }
                        .padding(.top, 100)
                    } else {
                        ScrollView {
                            VStack(spacing: 12) {
                                ForEach(app.notifications) { notif in
                                    NotificationsRow(notification: notif)
                                        .environmentObject(app)
                                }
                            }
                            .padding(.vertical, 10)
                            .padding(.horizontal, 4)
                        }
                        .scrollIndicators(.hidden)
                    }
                }
                .padding(.horizontal)
            }
            .navigationTitle("Benachrichtigungen")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarBackground(palette.background, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .id(theme.currentPreset)
            .task {
                await loadNotifications()
            }
            .refreshable {
                await loadNotifications()
            }
        }
    }

    // MARK: - Laden der Benachrichtigungen
    @MainActor
    private func loadNotifications() async {
        loading = true
        error = nil
        do {
            try await app.loadNotifications()
        } catch {
            self.error = error.localizedDescription
        }
        withAnimation(.easeOut(duration: 0.3)) {
            loading = false
        }
    }
}
