import SwiftUI
import Foundation

@MainActor
final class ChallengesOverviewViewModel: ObservableObject {
    @Published var challenges: [ChallengeOverview] = []
    @Published var isLoading = false
    @Published var error: String?

    private var currentTask: Task<Void, Never>?

    func loadChallenges(app: AppState) async {
        // Wenn schon ein Task läuft, abbrechen
        currentTask?.cancel()

        currentTask = Task {
            await runLoad(app: app)
        }
    }

    private func runLoad(app: AppState) async {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let result = try await app.Api_Challenge.challengeOverview()
            self.challenges = result
        } catch {
            if (error as? CancellationError) == nil {
                self.error = error.localizedDescription
                print("⚠️ Fehler beim Laden:", error.localizedDescription)
            } else {
                print("ℹ️ Task abgebrochen (erwartet).")
            }
        }
    }
}

// MARK: - View
struct ChallengesOverviewView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager
    @StateObject private var vm = ChallengesOverviewViewModel()
    @State private var showCreate = false

    private var palette: Theme { theme.theme }

    var body: some View {
        NavigationStack {
            ZStack {
                palette.backgroundGradient
                    .ignoresSafeArea()

                VStack(alignment: .leading, spacing: 10) {
                    // MARK: - Titel
                    VStack(spacing: 5) {
                        Text("Deine Challenges")
                            .font(.system(size: 36, weight: .bold))
                            .foregroundColor(palette.textPrimary)
                            .shadow(color: palette.accent.opacity(0.6), radius: 10)
                            .padding(.bottom, 4)

                        Text("Eine bessere Version von dir selbst.")
                            .font(.subheadline)
                            .foregroundColor(palette.textSecondary)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.top, 25)

                    // MARK: - Spinner mittig
                    if vm.isLoading {
                        HStack {
                            Spacer()
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: palette.accent))
                                .scaleEffect(1.0)
                                .padding(.vertical, 12)
                            Spacer()
                        }
                    }

                    // MARK: - Content
                    listContent
                }
                .padding(.horizontal)
            }
            .navigationBarHidden(true)
            .task { await reload() }
            .refreshable { await reload() }
            .sheet(isPresented: $showCreate) {
                CreateChallengeView {
                    await reload()
                }
                .environmentObject(app)
                .environmentObject(theme)
            }
            .overlay(alignment: .bottom) {
                floatingButtons
            }
        }
    }

    // MARK: - Gemeinsame Reload-Funktion
    private func reload() async {
        await vm.loadChallenges(app: app)
    }

    // MARK: - Floating Buttons
    private var floatingButtons: some View {
        HStack {
            Button {
                showCreate = true
            } label: {
                Image(systemName: "plus")
                    .font(.system(size: 28, weight: .heavy))
                            .foregroundColor(palette.textPrimary)
                    .frame(width: 60, height: 60)
                    .background(
                        Circle()
                                    .fill(palette.accent)
                                    .shadow(color: palette.accent.opacity(1.0), radius: 15)
                    )
            }
            Spacer()
        }
        .padding(.horizontal, 25)
        .padding(.bottom, 35)
    }

    // MARK: - Liste / Content
    @ViewBuilder
    private var listContent: some View {
        if let error = vm.error {
            Text("🚨 FEHLER: \(error)")
                .foregroundColor(palette.danger)
                .padding()
                .bold()
        } else if vm.challenges.isEmpty && !vm.isLoading {
            VStack {
                Text("Keine Challenges gefunden. Sei der Erste!")
                    .font(.title3.bold())
                    .foregroundColor(palette.textSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.top, 80)
                Spacer()
            }
        } else {
            ScrollView {
                VStack(spacing: 20) {
                    ForEach(vm.challenges) { overview in
                        ChallengeOverviewCard(overview: overview)
                        .padding(.horizontal, 16)
                    }
                }
                .padding(.vertical, 15)
                .padding(.bottom, 100)
            }
        }
    }
}

// MARK: - Challenge Card
struct ChallengeOverviewCard: View {
    let overview: ChallengeOverview
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager

