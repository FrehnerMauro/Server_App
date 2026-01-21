import SwiftUI

struct NotificationBellButton: View {
    @EnvironmentObject private var theme: ThemeManager
    @Binding var count: Int
    var action: () -> Void
    private var palette: Theme { theme.theme }

    var body: some View {

        Button(action: action) {
            ZStack(alignment: .topTrailing) {
                Image(systemName: "bell.fill")
                    .font(.title3)
                    .foregroundColor(palette.accent)

                

                if count > 0 {
                    Text("\(min(count, 99))")
                        .font(.caption2)
                        .bold()
                        .foregroundColor(.white)
                        .frame(width: 18, height: 18)
                        .background(Circle().fill(Color.red))
                        .offset(x: 8, y: -8)
                        .transition(.scale.combined(with: .opacity))
                }
            }
        }
        .animation(.easeInOut, value: count)
    }
}
