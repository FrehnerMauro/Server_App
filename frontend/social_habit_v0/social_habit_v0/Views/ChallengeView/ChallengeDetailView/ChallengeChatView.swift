//
//  ChallengeChatView.swift
//  social_habit_v0
//
//  Created by Mauro Frehner on 29.10.2025.
//

import SwiftUI
import PhotosUI

// MARK: - ViewModel
@MainActor
final class ChallengeChatViewModel: ObservableObject {
    @Published var response: ChallengeChatResponse?
    @Published var isLoading = false
    @Published var error: String?
    @Published var messageText = ""
    @Published var currentUserId: Int?

    func loadChat(app: AppState, challengeId: Int) async {
        isLoading = true
        error = nil
        do {
            let res = try await app.Api_Challenge.challengeChatList(challengeId)
            self.response = res
            self.currentUserId = res.currentUserId
        } catch {
            self.error = error.localizedDescription
            print("❌ Fehler beim Laden des Chats: \(error)")
        }
        isLoading = false
    }

    func sendMessage(app: AppState, challengeId: Int) async {
        guard !messageText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }

        print("✉️ Sende Textnachricht: '\(messageText)'")
        do {
            try await app.Api_Challenge.sendMessage(challengeId: challengeId, text: messageText)
            print("✅ Nachricht gesendet.")
            messageText = ""
            await loadChat(app: app, challengeId: challengeId)
        } catch {
            print("❌ Fehler beim Senden der Nachricht: \(error)")
        }
    }
}

