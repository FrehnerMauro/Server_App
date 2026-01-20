import SwiftUI

struct NotificationBellButton: View {
    @Binding var count: Int
    var action: () -> Void
    private let primaryAccent = Color(red: 0.0, green: 0.9, blue: 1.0)



    var body: some View {

        Button(action: action) {
            ZStack(alignment: .topTrailing) {
                Image(systemName: "bell.fill")
                    .font(.title3)
                    .foregroundColor(primaryAccent)

                

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
