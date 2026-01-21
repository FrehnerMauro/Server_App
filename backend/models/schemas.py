from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

# Auth
class LoginBody(BaseModel):
    email: str
    password: str 

class RegisterBody(BaseModel):
    vorname: str
    name: str
    email: str
    password: str 
    avatar: str | None = None
    nb_state: Optional[str] = None

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
    visibility: Optional[str] = "friends"  # 'friends' oder 'private'
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