    @State private var showReportSheet = false
    @State private var reportReason: String = ""
    @State private var isReporting = false
    @State private var reportSuccess: Bool? = nil

    private var palette: Theme { theme.theme }

    var body: some View {
        let ch = overview.challenge
        // HIER: Der oberste Member, welcher der gewünschte Member ist (wird an ChatView übergeben)
        
        
        NavigationLink(
            destination: ChallengeChatView(
                challengeId: ch.ch_id,
                title: ch.name,

            ).environmentObject(app)
        ) {
            VStack(alignment: .leading, spacing: 20) {
                HStack {
                    Text(ch.name)
                        .font(.system(size: 26, weight: .heavy))
                        .foregroundColor(palette.textPrimary)
                        .lineLimit(2)
                    Spacer()
                    
                    // 👉 Direktes Info-Symbol statt Menü
                    NavigationLink(
                        destination: ChallengeInfoView(challengeId: ch.ch_id)
                            .environmentObject(app)
                    ) {
                        Image(systemName: "info.circle.fill")
                            .foregroundColor(palette.accent)
                            .font(.title2.weight(.bold))
                            .padding(8)

                    }
                }

                HStack(spacing: 20) {
                    Label("\(ch.dauerTage) Tage", systemImage: "timer")
                    Label("\(ch.erlaubteFailsTage) Fails", systemImage: "hand.thumbsdown")
                }
                .font(.caption.weight(.semibold))
                .foregroundColor(palette.accent)

                Rectangle().frame(height: 1)
                    .foregroundColor(palette.textSecondary.opacity(0.3))

                VStack(spacing: 25) {
                    ForEach(overview.members) { member in
                        MemberProgressLine(member: member, totalDays: ch.dauerTage)
                    }
                }
            }
            .padding(25)
            .background(
                RoundedRectangle(cornerRadius: 20)
                        .fill(palette.surface.opacity(0.95))
                    .overlay(
                        RoundedRectangle(cornerRadius: 20)
                            .stroke(palette.accent.opacity(0.4), lineWidth: 2)
                    )
            )
                    .shadow(color: palette.accent.opacity(0.3), radius: 15, x: 0, y: 8)
        }
        .buttonStyle(.plain)
        .sheet(isPresented: $showReportSheet) {
            reportSheet(challengeId: ch.ch_id, challengeName: ch.name)
                .presentationDetents([.medium])
        }
    }

    // MARK: - Report Sheet
    @ViewBuilder
    private func reportSheet(challengeId: Int, challengeName: String?) -> some View {
        // ... (Der Code für reportSheet bleibt unverändert)
        VStack(alignment: .leading, spacing: 18) {
            Text("Challenge melden")
                .font(.title2.bold())
                .foregroundColor(palette.textPrimary)

            Text("Du meldest: **\(challengeName ?? "Unbekannte Challenge")**")
                .foregroundColor(palette.textSecondary)

            TextField("Grund der Meldung (z. B. unangemessener Inhalt)", text: $reportReason)
                .textFieldStyle(.roundedBorder)
                .padding(.vertical, 4)
                .background(palette.surface.opacity(0.4))
                .cornerRadius(8)
                .foregroundColor(palette.textPrimary)

            if isReporting {
                ProgressView("Sende Meldung...")
                    .tint(palette.accent)
            }

            if let success = reportSuccess {
                Text(success ? "✅ Meldung erfolgreich gesendet." : "❌ Fehler beim Melden.")
                    .foregroundColor(success ? palette.success : palette.danger)
                    .font(.footnote.bold())
            }

            Button {
                Task { await sendReport(challengeId: challengeId) }
            } label: {
                HStack {
                    Spacer()
                    Text("Meldung senden")
                        .bold()
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(palette.accent)
                        .foregroundColor(palette.textPrimary)
                        .cornerRadius(10)
                    Spacer()
                }
            }
            .disabled(isReporting || reportReason.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

            Spacer()
        }
        .padding()
        .background(
            palette.backgroundGradient
                .ignoresSafeArea()
        )
    }

    // MARK: - API Call
    private func sendReport(challengeId: Int) async {
        guard !reportReason.trimmingCharacters(in: .whitespaces).isEmpty else { return }

        isReporting = true
        reportSuccess = nil

        do {
            let ok = try await app.Api_Report.createReport(
                challengeId: challengeId,
                reason: reportReason
            )
            await MainActor.run {
                reportSuccess = ok
                if ok { reportReason = "" }
            }
        } catch {
            await MainActor.run { reportSuccess = false }
        }

        try? await Task.sleep(nanoseconds: 1_200_000_000) // kleiner Delay
        await MainActor.run {
            isReporting = false
            showReportSheet = false
        }
    }
}

// MARK: - Fortschrittszeile (komplett überarbeitet)
struct MemberProgressLine: View {
    let member: ChallengeMember
    let totalDays: Int
    @State private var animate = false

