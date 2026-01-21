import SwiftUI

struct NotificationsRow: View {
    @EnvironmentObject var app: AppState
    let notification: NotificationItem
    @State private var isProcessing = false
    @State private var actionDone = false
    @State private var errorMessage: String?
    @State private var isHidden = false

    private var apiFriends: api_friends { app.Api_Friends }
    private var apiChallenge: api_challenge { app.Api_Challenge }
    private var apiNotifications: api_notifications { app.Api_Notifications }

    var body: some View {
        if !isHidden {
            VStack(alignment: .leading, spacing: 10) {
                // Nachrichtentext
                Text(notification.message)
                    .font(.system(size: 16, weight: notification.isRead ? .regular : .bold))
                    .foregroundColor(.white)
                    .onTapGesture {
                        Task { await markAsReadIfNeeded(animated: true) }
                    }

                // Buttons bei Aktionen
                if !actionDone {
                    if notification.type == .friendRequest {
                        actionButtons(
                            acceptAction: { await handleFriendRequest(accept: true) },
                            declineAction: { await handleFriendRequest(accept: false) }
                        )
                    } else if notification.type == .challengeInvite {
                        actionButtons(
                            acceptAction: { await handleChallengeInvite(accept: true) },
                            declineAction: { await handleChallengeInvite(accept: false) }
                        )
                    }
                } else {
                    Text("✅ Erledigt")
                        .font(.caption)
                        .foregroundColor(.green)
                }

                if let err = errorMessage {
                    Text("⚠️ \(err)")
                        .font(.caption)
                        .foregroundColor(.red)
                }

                HStack {
                    Spacer()
                    Text(formatDate(notification.created_at))
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.6))
                }
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 14)
                    .fill(Color(red: 0.1, green: 0.1, blue: 0.25).opacity(0.95))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .stroke(notification.isRead ? Color.white.opacity(0.2) : Color.cyan.opacity(0.6), lineWidth: 1.2)
                    )
            )
            .shadow(color: Color.cyan.opacity(0.3), radius: 6, x: 0, y: 2)
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .transition(.move(edge: .trailing).combined(with: .opacity))
            .animation(.easeInOut(duration: 0.35), value: isHidden)
        }
    }

    // MARK: - Buttons Layout
    @ViewBuilder
    private func actionButtons(
        acceptAction: @escaping () async -> Void,
        declineAction: @escaping () async -> Void
    ) -> some View {
        HStack(spacing: 15) {
            Button {
                Task { await acceptAction() }
            } label: {
                Label("Annehmen", systemImage: "checkmark.circle.fill")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundColor(.green)
            }
            .disabled(isProcessing)

            Button {
                Task { await declineAction() }
            } label: {
                Label("Ablehnen", systemImage: "xmark.circle.fill")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundColor(.red)
            }
            .disabled(isProcessing)
        }
        .padding(.top, 6)
    }

    // MARK: - Animation beim Lesen oder Bearbeiten
    private func hideWithAnimation() {
        withAnimation {
            isHidden = true
        }
        Task {
            try? await Task.sleep(for: .seconds(0.4))
            await app.refreshUnread()
        }
    }

    // MARK: - Aktionen
    private func handleFriendRequest(accept: Bool) async {
        guard let id = notification.target_id else { return }
        isProcessing = true
        errorMessage = nil

        do {
            if accept {
                try await apiFriends.acceptFriendRequest(id)
            } else {
                try await apiFriends.declineFriendRequest(id)
            }
            try await apiNotifications.markAsRead(notification.id)
            actionDone = true
            hideWithAnimation()
        } catch {
            errorMessage = error.localizedDescription
        }

        isProcessing = false
    }

    private func handleChallengeInvite(accept: Bool) async {
        guard let targetId = notification.target_id else { return }
        isProcessing = true
        errorMessage = nil
        do {
            if accept {
                try await apiChallenge.acceptChallengeInvite(targetId)
            } else {
                try await apiChallenge.declineChallengeInvite(targetId)
            }
            try await apiNotifications.markAsRead(notification.id)
            actionDone = true
            hideWithAnimation()
        } catch {
            errorMessage = error.localizedDescription
        }
        isProcessing = false
    }

    private func markAsReadIfNeeded(animated: Bool = false) async {
        guard !notification.isRead else { return }

        if notification.type == .friendRequest || notification.type == .challengeInvite {
            return // diese erst bei Aktion
        }

        do {
            try await apiNotifications.markAsRead(notification.id)
            if animated { hideWithAnimation() }
        } catch {
            errorMessage = "Fehler beim Lesen: \(error.localizedDescription)"
        }
    }

    // MARK: - Helper
    private func formatDate(_ ms: Int) -> String {
        let date = Date(timeIntervalSince1970: Double(ms) / 1000.0)
        let f = DateFormatter()
        f.dateStyle = .short
        f.timeStyle = .short
        return f.string(from: date)
    }
}
