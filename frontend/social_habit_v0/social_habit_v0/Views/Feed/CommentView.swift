import SwiftUI
import Foundation

// Benötigt Zugriff auf FeedCommentDTO und api_feed (definiert in Feed.swift)

struct CommentsView: View {
    let postId: Int
    let apiFeed: api_feed // api_feed muss injiziert werden.
    let primaryAccent: Color
    let secondaryAccent: Color
    let textPrimary: Color
    let textSecondary: Color
    var onCommentAdded: (() -> Void)? = nil
    
    @State private var comments: [FeedCommentDTO] = []
    @State private var newCommentText: String = ""
    @State private var loadingComments: Bool = false
    @State private var error: String?
    @State private var isSubmitting: Bool = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // --- Kommentar Eingabe ---
            VStack(spacing: 12) {
                HStack(spacing: 10) {
                    TextField("Deine Antwort...", text: $newCommentText)
                        .textFieldStyle(.plain)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 12)
                        .background(Color.white.opacity(0.95))
                        .foregroundColor(Color.black)
                        .cornerRadius(12)
                        .font(.system(size: 15, weight: .medium))

                    Button {
                        Task { await addComment() }
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .foregroundColor(.white)
                            .font(.system(size: 28, weight: .semibold))
                            .frame(width: 44, height: 44)
                            .background(
                                Circle()
                                    .fill(
                                        LinearGradient(
                                            gradient: Gradient(colors: [primaryAccent, secondaryAccent]),
                                            startPoint: .topLeading,
                                            endPoint: .bottomTrailing
                                        )
                                    )
                            )
                            .shadow(color: primaryAccent.opacity(0.5), radius: 4)
                    }
                    .disabled(newCommentText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSubmitting)
                    .opacity(newCommentText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSubmitting ? 0.5 : 1.0)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 14)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(secondaryAccent.opacity(0.3))
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(primaryAccent.opacity(0.4), lineWidth: 1)
                    )
            )
            .padding(.bottom, 12)
            
            // --- Kommentare Header mit Divider ---
            if !comments.isEmpty {
                HStack(spacing: 10) {
                    Image(systemName: "bubble.left.and.bubble.right.fill")
                        .foregroundColor(primaryAccent)
                        .font(.system(size: 14, weight: .semibold))
                    
                    Text("Kommentare (\(comments.count))")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(textPrimary)
                    
                    Spacer()
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
            }
            
            // --- Kommentare Liste ---
            if loadingComments {
                HStack {
                    Spacer()
                    ProgressView()
                        .tint(primaryAccent)
                    Spacer()
                }
                .padding(.vertical, 20)
            } else if let err = error {
                HStack {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(primaryAccent)
                    Text("Fehler: \(err)")
                        .font(.caption)
                        .foregroundColor(textSecondary)
                }
                .padding(.vertical, 12)
                .padding(.horizontal, 12)
                .frame(maxWidth: .infinity)
                .background(primaryAccent.opacity(0.1))
                .cornerRadius(8)
            } else if comments.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "bubble.right.fill")
                        .foregroundColor(primaryAccent.opacity(0.4))
                        .font(.system(size: 28, weight: .semibold))
                    
                    Text("Sei der Erste!")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundColor(textSecondary)
                    
                    Text("Schreibe einen Kommentar")
                        .font(.caption)
                        .foregroundColor(textSecondary.opacity(0.7))
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 24)
            } else {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(Array(comments.enumerated()), id: \.element.id) { index, comment in
                        commentRow(comment)
                        
                        if index < comments.count - 1 {
                            Divider()
                                .background(primaryAccent.opacity(0.15))
                        }
                    }
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 6)
            }
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(
                    LinearGradient(
                        gradient: Gradient(colors: [
                            Color(red: 0.12, green: 0.12, blue: 0.32).opacity(0.85),
                            Color(red: 0.12, green: 0.12, blue: 0.32).opacity(0.75)
                        ]),
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(primaryAccent.opacity(0.2), lineWidth: 1)
        )
        .padding(.horizontal, 8)
        .onAppear {
            Task { await loadComments() }
        }
    }
    
    @ViewBuilder
    private func commentRow(_ comment: FeedCommentDTO) -> some View {
        HStack(alignment: .top, spacing: 12) {
            // Avatar mit Rahmen
            ZStack {
                Circle()
                    .fill(primaryAccent.opacity(0.15))
                
                if let avatar = comment.avatarUrl, !avatar.isEmpty {
                    RemoteOrDataURLImage(urlString: avatar)
                        .frame(width: 32, height: 32)
                        .clipShape(Circle())
                } else {
                    Circle().fill(primaryAccent.opacity(0.3))
                        .overlay(Image(systemName: "person.fill")
                            .foregroundColor(.white.opacity(0.7)))
                        .frame(width: 32, height: 32)
                }
            }
            .frame(width: 40, height: 40)
            
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 8) {
                    Text(comment.displayName ?? "Unbekannt")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(primaryAccent)
                    
                    Text(formatTs(comment.createdAt))
                        .font(.caption2)
                        .foregroundColor(textSecondary)
                    
                    Spacer()
                }
                
                Text(comment.text)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(textPrimary)
                    .lineSpacing(1)
            }
            
            Spacer()
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 4)
    }
    
    // MARK: - API Funktionen
    @MainActor
    private func loadComments() async {
        loadingComments = true
        error = nil
        do {
            comments = try await apiFeed.feedComments(postId: postId).reversed()
        } catch {
            self.error = error.localizedDescription
            print("❌ Fehler beim Laden der Kommentare: \(error.localizedDescription)")
        }
        loadingComments = false
    }

    @MainActor
    private func addComment() async {
        let textToSend = newCommentText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !textToSend.isEmpty else { return }

        isSubmitting = true
        error = nil
        do {
            let success = try await apiFeed.feedAddComment(postId: postId, text: textToSend)
            if success {
                newCommentText = ""
                await loadComments()
                onCommentAdded?()
            } else {
                self.error = "Kommentar konnte nicht hinzugefügt werden (Serverfehler)."
            }
        } catch {
            self.error = "Fehler beim Hinzufügen des Kommentars: \(error.localizedDescription)"
            print("❌ Fehler beim Hinzufügen des Kommentars: \(error.localizedDescription)")
        }
        isSubmitting = false
    }
}

// MARK: - Helper-Funktion (formatTs in CommentsView kopiert)

/// Formatiert einen UNIX-Timestamp (Millisekunden) in einen schönen Datumsstring.
private func formatTs(_ ms: Double) -> String {
    let date = Date(timeIntervalSince1970: ms / 1000)
    let f = DateFormatter()
    f.timeStyle = .short

    if Calendar.current.isDateInToday(date) {
        return "Heute \(f.string(from: date))"
    } else if Calendar.current.isDateInYesterday(date) {
        return "Gestern \(f.string(from: date))"
    } else {
        f.dateStyle = .medium
        f.timeStyle = .short
        return f.string(from: date)
    }
}
