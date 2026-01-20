import SwiftUI
import UIKit

struct UsersFriendsView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager

    let userId: Int

    @State private var errorMessage: String?
    @State private var profile: ProfileMeResponse?
    @State private var likedPosts: Set<Int> = []
    @State private var expandedPostId: Int? = nil

    // Report / Remove friend
    @State private var showReportSheet = false
    @State private var reportReason = ""
    @State private var reportedUserId: Int? = nil
    @State private var showReportSuccess = false
    @State private var showRemoveFriendAlert = false

    private var Api_Profiles: api_profiles { app.Api_Profiles }
    private var Api_Feed: api_feed { app.Api_Feed }
    private var Api_Report: api_report { app.Api_Report }
    private var Api_Friends: api_friends { app.Api_Friends }

    private let deepBackgroundColor = Color(red: 0.0, green: 0.0, blue: 0.15)
    private let primaryAccent = Color(red: 0.0, green: 0.9, blue: 1.0)
    private var palette: Theme { theme.theme }

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Color(red: 0.05, green: 0.05, blue: 0.2), deepBackgroundColor],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

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
                            .tint(primaryAccent)
                            .padding()
                    }
                }
                .padding(.bottom, 40)
            }
            .refreshable { await reloadProfile() }
        }
        .onAppear { Task { await reloadProfile() } }
        
        .alert("Beitrag wurde gemeldet ✅", isPresented: $showReportSuccess) {
            Button("OK", role: .cancel) {}
        } message: {
            Text("Danke für deine Rückmeldung.")
        }
        .alert("Freund entfernen?", isPresented: $showRemoveFriendAlert) {
            Button("Abbrechen", role: .cancel) {}
            Button("Entfernen", role: .destructive) {
                Task { await removeFriend() }
            }
        } message: {
            Text("Möchtest du diesen Freund wirklich entfernen?")
        }
        .sheet(isPresented: $showReportSheet) { reportSheet }
    }

    // MARK: - Profilkarte
    private func profileCard(_ profile: ProfileMeResponse) -> some View {
        VStack(alignment: .leading, spacing: 15) {
            HStack(spacing: 15) {
                avatarView(profile)
                VStack(alignment: .leading) {
                    Text(profile.display_name ?? "Benutzer")
                        .font(.title2.bold())
                        .foregroundColor(.white)
                    Text("Benutzer-ID: \(profile.id)")
                        .font(.subheadline)
                        .foregroundColor(.white.opacity(0.7))
                }
                Spacer()
                Menu {
                    Button(role: .destructive) {
                        reportedUserId = profile.id
                        showReportSheet = true
                    } label: {
                        Label("Profil melden", systemImage: "exclamationmark.triangle")
                    }

                    Button(role: .destructive) {
                        showRemoveFriendAlert = true
                    } label: {
                        Label("Freund entfernen", systemImage: "person.fill.xmark")
                    }

                    // 🧱 NEU: Freund blockieren
                    Button(role: .destructive) {
                        Task { await blockFriend() }
                    } label: {
                        Label("Freund blockieren", systemImage: "hand.raised.fill")
                    }
                } label: {
                    Image(systemName: "ellipsis")
                        .foregroundColor(primaryAccent)
                        .font(.title2.weight(.bold))
                }            }

            Divider().background(primaryAccent.opacity(0.5))
            HStack {
                chip(text: "Freunde: \(profile.anzahl_freunde)", systemImage: "person.2.fill")
                chip(text: "Posts: \(profile.anzahl_posts)", systemImage: "photo.on.rectangle")
            }
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 18)
                .fill(Color.black.opacity(0.4))
                .overlay(RoundedRectangle(cornerRadius: 18).stroke(primaryAccent.opacity(0.6), lineWidth: 1.5))
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
                    .fill(primaryAccent.opacity(0.25))
                    .frame(width: 60, height: 60)
                    .overlay(Text(initials(from: profile.display_name ?? ""))
                        .font(.title3.bold())
                        .foregroundColor(.white))
            }
        }
        .overlay(Circle().stroke(primaryAccent, lineWidth: 2))
        .shadow(color: primaryAccent.opacity(0.6), radius: 8)
    }

    // MARK: - Posts
    private func postsSection(_ profile: ProfileMeResponse) -> some View {
        VStack(spacing: 15) {
            let posts = (profile.meine_posts.freunde + (profile.meine_posts.public_ ?? []))
                .sorted(by: { $0.created_at > $1.created_at })

            if posts.isEmpty {
                Text("Keine Posts vorhanden.")
                    .font(.headline)
                    .foregroundColor(.white.opacity(0.7))
                    .padding(.vertical, 40)
                    .frame(maxWidth: .infinity)
                    .background(RoundedRectangle(cornerRadius: 15).fill(Color.black.opacity(0.25)))
                    .padding(.horizontal, 16)
            } else {
                VStack(spacing: 15) {
                    ForEach(posts) { post in
                        profilePostCard(post)
                    }
                }
                .padding([.top, .horizontal], 16)
                .background(
                    RoundedRectangle(cornerRadius: 20)
                        .fill(Color(red: 0.1, green: 0.1, blue: 0.3).opacity(0.9))
                        .shadow(color: primaryAccent.opacity(0.2), radius: 10, x: 0, y: 5)
                )
                .padding(.horizontal)
            }
        }
    }
    
    private func blockFriend() async {
        do {
            try await Api_Friends.blockUser(userId)
            await MainActor.run {
                dismiss()
            }
        } catch {
            await MainActor.run {
                errorMessage = "Fehler beim Blockieren: \(error.localizedDescription)"
            }
        }
    }

    // MARK: - Einzelner Post
    private func profilePostCard(_ p: ProfilePost) -> some View {
        let isLiked = likedPosts.contains(p.id)

        return VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(formatTs(Double(p.created_at)))
                    .font(.caption)
                    .foregroundColor(primaryAccent)
                Spacer()
                Menu {
                    Button(role: .destructive) {
                        reportedUserId = p.id
                        showReportSheet = true
                    } label: {
                        Label("Beitrag melden", systemImage: "exclamationmark.triangle")
                    }
                } label: {
                    Image(systemName: "ellipsis")
                        .foregroundColor(primaryAccent)
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
                    .foregroundColor(.white)
            }

            HStack(spacing: 25) {
                Button {
                    Task { await toggleLike(p) }
                } label: {
                    HStack {
                        Image(systemName: isLiked ? "heart.fill" : "heart")
                            .foregroundColor(isLiked ? .pink : .white)
                        Text("\(p.like_count + (isLiked ? 1 : 0))")
                            .font(.subheadline.weight(.semibold))
                            .foregroundColor(.white)
                    }
                }

                Button {
                    withAnimation {
                        expandedPostId = expandedPostId == p.id ? nil : p.id
                    }
                } label: {
                    HStack {
                        Image(systemName: "bubble.right.fill")
                            .foregroundColor(primaryAccent)
                        Text("\(p.comment_count)")
                            .font(.subheadline.weight(.semibold))
                            .foregroundColor(.white)
                    }
                }

                Spacer()
            }
            .padding(.top, 4)

            if expandedPostId == p.id {
                CommentsView(
                    postId: p.id,
                    apiFeed: Api_Feed,
                    primaryAccent: primaryAccent,
                    secondaryAccent: deepBackgroundColor,
                    textPrimary: palette.textPrimary,
                    textSecondary: palette.textSecondary
                )
                .environmentObject(app)
                .transition(.opacity.combined(with: .move(edge: .bottom)))
                .padding(.top, 10)
            }
        }
        .padding()
        .background(Color.black.opacity(0.35))
        .cornerRadius(12)
        .animation(.easeInOut, value: expandedPostId)
    }

    // MARK: - Report Sheet
    private var reportSheet: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 20) {
                Text("Profil melden")
                    .font(.title2.bold())
                    .foregroundColor(.white)

                Text("Bitte gib kurz an, warum du dieses Profil melden möchtest.")
                    .font(.subheadline)
                    .foregroundColor(.white.opacity(0.8))

                TextField("Grund der Meldung ...", text: $reportReason)
                    .padding()
                    .background(Color.white.opacity(0.1))
                    .cornerRadius(10)
                    .foregroundColor(.white)

                Spacer()

                Button {
                    Task { await sendReport() }
                } label: {
                    Text("Senden")
                        .bold()
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(primaryAccent)
                        .foregroundColor(.black)
                        .cornerRadius(12)
                }
            }
            .padding()
            .background(
                LinearGradient(
                    colors: [Color(red: 0.05, green: 0.05, blue: 0.2), deepBackgroundColor],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()
            )

            
        }
        .presentationDetents([.medium])
    }

    // MARK: - Aktionen
    private func toggleLike(_ post: ProfilePost) async {
        do {
            if likedPosts.contains(post.id) {
                try await Api_Feed.feedUnlike(postId: post.id)
                await MainActor.run { likedPosts.remove(post.id) }
            } else {
                try await Api_Feed.feedLike(postId: post.id)
                await MainActor.run { likedPosts.insert(post.id) }
            }
        } catch {
            print("❌ Fehler beim Liken: \(error.localizedDescription)")
        }
    }

    private func removeFriend() async {
        do {
            try await Api_Friends.removeFriend(userId: userId)
            await MainActor.run {
                dismiss()
            }
        } catch {
            await MainActor.run { errorMessage = "Fehler beim Entfernen: \(error.localizedDescription)" }
        }
    }

    private func sendReport() async {
        guard let uid = reportedUserId else { return }
        let reason = reportReason.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !reason.isEmpty else { return }

        do {
            let ok = try await Api_Report.createReport(userId: uid, reason: reason)
            if ok {
                await MainActor.run {
                    showReportSheet = false
                    reportReason = ""
                    showReportSuccess = true
                }
            }
        } catch {
            await MainActor.run {
                showReportSheet = false
                errorMessage = "Fehler beim Melden: \(error.localizedDescription)"
            }
        }
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
        .background(primaryAccent.opacity(0.2))
        .clipShape(Capsule())
        .foregroundColor(.white)
        .overlay(Capsule().stroke(primaryAccent.opacity(0.5), lineWidth: 1))
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
            let prof = try await Api_Profiles.getUserProfile(userId: userId)
            await MainActor.run { self.profile = prof }
        } catch {
            await MainActor.run { self.errorMessage = error.localizedDescription }
        }
    }
}
