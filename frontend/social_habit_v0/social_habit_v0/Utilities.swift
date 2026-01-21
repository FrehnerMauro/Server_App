//
//  Utilities.swift
//  SocialAppV0
//
//  Kompatibel ab iOS 16 (keine onChange(of:initial:) Nutzung)
//  Keine scharfen s verwendet.
//

import SwiftUI
import PhotosUI
import Combine

// MARK: - Kleine UI Helfer

struct GradientButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.vertical, 10).padding(.horizontal, 14)
            .background(
                LinearGradient(colors: [Color.accentColor, Color.accentColor.opacity(0.6)],
                               startPoint: .topLeading, endPoint: .bottomTrailing)
            )
            .foregroundColor(.white)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .opacity(configuration.isPressed ? 0.85 : 1)
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

struct OutlineCapsuleStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.vertical, 9).padding(.horizontal, 12)
            .background(.ultraThinMaterial)
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(Color.secondary.opacity(0.25), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .opacity(configuration.isPressed ? 0.85 : 1)
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

struct PrimaryButton: ButtonStyle { func makeBody(configuration: Configuration) -> some View { GradientButtonStyle().makeBody(configuration: configuration) } }
struct OutlineButton: ButtonStyle { func makeBody(configuration: Configuration) -> some View { OutlineCapsuleStyle().makeBody(configuration: configuration) } }

// MARK: - Data URL Image (data:image/jpeg;base64,...)

struct DataURLImage: View {
    let dataURL: String
    var contentMode: ContentMode = .fit
    var cornerRadius: CGFloat = 16
    var placeholderHeight: CGFloat? = 200

    @State private var uiImage: UIImage?

    var body: some View {
        Group {
            if let image = uiImage {
                imageView(image)
            } else {
                placeholder
                    .onAppear(perform: load)
            }
        }
    }

    @ViewBuilder
    private func imageView(_ image: UIImage) -> some View {
        let swiftUIImage = Image(uiImage: image)
            .resizable() // HIER drin, nicht draussen

        switch contentMode {
        case .fit:
            swiftUIImage
                .scaledToFit()
                .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
        case .fill:
            swiftUIImage
                .scaledToFill()
                .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
        @unknown default:
            swiftUIImage
                .scaledToFit()
                .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
        }
    }

    private var placeholder: some View {
        ZStack {
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                .fill(Color.gray.opacity(0.15))
            Image(systemName: "photo")
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .frame(height: placeholderHeight)
        .overlay(
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                .stroke(Color.black.opacity(0.05), lineWidth: 1)
        )
    }

    private func load() {
        if let cached = Self.cache.object(forKey: dataURL as NSString) {
            uiImage = cached
            return
        }
        if let img = decodeDataURL(dataURL) {
            Self.cache.setObject(img, forKey: dataURL as NSString)
            uiImage = img
        }
    }

    private static let cache = NSCache<NSString, UIImage>()

    private func decodeDataURL(_ url: String) -> UIImage? {
        guard let commaIndex = url.firstIndex(of: ",") else { return nil }
        let meta = url[..<commaIndex].lowercased()
        let base64Part = url[url.index(after: commaIndex)...]

        guard meta.contains("base64") else { return nil }

        let cleaned = base64Part
            .replacingOccurrences(of: "\r", with: "")
            .replacingOccurrences(of: "\n", with: "")
            .replacingOccurrences(of: " ", with: "")
            .replacingOccurrences(of: "\t", with: "")
            .replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")

        let rem = cleaned.count % 4
        let padded: String
        if rem == 0 {
            padded = cleaned
        } else {
            padded = cleaned + String(repeating: "=", count: 4 - rem)
        }

        guard let data = Data(base64Encoded: padded, options: [.ignoreUnknownCharacters]),
              let img = UIImage(data: data) else {
            return nil
        }
        return img
    }
}

// MARK: - Kleine Helfer

extension UIImage {
    /// JPEG -> data URL (fuer /confirm)
    func jpegDataURL(quality: CGFloat = 0.8) -> String? {
        guard let data = self.jpegData(compressionQuality: quality) else { return nil }
        return "data:image/jpeg;base64," + data.base64EncodedString()
    }
}

extension String {
    var trimmed: String { trimmingCharacters(in: .whitespacesAndNewlines) }
    var nilIfEmpty: String? { trimmed.isEmpty ? nil : trimmed }
}

struct CapsuleBadge: View {
    var text: String
    var body: some View {
        Text(text)
            .font(.caption)
            .padding(.horizontal, 10).padding(.vertical, 6)
            .background(Color.blue.opacity(0.15))
            .foregroundColor(.blue)
            .clipShape(Capsule())
    }
}

struct BellWithDot: View {
    var hasUnread: Bool
    var body: some View {
        ZStack(alignment: .topTrailing) {
            Image(systemName: "bell")
                .imageScale(.large)
            if hasUnread {
                Circle().fill(Color.red).frame(width: 9, height: 9)
                    .offset(x: 3, y: -3)
            }
        }
        .accessibilityLabel(hasUnread ? "Neue Benachrichtigungen" : "Keine Benachrichtigungen")
    }
}

// MARK: - Bild → DataURL Helper

func uiImageToJPEGDataURL(_ image: UIImage, quality: CGFloat = 0.85) -> String? {
    guard let data = image.jpegData(compressionQuality: quality) else { return nil }
    let b64 = data.base64EncodedString()
    return "data:image/jpeg;base64," + b64
}

func dataToUIImage(_ data: Data) -> UIImage? {
    UIImage(data: data)
}

// MARK: - ImagePicker (PhotosPicker ab iOS 16)

struct ImagePicker: UIViewControllerRepresentable {
    var sourceType: UIImagePickerController.SourceType = .photoLibrary
    let onImagePicked: (UIImage) -> Void
    
    @Environment(\.dismiss) private var dismiss
    
    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = sourceType
        picker.delegate = context.coordinator
        return picker
    }
    
    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}
    
    func makeCoordinator() -> Coordinator { Coordinator(self) }
    
    final class Coordinator: NSObject, UINavigationControllerDelegate, UIImagePickerControllerDelegate {
        let parent: ImagePicker
        init(_ parent: ImagePicker) { self.parent = parent }
        
        func imagePickerController(_ picker: UIImagePickerController,
                                   didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]) {
            if let img = info[.originalImage] as? UIImage {
                parent.onImagePicked(img)
            }
            parent.dismiss()
        }
        
        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            parent.dismiss()
        }
    }
}

