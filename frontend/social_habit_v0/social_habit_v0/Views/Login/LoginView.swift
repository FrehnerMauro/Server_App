import SwiftUI

struct LoginView: View {
    @EnvironmentObject var app: AppState
    @EnvironmentObject var theme: ThemeManager

    @State private var email: String = ""
    @State private var password: String = ""
    @State private var loading = false
    @State private var error: String?
    @State private var info: String?
    @State private var showRegister = false
    @FocusState private var focusedField: Field?

    enum Field {
        case email, password
    }

    private var palette: Theme { theme.theme }

    var body: some View {
        VStack(spacing: 35) {
            VStack(spacing: 8) {
                Text("SteadyTurtle")
                    .font(.system(size: 36, weight: .bold, design: .rounded))
                    .foregroundColor(palette.accent)
                    .shadow(color: palette.accent.opacity(0.7), radius: 12)
                Text("Willkommen zurück 👋")
                    .foregroundColor(palette.textSecondary)
                    .font(.headline)
            }
            .padding(.top, 60)

            SurfaceContainer {
                VStack(spacing: 16) {
                    LoginField(
                        title: "E-Mail",
                        text: $email,
                        icon: "envelope.fill",
                        isSecure: false,
                        focused: $focusedField,
                        fieldType: .email,
                        accent: palette.accent
                    )

                    LoginField(
                        title: "Passwort",
                        text: $password,
                        icon: "lock.fill",
                        isSecure: true,
                        focused: $focusedField,
                        fieldType: .password,
                        accent: palette.accent
                    )
                }
            }

            Button {
                Task { await doLogin() }
            } label: {
                HStack {
                    if loading {
                        ProgressView().tint(.black)
                    } else {
                        Image(systemName: "arrow.right.circle.fill")
                            .font(.title2)
                        Text("Einloggen").fontWeight(.bold)
                    }
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(palette.accentGradient)
                .foregroundColor(.black)
                .cornerRadius(14)
                .shadow(color: palette.accent.opacity(0.6), radius: 10, x: 0, y: 6)
            }
            .disabled(loading)
            .padding(.horizontal, 24)

            if let error = error {
                Text("🚨 \(error)")
                    .foregroundColor(palette.danger)
                    .font(.footnote)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
                    .transition(.opacity)
            }

            if let info = info {
                Text("✅ \(info)")
                    .foregroundColor(palette.success)
                    .font(.footnote)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
                    .transition(.opacity)
            }

            Spacer()

            VStack(spacing: 6) {
                Text("Noch kein Konto?")
                    .foregroundColor(palette.textSecondary)
                Button {
                    showRegister = true
                } label: {
                    Text("Jetzt registrieren")
                        .foregroundColor(palette.accent)
                        .fontWeight(.semibold)
                        .underline()
                }
            }
            .padding(.bottom, 40)
        }
        .padding(.horizontal)
        .appBackground()
        .sheet(isPresented: $showRegister) {
            RegisterView()
                .environmentObject(app)
                .environmentObject(theme)
        }
    }

    private func doLogin() async {
        guard !email.isEmpty, !password.isEmpty else {
            error = "Bitte E-Mail und Passwort eingeben."
            return
        }

        loading = true
        error = nil
        info = nil
        defer { loading = false }

        do {
            try await app.loginAndBootstrap(email: email, passwort: password)
            await MainActor.run {
                info = "Login erfolgreich!"
            }
        } catch {
            await MainActor.run {
                self.error = "Login fehlgeschlagen. Bitte überprüfe deine Daten."
            }
        }
    }
}

struct LoginField: View {
    let title: String
    @Binding var text: String
    let icon: String
    var isSecure: Bool
    @FocusState.Binding var focused: LoginView.Field?
    var fieldType: LoginView.Field
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
                        .keyboardType(.emailAddress)
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
    LoginView()
        .environmentObject(AppState())
        .environmentObject(ThemeManager())
}
