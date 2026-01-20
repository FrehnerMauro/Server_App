import SwiftUI

struct FriendsView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager

    @State private var friends: [User] = []
    @State private var allUsers: [User] = []

    @State private var loadingFriends = false
    @State private var loadingUsers = false

    @State private var friendSearch: String = ""
    @State private var showAddSheet = false
    @State private var addSearch: String = ""
    @State private var requestingIds: Set<Int> = []

    @State private var error: String?

    private var Api_Friends: api_friends { app.Api_Friends }
    private var Api_Profiles: api_profiles { app.Api_Profiles }

    private var palette: Theme { theme.theme }

    var body: some View {
        NavigationStack {
            ZStack {
                backgroundGradient
                VStack(spacing: 0) {
                    header
                    if let err = error {
                        errorBanner(err)
                    }
                    searchField
                    friendListSection
                }
            }
            .task { await loadFriends() }
            .sheet(isPresented: $showAddSheet) {
                addFriendsSheet
            }
        }
    }
}

// MARK: - Background + Header
private extension FriendsView {
    var backgroundGradient: some View {
        palette.backgroundGradient
            .ignoresSafeArea()
    }

    var header: some View {
        HStack {
            Spacer()
            Text("Freunde")
                .font(.largeTitle.bold())
                .foregroundColor(palette.textPrimary)
                .shadow(color: palette.accent.opacity(0.5), radius: 5)
            Spacer()
            Button {
                showAddSheet = true
            } label: {
                Image(systemName: "person.badge.plus")
                    .font(.system(size: 22, weight: .bold))
                    .foregroundColor(palette.accent)
                    .padding(8)
                    .background(
                        Circle()
                            .fill(Color.white.opacity(0.1))
                            .shadow(color: palette.accent.opacity(0.5), radius: 5)
                    )
            }
            .padding(.trailing, 12)
        }
        .padding(.horizontal)
        .padding(.top, 15)
        .padding(.bottom, 10)
    }
}

// MARK: - Error + Search
private extension FriendsView {
    func errorBanner(_ message: String) -> some View {
        Text("🚨 FEHLER: \(message)")
            .foregroundColor(.red)
            .font(.footnote)
            .padding(.horizontal)
            .padding(.vertical, 10)
    }

    var searchField: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("Freunde suchen")
                .font(.subheadline.bold())
                .foregroundColor(palette.textSecondary)
            HStack {
                Image(systemName: "magnifyingglass").foregroundColor(palette.accent)
                TextField("Name oder E-Mail", text: $friendSearch)
                    .textFieldStyle(.plain)
                    .foregroundColor(palette.textPrimary)
                    .colorScheme(.dark)
            }
            .padding(.horizontal, 15)
            .padding(.vertical, 12)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.black.opacity(0.3))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(palette.accent.opacity(0.4), lineWidth: 1)
                    )
            )
        }
        .padding(.horizontal, 16)
        .padding(.top, 10)
    }
}

// MARK: - Friends List
private extension FriendsView {
    var friendListSection: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 15) {
                Text("Deine Kontakte (\(friends.count))")
                    .font(.title3.bold())
                    .foregroundColor(palette.textPrimary)
                    .padding(.top, 25)
                    .padding(.horizontal, 16)

                listBody
            }
            .padding(.bottom, 40)
        }
        .scrollIndicators(.hidden)
    }

    @ViewBuilder
    var listBody: some View {
        VStack(spacing: 0) {
            if loadingFriends && friends.isEmpty {
                HStack { Spacer(); ProgressView().tint(palette.accent).padding(); Spacer() }
            } else {
                let list = filteredFriends()
                if list.isEmpty {
                    Text(friendSearch.isEmpty ? "Du hast noch keine Freunde." : "Keine Freunde gefunden")
                        .foregroundStyle(.white.opacity(0.65))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 30)
                } else {
                    ForEach(list, id: \.id) { u in
                        NavigationLink(destination: UsersFriendsView(userId: u.id)) {
                            friendRow(for: u)
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(.white)
                        .listRowInsets(EdgeInsets())
                        if u.id != list.last?.id {
                            Divider().background(.white.opacity(0.1)).padding(.leading, 80)
                        }
                    }
                    .padding(.horizontal, 16)
                }
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 20)
                .fill(palette.surface.opacity(0.9))
                .shadow(color: palette.accent.opacity(0.3), radius: 10, x: 0, y: 5)
        )
        .padding(.horizontal, 16)
    }

    func friendRow(for u: User) -> some View {
        HStack(spacing: 15) {
            ZStack {
                Circle().fill(palette.accent.opacity(0.8))
                if let avatar = u.avatar, !avatar.isEmpty, let url = URL(string: avatar) {
                    AsyncImage(url: url) { phase in
                        switch phase {
                        case .success(let img): img.resizable().scaledToFill()
                        default:
                            Text(initials(from: u))
                                .foregroundColor(.white)
                                .font(.system(size: 16, weight: .bold))
                        }
                    }
                } else {
                    Text(initials(from: u))
                        .foregroundColor(.white)
                        .font(.system(size: 16, weight: .bold))
                }
            }
            .frame(width: 50, height: 50)
            .clipShape(Circle())
            .shadow(color: palette.accent.opacity(0.7), radius: 10, x: 0, y: 0)
            .overlay(Circle().stroke(palette.accent, lineWidth: 2))

            VStack(alignment: .leading, spacing: 4) {
                Text(u.name)
                    .font(.headline.weight(.semibold))
                    .foregroundColor(.white)
                if let e = u.email, !e.isEmpty {
                    Text(e)
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.7))
                }
            }
            Spacer()
            Image(systemName: "chevron.right")
                .foregroundColor(palette.accent)
        }
        .padding(.vertical, 10)
    }
}

// MARK: - Helper + Sheet
private extension FriendsView {
    func initials(from u: User) -> String {
        let full = ([u.vorname, u.name].compactMap { $0 }.joined(separator: " "))
            .trimmingCharacters(in: .whitespacesAndNewlines)
        let parts = full.split(separator: " ")
        return parts.prefix(2).map { String($0.prefix(1)).uppercased() }.joined()
    }

    func filteredFriends() -> [User] {
        let q = friendSearch.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !q.isEmpty else { return friends }
        return friends.filter { u in
            let s = "\(u.name) \(u.email ?? "") \(u.vorname ?? "")".lowercased()
            return s.contains(q)
        }
    }

    var addFriendsSheet: some View {
        FriendSearchView()
            .environmentObject(app)
            .presentationDetents([.medium, .large])
    }

    @MainActor
    func loadFriends() async {
        guard !loadingFriends else { return }
        loadingFriends = true
        defer { loadingFriends = false }
        do {
            friends = try await Api_Friends.listFriends()
        } catch {
            self.error = error.localizedDescription
        }
    }
}
