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
    
    @State private var comments: [FeedCommentDTO] = []
    @State private var newCommentText: String = ""
    @State private var loadingComments: Bool = false
    @State private var error: String? // <<-- WICHTIG: Muss @State sein
    
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            
            // --- Kommentar Eingabe ---
            HStack(spacing: 8) {
                TextField("Dein Kommentar...", text: $newCommentText)
                    .textFieldStyle(.roundedBorder)
                    .padding(8)
                    .background(primaryAccent.opacity(0.15))
                    .foregroundColor(textPrimary)
                    .cornerRadius(8)
                
                Button {
                    Task { await addComment() }
                } label: {
                    Image(systemName: "paperplane.fill")
                        .foregroundColor(newCommentText.isEmpty ? .gray : primaryAccent)
                        .font(.title2.weight(.bold))
                }
                .disabled(newCommentText.isEmpty)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(Color(red: 0.15, green: 0.15, blue: 0.4).opacity(0.9))
            .cornerRadius(8)
            
            // --- Kommentare Liste ---
            if loadingComments {
                ProgressView("Lade Kommentare...")
                    .tint(primaryAccent)
                    .padding(.vertical, 10)
            } else if let err = error {
                Text("⚠️ Fehler beim Laden: \(err)")
                    .foregroundColor(primaryAccent)
                    .padding(.vertical, 10)
            } else if comments.isEmpty {
                Text("Noch keine Kommentare 💬")
                    .foregroundColor(.white.opacity(0.7))
                    .padding(.vertical, 10)
            } else {
                ForEach(comments, id: \.id) { comment in
                    commentRow(comment)
                }
            }
        }
        .padding(5)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(red: 0.1, green: 0.1, blue: 0.3).opacity(0.95))
        )
        .padding(.horizontal, 8)
        .onAppear {
            Task { await loadComments() }
        }
    }
    
    @ViewBuilder
    private func commentRow(_ comment: FeedCommentDTO) -> some View {
        HStack(alignment: .top, spacing: 10) {
            // Avatar (sehr klein)
            if let avatar = comment.avatarUrl, !avatar.isEmpty {
                RemoteOrDataURLImage(urlString: avatar)
                    .frame(width: 30, height: 30)
                    .clipShape(Circle())
            } else {
                Circle().fill(secondaryAccent.opacity(0.3))
                    .overlay(Image(systemName: "person.fill")
                        .foregroundColor(.white.opacity(0.6)))
                    .frame(width: 30, height: 30)
            }
            
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(comment.displayName ?? "Unbekannt")
                        .font(.subheadline.weight(.bold))
                        .foregroundColor(primaryAccent)
                    
                    // Verwendung der lokalen formatTs Funktion
                    Text("(\(formatTs(comment.createdAt)))")
                        .font(.caption)
                        .foregroundColor(textSecondary)
                }
                
                Text(comment.text)
                    .font(.callout)
                    .foregroundColor(textPrimary)
            }
            Spacer()
        }
        .padding(.vertical, 4)
    }
    
    // MARK: - API Funktionen
    @MainActor
    private func loadComments() async {
        loadingComments = true
        error = nil
        do {
            comments = try await apiFeed.feedComments(postId: postId).reversed() // Neueste oben
        } catch {
            self.error = error.localizedDescription // Fehler behoben: Zuweisung zu String?
            print("❌ Fehler beim Laden der Kommentare: \(error.localizedDescription)")
        }
        loadingComments = false
    }

    @MainActor
    private func addComment() async {
        let textToSend = newCommentText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !textToSend.isEmpty else { return }

        do {
            let success = try await apiFeed.feedAddComment(postId: postId, text: textToSend)
            if success {
                newCommentText = ""
                await loadComments()
            } else {
                self.error = "Kommentar konnte nicht hinzugefügt werden (Serverfehler)." // Fehler behoben: Zuweisung zu String?
            }
        } catch {
            self.error = "Fehler beim Hinzufügen des Kommentars: \(error.localizedDescription)" // Fehler behoben: Zuweisung zu String?
            print("❌ Fehler beim Hinzufügen des Kommentars: \(error.localizedDescription)")
        }
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
