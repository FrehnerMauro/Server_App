import SwiftUI
import UIKit


struct ChallengeConfirmImagePicker: View {
    @EnvironmentObject var app: AppState
    @Environment(\.dismiss) private var dismiss     // 👈 ermöglicht Zurücknavigation
    let challengeId: Int

    @State private var showCamera = false
    @State private var selectedImage: UIImage?
    @State private var caption: String = ""
    @State private var visibility: String
    @State private var uploading = false
    @State private var showSheet = false
    @State private var error: String?

    init(challengeId: Int, visibility: String) {
        self.challengeId = challengeId
        _visibility = State(initialValue: visibility)
    }

    var body: some View {
        Button {
            showCamera = true
        } label: {
            if uploading {
                ProgressView()
                    .tint(.white)
                    .padding(8)
                    .background(Color.blue.opacity(0.8))
                    .clipShape(Circle())
            } else {
                Image(systemName: "camera.fill")
                    .font(.title2)
                    .foregroundColor(.white)
                    .padding(6)
                    .background(Color.blue.opacity(0.8))
                    .clipShape(Circle())
            }
        }
        .sheet(isPresented: $showCamera) {
            CameraView(image: $selectedImage)
        }
        .onChange(of: selectedImage) { newValue in
            if newValue != nil {
                showSheet = true
            }
        }
        .sheet(isPresented: $showSheet) {
            confirmSheet
        }
    }

    // MARK: - Confirm Sheet Inhalt
    private var confirmSheet: some View {
        VStack(spacing: 20) {
            Text("Bestätigungsbild posten")
                .font(.headline)
                .padding(.top)

            if let img = selectedImage {
                Image(uiImage: img)
                    .resizable()
                    .scaledToFit()
                    .frame(maxHeight: 250)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .shadow(radius: 6)
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Bildunterschrift")
                    .font(.caption)
                    .foregroundColor(.gray)
                TextField("z. B. Heute geschafft 💪", text: $caption)
                    .textFieldStyle(.roundedBorder)
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Sichtbarkeit")
                    .font(.caption)
                    .foregroundColor(.gray)
                Picker("Sichtbarkeit", selection: $visibility) {
                    Text("Privat").tag("private")
                    Text("Freunde").tag("friends")
                }
                .pickerStyle(.segmented)
            }

            Button {
                Task { await handleImageUpload() }
            } label: {
                HStack {
                    if uploading { ProgressView().tint(.white) }
                    Text(uploading ? "Wird hochgeladen…" : "Posten")
                        .bold()
                }
                .padding()
                .frame(maxWidth: .infinity)
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(12)
            }
            .disabled(uploading)

            if let error {
                Text(error)
                    .foregroundColor(.red)
                    .padding(.top, 8)
            }

            Spacer()
        }
        .padding()
    }

    // MARK: - Upload Logik + automatische Rückkehr
    private func handleImageUpload() async {
        guard let image = selectedImage,
              let jpeg = image.jpegData(compressionQuality: 0.8) else { return }

        uploading = true
        error = nil

        do {
            let base64 = jpeg.base64EncodedString()
            let dataURL = "data:image/jpeg;base64,\(base64)"

            try await app.Api_Challenge.confirm(
                challengeId,
                imageDataURL: dataURL,
                caption: caption.isEmpty ? nil : caption,
                visibility: visibility
            )

            // ✅ Nach erfolgreichem Post automatisch zurück
            await MainActor.run {
                uploading = false
                dismiss()         // schließt Confirm-Sheet
                dismiss()         // schließt Chat-View → zurück zur Challenge-View
            }
        } catch {
            await MainActor.run {
                self.error = error.localizedDescription
                uploading = false
            }
        }
    }
}

// MARK: - CameraView (nur Kamera, quadratischer Zuschnitt)
struct CameraView: UIViewControllerRepresentable {
    @Environment(\.dismiss) var dismiss
    @Binding var image: UIImage?

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.allowsEditing = true      // ✅ aktiviert quadratischen Zuschnitt
        picker.cameraCaptureMode = .photo
        picker.delegate = context.coordinator
        picker.mediaTypes = ["public.image"]
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    final class Coordinator: NSObject, UINavigationControllerDelegate, UIImagePickerControllerDelegate {
        let parent: CameraView

        init(_ parent: CameraView) { self.parent = parent }

        func imagePickerController(_ picker: UIImagePickerController,
                                   didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]) {
            // Wenn der Benutzer zugeschnitten hat → das bearbeitete Bild nehmen
            if let edited = info[.editedImage] as? UIImage {
                parent.image = edited
            } else if let original = info[.originalImage] as? UIImage {
                parent.image = original
            }
            parent.dismiss()
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            parent.dismiss()
        }
    }
}
