import SwiftUI
import UIKit

struct IdentifiableInt: Identifiable { let id: Int }

struct ProfileView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager

    @State private var errorMessage: String?
    @State private var profile: ProfileMeResponse?
    @State private var activeTab: String = "freunde"
    @State private var showSettings = false
    @State private var showDeleteAlert = false
    @State private var postToDelete: Int? = nil
    @State private var likedPosts: [Int: Bool] = [:]  // Tracking von lokalen Like-Änderungen
    @State private var expandedPostId: Int? = nil   // 👈 Für Inline-Kommentare

    private var Api_Profiles: api_profiles { app.Api_Profiles }
    private var Api_Feed: api_feed { app.Api_Feed }

    private var palette: Theme { theme.theme }

    var body: some View {
        ZStack {
            palette.backgroundGradient
                .ignoresSafeArea()

            VStack(spacing: 0) {
                header

                ScrollView {
                    VStack(spacing: 20) {
                        if let err = errorMessage {
                            Text("🚨 FEHLER: \(err)")
                                .foregroundColor(.red)
                                .font(.subheadline)
                                .padding()
                        }

                        if let profile = profile {
                            profileCard(profile)
                                .padding(.horizontal)
                            postsSection(profile)
                        } else {
                            ProgressView("Lade Profil …")
                                .tint(palette.accent)
                                .padding()
                        }
                    }
                    .padding(.bottom, 40)
                }
                .refreshable { await reloadProfile() }
            }
        }
        .onAppear { Task { await reloadProfile() } }
        .sheet(isPresented: $showSettings) {
            NavigationStack {
                SettingsView()
                    .environmentObject(app)
            }
            .presentationDetents([.large])
        }
        .alert("Beitrag löschen?", isPresented: $showDeleteAlert) {
            Button("Abbrechen", role: .cancel) {}
            Button("Löschen", role: .destructive) { Task { await deletePost() } }
        } message: {
            Text("Willst du diesen Beitrag wirklich löschen?")
        }
        .id(theme.currentPreset)
    }

    // MARK: - Header
    private var header: some View {
        HStack {
            Spacer()
            Text("Dein Profil")
                .font(.largeTitle.bold())
                .foregroundColor(palette.textPrimary)
                .shadow(color: palette.accent.opacity(0.5), radius: 5)
            Spacer()
            Button { showSettings = true } label: {
                Image(systemName: "gearshape.fill")
                    .font(.system(size: 24, weight: .bold))
                    .foregroundColor(palette.accent)
                    .shadow(color: palette.accent.opacity(0.8), radius: 3)
            }
        }
        .padding(.horizontal)
        .padding(.top, 15)
        .padding(.bottom, 10)
    }

    // MARK: - Posts
    private func postsSection(_ profile: ProfileMeResponse) -> some View {
        VStack(spacing: 12) {
            HStack(spacing: 20) {
                tabButton(title: "Freunde Posts", tab: "freunde")
                tabButton(title: "Private Posts", tab: "privat")
                Spacer()
            }
            .padding(.horizontal, 16)

            let posts = activeTab == "freunde" ? profile.meine_posts.freunde : profile.meine_posts.privat

            if (posts?.isEmpty ?? true) {
                Text("Keine Posts in dieser Kategorie.")
                    .font(.headline)
                    .foregroundColor(.white.opacity(0.7))
                    .padding(.vertical, 40)
                    .frame(maxWidth: .infinity)
                    .background(RoundedRectangle(cornerRadius: 15).fill(Color.black.opacity(0.25)))
                    .padding(.horizontal, 16)
            } else {
                VStack(spacing: 15) {
                    ForEach((posts ?? []).sorted(by: { $0.created_at > $1.created_at })) { p in
                        profilePostCard(p)
                    }
                }
                .padding([.top, .horizontal], 16)
                .background(
                    RoundedRectangle(cornerRadius: 20)
                        .fill(palette.surface.opacity(0.9))
                        .shadow(color: palette.accent.opacity(0.2), radius: 10, x: 0, y: 5)
                )
                .padding(.horizontal)
            }
        }
    }

    private func tabButton(title: String, tab: String) -> some View {
        Button { activeTab = tab } label: {
            VStack(spacing: 6) {
                Text(title)
                    .font(.subheadline.weight(.medium))
                    .foregroundColor(activeTab == tab ? palette.textPrimary : palette.textSecondary)
                Capsule()
                    .fill(activeTab == tab ? palette.accent : Color.clear)
                    .frame(height: 3)
                    .shadow(color: activeTab == tab ? palette.accent.opacity(0.7) : .clear, radius: 4)
            }
        }
    }

    // MARK: - Profilkarte
    private func profileCard(_ profile: ProfileMeResponse) -> some View {
        VStack(alignment: .leading, spacing: 15) {
            HStack(spacing: 15) {
                avatarView(profile)
                VStack(alignment: .leading) {
                    Text(profile.display_name ?? "Ich")
                        .font(.title2.bold())
                        .foregroundColor(.white)
                    Text("Benutzer-ID: \(profile.id)")
                        .font(.subheadline)
                        .foregroundColor(.white.opacity(0.7))
                }
                Spacer()
            }

            Divider().background(palette.accent.opacity(0.5))
            HStack {
                chip(text: "Freunde: \(profile.anzahl_freunde)", systemImage: "person.2.fill")
                chip(text: "Posts: \(profile.anzahl_posts)", systemImage: "photo.on.rectangle")
            }
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 18)
                .fill(palette.surface.opacity(0.8))
                .overlay(RoundedRectangle(cornerRadius: 18).stroke(palette.accent.opacity(0.6), lineWidth: 1.5))
                .shadow(color: .black.opacity(0.5), radius: 15, x: 0, y: 8)
        )
    }

    private func avatarView(_ profile: ProfileMeResponse) -> some View {
        ZStack {
            if let avatar = profile.avatar_url, !avatar.isEmpty {
                RemoteOrDataURLImage(urlString: avatar)
                    .frame(width: 60, height: 60)
                    .clipShape(Circle())
            } else {
                Circle()
                    .fill(palette.accent.opacity(0.25))
                    .frame(width: 60, height: 60)
                    .overlay(Text(initials(from: profile.display_name ?? "Ich"))
                        .font(.title3.bold())
                        .foregroundColor(.white))
            }
        }
        .overlay(Circle().stroke(palette.accent, lineWidth: 2))
        .shadow(color: palette.accent.opacity(0.6), radius: 8)
    }

    // MARK: - Einzelner Post
    private func profilePostCard(_ p: ProfilePost) -> some View {
        // Verwende den lokalen Override, falls vorhanden, sonst Server-Wert
        let isLiked = likedPosts[p.id] ?? (p.liked_by_me ?? false)
        let currentLikeCount = p.like_count + (isLiked != (p.liked_by_me ?? false) ? (isLiked ? 1 : -1) : 0)

        return VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(formatTs(Double(p.created_at)))
                    .font(.caption)
                    .foregroundColor(palette.accent)
                Spacer()

                Menu {
                    Button(role: .destructive) {
                        postToDelete = p.id
                        showDeleteAlert = true
                    } label: {
                        Label("Beitrag löschen", systemImage: "trash")
                    }
                } label: {
                    Image(systemName: "ellipsis")
                        .foregroundColor(palette.accent)
                        .font(.title2.weight(.bold))
                }
            }

            if let url = p.image_url, !url.isEmpty {
                RemoteOrDataURLImage(urlString: url)
                    .scaledToFit()
                    .frame(maxHeight: 300)
                    .cornerRadius(12)
            }

            if !p.content.isEmpty {
                Text(p.content)
                    .font(.body)
                    .foregroundColor(palette.textPrimary)
            }

            HStack(spacing: 25) {
                // ❤️ Like
                Button {
                    Task { await toggleLike(p) }
                } label: {
                    HStack {
                        Image(systemName: isLiked ? "heart.fill" : "heart")
                            .foregroundColor(isLiked ? palette.accent : palette.textPrimary)
                        Text("\(currentLikeCount)")
                            .font(.subheadline.weight(.semibold))
                            .foregroundColor(palette.textPrimary)
                    }
                }

                // 💬 Kommentare inline anzeigen
                Button {
                    withAnimation {
                        if expandedPostId == p.id {
                            expandedPostId = nil
                        } else {
                            expandedPostId = p.id
                        }
                    }
                } label: {
                    HStack {
                        Image(systemName: "bubble.right.fill")
                            .foregroundColor(palette.accent)
                        Text("\(p.comment_count)")
                            .font(.subheadline.weight(.semibold))
                            .foregroundColor(palette.textPrimary)
                    }
                }

                Spacer()
            }
            .padding(.top, 4)

            // 👇 Inline-Kommentare
            if expandedPostId == p.id {
                CommentsView(
                    postId: p.id,
                    apiFeed: Api_Feed,
                    primaryAccent: palette.accent,
                    secondaryAccent: palette.accentStrong,
                    textPrimary: palette.textPrimary,
                    textSecondary: palette.textSecondary
                )
                .environmentObject(app)
                .transition(.opacity.combined(with: .move(edge: .bottom)))
                .padding(.top, 10)
            }
        }
        .padding()
        .background(palette.surface.opacity(0.7))
        .cornerRadius(12)
        .animation(.easeInOut, value: expandedPostId)
    }

    // MARK: - Aktionen
    private func toggleLike(_ post: ProfilePost) async {
        let currentLikedState = likedPosts[post.id] ?? (post.liked_by_me ?? false)
        let newLikedState = !currentLikedState
        
        // Optimistisches Update
        await MainActor.run {
            likedPosts[post.id] = newLikedState
        }
        
        do {
            if newLikedState {
                try await Api_Feed.feedLike(postId: post.id)
            } else {
                try await Api_Feed.feedUnlike(postId: post.id)
            }
        } catch {
            // Rollback bei Fehler
            await MainActor.run {
                likedPosts[post.id] = currentLikedState
            }
        }
    }

    private func deletePost() async {
        guard let pid = postToDelete else { return }
        do {
            try await Api_Feed.feedDelete(postId: pid)
            await reloadProfile()
        } catch {
            await MainActor.run { self.errorMessage = error.localizedDescription }
        }
        postToDelete = nil
    }

    // MARK: - Helpers
    private func chip(text: String, systemImage: String) -> some View {
        HStack {
            Image(systemName: systemImage)
            Text(text)
        }
        .font(.caption.weight(.medium))
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(palette.accent.opacity(0.2))
        .clipShape(Capsule())
        .foregroundColor(palette.textPrimary)
        .overlay(Capsule().stroke(palette.accent.opacity(0.5), lineWidth: 1))
    }

    private func initials(from name: String) -> String {
        let parts = name.split(separator: " ")
        return parts.prefix(2).map { $0.prefix(1).uppercased() }.joined()
    }

    private func formatTs(_ ms: Double) -> String {
        let date = Date(timeIntervalSince1970: ms / 1000)
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }

    private func reloadProfile() async {
        await MainActor.run { self.errorMessage = nil }
        do {
            let prof = try await Api_Profiles.getMyProfileFull()
            await MainActor.run { self.profile = prof }
        } catch {
            await MainActor.run { self.errorMessage = error.localizedDescription }
        }
    }
}

// MARK: - Remote/Base64 Bilder
struct RemoteOrDataURLImage: View {
    let urlString: String

    var body: some View {
        if urlString.lowercased().hasPrefix("data:image/") {
            if let uiImage = decodeDataURL(urlString) {
                Image(uiImage: uiImage).resizable().scaledToFill()
            } else {
                Color.gray.opacity(0.2)
            }
        } else if let url = URL(string: urlString) {
            AsyncImage(url: url) { phase in
                switch phase {
                case .empty:
                    ProgressView().tint(.white)
                case .success(let image):
                    image.resizable().scaledToFill()
                case .failure(_):
                    Color.gray.opacity(0.3)
                @unknown default:
                    Color.clear
                }
            }
        } else {
            Color.clear
        }
    }

    private func decodeDataURL(_ s: String) -> UIImage? {
        guard let comma = s.firstIndex(of: ",") else { return nil }
        let base64 = String(s[s.index(after: comma)...])
        guard let data = Data(base64Encoded: base64) else { return nil }
        return UIImage(data: data)
    }
}
