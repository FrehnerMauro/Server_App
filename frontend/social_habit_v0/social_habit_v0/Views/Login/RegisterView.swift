import SwiftUI

struct RegisterView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager
    @Environment(\.dismiss) private var dismiss

    @State private var vorname = ""
    @State private var nachname = ""
    @State private var email = ""
    @State private var password = ""

    @State private var acceptedTerms = false
    @State private var showTermsSheet = false

    @State private var loading = false
    @State private var error: String?
    @FocusState private var focusedField: Field?

    enum Field {
        case vorname, nachname, email, password
    }

    private var palette: Theme { theme.theme }

    var body: some View {
        ScrollView {
            VStack(spacing: 35) {
                VStack(spacing: 8) {
                    Text("Konto erstellen")
                        .font(.system(size: 32, weight: .bold, design: .rounded))
                        .foregroundColor(palette.accent)
                        .shadow(color: palette.accent.opacity(0.7), radius: 12)
                    Text("Starte jetzt mit deiner ersten Challenge 🚀")
                        .foregroundColor(palette.textSecondary)
                        .font(.headline)
                }
                .padding(.top, 60)

                SurfaceContainer {
                    VStack(spacing: 18) {
                        RegisterField(title: "Vorname", text: $vorname, icon: "person.fill", focused: $focusedField, fieldType: .vorname, accent: palette.accent)
                        RegisterField(title: "Nachname", text: $nachname, icon: "person.text.rectangle", focused: $focusedField, fieldType: .nachname, accent: palette.accent)
                        RegisterField(title: "E-Mail", text: $email, icon: "envelope.fill", focused: $focusedField, fieldType: .email, accent: palette.accent)
                        RegisterField(title: "Passwort", text: $password, icon: "lock.fill", isSecure: true, focused: $focusedField, fieldType: .password, accent: palette.accent)
                    }
                }

                HStack(alignment: .top, spacing: 10) {
                    Button { acceptedTerms.toggle() } label: {
                        Image(systemName: acceptedTerms ? "checkmark.square.fill" : "square")
                            .foregroundColor(palette.accent)
                            .font(.title3)
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Ich habe die")
                            .foregroundColor(palette.textSecondary)
                        Button("Nutzungsbedingungen gelesen und akzeptiere sie.") {
                            showTermsSheet = true
                        }
                        .foregroundColor(palette.accent)
                        .underline()
                        .font(.callout.bold())
                    }
                }
                .padding(.horizontal, 24)

                Button {
                    Task { await doRegister() }
                } label: {
                    HStack {
                        if loading { ProgressView().tint(.black) }
                        else {
                            Image(systemName: "checkmark.circle.fill")
                                .font(.title2)
                            Text("Registrieren & Loslegen").fontWeight(.bold)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(acceptedTerms ? palette.accentGradient : LinearGradient(colors: [.gray], startPoint: .topLeading, endPoint: .bottomTrailing))
                    .foregroundColor(.black)
                    .cornerRadius(14)
                    .shadow(color: acceptedTerms ? palette.accent.opacity(0.6) : .clear, radius: 12, x: 0, y: 6)
                }
                .disabled(loading || !acceptedTerms)
                .padding(.horizontal, 24)

                if let error = error {
                    Text("🚨 \(error)")
                        .foregroundColor(palette.danger)
                        .font(.footnote)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                }

                VStack(spacing: 6) {
                    Text("Bereits registriert?")
                        .foregroundColor(palette.textSecondary)
                    Button { dismiss() } label: {
                        Text("Zum Login")
                            .foregroundColor(palette.accent)
                            .fontWeight(.semibold)
                            .underline()
                    }
                }
                .padding(.bottom, 40)
            }
            .padding(.horizontal)
        }
        .appBackground()
        .sheet(isPresented: $showTermsSheet) {
            TermsSheet(accepted: $acceptedTerms)
                .environmentObject(theme)
        }
    }

    private func doRegister() async {
        guard !vorname.isEmpty, !nachname.isEmpty, !email.isEmpty, !password.isEmpty else {
            error = "Bitte alle Felder ausfüllen."
            return
        }
        guard acceptedTerms else {
            error = "Bitte akzeptiere die AGB."
            return
        }

        loading = true
        error = nil
        defer { loading = false }

        do {
            _ = try await app.Api_Login_Register.register(
                vorname: vorname,
                name: nachname,
                email: email,
                passwort: password,
                nb_state: "accepted"
            )

            let login = try await app.Api_Login_Register.login(email: email, passwort: password)

            await MainActor.run {
                app.token = login.token
                app.me = login.user
            }

        } catch {
            self.error = "Registrierung oder Login fehlgeschlagen. Bitte überprüfe deine Eingaben."
        }
    }
}

struct TermsSheet: View {
    @Binding var accepted: Bool
    @EnvironmentObject var theme: ThemeManager
    @Environment(\.dismiss) private var dismiss

    private var palette: Theme { theme.theme }

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 15) {
                    Text("Nutzungsbedingungen")
                        .font(.title.bold())
                        .foregroundColor(palette.accent)
                        .padding(.bottom, 10)

                    Text("""
                    Willkommen bei Social Habit!

                    Mit der Nutzung dieser App erklärst du dich einverstanden, dass:

                    • Du keine beleidigenden, diskriminierenden oder illegalen Inhalte postest.
                    • Du deine Daten freiwillig teilst.
                    • Wir die App-Funktionen verbessern und Statistiken anonymisiert auswerten dürfen.
                    • Du die Verantwortung für deine eigenen Challenges trägst.

                    Wenn du diese Bedingungen nicht akzeptierst, kannst du Social Habit leider nicht verwenden.
                    """)
                    .foregroundColor(palette.textSecondary)
                    .padding(.bottom, 30)

                    Button {
                        accepted = true
                        dismiss()
                    } label: {
                        Text("Ich akzeptiere die Nutzungsbedingungen")
                            .bold()
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(palette.accentGradient)
                            .foregroundColor(.black)
                            .cornerRadius(12)
                    }
                }
                .padding()
            }
            .background(palette.backgroundGradient.ignoresSafeArea())
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

struct RegisterField: View {
    let title: String
    @Binding var text: String
    let icon: String
    var isSecure: Bool = false
    @FocusState.Binding var focused: RegisterView.Field?
    var fieldType: RegisterView.Field
    let accent: Color

    var body: some View {
        HStack {
            Image(systemName: icon)
                .foregroundColor(accent)
                .font(.title3)
                .frame(width: 28)

            Group {
                if isSecure {
                    SecureField(title, text: $text)
                        .textContentType(.password)
                        .focused($focused, equals: fieldType)
                } else {
                    TextField(title, text: $text)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled(true)
                        .focused($focused, equals: fieldType)
                }
            }
            .foregroundColor(.white)
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.white.opacity(0.06))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(accent.opacity(focused == fieldType ? 0.85 : 0.35), lineWidth: 1.5)
                )
        )
        .shadow(color: focused == fieldType ? accent.opacity(0.45) : .clear, radius: 8, x: 0, y: 4)
    }
}

#Preview {
    RegisterView()
        .environmentObject(AppState())
        .environmentObject(ThemeManager())
}
