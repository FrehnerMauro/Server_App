//
//  ChallengeInfoView.swift
//  social_habit_v0
//
//  Created by Mauro Frehner on 12.10.2025.
//

import SwiftUI

struct ChallengeInfoView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager
    let challengeId: Int

    @State private var info: ChallengeInfoResponse?
    @State private var error: String?
    @State private var isLoading = false
    @State private var showAlert = false
    @State private var alertMessage = ""

    private var palette: Theme { theme.theme }

    var body: some View {
        ZStack {
            palette.backgroundGradient
                .ignoresSafeArea()

            if isLoading {
                ProgressView("Lade Challenge...")
                    .tint(palette.accent)
                    .font(.headline)
            } else if let error {
                VStack {
                    Text("⚠️ Fehler")
                        .font(.title.bold())
                        .foregroundColor(palette.danger)
                    Text(error)
                        .foregroundColor(palette.textSecondary)
                        .multilineTextAlignment(.center)
                        .padding()
                    Button("Erneut versuchen") {
                        Task { await loadInfo() }
                    }
                    .padding()
                    .background(palette.accent)
                    .foregroundColor(palette.textPrimary)
                    .clipShape(Capsule())
                }
                .padding()
            } else if let info {
                ScrollView {
                    VStack(spacing: 25) {
                        challengeHeader(info.challenge)
                        membersSection(info.members)
                    }
                    .padding(.horizontal)
                    .padding(.bottom, 50)
                }
                .refreshable { await loadInfo() }
            }
        }
        .navigationTitle("Challenge Info")
        .navigationBarTitleDisplayMode(.inline)
        .task { await loadInfo() }
        .alert(isPresented: $showAlert) {
            Alert(title: Text("Challenge Info"),
                  message: Text(alertMessage),
                  dismissButton: .default(Text("OK")))
        }
    }

    // MARK: - Challenge Header (vollständige Anzeige)
    private func challengeHeader(_ ch: ChallengeInfoResponse.ChallengeInfo) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            // Titelzeile mit Menü
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(ch.title ?? "Unbenannte Challenge")
                        .font(.title2.bold())
                        .foregroundColor(palette.textPrimary)

                    if let desc = ch.description, !desc.isEmpty {
                        Text(desc)
                            .foregroundColor(palette.textSecondary)
                            .font(.body)
                    }
                }

                Spacer()

                Menu {
                    Button("Challenge melden") {
                        Task { await reportChallenge(ch.id) }
                    }
                    Button("Challenge verlassen", role: .destructive) {
                        Task { await leaveChallenge(ch.id) }
                    }
                } label: {
                    Image(systemName: "ellipsis")
                        .foregroundColor(palette.accent)
                        .font(.title2.bold())
                }
            }

            Divider().background(palette.accent.opacity(0.4))

            // Detailinfos
            VStack(alignment: .leading, spacing: 8) {
                infoRow(label: "Ersteller-ID", value: "\(ch.creator_id)")
                if let start = ch.start_at {
                    infoRow(label: "Startdatum", value: formatTs(Double(start)))
                }
                if let dur = ch.duration_days {
                    infoRow(label: "Dauer (Tage)", value: "\(dur)")
                }
                if let fails = ch.allowed_fails {
                    infoRow(label: "Erlaubte Fails", value: "\(fails)")
                }
                if let weekdays = ch.due_weekdays, !weekdays.isEmpty {
                    let readable = readableWeekdays(from: weekdays)
                    infoRow(label: "Fällige Wochentage", value: readable)
                }
                if let created = ch.created_at {
                    infoRow(label: "Erstellt am", value: formatTs(Double(created)))
                }
                if let updated = ch.updated_at {
                    infoRow(label: "Aktualisiert am", value: formatTs(Double(updated)))
                }
            }
            .padding(.top, 4)
            .font(.callout)
            .foregroundColor(.white.opacity(0.8))
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 18)
                .fill(Color.black.opacity(0.3))
                .overlay(
                    RoundedRectangle(cornerRadius: 18)
                        .stroke(palette.accent.opacity(0.5), lineWidth: 1.2)
                )
                .shadow(color: palette.accent.opacity(0.3), radius: 10, x: 0, y: 5)
        )
        .padding(.top, 10)
    }

    // MARK: - Info-Row Helper
    private func infoRow(label: String, value: String) -> some View {
        HStack(alignment: .top) {
            Text(label + ":")
                .foregroundColor(palette.textSecondary)
            Spacer()
            Text(value)
                .foregroundColor(palette.textPrimary)
                .multilineTextAlignment(.trailing)
        }
    }

    // MARK: - Mitgliederliste
    private func membersSection(_ members: [ChallengeInfoResponse.ChallengeMemberInfo]) -> some View {
        VStack(alignment: .leading, spacing: 15) {
            Text("Mitglieder (\(members.count))")
                .font(.headline.bold())
                .foregroundColor(palette.textPrimary)
                .padding(.leading, 4)

            ForEach(members) { m in
                HStack(spacing: 15) {
                    memberAvatar(m)
                    
                    VStack(alignment: .leading, spacing: 3) {
                        Text(m.display_name)
                            .font(.subheadline.bold())
                            .foregroundColor(palette.textPrimary)
                        if let joined = m.joined_at {
                            Text(formatTs(Double(joined)))
                                .font(.caption)
                                .foregroundColor(palette.textSecondary)
                        }
                    }

                    Spacer()
                }
                .padding(10)
                .background(Color.white.opacity(0.05))
                .cornerRadius(10)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 20)
                .fill(Color.black.opacity(0.3))
        )
    }

    // MARK: - Aktionen
    private func loadInfo() async {
        isLoading = true
        error = nil
        do {
            let data = try await app.Api_Challenge.getChallengeInfo(challengeId)
            await MainActor.run { self.info = data }
        } catch {
            await MainActor.run { self.error = error.localizedDescription }
        }
        isLoading = false
    }

    private func reportChallenge(_ id: Int) async {
        do {
            let ok = try await app.Api_Report.createReport(challengeId: id, reason: "Unangemessener Inhalt")
            await MainActor.run {
                alertMessage = ok ? "Challenge erfolgreich gemeldet." : "Fehler beim Melden der Challenge."
                showAlert = true
            }
        } catch {
            await MainActor.run {
                alertMessage = "Fehler beim Melden: \(error.localizedDescription)"
                showAlert = true
            }
        }
    }

    private func leaveChallenge(_ id: Int) async {
        do {
            try await app.Api_Challenge.leaveChallenge(id)
            await MainActor.run {
                alertMessage = "Du hast die Challenge erfolgreich verlassen."
                showAlert = true
            }
        } catch let error as APIError {
            await MainActor.run {
                alertMessage = error.message
                showAlert = true
            }
        } catch {
            await MainActor.run {
                alertMessage = "Unbekannter Fehler beim Verlassen der Challenge."
                showAlert = true
            }
        }
    }

    // MARK: - Helper
    private func memberAvatar(_ member: ChallengeInfoResponse.ChallengeMemberInfo) -> some View {
        if let avatar = member.avatar_url, !avatar.isEmpty {
            return AnyView(
                RemoteOrDataURLImage(urlString: avatar)
                    .frame(width: 50, height: 50)
                    .clipShape(Circle())
                    .overlay(Circle().stroke(palette.accent, lineWidth: 2))
            )
        } else {
            return AnyView(
                Circle()
                    .fill(palette.accent.opacity(0.25))
                    .overlay(
                        Text(initials(from: member.display_name))
                            .font(.headline.bold())
                                .foregroundColor(palette.textPrimary)
                    )
                    .frame(width: 50, height: 50)
                    .overlay(Circle().stroke(palette.accent, lineWidth: 2))
            )
        }
    }
    
    private func initials(from name: String) -> String {
        let parts = name.split(separator: " ")
        return parts.prefix(2).map { $0.prefix(1).uppercased() }.joined()
    }

    private func formatTs(_ ms: Double) -> String {
        let date = Date(timeIntervalSince1970: ms / 1000)
        let f = DateFormatter()
        f.dateStyle = .short
        f.timeStyle = .short
        return f.string(from: date)
    }

    private func readableWeekdays(from str: String) -> String {
        // Eingabe wie: "0,2,4" oder "[0,2,4]"
        let cleaned = str.replacingOccurrences(of: "[\\[\\]\\s]", with: "", options: .regularExpression)
        let nums = cleaned.split(separator: ",").compactMap { Int($0) }
        let names = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        let mapped = nums.compactMap { $0 < names.count ? names[$0] : nil }
        return mapped.isEmpty ? "-" : mapped.joined(separator: ", ")
    }
}
