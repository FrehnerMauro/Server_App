import SwiftUI
import PhotosUI

struct SettingsView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager
    @Environment(\.dismiss) private var dismiss

    @State private var displayName: String = ""
    @State private var password: String = ""
    @State private var avatar: UIImage?
    @State private var selectedItem: PhotosPickerItem?
    @State private var accentSelection: Color = ThemePreset.ocean.accent

    @State private var loading = false
    @State private var info: String?
    @State private var error: String?
    @State private var showingDeleteConfirm = false
    @State private var showingBlocked = false

    private var palette: Theme { theme.theme }
    private var Api_Settings: api_settings { app.Api_Settings }

    private let privacyURL = URL(string: "https://socialhabit.org/privacy.html")!
    private let termsURL = URL(string: "https://socialhabit.org/termes_of_use.html")!

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    avatarSection
                    themeSection
                    nameSection
                    passwordSection
                    privacySection
                    actionsSection

                    if let info = info {
                        Text(info)
                            .foregroundColor(palette.success)
                            .font(.footnote.bold())
                            .padding(.top, 8)
                            .transition(.opacity)
                    }

                    if let error = error {
                        Text("🚨 \(error)")
                            .foregroundColor(palette.danger)
                            .font(.footnote.bold())
                            .padding(.top, 8)
                            .transition(.opacity)
                    }
                }
                .padding()
                .padding(.bottom, 50)
            }
            .navigationTitle("Einstellungen")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarBackground(palette.background, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
        }
        .appBackground()
        .onAppear {
            displayName = app.meSettings?.display_name ?? ""
            accentSelection = palette.accent
        }
        .onChange(of: theme.theme) { _ in
            accentSelection = palette.accent
        }
        .onChange(of: selectedItem) { item in
            Task {
                if let data = try? await item?.loadTransferable(type: Data.self),
                   let ui = UIImage(data: data) {
                    avatar = ui
                }
            }
        }
        .sheet(isPresented: $showingBlocked) {
            NavigationStack {
                BlockedUsersView()
                    .environmentObject(app)
            }
            .presentationDetents([.medium, .large])
        }
        .alert("Profil wirklich löschen?", isPresented: $showingDeleteConfirm) {
            Button("Abbrechen", role: .cancel) {}
            Button("Löschen", role: .destructive) {
                Task { await deleteAccount() }
            }
        }
    }

    private var avatarSection: some View {
        SettingsSection(title: "Profilbild") {
            VStack(spacing: 10) {
                avatarDisplay
                    .frame(width: 110, height: 110)
                    .clipShape(Circle())
                    .shadow(color: palette.accent.opacity(0.8), radius: 10)

                PhotosPicker(selection: $selectedItem, matching: .images) {
                    Text("Neues Bild auswählen")
                        .font(.footnote.bold())
                        .foregroundColor(palette.accent)
                }

                Button {
                    Task { await updateAvatar() }
                } label: {
                    HStack {
                        if loading { ProgressView() }
                        Text("Avatar speichern").bold()
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(palette.accent)
                .foregroundColor(.black)
                .disabled(loading || avatar == nil)
            }
        }
    }

    private var themeSection: some View {
        SettingsSection(title: "Design & Farben") {
            VStack(alignment: .leading, spacing: 12) {
                Text("Akzentfarbe")
                    .font(.subheadline)
                    .foregroundColor(palette.textSecondary)

                ColorPicker("Akzentfarbe", selection: $accentSelection, supportsOpacity: false)
                    .labelsHidden()
                    .onChange(of: accentSelection) { newValue in
                        theme.setCustomAccent(newValue)
                    }

                if theme.usesCustomAccent {
                    Button {
                        theme.selectPreset(theme.currentPreset)
                        accentSelection = palette.accent
                    } label: {
                        Label("Zurück zum Preset", systemImage: "arrow.uturn.backward")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                    .tint(palette.textSecondary)
                }

                Text("Voreinstellungen")
                    .font(.subheadline)
                    .foregroundColor(palette.textSecondary)

                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                    ForEach(ThemePreset.allCases) { preset in
                        Button {
                            theme.selectPreset(preset)
                            accentSelection = palette.accent
                        } label: {
                            ThemePresetChip(preset: preset, isSelected: !theme.usesCustomAccent && theme.currentPreset == preset)
                        }
                    }
                }
            }
        }
    }

    private var nameSection: some View {
        SettingsSection(title: "Name ändern") {
            VStack(spacing: 10) {
                DarkField(title: "Anzeigename", text: $displayName)

                Button {
                    Task { await updateName() }
                } label: {
                    HStack {
                        if loading { ProgressView() }
                        Text("Namen speichern").bold()
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(palette.accent)
                .foregroundColor(.black)
                .disabled(loading)
            }
        }
    }

    private var passwordSection: some View {
        SettingsSection(title: "Passwort ändern") {
            VStack(spacing: 10) {
                DarkField(title: "Neues Passwort", text: $password, isSecure: true)

                Button {
                    Task { await updatePassword() }
                } label: {
                    HStack {
                        if loading { ProgressView() }
                        Text("Passwort speichern").bold()
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(palette.accent)
                .foregroundColor(.black)
                .disabled(loading || password.isEmpty)
            }
        }
    }

    private var privacySection: some View {
        SettingsSection(title: "Datenschutz & Blockierungen") {
            Button {
                UIApplication.shared.open(privacyURL)
            } label: {
                SettingsLinkRow(title: "Datenschutzerklärung", iconName: "lock.shield", tint: .purple)
            }

            Button {
                UIApplication.shared.open(termsURL)
            } label: {
                SettingsLinkRow(title: "AGB", iconName: "doc.text", tint: .blue)
            }

            Button {
                showingBlocked = true
            } label: {
                SettingsLinkRow(title: "Blockierte Benutzer", iconName: "person.fill.xmark", tint: .red)
            }
        }
    }

    private var actionsSection: some View {
        SettingsSection(title: "Aktionen") {
            Button {
                Task { await logout() }
            } label: {
                SettingsLinkRow(title: "Abmelden", iconName: "arrow.right.circle", tint: .orange, showChevron: false)
            }
            .buttonStyle(.plain)

            Button(role: .destructive) {
                showingDeleteConfirm = true
            } label: {
                SettingsLinkRow(title: "Profil löschen", iconName: "trash", tint: .red, showChevron: false)
            }
            .buttonStyle(.plain)
        }
    }

    @ViewBuilder
    private var avatarDisplay: some View {
        if let avatar = avatar {
            Image(uiImage: avatar).resizable().scaledToFill()
        } else if let url = app.meSettings?.avatar_url, let u = URL(string: url) {
            AsyncImage(url: u) { phase in
                switch phase {
                case .success(let img): img.resizable().scaledToFill()
                default: Color.white.opacity(0.2)
                }
            }
        } else {
            Circle()
                .fill(palette.accent.opacity(0.2))
                .overlay(
                    Text(initials(from: app.meSettings?.display_name ?? "ME"))
                        .font(.title2.bold())
                        .foregroundColor(palette.textPrimary)
                )
        }
    }

    private func updateAvatar() async {
        guard let img = avatar, let jpeg = img.jpegData(compressionQuality: 0.8) else { return }
        loading = true; defer { loading = false }

        do {
            let url = app.Api.baseURL.appendingPathComponent("settings/me/avatar")
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            let boundary = "Boundary-\(UUID().uuidString)"
            req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
            if let token = app.token {
                req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }
            req.httpBody = app.Api.makeMultipartBody(
                boundary: boundary,
                fileField: "file",
                filename: "avatar.jpg",
                mime: "image/jpeg",
                data: jpeg
            )

            let (_, resp) = try await URLSession.shared.data(for: req)
            if let http = resp as? HTTPURLResponse, (200...299).contains(http.statusCode) {
                info = "Avatar erfolgreich aktualisiert."
            } else {
                throw APIError(message: "Avatar konnte nicht hochgeladen werden.")
            }
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func updateName() async {
        loading = true; defer { loading = false }
        do {
            let user = try await Api_Settings.updateMe(displayName: displayName, password: nil)
            app.meSettings = SettingsUser(
                id: user.id,
                display_name: user.display_name,
                avatar_url: user.avatar_url,
                email: user.email
            )
            info = "Name erfolgreich geändert."
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func updatePassword() async {
        loading = true; defer { loading = false }
        do {
            _ = try await Api_Settings.updateMe(displayName: nil, password: password)
            password = ""
            info = "Passwort erfolgreich geändert."
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func logout() async {
        do {
            try await Api_Settings.logout()
            await MainActor.run {
                app.logout()
                dismiss()
            }
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func deleteAccount() async {
        do {
            try await Api_Settings.deleteProfile()
            await MainActor.run {
                app.logout()
                dismiss()
            }
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func initials(from name: String) -> String {
        let parts = name.split(separator: " ")
        return parts.prefix(2).map { $0.prefix(1).uppercased() }.joined()
    }
}

struct SettingsSection<Content: View>: View {
    @EnvironmentObject private var theme: ThemeManager
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.headline)
                .foregroundColor(theme.theme.textSecondary)

            SurfaceContainer {
                VStack(alignment: .leading, spacing: 12) {
                    content
                }
            }
        }
    }
}

struct DarkField: View {
    @EnvironmentObject private var theme: ThemeManager
    let title: String
    @Binding var text: String
    var isSecure: Bool = false
    var isDisabled: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title)
                .font(.caption)
                .foregroundColor(theme.theme.textSecondary)
            Group {
                if isSecure {
                    SecureField("••••••", text: $text)
                } else {
                    TextField(title, text: $text)
                }
            }
            .padding(10)
            .background(RoundedRectangle(cornerRadius: 8).fill(Color.white.opacity(0.95)))
            .foregroundColor(.black)
            .disabled(isDisabled)
        }
    }
}

struct SettingsLinkRow: View {
    @EnvironmentObject private var theme: ThemeManager
    let title: String
    let iconName: String
    let tint: Color
    var showChevron: Bool = true

    var body: some View {
        HStack {
            Image(systemName: iconName)
                .foregroundColor(tint)
            Text(title)
                .foregroundColor(theme.theme.textPrimary)
            Spacer()
            if showChevron {
                Image(systemName: "chevron.right")
                    .foregroundColor(theme.theme.textSecondary)
            }
        }
        .contentShape(Rectangle())
    }
}

struct ThemePresetChip: View {
    let preset: ThemePreset
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 10) {
            Circle().fill(preset.accent)
                .frame(width: 24, height: 24)
            Text(preset.displayName)
                .font(.subheadline.weight(.semibold))
            Spacer()
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 12)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.white.opacity(0.06))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(isSelected ? preset.accent : Color.white.opacity(0.08), lineWidth: 1.5)
                )
        )
    }
}