    // Fortschritt (inkl. Sonderfaelle)
    private var progress: Double {
        switch member.status {
        case "completed": return 1.0
        case "blocked":   return 1.0
        default:
            let denom = max(totalDays, 1)
            return min(1.0, max(0.0, Double(member.done_days) / Double(denom)))
        }
    }

    // Balken-Farben nach Status
    private var barGradient: LinearGradient {
        switch member.status {
        case "completed":
            return LinearGradient(colors: [.yellow, .orange], startPoint: .leading, endPoint: .trailing)
        case "blocked":
            return LinearGradient(colors: [.red, .red.opacity(0.8)], startPoint: .leading, endPoint: .trailing)
        default:
            return LinearGradient(colors: [.green, .cyan], startPoint: .leading, endPoint: .trailing)
        }
    }

    private var percentText: String {
        "\(Int(progress * 100))%"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            // Kopfzeile: Name + Badges/Stati + Prozent
            HStack(spacing: 10) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(member.display_name)
                        .font(.headline.weight(.heavy))
                        .foregroundColor(.white)

                    // Status-spezifischer Zusatztext
                    switch member.status {
                    case "run":
                        if member.streak > 0 {
                            HStack(spacing: 6) {
                                Text("\(member.streak) Tage Streak")
                                    .font(.caption.bold())
                                    .foregroundColor(.orange)
                                Text("🔥")
                                    .font(.system(size: 20))
                                    .scaleEffect(animate ? 1.2 : 1.0)
                                    .animation(.easeInOut(duration: 0.6).repeatForever(autoreverses: true), value: animate)
                            }
                        }
                        if member.fail_days > 0 {
                            HStack(spacing: 6) {
                                Text("Fails: \(member.fail_days)x")
                                    .font(.caption.bold())
                                    .foregroundColor(.red)
                                Text("💀")
                                    .font(.system(size: 20))
                                    .scaleEffect(animate ? 1.2 : 1.0)
                                    .animation(.easeInOut(duration: 0.6).repeatForever(autoreverses: true), value: animate)
                            }
                        }

                    case "not_started":
                        Text("Noch nicht gestartet")
                            .font(.caption.bold())
                            .foregroundColor(.white.opacity(0.7))

                    case "pending":
                        Text("Eingeladen")
                            .font(.caption.bold())
                            .foregroundColor(.cyan.opacity(0.9))

                    case "completed":
                        HStack(spacing: 6) {
                            Text("Abgeschlossen")
                                .font(.caption.bold())
                                .foregroundColor(.yellow)
                            Text("🎉")
                        }

                    case "blocked":
                        HStack(spacing: 6) {
                            Text("Blockiert")
                                .font(.caption.bold())
                                .foregroundColor(.red)
                            Text("🚫")
                        }

                    default:
                        EmptyView()
                    }
                }

                Spacer()

                // Prozentanzeige nur, wenn sinnvoll
                if ["run", "completed", "blocked"].contains(member.status) {
                    Text(percentText)
                        .font(.subheadline.bold())
                        .foregroundColor(member.status == "completed" ? .yellow :
                                         (member.status == "blocked" ? .red : .white))
                }
            }
            .onAppear { animate = true }

