import SwiftUI

struct Theme: Equatable {
    let name: String
    let accent: Color
    let accentStrong: Color
    let background: Color
    let backgroundSecondary: Color
    let surface: Color
    let surfaceMuted: Color
    let textPrimary: Color
    let textSecondary: Color
    let success: Color
    let warning: Color
    let danger: Color

    var backgroundGradient: LinearGradient {
        LinearGradient(colors: [background, backgroundSecondary], startPoint: .topLeading, endPoint: .bottomTrailing)
    }

    var accentGradient: LinearGradient {
        LinearGradient(colors: [accentStrong, accent], startPoint: .topLeading, endPoint: .bottomTrailing)
    }
}

enum ThemePreset: String, CaseIterable, Identifiable {
    case ocean
    case forest
    case sunset
    case graphite
    case blossom
    case amethyst

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .ocean: return "Ocean"
        case .forest: return "Forest"
        case .sunset: return "Sunset"
        case .graphite: return "Graphite"
        case .blossom: return "Blossom"
        case .amethyst: return "Amethyst"
        }
    }

    var accent: Color {
        switch self {
        case .ocean: return Color(red: 0.0, green: 0.78, blue: 1.0)
        case .forest: return Color(red: 0.0, green: 0.74, blue: 0.52)
        case .sunset: return Color(red: 1.0, green: 0.53, blue: 0.28)
        case .graphite: return Color(red: 0.78, green: 0.78, blue: 0.82)
        case .blossom: return Color(red: 0.91, green: 0.36, blue: 0.62)
        case .amethyst: return Color(red: 0.58, green: 0.46, blue: 0.96)
        }
    }
}

final class ThemeManager: ObservableObject {
    @Published private(set) var theme: Theme
    @Published private(set) var currentPreset: ThemePreset

    private let storage: ThemeStorage

    init(storage: ThemeStorage = .init()) {
        self.storage = storage
        let preset = storage.load()
        currentPreset = preset
        theme = ThemeFactory.make(accent: preset.accent, name: preset.displayName)
    }

    func selectPreset(_ preset: ThemePreset) {
        theme = ThemeFactory.make(accent: preset.accent, name: preset.displayName)
        currentPreset = preset
        storage.save(preset: preset)
    }
}

private enum ThemeFactory {
    static func make(accent: Color, name: String) -> Theme {
        let strong = accent.adjust(brightness: 1.1)
        let background = accent.adjust(saturation: 0.35, brightness: 0.25)
        let backgroundSecondary = accent.adjust(saturation: 0.45, brightness: 0.16)
        let surface = accent.adjust(saturation: 0.25, brightness: 0.28)
        let surfaceMuted = accent.adjust(saturation: 0.2, brightness: 0.32)

        return Theme(
            name: name,
            accent: accent,
            accentStrong: strong,
            background: background,
            backgroundSecondary: backgroundSecondary,
            surface: surface,
            surfaceMuted: surfaceMuted,
            textPrimary: .white,
            textSecondary: Color.white.opacity(0.8),
            success: Color.green.opacity(0.9),
            warning: Color.orange.opacity(0.9),
            danger: Color.red.opacity(0.9)
        )
    }
}

struct ThemeStorage {
    private let presetKey = "ui.theme.preset"
    private let legacyAccentKey = "ui.theme.accent"

    func load() -> ThemePreset {
        if UserDefaults.standard.object(forKey: legacyAccentKey) != nil {
            UserDefaults.standard.removeObject(forKey: legacyAccentKey)
        }

        return ThemePreset(rawValue: UserDefaults.standard.string(forKey: presetKey) ?? "") ?? .ocean
    }

    func save(preset: ThemePreset) {
        UserDefaults.standard.set(preset.rawValue, forKey: presetKey)
    }
}

struct AppBackground: ViewModifier {
    @EnvironmentObject private var theme: ThemeManager

    func body(content: Content) -> some View {
        ZStack {
            theme.theme.backgroundGradient.ignoresSafeArea()
            content
        }
    }
}

struct SurfaceContainer<Content: View>: View {
    @EnvironmentObject private var theme: ThemeManager
    let padding: CGFloat
    let content: Content

    init(padding: CGFloat = 16, @ViewBuilder content: () -> Content) {
        self.padding = padding
        self.content = content()
    }

    var body: some View {
        content
            .padding(padding)
            .background(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(theme.theme.surface.opacity(0.9))
                    .overlay(
                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                            .stroke(Color.white.opacity(0.08), lineWidth: 1)
                    )
            )
    }
}

extension View {
    func appBackground() -> some View { modifier(AppBackground()) }
}

extension Color {
    init?(hex: String) {
        var string = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        string = string.replacingOccurrences(of: "#", with: "")

        guard string.count == 6 || string.count == 8 else { return nil }

        var int: UInt64 = 0
        Scanner(string: string).scanHexInt64(&int)

        let a, r, g, b: UInt64
        if string.count == 8 {
            a = (int & 0xFF000000) >> 24
            r = (int & 0x00FF0000) >> 16
            g = (int & 0x0000FF00) >> 8
            b = (int & 0x000000FF)
        } else {
            a = 255
            r = (int & 0xFF0000) >> 16
            g = (int & 0x00FF00) >> 8
            b = int & 0x0000FF
        }

        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }

    var hexString: String? {
        let ui = UIColor(self)
        var r: CGFloat = 0
        var g: CGFloat = 0
        var b: CGFloat = 0
        var a: CGFloat = 0
        guard ui.getRed(&r, green: &g, blue: &b, alpha: &a) else { return nil }
        let ints = [r, g, b, a].map { Int(round($0 * 255)) }
        return String(format: "%02X%02X%02X%02X", ints[0], ints[1], ints[2], ints[3])
    }

    func adjust(saturation: CGFloat = 1.0, brightness: CGFloat = 1.0) -> Color {
        let ui = UIColor(self)
        var h: CGFloat = 0, s: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        guard ui.getHue(&h, saturation: &s, brightness: &b, alpha: &a) else { return self }

        let newS = min(max(s * saturation, 0), 1)
        let newB = min(max(b * brightness, 0), 1)
        return Color(hue: Double(h), saturation: Double(newS), brightness: Double(newB), opacity: Double(a))
    }
}