// MARK: - Hauptansicht
struct ChallengeChatView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager
    @StateObject private var vm = ChallengeChatViewModel()
    let challengeId: Int
    let title: String
    
    // MARK: - Reporting State
    @State private var showReportSheet = false
    @State private var reportReason = ""
    @State private var reportMessageId: Int? = nil
    @State private var isReporting = false
    @State private var reportInfo: String?
    @State private var reportError: String?

    private var palette: Theme { theme.theme }
    private let myBubbleColor = Color(red: 0.1, green: 0.3, blue: 0.8).opacity(0.9)
    private let otherBubbleColor = Color(red: 0.1, green: 0.1, blue: 0.3).opacity(0.8)

    var body: some View {
        ZStack {
            palette.backgroundGradient
                .ignoresSafeArea()
            
            VStack(spacing: 0) {
                if vm.isLoading && vm.response == nil {
                    ProgressView("Lade Chat …")
                        .padding()
                        .tint(palette.accent)
                } else if let error = vm.error {
                    Text("⚠️ Fehler: \(error)")
                        .foregroundColor(.red)
                        .padding()
                } else if let chat = vm.response {
                    chatList(chat)
                    chatInput()
                } else {
                    Text("Noch keine Nachrichten.")
                        .foregroundColor(.white.opacity(0.7))
                        .padding()
                }
            }
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbarColorScheme(.dark, for: .navigationBar)
        .toolbarBackground(.visible, for: .navigationBar)
        .toolbarBackground(palette.background, for: .navigationBar)
        .onAppear {
            UINavigationBar.appearance().titleTextAttributes = [.foregroundColor: UIColor.white]
        }
        .task {
            await vm.loadChat(app: app, challengeId: challengeId)
        }
        // MARK: - Report Sheet
        .sheet(isPresented: $showReportSheet) {
            NavigationStack {
                VStack(alignment: .leading, spacing: 16) {
                    Text("Nachricht melden")
                        .font(.title2.bold())
                        .foregroundColor(.white)

                    Text("Bitte gib den Grund an. Dein Report wird an das Moderationsteam uebermittelt.")
                        .font(.subheadline)
                        .foregroundColor(.white.opacity(0.8))

                    TextField("Grund (z. B. Beleidigung, Spam …)", text: $reportReason, axis: .vertical)
                        .textFieldStyle(.plain)
                        .padding(12)
                        .background(Color.white.opacity(0.1))
                        .foregroundColor(.white)
                        .cornerRadius(10)
                        .lineLimit(3...6)

                    if let info = reportInfo {
                        Text("✅ \(info)").foregroundColor(.green).font(.footnote.bold())
                    }
                    if let err = reportError {
                        Text("❌ \(err)").foregroundColor(.red).font(.footnote.bold())
                    }

                    Spacer()

                    Button {
                        Task { await submitReport() }
                    } label: {
                        HStack {
                            if isReporting { ProgressView().tint(.black) }
                            Text(isReporting ? "Sende…" : "Meldung senden").bold()
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(palette.accent)
                        .foregroundColor(palette.textPrimary)
                        .cornerRadius(12)
                    }
                    .disabled(isReporting || reportReason.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
                .padding()
                .background(palette.backgroundGradient.ignoresSafeArea())
            }
            .presentationDetents([.medium])
        }
    }

    // MARK: - Chatliste
    @ViewBuilder
    private func chatList(_ chat: ChallengeChatResponse) -> some View {
        let messages = chat.chat
        let members = chat.members

        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 12) {
                    ForEach(messages) { msg in
                        ChatBubbleView(
                            message: msg,
                            members: members,
                            currentUserId: vm.currentUserId,
                            primaryAccent: palette.accent,
                            myBubbleColor: myBubbleColor,
                            otherBubbleColor: otherBubbleColor,
                            textPrimary: palette.textPrimary,
                            textSecondary: palette.textSecondary,
                            onReport: { messageId in
                                UIImpactFeedbackGenerator(style: .light).impactOccurred()
                                reportMessageId = messageId
                                reportReason = ""
                                reportInfo = nil
                                reportError = nil
                                showReportSheet = true
                            }
                        )
                    }
                }
                .padding(.top, 10)
                .padding(.horizontal, 5)
                .padding(.bottom, 5)
                .onChange(of: vm.response?.chat.count) { _ in
                    if messages.last?.id != nil {
                        withAnimation {
                            proxy.scrollTo(messages.last!.id, anchor: .bottom)
                        }
                    }
                }
            }
        }
    }

    // MARK: - Eingabezeile
    @ViewBuilder
    private func chatInput() -> some View {
        VStack(spacing: 8) {
            HStack(alignment: .bottom, spacing: 10) {

                // 📸 Bild hochladen (als Confirm)
                ChallengeConfirmImagePicker(challengeId: challengeId, visibility: "friends")
                    .environmentObject(app)
                    .environmentObject(vm) // ViewModel an Picker weitergeben
                    .buttonStyle(ImagePickerButtonStyle(primaryAccent: palette.accent))

                // 📝 Textfeld
                TextField("Nachricht schreiben …", text: $vm.messageText, axis: .vertical)
                    .textFieldStyle(.plain)
                    .foregroundColor(.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .background(Color.black.opacity(0.6))
                    .clipShape(RoundedRectangle(cornerRadius: 25))
                    .lineLimit(1...5)
                    .autocorrectionDisabled(true)
                    .shadow(color: palette.accent.opacity(0.4), radius: 5)
                
                // 📤 Senden
                Button {
                    Task { await vm.sendMessage(app: app, challengeId: challengeId) }
                } label: {
                    Image(systemName: "arrow.up")
                        .font(.title3.weight(.bold))
                        .foregroundColor(.white)
                        .padding(12)
                        .background(
                            vm.messageText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                            ? Color.gray.opacity(0.7)
                            : palette.accent.opacity(0.9)
                        )
                        .clipShape(Circle())
                        .shadow(color: palette.accent.opacity(vm.messageText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? 0 : 0.8), radius: 8)
                }
                .disabled(vm.messageText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
            .padding(.horizontal)
            .padding(.vertical, 10)
        }
        .background(Color.black.opacity(0.3))
    }

    // MARK: - Report submit
    private func submitReport() async {
        guard let mid = reportMessageId else { return }
        let reason = reportReason.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !reason.isEmpty else { return }

        isReporting = true
        reportInfo = nil
        reportError = nil
        do {
            let ok = try await app.Api_Report.createReport(
                userId: nil,
                postId: nil,
                challengeId: nil,
                messageId: mid,
                commentId: nil,
                reason: reason
            )
            if ok {
                reportInfo = "Meldung erfolgreich gesendet."
                // kleines Delay fuer Feedback
                try? await Task.sleep(nanoseconds: 900_000_000)
                showReportSheet = false
            } else {
                reportError = "Server hat die Meldung abgelehnt."
            }
        } catch {
            reportError = error.localizedDescription
        }
        isReporting = false
    }
}

// MARK: - ButtonStyle
struct ImagePickerButtonStyle: ButtonStyle {
    let primaryAccent: Color
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.title3.weight(.bold))
            .foregroundColor(.white)
            .padding(12)
            .background(primaryAccent.opacity(0.8))
            .clipShape(Circle())
            .scaleEffect(configuration.isPressed ? 0.9 : 1.0)
            .shadow(color: primaryAccent.opacity(0.8), radius: 8)
    }
}

// MARK: - Chat Bubble View (mit Confirm-Design + Report)
struct ChatBubbleView: View {
    let message: ChatMessage
    let members: [ChatMember]
    let currentUserId: Int?
    let primaryAccent: Color
    let myBubbleColor: Color
    let otherBubbleColor: Color
    let textPrimary: Color
    let textSecondary: Color
    let onReport: (Int) -> Void

    private var isMine: Bool { message.userId == currentUserId }
    private var member: ChatMember? { members.first(where: { $0.userId == message.userId }) }

    private func formattedTime(_ timestamp: Int) -> String {
        let date = Date(timeIntervalSince1970: TimeInterval(timestamp))
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }

    private var bubbleShape: some Shape { BubbleTailShape(isMine: isMine) }
    private var bubbleFillColor: Color { isMine ? myBubbleColor : otherBubbleColor }
    private var bubbleStrokeColor: Color { isMine ? primaryAccent.opacity(0.6) : Color.white.opacity(0.4) }
    private var textColor: Color { textPrimary }

    private var isConfirm: Bool {
        message.imageUrl != nil && !(message.imageUrl?.isEmpty ?? true)
    }

    var body: some View {
        HStack(alignment: .bottom, spacing: 6) {
            if isMine { Spacer(minLength: 40) }
            if !isMine { avatar }

            VStack(alignment: isMine ? .trailing : .leading, spacing: 6) {
                if !isMine {
                    Text(member?.displayName ?? "Unbekannt")
                        .font(.caption2.weight(.medium))
                        .foregroundColor(textSecondary)
                        .foregroundColor(primaryAccent)
                        .padding(.horizontal, 8)
                }

                // CONFIRM Block (bild + optional text)
                if isConfirm {
                    confirmBlock
                        .contextMenu { reportMenu }
                        .onLongPressGesture {
                            onReport(message.id)
                        }
                        .padding(isMine ? .trailing : .leading, 6)
                        .padding(.vertical, 4)
                }

                // Nur Text
                if !isConfirm && !message.text.isEmpty {
                    Text(message.text)
                        .multilineTextAlignment(isMine ? .trailing : .leading)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(bubbleFillColor)
                        .foregroundColor(textColor)
                        .clipShape(bubbleShape)
                        .overlay(bubbleShape.stroke(bubbleStrokeColor, lineWidth: 1.5))
                        .shadow(color: isMine ? primaryAccent.opacity(0.4) : Color.black.opacity(0.4),
                                radius: 5, x: isMine ? 2 : -2, y: 3)
                        .contextMenu { reportMenu }
                        .onLongPressGesture {
                            onReport(message.id)
                        }
                }

                Text(formattedTime(message.createdAt))
                    .font(.caption2)
                    .foregroundColor(.white.opacity(0.6))
                    .padding(isMine ? .trailing : .leading, 12)
            }
            if !isMine { Spacer(minLength: 40) }
        }
        .id(message.id)
        .padding(.horizontal, 10)
        .padding(.vertical, 4)
        .frame(maxWidth: .infinity, alignment: isMine ? .trailing : .leading)
    }

    private var avatar: some View {
        if let avatarUrl = member?.avatarUrl, !avatarUrl.isEmpty {
            return AnyView(
                RemoteOrDataURLImage(urlString: avatarUrl)
                    .frame(width: 38, height: 38)
                    .clipShape(Circle())
                    .overlay(Circle().stroke(primaryAccent.opacity(0.8), lineWidth: 2))
                    .shadow(color: primaryAccent.opacity(0.7), radius: 3)
            )
        } else {
            return AnyView(
                Circle().fill(primaryAccent.opacity(0.3))
                    .overlay(Image(systemName: "person.fill").foregroundColor(.white))
                    .frame(width: 38, height: 38)
                    .clipShape(Circle())
                    .overlay(Circle().stroke(primaryAccent.opacity(0.8), lineWidth: 2))
                    .shadow(color: primaryAccent.opacity(0.7), radius: 3)
            )
        }
    }

    private var confirmBlock: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 5) {
                Text("Bestätigung")
                    .font(.caption.bold())
                    .foregroundColor(.green)
                Text("✅")
            }
            .padding(.horizontal, 8)
            .padding(.top, 6)

            AsyncImage(url: URL(string: message.imageUrl ?? "")) { phase in
                switch phase {
                case .success(let image):
                    image
                        .resizable()
                        .scaledToFit()
                        .frame(maxWidth: 250)
                        .cornerRadius(12)
                        .shadow(color: .green.opacity(0.4), radius: 8)
                case .failure(_):
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color.gray.opacity(0.3))
                        .frame(width: 220, height: 160)
                        .overlay(Text("⚠️ Bild konnte nicht geladen werden").font(.caption))
                default:
                    ProgressView()
                        .frame(width: 220, height: 160)
                }
            }

            if !message.text.isEmpty {
                Text(message.text)
                    .font(.subheadline)
                    .foregroundColor(.white)
                    .multilineTextAlignment(isMine ? .trailing : .leading)
                    .padding(.horizontal, 8)
                    .padding(.bottom, 8)
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 15)
                .fill(Color.green.opacity(0.2))
                .overlay(
                    RoundedRectangle(cornerRadius: 15)
                        .stroke(Color.green.opacity(0.5), lineWidth: 2)
                )
                .shadow(color: .green.opacity(0.5), radius: 8)
        )
    }

    @ViewBuilder
    private var reportMenu: some View {
        Button(role: .destructive) {
            onReport(message.id)
        } label: {
            Label("Nachricht melden", systemImage: "exclamationmark.triangle")
        }
    }
}