struct ImagePickerButton: View {
    /// ausgewaehltes Bild (UIImage) fuer Preview
    @Binding var image: UIImage?
    /// fertig konvertierte DataURL (fuer API /challenges/{id}/confirm)
    @Binding var dataURL: String?
    /// optionaler Fehlertext
    @Binding var errorText: String?
    
    @State private var pickerItem: PhotosPickerItem?
    @State private var isLoading = false
    
    // Kamera
    @State private var showCamera = false
    @State private var cameraUnavailableReason: String?
    
    var title: String = "Foto wählen"
    var systemImage: String = "photo.on.rectangle"
    var jpegQuality: CGFloat = 0.85
    
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            // Aktion-Buttons
            HStack(spacing: 10) {
                // Galerie
                PhotosPicker(selection: $pickerItem, matching: .images, photoLibrary: .shared()) {
                    Label(title, systemImage: systemImage)
                        .font(.callout.weight(.semibold))
                        .padding(.horizontal, 12).padding(.vertical, 10)
                        .background(Color(.secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                }
                
                // Kamera
                Button {
                    openCamera()
                } label: {
                    Label("Foto aufnehmen", systemImage: "camera.fill")
                        .font(.callout.weight(.semibold))
                        .padding(.horizontal, 12).padding(.vertical, 10)
                        .background(Color(.secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                }
                .sheet(isPresented: $showCamera) {
                    ImagePicker(sourceType: .camera) { ui in
                        self.image = ui
                        self.dataURL = uiImageToJPEGDataURL(ui, quality: jpegQuality)
                    }
                }
            }
            // Reaktionen auf Picker-Auswahl (Galerie)
            .onChange(of: pickerItem) { newItem in
                guard let item = newItem else { return }
                loadImage(from: item)
            }
            
            if isLoading {
                ProgressView("Lädt Bild ...")
            }
            

            
            if let reason = cameraUnavailableReason {
                Text(reason).foregroundColor(.orange).font(.footnote)
            }
            
            if let err = errorText, !err.isEmpty {
                Text(err).foregroundColor(.red).font(.footnote)
            }
        }
    }
    
    private func openCamera() {
        #if targetEnvironment(simulator)
        cameraUnavailableReason = "Kamera ist im Simulator nicht verfuegbar."
        showCamera = false
        #else
        if UIImagePickerController.isSourceTypeAvailable(.camera) {
            cameraUnavailableReason = nil
            showCamera = true
        } else {
            cameraUnavailableReason = "Kamera ist nicht verfuegbar."
            showCamera = false
        }
        #endif
    }
    
    private func loadImage(from item: PhotosPickerItem) {
        isLoading = true
        errorText = nil
        
        Task {
            do {
                if let data = try await item.loadTransferable(type: Data.self),
                   let uiImg = UIImage(data: data) {
                    await MainActor.run {
                        self.image = uiImg
                        self.dataURL = uiImageToJPEGDataURL(uiImg, quality: jpegQuality)
                        self.isLoading = false
                    }
                } else {
                    await MainActor.run {
                        self.errorText = "Konnte Bilddaten nicht laden."
                        self.isLoading = false
                    }
                }
            } catch {
                await MainActor.run {
                    self.errorText = "Laden fehlgeschlagen: \(error.localizedDescription)"
                    self.isLoading = false
                }
            }
        }
    }
}

// MARK: - TextField Helper (onChange iOS16)

struct DebouncedTextField: View {
    @Binding var text: String
    var title: String
    var prompt: String = ""
    var debounce: TimeInterval = 0.35
    var onCommit: (String) -> Void
    
    @State private var internalText: String = ""
    @State private var debouncer: AnyCancellable?
    
    var body: some View {
        TextField(title, text: $internalText, prompt: Text(prompt))
            .textInputAutocapitalization(.none)
            .autocorrectionDisabled()
            .onAppear {
                internalText = text
            }
            .onChange(of: internalText) { newVal in
                text = newVal
                debouncer?.cancel()
                debouncer = Just(newVal)
                    .delay(for: .seconds(debounce), scheduler: RunLoop.main)
                    .sink { val in
                        onCommit(val)
                    }
            }
    }
}

// MARK: - AsyncButton (Loading Zustand)

struct AsyncButton<Label: View>: View {
    var action: () async throws -> Void
    @ViewBuilder var label: () -> Label
    
    @State private var isRunning = false
    @State private var localError: String?
    
    var body: some View {
        Button {
            Task {
                await run()
            }
        } label: {
            ZStack {
                label()
                    .opacity(isRunning ? 0 : 1)
                if isRunning {
                    ProgressView()
                }
            }
        }
        .disabled(isRunning)
        .alert("Fehler", isPresented: Binding(get: { localError != nil }, set: { _ in localError = nil })) {
            Button("OK", role: .cancel) { }
        } message: {
            Text(localError ?? "")
        }
    }
    
    @MainActor
    private func run() async {
        guard !isRunning else { return }
        isRunning = true
        defer { isRunning = false }
        do {
            try await action()
        } catch {
            localError = error.localizedDescription
        }
    }
}

// MARK: - Visuelles Wrapper Card

struct GlassCard<Content: View>: View {
    var title: String?
    @ViewBuilder var content: () -> Content
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let title {
                Text(title)
                    .font(.system(size: 25, weight: .bold))

                
                    .font(.headline)
                    .foregroundColor(.white)
                    
            }
            content()
        }
        .padding(16)

        
    }
}

