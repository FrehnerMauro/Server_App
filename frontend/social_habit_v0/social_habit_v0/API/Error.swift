//
//  Error.swift
//  social_habit_v0
//
//  Created by Mauro Frehner on 11.10.2025.
//

//
//  APIError.swift
//

import Foundation

struct APIError: Error, LocalizedError {
    let message: String
    var errorDescription: String? { message }
}
