from typing import Optional, List
from pydantic import BaseModel, EmailStr

# Auth
class RegisterBody(BaseModel):
    vorname: Optional[str] = None
    name: str
    email: EmailStr
    passwort: str
    avatar: Optional[str] = None

class LoginBody(BaseModel):
    email: EmailStr
    passwort: str

# Challenges
class CreateChallengeBody(BaseModel):
    name: str
    beschreibung: Optional[str] = None
    art: Optional[str] = None
    startAt: Optional[int] = None
    faelligeWochentage: List[int]
    friendsToAdd: Optional[List[int]] = None
    days: Optional[int] = None
    dauerTage: Optional[int] = None
    erlaubteFailsTage: Optional[int] = None

class ChatBody(BaseModel):
    text: str

class ConfirmBody(BaseModel):
    imageUrl: str
    caption: Optional[str] = None
    visibility: Optional[str] = "freunde"
    user_id: Optional[int] = None
    challenge_id: Optional[int] = None
    timestamp: Optional[int] = None

class ChallengeInviteBody(BaseModel):
    toUserId: int
    message: Optional[str] = None

# Friends
class FriendReqBody(BaseModel):
    toUserId: int
    message: Optional[str] = None
    
    
class LogChallengeBody(BaseModel):
    challenge_id: int
    member_id: int
    conf_count: int
    fail_count: int
    streak: int
    blocked: bool
    state: str  # Pending, not Pending, completed