// ======================================================================
// MARK: - Challenge / Date Utilities + UI Chips (NEU)
// ======================================================================

/// Aktueller TZ-Offset in Minuten (z. B. Europa/Zurich ~ 60/120)
func tzOffsetMinutesNow() -> Int {
    TimeZone.current.secondsFromGMT() / 60
}

/// Millisekunden (UTC) -> "YYYY-MM-DD" in lokaler Zeitzone (ueber tzOffsetMinutes)
func msToLocalYMD(_ ms: Int64, tzOffsetMinutes: Int) -> String {
    let secs = TimeInterval(ms) / 1000.0
    let tz = TimeZone(secondsFromGMT: tzOffsetMinutes * 60) ?? .current
    var cal = Calendar(identifier: .gregorian); cal.timeZone = tz
    let d = Date(timeIntervalSince1970: secs)
    return ymdFromDate(d, calendar: cal)
}

/// Datum -> "YYYY-MM-DD" (lokale TZ oder Custom Calendar)
func ymdFromDate(_ date: Date, calendar: Calendar = {
    var cal = Calendar(identifier: .gregorian)
    cal.timeZone = .current
    return cal
}()) -> String {
    let comps = calendar.dateComponents([.year, .month, .day], from: date)
    let y = comps.year ?? 1970, m = comps.month ?? 1, d = comps.day ?? 1
    return String(format: "%04d-%02d-%02d", y, m, d)
}

