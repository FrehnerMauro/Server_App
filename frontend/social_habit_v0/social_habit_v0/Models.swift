import Foundation

//-----------------------------------------------------------------------------------------------------
// MARK: - AUTH
public struct LoginResponse: Codable, Equatable {
    public var token: String
    public var user: User?
}

// MARK: - LOGIN REGISTER
public struct RegisterBody: Codable {
    public var vorname: String?
    public var name: String
    public var email: String
    public var passwort: String
    public var avatar: String?
    public var nb_state: String?
}

public struct LoginBody: Codable {
    public var email: String
    public var passwort: String

}



//-----------------------------------------------------------------------------------------------------
public struct FriendReqBody: Codable {
    public var Id: Int
    public var fromUserId: Int
    public var toUserId: Int
    public var message: String?
    public var status: String            // "pending" | "accepted" | "declined"
    public var createdAt: Int?
}



//-----------------------------------------------------------------------------------------------------
// MARK: - CREATE CHALLENGE
public struct CreateChallengeBody: Codable {
    public var name: String
    public var beschreibung: String?
    public var art: String?
    public var startAt: Int64?
    public var faelligeWochentage: [Int]
    public var friendsToAdd: [Int]?
    public var days: [String]?
    public var dauerTage: Int?
    public var erlaubteFailsTage: Int?
}

// MARK: - CHALLENGE CHAT
public struct ChatBody: Codable {
    public var text: String
}

// MARK: - CHALLENGE CONFIRM
public struct ConfirmBody: Codable {
    public var imageUrl: String
    public var caption: String?
    public var visibility: String              // "freunde" | "privat" | optional "public"
}

// MARK: - CHALLENGE INVITE
public struct ChallengeInvite: Codable, Identifiable, Equatable {
    public var id: Int
    public var challengeId: Int
    public var fromUserId: Int
    public var toUserId: Int
    public var message: String?
    public var status: String            // "pending" | "accepted" | "declined"
    public var createdAt: Int?
}













// MARK: - FEED

public struct FeedEvidence: Codable, Equatable {
    public var imageUrl: String?
    public var caption: String?
    
    private enum CodingKeys: String, CodingKey {
        case imageUrl = "image_url"
    }
}

// ⚠️ Korrigiert: Fügt User-Details über CodingKeys hinzu
public struct FeedComment: Codable, Identifiable, Equatable {
    public var id: Int
    public var userId: Int
    public var text: String
    public var createdAt: Int
    
    // NEU: User-Details, die der Server (feed.py) jetzt liefert
    public var displayName: String? // Mappt zu display_name vom Server
    public var avatarUrl: String?   // Mappt zu avatar_url vom Server
    
    private enum CodingKeys: String, CodingKey {
        case id, text, createdAt
        case userId = "user_id"
        case displayName = "display_name"
        case avatarUrl = "avatar_url"
    }
}


struct Post: Codable, Identifiable {
    var id: Int
    var user_id: Int
    var caption: String
    var image_url: String?
    var visibility: String
    var created_at: UInt64
    var display_name: String
    var avatar_url: String?
}


struct FeedPost: Codable, Identifiable {
    let id: Int
    let user_id: Int?
    let display_name: String
    let avatar_url: String?
    let image_url: String?
    let content: String
    var likedByMe: Bool?
    var likesCount: Int?
    var commentsCount: Int?
    let created_at: Double
    let updated_at: Double?
    
    // Zusatzfelder für Abwärtskompatibilität (z. B. ProfileView)
    var visibility: String? = "freunde"
    var timestamp: Int? { Int(created_at) }
    
    enum CodingKeys: String, CodingKey {
        case id
        case user_id  = "user_id"
        case display_name = "display_name"
        case avatar_url = "avatar_url"
        case image_url = "image_url"
        case content
        case likedByMe
        case likesCount
        case commentsCount
        case created_at = "created_at"
        case updated_at = "updated_at"
        case visibility
    }
}

// MARK: - FeedPost Model

// MARK: - USER / FRIENDS / NOTIFICATIONS