            // Fortschrittsbalken + Avatar + Status-Badges oben drauf
            GeometryReader { geo in
                let width = geo.size.width
                let avatarSize: CGFloat = 35
                let x = max(avatarSize / 2,
                            min(width - avatarSize / 2, width * progress))

                ZStack(alignment: .leading) {
                    // Hintergrund
                    Capsule()
                        .fill(member.status == "pending" ? Color.cyan.opacity(0.15) : Color.white.opacity(0.15))
                        .frame(height: 12)

                    // Gefuellter Balken (nur fuer run/completed/blocked)
                    if ["run", "completed", "blocked"].contains(member.status) {
                        Capsule()
                            .fill(barGradient)
                            .frame(width: max(10, width * progress), height: 12)
                            .shadow(color:
                                        member.status == "completed" ? .yellow.opacity(0.6) :
                                        (member.status == "blocked" ? .red.opacity(0.6) : .cyan.opacity(0.6)),
                                    radius: 8, x: 0, y: 0)
                            .animation(.spring(response: 0.7, dampingFraction: 0.8), value: progress)
                    }

                    // Avatar + Overlay (Krone/Block + Farbring)
                    ZStack {
                        if let avatar = member.avatar_url, !avatar.isEmpty {
                            RemoteOrDataURLImage(urlString: avatar)
                                .frame(width: avatarSize, height: avatarSize)
                                .clipShape(Circle())
                        } else {
                            Circle().fill(Color.gray.opacity(0.5))
                                .frame(width: avatarSize, height: avatarSize)
                        }
                        
                        Circle()
                            .stroke(borderColor(for: member), lineWidth: 4)
                            .shadow(color: borderColor(for: member).opacity(0.9),
                                    radius: member.today_done == 1 ? 8 : 4)
                            .frame(width: avatarSize, height: avatarSize)
                        if member.status == "completed" {
                            Image(systemName: "crown.fill")
                                .font(.system(size: 16))
                                .foregroundColor(.yellow)
                                .offset(y: -26)
                                .shadow(color: .yellow, radius: 5)
                        }

                        // 🚫 fuer blocked
                        if member.status == "blocked" {
                            Text("🚫")
                                .font(.system(size: 18))
                                .offset(y: -26)
                                .shadow(color: .red, radius: 4)
                        }
                    }
                    .offset(x: x - avatarSize / 2)
                }
            }
            .frame(height: 35)
            .padding(.top, 8)
        }
    }

    // MARK: - Ringfarbe abhängig von Status + heute done/pending
    private func borderColor(for member: ChallengeMember) -> Color {
        if member.today_done == 1 {
            return .green // ✅ Heute abgeschlossen
        } else if member.today_pending == 1 {
            return .red // ❌ Heute noch offen/pending
        } else {
            switch member.status {
            case "completed": return .yellow
            case "blocked":   return .red
            default:          return .cyan // Standard: aktiv oder wartet
            }
        }
    }
}

// MARK: - ChallengeResponse Model
struct ChallengeResponse: Codable {
    let id: Int
    let name: String?
}