/// "YYYY-MM-DD" -> Wochentag So=0..Sa=6 (Backend-konform)
func weekdayIndexFromYMD(_ ymd: String, tz: TimeZone = .current) -> Int {
    let parts = ymd.split(separator: "-").compactMap { Int($0) }
    guard parts.count == 3 else { return 0 }
    var cal = Calendar(identifier: .gregorian); cal.timeZone = tz
    let comps = DateComponents(year: parts[0], month: parts[1], day: parts[2])
    let date = cal.date(from: comps) ?? Date()
    // Apple: So=1..Sa=7  -> Backend: So=0..Sa=6
    let wd = cal.component(.weekday, from: date)
    return (wd + 6) % 7
}

/// Kurznamen fuer Wochentage So..Sa (DE)
func weekdayShortName(_ idx: Int) -> String {
    switch ((idx % 7) + 7) % 7 {
    case 0: return "So"
    case 1: return "Mo"
    case 2: return "Di"
    case 3: return "Mi"
    case 4: return "Do"
    case 5: return "Fr"
    default: return "Sa"
    }
}

/// Sichere Konvertierung Int? -> Int64?
func toInt64(_ x: Int?) -> Int64? { x.map(Int64.init) }

// MARK: - Name/Initials Helpers

func fullName(vorname: String?, name: String?) -> String {
    let v = (vorname ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
    let n = (name ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
    return [v, n].filter { !$0.isEmpty }.joined(separator: " ")
}

func initialsFromText(_ text: String) -> String {
    let parts = text.split(whereSeparator: { $0.isWhitespace || $0 == "-" })
    return parts.prefix(2).map { String($0.prefix(1)).uppercased() }.joined()
}



// MARK: - Status / Tag Chips (UI)

struct StatusChip: View {
    var text: String          // "erledigt" | "versaeumt" | "offen" | "nicht_pending"
    var body: some View {
        Text(text)
            .font(.caption).bold()
            .padding(.horizontal, 8).padding(.vertical, 5)
            .background(bg)
            .foregroundColor(.white)
            .clipShape(Capsule())
            .accessibilityLabel("Status: \(text)")
    }
    private var bg: Color {
        switch text {
        case "erledigt": return .green
        case "versaeumt": return .red
        case "offen": return .orange
        case "nicht_pending": return .gray
        default: return .blue
        }
    }
}

struct TagView: View {
    var text: String
    var color: Color = .blue
    var body: some View {
        Text(text)
            .font(.caption2).bold()
            .padding(.horizontal, 6).padding(.vertical, 3)
            .background(color.opacity(0.18))
            .foregroundColor(color)
            .clipShape(Capsule())
            .accessibilityLabel(text)
    }
}

/// Heute-Status Punkt wie in der Liste: pending/erledigt/nicht_pending
struct TodayStatusDot: View {
    var pending: Bool
    var status: String?   // "erledigt" | "versaeumt" | "offen" | nil
    var body: some View {
        ZStack {
            Circle()
                .strokeBorder(borderColor, lineWidth: strokeWidth)
                .background(Circle().fill(fillColor))
            if status == "erledigt" {
                Image(systemName: "checkmark")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundColor(.white)
            } else if status == "versaeumt" {
                Image(systemName: "xmark")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(.white)
            }
        }
        .frame(width: 24, height: 24)
        .accessibilityLabel(accessibilityText)
    }
    private var fillColor: Color {
        if status == "erledigt" { return .green }
        if pending { return .clear }
        return .blue
    }
    private var borderColor: Color {
        if status == "erledigt" { return .green }
        if pending { return Color.white.opacity(0.95) }
        return .blue
    }
    private var strokeWidth: CGFloat { pending ? 2 : 0 }
    private var accessibilityText: String {
        if status == "erledigt" { return "Erledigt" }
        if pending { return "Pending" }
        return "Nicht pending"
    }
}
// MARK: - Placeholder Helper
extension View {
    func placeholder<Content: View>(
        when shouldShow: Bool,
        alignment: Alignment = .leading,
        @ViewBuilder placeholder: () -> Content
    ) -> some View {
        ZStack(alignment: alignment) {
            placeholder().opacity(shouldShow ? 1 : 0)
            self
        }
    }
}


extension Int {
    /// Interpretiere diesen Int als Millisekunden seit 1970 (Unix epoch) und konvertiere zu Date

}
//
//  Utilities.swift
//  social_habit_v0
//
//  Zentrale kleine Helfer & Extensions
//


// MARK: - Timezone

/// Lokaler TZ-Offset in Minuten (wie Server-Parameter tzOffsetMinutes)
public func localTzOffsetMinutes() -> Int {
    TimeZone.current.secondsFromGMT() / 60
}

// MARK: - Epoch ms → Date

public extension Int {
    /// Interpretiert den Int als Millisekunden seit 1970 und gibt ein Date zurück.
    func asDateFromMs() -> Date {
        Date(timeIntervalSince1970: TimeInterval(self) / 1000.0)
    }
}

public extension Int64 {
    /// Interpretiert den Int64 als Millisekunden seit 1970 und gibt ein Date zurück.
    func asDateFromMs() -> Date {
        Date(timeIntervalSince1970: TimeInterval(self) / 1000.0)
    }
}

// MARK: - Date → String

public extension Date {
    /// Kurzes, lokales Datums-/Zeitformat (z. B. "27.09.25, 14:37")
    func formattedShort(dateStyle: DateFormatter.Style = .short,
                        timeStyle: DateFormatter.Style = .short) -> String {
        let f = DateFormatter()
        f.dateStyle = dateStyle
        f.timeStyle = timeStyle
        return f.string(from: self)
    }
}
// MARK: - Date → Int (Millisekunden seit 1970)

public extension Date {
    /// Gibt den Unix-Zeitstempel in **Millisekunden** (UTC) als Int64 zurück.
    func asMsSince1970() -> Int64 {
        Int64(self.timeIntervalSince1970 * 1000)
    }

    /// Alternativ als Int (gekürzt, nur wenn du sicher bist, dass keine Überläufe passieren)
    func asMsSince1970Int() -> Int {
        Int(self.timeIntervalSince1970 * 1000)
    }
}



// schneller: DateFormatter nur einmal bauen
private let _tsFormatter: DateFormatter = {
    let df = DateFormatter()
    df.dateStyle = .short
    df.timeStyle = .short
    return df
}()

func formatTS(_ ms: Int) -> String {
    let date = Date(timeIntervalSince1970: TimeInterval(ms) / 1000.0)
    return _tsFormatter.string(from: date)
}

/// Data-URL ("data:image/jpeg;base64,...") -> UIImage
func decodeDataURLToUIImage(_ dataURL: String) -> UIImage? {
    guard dataURL.lowercased().hasPrefix("data:image"),
          let comma = dataURL.firstIndex(of: ",") else { return nil }
    let b64 = String(dataURL[dataURL.index(after: comma)...])
    guard let data = Data(base64Encoded: b64) else { return nil }
    return UIImage(data: data)
}