public struct UpdateMeBody: Codable {
    public var vorname: String?
    public var name: String?
    /// Optional: Wenn du einen Avatar als Data-URL oder http(s) URL direkt setzen willst
    public var avatar: String?
}

public struct UpdateMeResponse: Codable {
    public var id: Int
    public var vorname: String?
    public var name: String
    public var email: String?
    public var avatar: String?
}

public struct User: Codable, Identifiable, Equatable {
    public var id: Int
    public var name: String
    public var nb_state: String?
    public var avatar: String?
    public var vorname: String? = nil
    public var email: String? = nil

    enum CodingKeys: String, CodingKey {
        case id = "friend_id"
        case name = "display_name"
        case nb_state
        case avatar = "avatar_url"
        case vorname
        case email
    }
}

public struct FriendRequest: Codable, Identifiable, Equatable {
    public var id: Int
    public var fromUserId: Int
    public var toUserId: Int
    public var message: String?
    public var status: String                  // "pending" | "accepted" | "declined"
    public var createdAt: Int?
}



// MARK: - CHALLENGES (Basis)

public struct Challenge: Codable, Identifiable, Equatable {
    public var id: Int
    public var name: String
    public var beschreibung: String?
    public var ownerId: Int
    public var faelligeWochentage: [Int]?
    public var hinzugefuegtAt: Int?
    public var dauerTage: Int?
    public var erlaubteFailsTage: Int?
}

public struct TodayStatus: Codable, Equatable {
    public var status: String                  // "open" | "done"
    public var pending: Bool?
}

public struct ChallengeWithToday: Codable, Identifiable, Equatable {
    public var id: Int
    public var name: String
    public var beschreibung: String?
    public var ownerId: Int
    public var faelligeWochentage: [Int]?
    public var hinzugefuegtAt: Int?
    public var today: TodayStatus?

    public init(id: Int, name: String, beschreibung: String?, ownerId: Int,
                faelligeWochentage: [Int]?, hinzugefuegtAt: Int?, today: TodayStatus?) {
        self.id = id
        self.name = name
        self.beschreibung = beschreibung
        self.ownerId = ownerId
        self.faelligeWochentage = faelligeWochentage
        self.hinzugefuegtAt = hinzugefuegtAt
        self.today = today
    }

    public init(from c: Challenge, today: TodayStatus? = nil) {
        self.init(id: c.id,
                  name: c.name,
                  beschreibung: c.beschreibung,
                  ownerId: c.ownerId,
                  faelligeWochentage: c.faelligeWochentage,
                  hinzugefuegtAt: c.hinzugefuegtAt,
                  today: today)
    }
}

public struct Member: Codable, Identifiable, Equatable {
    public var id: Int
    public var vorname: String?
    public var name: String
    public var avatar: String?
}

public struct ChallengeChatResponse: Codable {
    public var challengeId: Int
    public var currentUserId: Int?       // 👈 NEU
    public var chat: [ChatMessage]
    public var members: [ChatMember]

    enum CodingKeys: String, CodingKey {
        case challengeId = "challenge_id"
        case currentUserId = "current_user_id"   
        case chat
        case members
    }
}

public struct ChatMessage: Codable, Identifiable, Equatable {
    public var id: Int
    public var userId: Int
    public var text: String
    public var imageUrl: String?
    public var createdAt: Int

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case text = "text"
        case imageUrl = "image_url"
        case createdAt = "created_at"
    }
}

public struct ChatMember: Codable, Identifiable, Equatable {
    public var id: Int { userId }
    public var userId: Int
    public var displayName: String
    public var avatarUrl: String?
    public var colorHex: String?

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case displayName = "display_name"
        case avatarUrl = "avatar_url"
        case colorHex = "color_hex"
    }
}

// MARK: - ACTIVITY / LOGS (Challenge-Activity)

public struct ActivityEvidence: Codable, Equatable {
    public var imageUrl: String?
    public var caption: String?
}

struct ActivityItem: Codable, Identifiable {
    let id: Int
    let action: String?
    let evidence: Evidence?
    let timestamp: Int?
    let userId: Int?
    let vorname: String?
    let name: String?
    let avatar: String?
}
struct Evidence: Codable {
    let imageUrl: String?
    let caption: String?
}