// MARK: - Bubble Tail Shape
struct BubbleTailShape: Shape {
    let isMine: Bool

    func path(in rect: CGRect) -> Path {
        let radius: CGFloat = 14
        let tailWidth: CGFloat = 8
        let tailHeight: CGFloat = 8
        let tailBaseY: CGFloat = rect.maxY - tailHeight
        var path = Path()

        if isMine {
            path.move(to: CGPoint(x: rect.minX + radius, y: rect.minY))
            path.addLine(to: CGPoint(x: rect.maxX - tailWidth - radius, y: rect.minY))
            path.addArc(center: CGPoint(x: rect.maxX - tailWidth - radius, y: rect.minY + radius),
                         radius: radius, startAngle: .degrees(270), endAngle: .degrees(0), clockwise: false)
            path.addLine(to: CGPoint(x: rect.maxX - tailWidth, y: tailBaseY - radius))
            path.addLine(to: CGPoint(x: rect.maxX - tailWidth, y: tailBaseY))
            path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))
            path.addLine(to: CGPoint(x: rect.maxX - tailWidth, y: rect.maxY))
            path.addLine(to: CGPoint(x: rect.minX + radius, y: rect.maxY))
            path.addArc(center: CGPoint(x: rect.minX + radius, y: rect.maxY - radius),
                         radius: radius, startAngle: .degrees(90), endAngle: .degrees(180), clockwise: false)
            path.addLine(to: CGPoint(x: rect.minX, y: rect.minY + radius))
            path.addArc(center: CGPoint(x: rect.minX + radius, y: rect.minY + radius),
                         radius: radius, startAngle: .degrees(180), endAngle: .degrees(270), clockwise: false)
        } else {
            path.move(to: CGPoint(x: rect.minX + radius + tailWidth, y: rect.minY))
            path.addLine(to: CGPoint(x: rect.maxX - radius, y: rect.minY))
            path.addArc(center: CGPoint(x: rect.maxX - radius, y: rect.minY + radius),
                         radius: radius, startAngle: .degrees(270), endAngle: .degrees(0), clockwise: false)
            path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY - radius))
            path.addArc(center: CGPoint(x: rect.maxX - radius, y: rect.maxY - radius),
                         radius: radius, startAngle: .degrees(0), endAngle: .degrees(90), clockwise: false)
            path.addLine(to: CGPoint(x: rect.minX, y: rect.maxY))
            path.addLine(to: CGPoint(x: rect.minX + tailWidth, y: tailBaseY))
            path.addLine(to: CGPoint(x: rect.minX + tailWidth, y: rect.minY + radius))
            path.addArc(center: CGPoint(x: rect.minX + radius + tailWidth, y: rect.minY + radius),
                         radius: radius, startAngle: .degrees(180), endAngle: .degrees(270), clockwise: false)
        }
        return path
    }
}