// MARK: - CreateChallengeView
struct CreateChallengeView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager
    @Environment(\.dismiss) private var dismiss

    private var palette: Theme { theme.theme }

    @State private var nameField: String = ""
    @State private var selectedDays: [Int] = [0, 2, 4]
    @State private var dauerInput: String = ""
    @State private var failsInput: String = ""
    @State private var startAt: Date = Date()

    @State private var error: String?
    @State private var creating = false

    @State private var inviteFriends = false
    @State private var friends: [User] = []
    @State private var searchQuery: String = ""
    @State private var selectedFriends: [User] = []

    let onCreation: () async -> Void

    private var Api_Challenge: api_challenge { app.Api_Challenge }
    private var Api_Friends: api_friends { app.Api_Friends }

    /// Debug-Ausgaben aktivieren/deaktivieren
    private let DEBUG_INVITES = true

    var body: some View {
        ZStack {
            palette.backgroundGradient
                .ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    TitleHeader(text: "Neue Challenge", accentColor: palette.accent)

                    VStack(alignment: .leading, spacing: 16) {
                        SectionHeader("Name der Challenge")
                        TextField("", text: $nameField)
                            .padding(12)
                            .background(palette.surface)
                            .cornerRadius(10)
                            .foregroundColor(palette.textPrimary)
                            .placeholder(when: nameField.isEmpty) {
                                Text("z. B. Tägliches Joggen")
                                    .foregroundColor(palette.textSecondary)
                                    .padding(.leading, 12)
                            }

                        SectionHeader("Startdatum")
                        DatePicker("Start", selection: $startAt, displayedComponents: [.date])
                            .datePickerStyle(.graphical)
                            .tint(palette.accent)
                            .colorScheme(.dark)

                        SectionHeader("Fällige Wochentage")
                        WeekdayPicker(selectedDays: $selectedDays, accentColor: palette.accent)

                        SectionHeader("Dauer und erlaubte Fails")
                        DurationFailsInputs(dauerInput: $dauerInput, failsInput: $failsInput)

                        SectionHeader("Freunde einladen")
                        Toggle(isOn: $inviteFriends.animation(.easeInOut)) {
                            Text(inviteFriends ? "Freunde auswählen" : "Keine Freunde einladen")
                                .foregroundColor(palette.textPrimary)
                                .font(.headline)
                        }
                        .tint(palette.accent)

                        if inviteFriends { inviteFriendsSection }

                        if let error {
                            Text(error)
                            .foregroundColor(palette.danger)
                                .font(.footnote)
                                .padding(.top, 5)
                        }

                        SubmitRow(
                            creating: creating,
                            onSubmit: { Task { await createChallenge() } },
                            accentColor: palette.accent
                        )
                        .padding(.top, 10)
                    }
                }
                .padding()
            }
        }
        .task { await loadFriends() }
    }

    // MARK: - Freunde Sektion
    @ViewBuilder
    private var inviteFriendsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            TextField("Nach Freunden suchen...", text: $searchQuery)
                .padding(10)
                .background(palette.surface)
                .cornerRadius(8)
                .foregroundColor(palette.textPrimary)

            ForEach(filteredFriends(), id: \.id) { friend in
                Button {
                    if selectedFriends.contains(where: { $0.id == friend.id }) {
                        selectedFriends.removeAll { $0.id == friend.id }
                    } else {
                        selectedFriends.append(friend)
                    }
                } label: {
                    HStack {
                        Text(friend.name)
                            .foregroundColor(palette.textPrimary)
                        Spacer()
                        Text(selectedFriends.contains(where: { $0.id == friend.id }) ? "Angefragt" : "Einladen")
                            .foregroundColor(selectedFriends.contains(where: { $0.id == friend.id }) ? palette.success : palette.accent)
                            .font(.caption.bold())
                    }
                }
                .padding()
                .background(palette.surface.opacity(0.8))
                .cornerRadius(8)
            }
        }
    }

    // MARK: - Freunde Logik
    private func loadFriends() async {
        do {
            friends = try await Api_Friends.listFriends()
        } catch {
            print("⚠️ Fehler beim Laden der Freunde:", error.localizedDescription)
        }
    }

    private func filteredFriends() -> [User] {
        guard !searchQuery.isEmpty else { return friends }
        return friends.filter { $0.name.lowercased().contains(searchQuery.lowercased()) }
    }

    // MARK: - Challenge erstellen
    @MainActor
    private func createChallenge() async {
        error = nil
        guard !selectedDays.isEmpty else {
            error = "Bitte wähle mindestens einen Tag aus."
            return
        }

        let dauerTage = Int(dauerInput.trimmingCharacters(in: .whitespaces)) ?? 30
        let erlaubteFailsTage = Int(failsInput.trimmingCharacters(in: .whitespaces)) ?? 3

        creating = true
        defer { creating = false }

        do {
            // Challenge erstellen
            let newChallenge: ChallengeResponse = try await Api_Challenge.createChallenge(
                name: nameField.isEmpty ? "Ohne Titel" : nameField,
                daysOfWeek: selectedDays,
                startAt: Int64(startAt.timeIntervalSince1970 * 1000),
                beschreibung: nil,
                friendsToAdd: [],
                dauerTage: dauerTage,
                erlaubteFailsTage: erlaubteFailsTage
            )

            let challengeId = newChallenge.id
            if DEBUG_INVITES {
                print("✅ Neue Challenge erstellt: ID = \(challengeId), Name = \(newChallenge.name ?? "Unbenannt")")
            }

            // Freunde einladen
            for friend in selectedFriends {
                if DEBUG_INVITES {
                    print("📨 Sende Invite an \(friend.name) [ID \(friend.id)] für Challenge \(challengeId)")
                }

                do {
                    try await Api_Challenge.sendChallengeInvite(
                        challengeId: challengeId,
                        toUserId: friend.id,
                        message: "Ich habe dich zu meiner Challenge eingeladen!"
                    )
                    if DEBUG_INVITES {
                        print("✅ Einladung an \(friend.name) erfolgreich gesendet.")
                    }
                } catch {
                    print("❌ Einladung an \(friend.name) fehlgeschlagen: \(error.localizedDescription)")
                }
            }

            await onCreation()
            dismiss()
        } catch {
            if DEBUG_INVITES {
                print("❌ Fehler beim Erstellen der Challenge:", error.localizedDescription)
            }
            self.error = error.localizedDescription
        }
    }
}

