"""
Billing Service - Credit Management & Automatic Billing.
Handles credit deduction, billing events, and subscription management.
"""
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from backend.core.logging import get_logger
from backend.repositories.user_repository import UserRepository
from backend.common.store import Database

logger = get_logger(__name__)


class BillingService:
    """Service für Billing & Credit-Management."""
    
    # Pricing Configuration (in Credits)
    PRICING = {
        "challenge_join": 5.0,        # User tritt Challenge bei
        "confirmation": 2.0,           # User bestätigt Challenge-Aufgabe
        "friend_add": 1.0,             # User fügt Freund hinzu
        "notification": 0.5,           # Notifizierung senden
        "failed_task": -1.0,           # User verfehlt Aufgabe
        "monthly_base": 10.0,          # Monatliches Abo-Guthaben
    }
    
    # Billing Thresholds
    SUSPEND_THRESHOLD = -50.0          # User wird suspendiert bei -50 Credits
    WARNING_THRESHOLD = -10.0          # Warnung bei -10 Credits
    
    def __init__(self):
        """Initialisiert Billing Service."""
        self.user_repo = UserRepository()
        self.db = Database()
    
    def add_credits(self, user_id: int, amount: float, description: str = "") -> Dict[str, Any]:
        """
        Credits zu User hinzufügen.
        
        Args:
            user_id: User ID
            amount: Credit-Betrag (positiv oder negativ)
            description: Beschreibung des Events
        
        Returns:
            Dict mit user_id, new_balance, billing_status
        """
        try:
            user = self.user_repo.find_by_id(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return {"error": "User not found"}
            
            new_balance = (user.get("credits") or 10.0) + amount
            
            # Update user credits
            self.user_repo.update(user_id, {
                "credits": new_balance,
                "updated_at": int(time.time() * 1000)
            })
            
            # Track billing event
            self._create_billing_event(user_id, amount, description)
            
            # Check if suspension needed
            new_status = "active"
            if new_balance <= self.SUSPEND_THRESHOLD:
                new_status = "suspended"
                self.user_repo.update(user_id, {
                    "billing_status": new_status,
                    "updated_at": int(time.time() * 1000)
                })
                logger.warning(f"User {user_id} suspended. Balance: {new_balance}")
            
            logger.info(f"User {user_id}: Credits added {amount}. New balance: {new_balance}")
            
            return {
                "user_id": user_id,
                "new_balance": new_balance,
                "billing_status": new_status,
                "description": description
            }
        
        except Exception as e:
            logger.error(f"Error adding credits for user {user_id}: {str(e)}")
            return {"error": str(e)}
    
    def deduct_credits(self, user_id: int, event_type: str) -> Dict[str, Any]:
        """
        Credits für spezifisches Event abziehen.
        
        Args:
            user_id: User ID
            event_type: Typ des Events (aus PRICING)
        
        Returns:
            Dict mit Ergebnis
        """
        if event_type not in self.PRICING:
            logger.error(f"Unknown event type: {event_type}")
            return {"error": f"Unknown event type: {event_type}"}
        
        amount = self.PRICING[event_type]
        description = f"Event: {event_type}"
        
        return self.add_credits(user_id, amount, description)
    
    def daily_billing(self) -> Dict[str, Any]:
        """
        Tägliche Abrechnung - zieht monatliche Credits ab.
        Sollte als scheduled job einmal täglich laufen.
        
        Returns:
            Statistik über verarbeitete User
        """
        try:
            logger.info("Starting daily billing cycle...")
            
            # Hole alle aktiven User
            con, cur = self.db.begin_transaction()
            cur.execute(
                "SELECT id, credits, billing_status, last_billing_date FROM users WHERE billing_status != %s",
                ("cancelled",)
            )
            users = cur.fetchall()
            
            now = int(time.time() * 1000)
            processed = 0
            suspended = 0
            
            for user in users:
                user_id, credits, status, last_billing = user[0], user[1], user[2], user[3]
                
                # Check ob heute schon abgerechnet wurde
                if last_billing:
                    last_date = datetime.fromtimestamp(last_billing / 1000)
                    if last_date.date() == datetime.now().date():
                        continue  # Heute schon abgerechnet
                
                # Monatliches Abo-Guthaben abziehen
                new_balance = credits - self.PRICING["monthly_base"]
                
                # Update user
                cur.execute(
                    "UPDATE users SET credits = %s, last_billing_date = %s, updated_at = %s WHERE id = %s",
                    (new_balance, now, now, user_id)
                )
                
                # Track event
                cur.execute(
                    """INSERT INTO billing_events (user_id, event_type, amount, description, created_at)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (user_id, "monthly_base", -self.PRICING["monthly_base"], "Daily billing cycle", now)
                )
                
                # Suspend if needed
                if new_balance <= self.SUSPEND_THRESHOLD and status != "suspended":
                    cur.execute(
                        "UPDATE users SET billing_status = %s, updated_at = %s WHERE id = %s",
                        ("suspended", now, user_id)
                    )
                    logger.warning(f"User {user_id} suspended during billing. Balance: {new_balance}")
                    suspended += 1
                
                processed += 1
            
            self.db.commit(con)
            
            logger.info(f"Daily billing completed. Processed: {processed}, Suspended: {suspended}")
            return {
                "processed": processed,
                "suspended": suspended,
                "timestamp": now
            }
        
        except Exception as e:
            logger.error(f"Error in daily billing: {str(e)}")
            return {"error": str(e)}
    
    def get_user_credits(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Holt Kredit-Info für User.
        
        Args:
            user_id: User ID
        
        Returns:
            Dict mit credits, billing_status, subscription_tier
        """
        user = self.user_repo.find_by_id(user_id)
        if not user:
            return None
        
        return {
            "user_id": user_id,
            "credits": user.get("credits", 10.0),
            "billing_status": user.get("billing_status", "active"),
            "subscription_tier": user.get("subscription_tier", "free"),
            "last_billing_date": user.get("last_billing_date")
        }
    
    def get_billing_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Holt Abrechnung-Historie für User.
        
        Args:
            user_id: User ID
            limit: Max Anzahl Events
        
        Returns:
            Liste von Billing Events
        """
        try:
            con, cur = self.db.begin_transaction()
            cur.execute(
                """SELECT id, event_type, amount, description, created_at 
                   FROM billing_events 
                   WHERE user_id = %s 
                   ORDER BY created_at DESC 
                   LIMIT %s""",
                (user_id, limit)
            )
            events = cur.fetchall()
            self.db.commit(con)
            
            return [
                {
                    "id": e[0],
                    "event_type": e[1],
                    "amount": e[2],
                    "description": e[3],
                    "created_at": e[4]
                }
                for e in events
            ]
        except Exception as e:
            logger.error(f"Error fetching billing history: {str(e)}")
            return []
    
    def _create_billing_event(self, user_id: int, amount: float, description: str) -> None:
        """
        Erstellt Billing Event Log.
        
        Args:
            user_id: User ID
            amount: Credit-Betrag
            description: Event-Beschreibung
        """
        try:
            now = int(time.time() * 1000)
            
            # Determine event type from description
            event_type = "manual"
            for key in self.PRICING.keys():
                if key in description.lower():
                    event_type = key
                    break
            
            con, cur = self.db.begin_transaction()
            cur.execute(
                """INSERT INTO billing_events (user_id, event_type, amount, description, created_at)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, event_type, amount, description, now)
            )
            self.db.commit(con)
        except Exception as e:
            logger.error(f"Error creating billing event: {str(e)}")
