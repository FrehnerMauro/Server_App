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
                                        textSecondary: palette.textSecondary
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

        return VStack(alignment: .leading, spacing: 15) {
            HStack(spacing: 15) {
                if let avatar = post.avatar_url, !avatar.isEmpty {
                    RemoteOrDataURLImage(urlString: avatar)
                        .frame(width: 55, height: 55)
                        .clipShape(Circle())
                        .overlay(Circle().stroke(palette.accent, lineWidth: 2))
                        .shadow(color: palette.accent.opacity(0.7), radius: 5)
                } else {
                    Circle().fill(palette.accent.opacity(0.3))
                        .overlay(Image(systemName: "person.fill")
                            .foregroundColor(.white.opacity(0.8)))
                        .frame(width: 55, height: 55)
                        .overlay(Circle().stroke(palette.accent, lineWidth: 2))
                        .shadow(color: palette.accent.opacity(0.7), radius: 5)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text(post.display_name)
                        .font(.title3.weight(.bold))
                        .foregroundColor(palette.textPrimary)
                    Text(formatTs(post.created_at))
                        .font(.caption.weight(.semibold))
                        .foregroundColor(palette.accentStrong)

                    if let title = post.challenge_title, !title.isEmpty {
                        HStack(spacing: 6) {
                            Text(title)
                                .font(.caption.weight(.bold))
                                .foregroundColor(palette.accent)
                            if let progress = post.progress {
                                Text("– \(progress)%")
                                    .font(.caption.weight(.semibold))
                                    .foregroundColor(palette.textSecondary)
                            }
                        }
                        .padding(.top, 2)
                    }
                }

                Spacer()

                Menu {
                    Button("🚨 Beitrag melden", role: .destructive) {
                        reportTargetId = post.id
                        showReportSheet = true
                    }
                } label: {
                    Image(systemName: "ellipsis")
                        .foregroundColor(palette.accent)
                        .font(.title2.weight(.bold))
                }
            }

            if let img = post.image_url, !img.isEmpty {
                imageContainer(img)
            }

            if !post.content.isEmpty {
                Text(post.content)
                    .font(.body.weight(.medium))
                    .foregroundColor(palette.textPrimary)
            }

            HStack(spacing: 35) {
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
                    HStack {
                        Image(systemName: post.safeLikedByMe ? "heart.fill" : "heart")
                            .font(.system(size: 26, weight: .black))
                            .foregroundColor(post.safeLikedByMe ? palette.accent : palette.textPrimary)
                            .shadow(color: post.safeLikedByMe ? palette.accent.opacity(0.8) : .clear, radius: 4)
                            .scaleEffect(isAnimatingLike ? 1.2 : 1.0)
                        Text("\(post.safeLikesCount)")
                            .foregroundColor(palette.textPrimary)
                            .font(.title2.bold())
                    }
                }
                .buttonStyle(.plain)

                Button {
                    withAnimation {
                        expandedCommentsPostId = expandedCommentsPostId == post.id ? nil : post.id
                    }
                } label: {
                    HStack {
                        Image(systemName: "bubble.right.fill")
                            .foregroundColor(expandedCommentsPostId == post.id ? palette.accent : palette.accentStrong)
                            .font(.system(size: 26, weight: .black))
                        Text("\(post.safeCommentsCount)")
                            .foregroundColor(palette.textPrimary)
                            .font(.title2.bold())
                    }
                }
                .buttonStyle(.plain)

                Spacer()
            }
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(palette.surface.opacity(0.95))
                .overlay(RoundedRectangle(cornerRadius: 16)
                    .stroke(palette.accent.opacity(0.5), lineWidth: 1.5))
        )
        .shadow(color: palette.accent.opacity(0.4), radius: 12, x: 0, y: 5)
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
