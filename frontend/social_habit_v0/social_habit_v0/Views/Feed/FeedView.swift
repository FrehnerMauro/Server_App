import SwiftUI
import Foundation

struct FeedView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager
    @State private var posts: [FeedItemDTO] = []
    @State private var error: String?
    @State private var loading = false
    @State private var showReportSheet = false
    @State private var reportReason = ""
    @State private var reportTargetId: Int?
    @State private var expandedCommentsPostId: Int?
    
    // 🔔 Notifications
    @State private var showNotifications = false
    @State private var unreadCount = 0
    private var apiNotifications: api_notifications { app.Api_Notifications }

    private var apiFeed: api_feed { app.Api_Feed }
    private var apiReport: api_report { app.Api_Report }

    private var palette: Theme { theme.theme }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // MARK: - Header mit Glocke 🔔
                HStack(spacing: 0) {
                    ZStack {
                        // 🔹 Zentrierter Titel
                        Text("Feed")
                            .font(.system(size: 36, weight: .bold))
                            .foregroundColor(palette.textPrimary)
                            .shadow(color: palette.accent.opacity(0.6), radius: 10)
                            .frame(maxWidth: .infinity, alignment: .center)
                        
                        // 🔹 Glocke oben rechts
                        HStack {
                            Spacer()
                            NotificationBellButton(count: $unreadCount) {
                                showNotifications = true
                            }
                            .sheet(isPresented: $showNotifications) {
                                NotificationsView()
                                    .onDisappear {
                                        Task { await refreshNotificationCount() }
                                    }
                            }
                            .padding(.trailing, 20)
                        }
                    }
                }
                .padding(.vertical, 12)
                .background(palette.surface.opacity(0.95))

                // MARK: - Feed Content
                ScrollView {
                    LazyVStack(spacing: 20) {
                        if loading && posts.isEmpty {
                            ProgressView("Lade Feed…")
                                .tint(palette.accent)
                                .padding(40)
                        } else if let err = error {
                            Text("⚠️ Fehler: \(err)")
                                .foregroundColor(palette.accent)
                                .padding()
                        } else if posts.isEmpty {
                            Text("Keine Beiträge vorhanden 💤")
                                .foregroundColor(palette.textSecondary)
                                .padding(.top, 80)
                        } else {
                            ForEach(posts, id: \.id) { post in
                                postCard(post)
                                if expandedCommentsPostId == post.id {
                                    CommentsView(
                                        postId: post.id,
                                        apiFeed: apiFeed,
                                        primaryAccent: palette.accent,
                                        secondaryAccent: palette.accentStrong,
                                        textPrimary: palette.textPrimary,
                                        textSecondary: palette.textSecondary,
                                        onCommentAdded: {
                                            updatePostCommentCount(postId: post.id)
                                        }
                                    )
                                    .transition(.slide)
                                }
                            }
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 20)
                    .padding(.bottom, 60)
                }
            }
            .background(
                palette.backgroundGradient.ignoresSafeArea()
            )
            .sheet(isPresented: $showReportSheet) {
                reportSheet
            }
            .task {
                await loadFeed()
                await refreshNotificationCount()
            }
            .id(theme.currentPreset)
        }
    }

    // MARK: - Report Sheet
    private var reportSheet: some View {
        VStack(spacing: 25) {
            Text("🚨 Beitrag melden")
                .font(.title.bold())
                .foregroundColor(palette.accent)
                .padding(.top, 10)

            Text("Bitte gib optional einen Grund für die Meldung an. Missbrauch kann zur Sperrung führen.")
                .multilineTextAlignment(.center)
                .foregroundColor(palette.textSecondary)
                .padding(.horizontal)

            TextField("Grund (optional)", text: $reportReason)
                .padding()
                .background(palette.surface.opacity(0.6))
                .cornerRadius(10)
                .foregroundColor(palette.textPrimary)
                .padding(.horizontal, 30)

            HStack(spacing: 20) {
                Button("Abbrechen") {
                    showReportSheet = false
                    reportReason = ""
                }
                .foregroundColor(palette.textSecondary)

                Button("Melden") {
                    if let pid = reportTargetId {
                        Task { await sendReport(postId: pid) }
                    }
                    showReportSheet = false
                    reportReason = ""
                }
                .foregroundColor(palette.danger)
            }
            .padding(.top, 10)

            Spacer()
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(
            palette.backgroundGradient.ignoresSafeArea()
        )
    }

    // MARK: - Post Card
    private func postCard(_ post: FeedItemDTO) -> some View {
        @State var isAnimatingLike = false

        return VStack(alignment: .leading, spacing: 0) {
            // Header mit Avatar und Benutzerinfo
            HStack(spacing: 12) {
                // Avatar mit Pulsing-Effekt
                ZStack {
                    Circle()
                        .fill(palette.accent.opacity(0.2))
                        .frame(width: 60, height: 60)
                    
                    if let avatar = post.avatar_url, !avatar.isEmpty {
                        RemoteOrDataURLImage(urlString: avatar)
                            .frame(width: 56, height: 56)
                            .clipShape(Circle())
                    } else {
                        Circle().fill(palette.accent.opacity(0.3))
                            .overlay(Image(systemName: "person.fill")
                                .foregroundColor(.white.opacity(0.8)))
                            .frame(width: 56, height: 56)
                    }
                    
                    Circle()
                        .stroke(
                            LinearGradient(
                                gradient: Gradient(colors: [palette.accent, palette.accentStrong]),
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 2
                        )
                        .frame(width: 60, height: 60)
                }

                VStack(alignment: .leading, spacing: 6) {
                    Text(post.display_name)
                        .font(.system(size: 18, weight: .bold))
                        .foregroundColor(palette.textPrimary)
                    
                    HStack(spacing: 8) {
                        Image(systemName: "clock.fill")
                            .font(.caption)
                            .foregroundColor(palette.accentStrong)
                        Text(formatTs(post.created_at))
                            .font(.caption.weight(.semibold))
                            .foregroundColor(palette.accentStrong)
                    }

                    if let title = post.challenge_title, !title.isEmpty {
                        HStack(spacing: 6) {
                            Image(systemName: "checkmark.circle.fill")
                                .font(.caption)
                                .foregroundColor(palette.accent)
                            Text(title)
                                .font(.caption2.weight(.bold))
                                .foregroundColor(palette.accent)
                            if let progress = post.progress {
                                ZStack {
                                    Circle()
                                        .fill(palette.accent.opacity(0.2))
                                    
                                    CircularProgressView(progress: CGFloat(progress) / 100.0, color: palette.accent)
                                    
                                    Text("\(progress)%")
                                        .font(.caption2.weight(.bold))
                                        .foregroundColor(palette.accent)
                                }
                                .frame(width: 30, height: 30)
                            }
                        }
                    }
                }

                Spacer()

                Menu {
                    Button("🚨 Beitrag melden", role: .destructive) {
                        reportTargetId = post.id
                        showReportSheet = true
                    }
                } label: {
                    Image(systemName: "ellipsis.circle.fill")
                        .font(.system(size: 24))
                        .foregroundColor(palette.accentStrong)
                }
            }
            .padding(16)

            Divider()
                .background(palette.accent.opacity(0.2))

            // Content
            if let img = post.image_url, !img.isEmpty {
                imageContainer(img)
            }

            if !post.content.isEmpty {
                VStack(alignment: .leading, spacing: 0) {
                    Text(post.content)
                        .font(.system(size: 16, weight: .medium, design: .default))
                        .foregroundColor(palette.textPrimary)
                        .lineSpacing(2)
                }
                .padding(16)
            }

            Divider()
                .background(palette.accent.opacity(0.2))

            // Engagement Stats
            HStack(spacing: 0) {
                // Likes
                Button {
                    Task {
                        withAnimation(.spring(response: 0.2, dampingFraction: 0.7)) {
                            isAnimatingLike = true
                        }
                        await toggleLike(post)
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                            withAnimation(.easeOut(duration: 0.1)) {
                                isAnimatingLike = false
                            }
                        }
                    }
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: post.safeLikedByMe ? "heart.fill" : "heart")
                            .font(.system(size: 20, weight: .semibold))
                            .foregroundColor(post.safeLikedByMe ? palette.accent : palette.accentStrong)
                            .shadow(color: post.safeLikedByMe ? palette.accent.opacity(0.6) : .clear, radius: 3)
                            .scaleEffect(isAnimatingLike ? 1.15 : 1.0)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Gefällt mir")
                                .font(.caption2.weight(.bold))
                                .foregroundColor(palette.textSecondary)
                            Text("\(post.safeLikesCount)")
                                .font(.headline.weight(.bold))
                                .foregroundColor(palette.textPrimary)
                        }
                    }
                }
                .buttonStyle(.plain)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 16)
                .padding(.vertical, 12)

                Divider()
                    .frame(height: 30)
                    .background(palette.accent.opacity(0.2))

                // Comments
                Button {
                    withAnimation {
                        expandedCommentsPostId = expandedCommentsPostId == post.id ? nil : post.id
                    }
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: "bubble.right.fill")
                            .font(.system(size: 20, weight: .semibold))
                            .foregroundColor(expandedCommentsPostId == post.id ? palette.accent : palette.accentStrong)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Kommentare")
                                .font(.caption2.weight(.bold))
                                .foregroundColor(palette.textSecondary)
                            Text("\(post.safeCommentsCount)")
                                .font(.headline.weight(.bold))
                                .foregroundColor(palette.textPrimary)
                        }
                    }
                }
                .buttonStyle(.plain)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 16)
                .padding(.vertical, 12)

                Spacer()
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 18)
                .fill(
                    LinearGradient(
                        gradient: Gradient(colors: [
                            palette.surface.opacity(0.98),
                            palette.surface.opacity(0.92)
                        ]),
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 18)
                        .stroke(
                            LinearGradient(
                                gradient: Gradient(colors: [
                                    palette.accent.opacity(0.4),
                                    palette.accent.opacity(0.1)
                                ]),
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 1.5
                        )
                )
        )
        .shadow(color: palette.accent.opacity(0.3), radius: 10, x: 0, y: 4)
    }

    // MARK: - Notification Count laden
    private func refreshNotificationCount() async {
        do {
            let items = try await apiNotifications.notifications()
            unreadCount = items.filter { !$0.isRead }.count
        } catch {
            print("⚠️ Fehler beim Laden der Notifications:", error.localizedDescription)
        }
    }

    // MARK: - API
    @MainActor
    private func loadFeed() async {
        error = nil
        loading = true
        defer { loading = false }
        do {
            try await Task.sleep(for: .milliseconds(200))
            posts = try await apiFeed.feed()
        } catch {
            self.error = error.localizedDescription
        }
    }

    @MainActor
    private func sendReport(postId: Int) async {
        do {
            let ok = try await apiReport.createReport(
                postId: postId,
                reason: reportReason.isEmpty ? "Unangemessener Inhalt" : reportReason
            )
            if ok { print("✅ Report erfolgreich gesendet.") }
        } catch {
            print("❌ Fehler beim Melden:", error.localizedDescription)
        }
    }

    @MainActor
    private func toggleLike(_ post: FeedItemDTO) async {
        guard let index = posts.firstIndex(where: { $0.id == post.id }) else { return }

        var updated = posts[index]
        let liked = updated.safeLikedByMe

        updated.likedByMe = !liked
        updated.likesCount = (updated.likesCount ?? 0) + (liked ? -1 : 1)
        posts[index] = updated

        do {
            if liked {
                _ = try await apiFeed.feedUnlike(postId: post.id)
            } else {
                _ = try await apiFeed.feedLike(postId: post.id)
            }
        } catch {
            posts[index] = post
            self.error = error.localizedDescription
        }
    }

    @MainActor
    private func updatePostCommentCount(postId: Int) {
        guard let index = posts.firstIndex(where: { $0.id == postId }) else { return }
        
        var updated = posts[index]
        updated.commentsCount = (updated.commentsCount ?? 0) + 1
        posts[index] = updated
    }

    private func imageContainer(_ img: String) -> some View {
        Group {
            if img.starts(with: "data:image") {
                if let base64 = extractBase64Data(from: img),
                   let data = Data(base64Encoded: base64),
                   let ui = UIImage(data: data) {
                    Image(uiImage: ui)
                        .resizable()
                        .scaledToFit()
                }
            } else if let url = URL(string: img) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image): image.resizable().scaledToFit()
                    case .empty: ProgressView().tint(.white).frame(height: 200)
                    case .failure(_): Color.gray.opacity(0.3).frame(height: 200)
                    @unknown default: EmptyView().frame(height: 200)
                    }
                }
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: .black.opacity(0.4), radius: 6, x: 0, y: 3)
    }
}
// MARK: - Helper

private func extractBase64Data(from s: String) -> String? {
    if let comma = s.firstIndex(of: ",") {
        return String(s[s.index(after: comma)...])
    }
    return nil
}

private func formatTs(_ ms: Double) -> String {
    let date = Date(timeIntervalSince1970: ms / 1000)
    let f = DateFormatter()
    f.dateStyle = .medium
    f.timeStyle = .short
    return f.string(from: date)
}
