import SwiftUI

struct BlockedUsersView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager
    @State private var blockedUsers: [FriendBlock] = []
    @State private var errorMessage: String?
    @State private var isLoading = false
    @State private var showUnblockConfirm = false
    @State private var userToUnblock: FriendBlock?

    private var Api_Friends: api_friends { app.Api_Friends }
    private var palette: Theme { theme.theme }

    var body: some View {
        ZStack {
            palette.backgroundGradient
                .ignoresSafeArea()

            VStack {
                if isLoading {
                    ProgressView("Lade blockierte Benutzer …")
                        .tint(palette.accent)
                        .padding()
                } else if let err = errorMessage {
                    Text("❌ \(err)")
                        .foregroundColor(palette.danger)
                        .padding()
                } else if blockedUsers.isEmpty {
                    Text("Keine blockierten Benutzer.")
                        .foregroundColor(palette.textSecondary)
                        .padding()
                } else {
                    List {
                        ForEach(blockedUsers) { user in
                            HStack {
                                avatarView(for: user)
                                VStack(alignment: .leading) {
                                    Text(user.displayName)
                                        .font(.headline)
                                        .foregroundColor(palette.textPrimary)
                                    Text("ID: \(user.userId)")
                                        .font(.caption)
                                        .foregroundColor(palette.textSecondary)
                                }
                                Spacer()
                                Button(role: .destructive) {
                                    userToUnblock = user
                                    showUnblockConfirm = true
                                } label: {
                                    Label("Entblocken", systemImage: "person.fill.xmark")
                                        .font(.caption)
                                }
                                .buttonStyle(.borderedProminent)
                                .tint(.red)
                            }
                            .listRowBackground(Color.black.opacity(0.3))
                        }
                    }
                    .scrollContentBackground(.hidden)
                }
            }
            .navigationTitle("Blockierte Benutzer")
            .onAppear { Task { await loadBlockedUsers() } }
            .alert("Benutzer entblocken?", isPresented: $showUnblockConfirm) {
                Button("Abbrechen", role: .cancel) {}
                Button("Entblocken", role: .destructive) {
                    Task { await unblockSelectedUser() }
                }
            } message: {
                if let user = userToUnblock {
                    Text("Möchtest du **\(user.displayName)** wirklich entblocken?")
                }
            }
        }
    }

    // MARK: - Funktionen
    private func loadBlockedUsers() async {
        await MainActor.run {
            isLoading = true
            errorMessage = nil
        }
        do {
            let users = try await Api_Friends.listBlockedUsers()
            await MainActor.run {
                self.blockedUsers = users
                self.isLoading = false
            }
        } catch {
            await MainActor.run {
                self.errorMessage = "Fehler beim Laden: \(error.localizedDescription)"
                self.isLoading = false
            }
        }
    }

    private func unblockSelectedUser() async {
        guard let user = userToUnblock else { return }
        do {
            try await Api_Friends.unblockUser(user.userId)
            await loadBlockedUsers()
        } catch {
            await MainActor.run {
                self.errorMessage = "Fehler beim Entblocken: \(error.localizedDescription)"
            }
        }
    }

    // MARK: - Avatar
    private func avatarView(for user: FriendBlock) -> some View {
        ZStack {
            if let avatar = user.avatarUrl, !avatar.isEmpty {
                RemoteOrDataURLImage(urlString: avatar)
                    .frame(width: 45, height: 45)
                    .clipShape(Circle())
            } else {
                Circle()
                    .fill(palette.accent.opacity(0.25))
                    .frame(width: 45, height: 45)
                    .overlay(Text(initials(from: user.displayName))
                        .font(.headline)
                        .foregroundColor(.white))
            }
        }
        .overlay(Circle().stroke(palette.accent, lineWidth: 2))
        .shadow(color: palette.accent.opacity(0.5), radius: 5)
    }

    private func initials(from name: String) -> String {
        let parts = name.split(separator: " ")
        return parts.prefix(2).map { $0.prefix(1).uppercased() }.joined()
    }
}
