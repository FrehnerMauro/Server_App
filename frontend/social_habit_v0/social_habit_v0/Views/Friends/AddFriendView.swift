import SwiftUI

struct FriendSearchView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager
    
    @State private var query: String = ""
    @State private var results: [FriendSearchResult] = []
    @State private var error: String?
    @State private var loading = false
    @State private var infoMessage: String?
    @State private var requestingIds: Set<Int> = []
    
    private var Api_Friends: api_friends { app.Api_Friends }
    private var palette: Theme { theme.theme }
    
    var body: some View {
        ZStack {
            palette.backgroundGradient
                .ignoresSafeArea()
            
            VStack(spacing: 20) {
                header
                
                searchBar
                
                if loading {
                    ProgressView()
                        .tint(palette.accent)
                        .padding(.top, 40)
                } else if let err = error {
                    Text("🚨 \(err)")
                        .foregroundColor(palette.danger)
                        .font(.footnote.bold())
                        .padding(.top, 30)
                } else if results.isEmpty && !query.isEmpty {
                    Text("Keine Benutzer gefunden.")
                        .foregroundColor(palette.textSecondary)
                        .padding(.top, 40)
                } else {
                    resultsList
                }
                
                if let info = infoMessage {
                    Text(info)
                        .foregroundColor(palette.success)
                        .font(.footnote.bold())
                        .padding(.top, 8)
                }
                
                Spacer()
            }
            .padding(.horizontal)
        }
        .navigationBarBackButtonHidden(true)
    }
    
    // MARK: - Header
    private var header: some View {
        HStack {
            Text("Freunde hinzufügen")
                .font(.title.bold())
                .foregroundColor(palette.textPrimary)
                .shadow(color: palette.accent.opacity(0.5), radius: 5)
            Spacer()
        }
        .padding(.top, 20)
    }
    
    // MARK: - SearchBar
    private var searchBar: some View {
        HStack {
            Image(systemName: "magnifyingglass")
                .foregroundColor(palette.accent)
            TextField("Name oder E-Mail suchen", text: $query)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled(true)
                .foregroundColor(palette.textPrimary)
                .onSubmit { Task { await search() } }
            if !query.isEmpty {
                Button {
                    query = ""
                    results.removeAll()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(palette.textSecondary)
                }
            }
        }
        .padding(.vertical, 12)
        .padding(.horizontal, 16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.black.opacity(0.3))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(palette.accent.opacity(0.4), lineWidth: 1)
                )
        )
        .onChange(of: query) { q in
            Task {
                try? await Task.sleep(nanoseconds: 400_000_000)
                if q == query && !q.isEmpty {
                    await search()
                }
            }
        }
    }
    
    // MARK: - Results List
    private var resultsList: some View {
        ScrollView {
            LazyVStack(spacing: 15) {
                ForEach(results) { user in
                    HStack(spacing: 15) {
                        avatar(for: user)
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text(user.display_name)
                                .font(.headline)
                                .foregroundColor(palette.textPrimary)
                            if let relation = user.relation_status {
                                Text(statusText(for: relation))
                                    .font(.caption)
                                    .foregroundColor(.gray)
                            }
                        }
                        Spacer()
                        
                        if user.relation_status == nil {
                            if requestingIds.contains(user.id) {
                                ProgressView()
                                    .tint(palette.accent)
                            } else {
                                Button {
                                    Task { await sendRequest(to: user.id) }
                                } label: {
                                    Text("Anfragen")
                                        .font(.footnote.bold())
                                        .padding(.vertical, 6)
                                        .padding(.horizontal, 12)
                                        .background(palette.accent)
                                        .cornerRadius(8)
                                        .foregroundColor(palette.background)
                                }
                                .buttonStyle(.plain)
                            }
                        } else if user.relation_status == "pending" {
                            Label("Ausstehend", systemImage: "hourglass")
                                .font(.caption.bold())
                                .foregroundColor(palette.textSecondary)
                        } else if user.relation_status == "friend" {
                            Label("Freund", systemImage: "checkmark.circle.fill")
                                .font(.caption.bold())
                                .foregroundColor(palette.accent)
                        }
                    }
                    .padding(.vertical, 6)
                    Divider().background(palette.textSecondary.opacity(0.2))
                }
            }
            .padding(.horizontal, 4)
            .padding(.top, 10)
        }
    }
    
    // MARK: - Avatar
    private func avatar(for user: FriendSearchResult) -> some View {
        ZStack {
            Circle().fill(palette.accent.opacity(0.6))
            if let url = user.avatar_url, let u = URL(string: url) {
                AsyncImage(url: u) { phase in
                    switch phase {
                    case .success(let img): img.resizable().scaledToFill()
                    default:
                        Text(String(user.display_name.prefix(1)))
                            .font(.system(size: 18, weight: .bold))
                            .foregroundColor(.white)
                    }
                }
            } else {
                Text(String(user.display_name.prefix(1)))
                    .font(.system(size: 18, weight: .bold))
                    .foregroundColor(.white)
            }
        }
        .frame(width: 45, height: 45)
        .clipShape(Circle())
        .overlay(Circle().stroke(palette.accent, lineWidth: 2))
        .shadow(color: palette.accent.opacity(0.4), radius: 5)
    }
    
    // MARK: - Helpers
    private func statusText(for relation: String) -> String {
        switch relation {
        case "pending": return "Anfrage ausstehend"
        case "friend": return "Bereits befreundet"
        default: return ""
        }
    }
    
    private func search() async {
        guard !query.isEmpty else {
            results = []
            return
        }
        loading = true
        error = nil
        infoMessage = nil
        defer { loading = false }
        do {
            results = try await Api_Friends.searchUsers(query: query)
        } catch {
            self.error = error.localizedDescription
        }
    }
    
    private func sendRequest(to userId: Int) async {
        requestingIds.insert(userId)
        defer { requestingIds.remove(userId) }
        do {
            try await Api_Friends.sendFriendRequest(toUserId: userId, message: nil)
            infoMessage = "Anfrage gesendet."
            if let idx = results.firstIndex(where: { $0.id == userId }) {
                results[idx].relation_status = "pending"
            }
        } catch {
            self.error = error.localizedDescription
        }
    }
}