// MARK: - Kleine Hilfs-Views
private struct TitleHeader: View {
    let text: String
    let accentColor: Color
    var body: some View {
        Text(text)
            .font(.system(size: 40, weight: .heavy))
            .foregroundColor(.white)
            .shadow(color: accentColor.opacity(1.0), radius: 8)
            .padding(.top, 20)
    }
}

private struct SectionHeader: View {
    let title: String
    init(_ title: String) { self.title = title }
    @EnvironmentObject private var theme: ThemeManager
    private var palette: Theme { theme.theme }
    var body: some View {
        Text(title)
            .font(.subheadline.bold())
            .foregroundColor(palette.textSecondary)
            .padding(.top, 10)
    }
}

private struct WeekdayPicker: View {
    @Binding var selectedDays: [Int]
    let accentColor: Color
    private let labels = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

    var body: some View {
        HStack {
            ForEach(0..<7, id: \.self) { i in
                Button(action: { toggle(i) }) {
                    Text(labels[i])
                        .font(.caption.bold())
                        .frame(width: 38, height: 38)
                        .background(selectedDays.contains(i) ? accentColor : .gray.opacity(0.3))
                        .foregroundColor(.white)
                        .clipShape(Circle())
                }
            }
        }
    }

    private func toggle(_ day: Int) {
        if selectedDays.contains(day) {
            selectedDays.removeAll { $0 == day }
        } else {
            selectedDays.append(day)
        }
    }
}

private struct DurationFailsInputs: View {
    @Binding var dauerInput: String
    @Binding var failsInput: String
    @EnvironmentObject private var theme: ThemeManager
    private var palette: Theme { theme.theme }
    var body: some View {
        HStack(spacing: 12) {
            TextField("Dauer (Tage)", text: $dauerInput)
                .padding()
                .background(palette.surface)
                .cornerRadius(8)
                .foregroundColor(palette.textPrimary)
            TextField("Erlaubte Fails", text: $failsInput)
                .padding()
                .background(palette.surface)
                .cornerRadius(8)
                .foregroundColor(palette.textPrimary)
        }
    }
}

private struct SubmitRow: View {
    let creating: Bool
    let onSubmit: () -> Void
    let accentColor: Color

    var body: some View {
        Button(action: onSubmit) {
            HStack {
                if creating { ProgressView().tint(.white) }
                Text(creating ? "Wird erstellt..." : "Challenge starten")
                    .bold()
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(Capsule().fill(accentColor))
            .foregroundColor(.white)
        }
        .disabled(creating)
    }
}
