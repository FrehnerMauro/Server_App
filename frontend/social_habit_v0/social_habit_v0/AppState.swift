import Foundation
import SwiftUI

@MainActor
final class AppState: ObservableObject {

    // MARK: - API-Instanzen
    let Api: api
    let Api_Feed: api_feed
    let Api_Login_Register: api_login_register
    let Api_Profiles: api_profiles
    let Api_Challenge: api_challenge
    let Api_Notifications: api_notifications
    let Api_Friends: api_friends
    let Api_Log: api_log
    let Api_Report: api_report
    let Api_Settings: api_settings

    // MARK: - Session / UI
    @Published var token: String? {
        didSet {
            Api.setToken(token)
            let key = "jwtToken"
            // Speichere den Token nur, wenn er gesetzt ist. Lösche ihn, wenn er nil ist (beim Logout).
            if let t = token {
                UserDefaults.standard.set(t, forKey: key)
            } else {
                UserDefaults.standard.removeObject(forKey: key)
            }
        }
    }

    // MARK: - App-Daten
    @Published var me: User? = nil
    @Published var meSettings: SettingsUser? = nil
    @Published var challenges: [ChallengeWithToday] = []
    @Published var notifications: [NotificationItem] = []
    @Published var challengeInvites: [ChallengeInvite] = []
    @Published var myPosts: [FeedPost] = []
    @Published var otherProfile: User? = nil
    @Published var otherPublicPosts: [FeedPost] = []
    @Published var unreadCount: Int = 0
    @Published var isTurtleVisible: Bool = false


    // MARK: - Init
    init() {
        let defaultURL = URL(string: "https://api.socialhabit.org")!
        let baseURL: URL
        if let saved = UserDefaults.standard.string(forKey: "baseURL"),
           let u = URL(string: saved) {
            baseURL = u
        } else {
            baseURL = defaultURL
        }

        // APIs initialisieren
        let api = api(baseURL: baseURL)
        self.Api = api
        self.Api_Feed = api_feed(Api: api)
        self.Api_Login_Register = api_login_register(Api: api)
        self.Api_Profiles = api_profiles(Api: api)
        self.Api_Challenge = api_challenge(Api: api)
        self.Api_Notifications = api_notifications(Api: api)
        self.Api_Friends = api_friends(Api: api)
        self.Api_Log = api_log(Api: api)
        self.Api_Report = api_report(Api: api)
        self.Api_Settings = api_settings(Api: api)

        if let saved = UserDefaults.standard.string(forKey: "jwtToken"), !saved.isEmpty {
            self.token = saved
            api.setToken(saved)
            // Hinweis: Bootstrap-Daten (wie `me` oder `unreadCount`)
            // müssen nach der Initialisierung von der Hauptansicht geladen werden.
        } else {
            self.token = nil
            api.setToken(nil)
        }
    }

    // MARK: - Base URL setzen
    func setBaseURL(_ s: String) {
        guard let u = URL(string: s) else { return }
        UserDefaults.standard.set(s, forKey: "baseURL")
        Api.baseURL = u
    }

    // MARK: - Login & Bootstrap
    func loginAndBootstrap(email: String, passwort: String) async throws {
        let res = try await Api_Login_Register.login(email: email, passwort: passwort)
        self.token = res.token // didSet speichert den Token automatisch
        await refreshUnread()
    }

    // MARK: - Loader
    func reloadMe() async {
        guard Api.isAuthed else { return }
    }

    func loadChallenges(withToday: Bool) async throws {
        guard Api.isAuthed else { self.challenges = []; return }
        let tz = TimeZone.current.secondsFromGMT() / 60
        self.challenges = try await Api_Challenge.listChallenges(withToday: withToday, tzOffsetMinutes: tz)
    }

    func loadNotifications() async throws {
        guard Api.isAuthed else { self.notifications = []; return }
        self.notifications = try await Api_Notifications.notifications()
    }

    func loadChallengeInvites(direction: String) async throws {
        guard Api.isAuthed else { self.challengeInvites = []; return }
        self.challengeInvites = try await Api_Challenge.listChallengeInvites(direction: direction)
    }

    // MARK: - Unread Count
    // MARK: - Unread Count
    func refreshUnread() async {
        guard Api.isAuthed else { self.unreadCount = 0; return }
        do {
            async let notifTask = Api_Notifications.notifications()
            async let invTask   = Api_Challenge.listChallengeInvites(direction: "incoming")
            async let frTask    = Api_Friends.listFriendRequests(direction: "incoming")

            let (notifs, invites, friends) = try await (notifTask, invTask, frTask)

            let unreadNotifs = notifs.filter { ($0.read ?? 0) == 0 }.count
            let openInvites  = invites.count
            let openFriends  = friends.filter { ($0.status.lowercased() ?? "pending") == "pending" }.count

            self.unreadCount = unreadNotifs + openInvites + openFriends
        } catch {
            // Ignorieren
        }
    }

    // MARK: - Logout
    func logout() {
        // Das Setzen auf nil löst `didSet` aus, was den Token aus UserDefaults löscht
        self.token = nil
        self.me = nil
        self.meSettings = nil
        Api.setToken(nil)
    }
}