// MARK: - STATS / FAIL-LOGS


public struct StatsRecalcResponse: Codable, Equatable {
    public var ok: Bool
}

public struct BlockedListResponse: Codable, Equatable {
    public var challengeId: Int
    public var blocked: [Int]?
}

public struct TodayStatusResponse: Codable, Equatable {
    public var challengeId: Int
    public var today: TodayStatus
}

public struct FailLogsResponse: Codable, Equatable {
    public var challengeId: Int
    public var fails: [FailLog]
    public struct FailLog: Codable, Equatable {
        public var id: Int?
        public var userId: Int?
        public var timestamp: Int?
        public var reason: String?
    }
}

// MARK: - DAILY SUMMARY (minimal für bestehende Views)
// Deine API mappt /today-status -> ChallengeDailySummary(today: ...)

public struct ChallengeDailySummary: Codable, Equatable {
    public var entries: [ChallengeDailySummaryEntry] = [] // optional leer
    public var today: TodayStatus?

    public init(entries: [ChallengeDailySummaryEntry] = [], today: TodayStatus? = nil) {
        self.entries = entries
        self.today = today
    }
}

public struct ChallengeDailySummaryEntry: Codable, Identifiable, Equatable {
    public var id: String { date }             // convenience
    public var date: String                    // "YYYY-MM-DD"
    public var users: [ChallengeDailySummaryUser]
}

public struct ChallengeDailySummaryUser: Codable, Identifiable, Equatable {
    public var id: Int { userId }
    public var userId: Int
    public var status: String?                 // "done" / "open"
    public var confirmTimestamp: Int?
}



// MARK: - Gesamtstruktur
struct ChallengeOverview: Codable, Identifiable {
    var id: Int { challenge.ch_id }
    let challenge: ChallengeMeta
    let members: [ChallengeMember]
}

// MARK: - Challenge Meta
struct ChallengeMeta: Codable {
    let ch_id: Int
    let name: String
    let dauerTage: Int
    let erlaubteFailsTage: Int
    let start_at: Int64
    let status: String

    enum CodingKeys: String, CodingKey {
        case ch_id
        case name
        case dauerTage = "dauertage"
        case erlaubteFailsTage = "erlaubtefailstage"
        case start_at
        case status
    }
}

// MARK: - Challenge Member
struct ChallengeMember: Codable, Identifiable {
    var id: Int { user_id }
    let user_id: Int
    let display_name: String
    let avatar_url: String?
    let done_days: Int
    let fail_days: Int
    let streak: Int
    let neg_streak: Int
    let status: String
    let today_done: Int?
    let today_pending: Int?

    var isTodayDone: Bool { today_done == 1 }
    var isTodayPending: Bool { today_pending == 1 }

    enum CodingKeys: String, CodingKey {
        case user_id
        case display_name
        case avatar_url
        case done_days
        case fail_days
        case streak
        case neg_streak
        case status
        case today_done
        case today_pending
    }
}



// MARK: - Challenge Stats (per User)

struct ChallengeStatsUserResponse: Codable {
    let challengeId: Int
    let dauerTage: Int?
    let erlaubteFailsTage: Int?
    let faelligeWochentage: [Int]?
    let perUser: [ChallengeUserStats]
}

struct ChallengeUserStats: Codable, Identifiable {
    var id: Int { userId }
    let challenge_status: String?
    let userId: Int
    var confCount: Int
    var failCount: Int             // "failCount" im JSON
    let status: String?            // z. B. "pending"
    let streak: Int                // "streak" im JSON
    let negStreak: Int
    var challenge_today_status: String?

    private enum CodingKeys: String, CodingKey {
        case challenge_status = "challenge_status"
        case userId
        case confCount
        case failCount
        case status
        case streak
        case negStreak
        case challenge_today_status = "challenge_today_status"
    }
}
struct SendChallengeInviteBody: Encodable {
    let toUserId: Int
    let message: String?
}
