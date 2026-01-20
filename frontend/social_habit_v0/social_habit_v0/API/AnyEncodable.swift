//
//  AnyEncodable.swift
//  social_habit_v0
//
//  Created by Mauro Frehner on 11.10.2025.
//

//
//  AnyEncodable.swift
//

import Foundation

struct AnyEncodable: Encodable {
    let encodeFunc: (Encoder) throws -> Void
    init<T: Encodable>(_ wrapped: T) { self.encodeFunc = wrapped.encode }
    func encode(to encoder: Encoder) throws { try encodeFunc(encoder) }
}
