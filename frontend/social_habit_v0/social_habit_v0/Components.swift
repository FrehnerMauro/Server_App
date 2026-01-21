//
//  Components.swift
//  social_habit_v0
//
//  Erstellt von Mauro am 24.10.2025.
//

import SwiftUI
import Foundation

// MARK: - 🔹 Datum & Formatierungen

extension Double {
    /// Wandelt Millisekunden (z. B. 1761314262456) in ein Date-Objekt um
    var asDateFromMs: Date {
        Date(timeIntervalSince1970: self / 1000)
    }

    /// Gibt Datum formatiert als String zurück (z. B. „24.10.2025, 14:35“)
    var formattedDate: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        formatter.timeStyle = .short
        return formatter.string(from: self.asDateFromMs)
    }
}

// MARK: - 🔹 String Helpers

extension String {
    /// Extrahiert Base64-Daten aus einem `data:image/...;base64,...`-String
    var base64Cleaned: String? {
        if let comma = self.firstIndex(of: ",") {
            return String(self[self.index(after: comma)...])
        }
        return nil
    }

    /// Wandelt Base64-String in UIImage um (falls möglich)
    var asUIImageFromBase64: UIImage? {
        guard let base64 = self.base64Cleaned,
              let data = Data(base64Encoded: base64) else { return nil }
        return UIImage(data: data)
    }
}

// MARK: - 🔹 UI Komponenten

/// Bildanzeige: funktioniert mit URL oder Base64-Daten
struct SmartImage: View {
    let source: String?
    let cornerRadius: CGFloat

    init(_ source: String?, cornerRadius: CGFloat = 12) {
        self.source = source
        self.cornerRadius = cornerRadius
    }

    var body: some View {
        Group {
            if let src = source, !src.isEmpty {
                if src.starts(with: "data:image"),
                   let img = src.asUIImageFromBase64 {
                    Image(uiImage: img)
                        .resizable()
                        .scaledToFit()
                } else if let url = URL(string: src) {
                    AsyncImage(url: url) { phase in
                        switch phase {
                        case .success(let image):
                            image.resizable().scaledToFit()
                        case .empty:
                            ProgressView().tint(.white)
                        case .failure(_):
                            Color.gray.opacity(0.3)
                        @unknown default:
                            EmptyView()
                        }
                    }
                } else {
                    Color.gray.opacity(0.2)
                }
            } else {
                Color.gray.opacity(0.2)
            }
        }
        .cornerRadius(cornerRadius)
    }
}

/// Standardkarte für Inhalte mit Hintergrund und Rahmen
struct Card<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color.white.opacity(0.15))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(Color.white.opacity(0.1), lineWidth: 1)
            )
    }
}

// MARK: - 🔹 Farben & Styles

extension Color {
    static let gradientTop = Color(red: 0.5, green: 0.8, blue: 1.0)
    static let gradientBottom = Color(red: 0.2, green: 0.4, blue: 1.0)
    static let softWhite = Color.white.opacity(0.9)
}
// MARK: - 🔹 Circular Progress View

struct CircularProgressView: View {
    let progress: CGFloat
    let color: Color
    
    var body: some View {
        Circle()
            .stroke(color.opacity(0.2), lineWidth: 3)
            .background(Circle().fill(Color.clear))
            .overlay(
                Circle()
                    .trim(from: 0, to: progress)
                    .stroke(
                        LinearGradient(
                            gradient: Gradient(colors: [color, color.opacity(0.6)]),
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        style: StrokeStyle(lineWidth: 3, lineCap: .round)
                    )
                    .rotationEffect(.degrees(-90))
                    .animation(.easeInOut(duration: 0.5), value: progress)
            )
    }
}
// MARK: - 🔹 Beispiel-Nutzung

/*
 Beispiel für Datum:
    Text(post.created_at.formattedDate)

 Beispiel für Bild:
    SmartImage(post.image_url)

 Beispiel für Karte:
    Card {
        Text("Hallo Welt")
    }
*/
