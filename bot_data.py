import os
import json
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, List, Any, Optional
from dataclasses import dataclass, asdict
from config import config

logger = logging.getLogger(__name__)

@dataclass
class UserStats:
    """User statistics for monitoring and anti-spam"""
    user_id: int
    username: str
    first_seen: datetime
    last_seen: datetime
    message_count: int = 0
    spam_score: int = 0
    warnings: int = 0
    verification_status: str = "unverified"  # unverified, pending, verified
    last_spam_check: Optional[datetime] = None

class BotData:
    """Enhanced bot data management with anti-spam and security features"""
    
    def __init__(self):
        self.session_id = str(random.randint(100000, 999999))
        self.owner_id = config.OWNER_ID
        self.approved_users: Set[int] = set()
        self.banned_users: Dict[int, datetime] = {}  # {user_id: ban_end_time}
        self.group_states: Dict[int, bool] = {}
        self.chat_history: List[Dict[str, Any]] = []
        self.user_stats: Dict[int, UserStats] = {}
        
        # Anti-spam data
        self.spam_violations: Dict[int, List[datetime]] = {}  # {user_id: [violation_times]}
        self.message_hashes: Dict[str, List[datetime]] = {}  # {hash: [send_times]}
        self.user_message_counts: Dict[int, List[datetime]] = {}  # {user_id: [message_times]}
        
        # Rate limiting data
        self.rate_limit_violations: Dict[int, List[datetime]] = {}
        self.api_call_counts: Dict[int, List[datetime]] = {}
        
        # Security data
        self.failed_verifications: Dict[int, int] = {}
        self.suspicious_users: Set[int] = set()
        
        # Session management
        self.session_start_time = datetime.now()
        self.last_backup_time: Optional[datetime] = None
        
    def get_user_stats(self, user_id: int, username: str = "unknown") -> UserStats:
        """Get or create user statistics"""
        if user_id not in self.user_stats:
            self.user_stats[user_id] = UserStats(
                user_id=user_id,
                username=username,
                first_seen=datetime.now(),
                last_seen=datetime.now()
            )
        else:
            self.user_stats[user_id].last_seen = datetime.now()
            if username != "unknown":
                self.user_stats[user_id].username = username
        
        return self.user_stats[user_id]
    
    def increment_user_message_count(self, user_id: int):
        """Increment user message count for rate limiting"""
        now = datetime.now()
        if user_id not in self.user_message_counts:
            self.user_message_counts[user_id] = []
        
        self.user_message_counts[user_id].append(now)
        
        # Clean old entries (older than 1 hour)
        hour_ago = now - timedelta(hours=1)
        self.user_message_counts[user_id] = [
            msg_time for msg_time in self.user_message_counts[user_id]
            if msg_time > hour_ago
        ]
    
    def add_spam_violation(self, user_id: int, violation_type: str = "general"):
        """Add spam violation for user"""
        now = datetime.now()
        if user_id not in self.spam_violations:
            self.spam_violations[user_id] = []
        
        self.spam_violations[user_id].append(now)
        
        # Clean old violations (older than 24 hours)
        day_ago = now - timedelta(days=1)
        self.spam_violations[user_id] = [
            v_time for v_time in self.spam_violations[user_id]
            if v_time > day_ago
        ]
        
        # Update user stats
        user_stats = self.get_user_stats(user_id)
        user_stats.spam_score += 1
        
        logger.warning(f"Spam violation added for user {user_id}: {violation_type}")
    
    def is_rate_limited(self, user_id: int) -> bool:
        """Check if user is rate limited"""
        now = datetime.now()
        
        if user_id not in self.user_message_counts:
            return False
        
        # Check messages per minute
        minute_ago = now - timedelta(minutes=1)
        recent_messages = [
            msg_time for msg_time in self.user_message_counts[user_id]
            if msg_time > minute_ago
        ]
        
        if len(recent_messages) >= config.MAX_MESSAGES_PER_MINUTE:
            return True
        
        # Check messages per hour
        hour_ago = now - timedelta(hours=1)
        hourly_messages = [
            msg_time for msg_time in self.user_message_counts[user_id]
            if msg_time > hour_ago
        ]
        
        return len(hourly_messages) >= config.MAX_MESSAGES_PER_HOUR
    
    def clean_old_data(self):
        """Clean old data to prevent memory issues"""
        now = datetime.now()
        
        # Clean message hashes older than 1 hour
        hour_ago = now - timedelta(hours=1)
        for msg_hash in list(self.message_hashes.keys()):
            self.message_hashes[msg_hash] = [
                send_time for send_time in self.message_hashes[msg_hash]
                if send_time > hour_ago
            ]
            if not self.message_hashes[msg_hash]:
                del self.message_hashes[msg_hash]
        
        # Clean expired bans
        expired_bans = [
            user_id for user_id, ban_end in self.banned_users.items()
            if ban_end < now
        ]
        for user_id in expired_bans:
            del self.banned_users[user_id]
        
        # Keep only last 1000 chat history entries
        if len(self.chat_history) > 1000:
            self.chat_history = self.chat_history[-1000:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "session_id": self.session_id,
            "owner_id": self.owner_id,
            "approved_users": list(self.approved_users),
            "banned_users": {str(k): v.isoformat() for k, v in self.banned_users.items()},
            "group_states": {str(k): v for k, v in self.group_states.items()},
            "chat_history": self.chat_history[-100:],  # Keep last 100 chats
            "user_stats": {
                str(k): {
                    "user_id": v.user_id,
                    "username": v.username,
                    "first_seen": v.first_seen.isoformat(),
                    "last_seen": v.last_seen.isoformat(),
                    "message_count": v.message_count,
                    "spam_score": v.spam_score,
                    "warnings": v.warnings,
                    "verification_status": v.verification_status,
                    "last_spam_check": v.last_spam_check.isoformat() if v.last_spam_check else None
                }
                for k, v in self.user_stats.items()
            },
            "spam_violations": {
                str(k): [t.isoformat() for t in v]
                for k, v in self.spam_violations.items()
            },
            "suspicious_users": list(self.suspicious_users),
            "session_start_time": self.session_start_time.isoformat(),
            "last_backup_time": self.last_backup_time.isoformat() if self.last_backup_time else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BotData':
        """Create from dictionary"""
        bot_data = cls()
        
        bot_data.session_id = data.get("session_id", str(random.randint(100000, 999999)))
        bot_data.owner_id = data.get("owner_id", config.OWNER_ID)
        bot_data.approved_users = set(data.get("approved_users", []))
        bot_data.banned_users = {
            int(k): datetime.fromisoformat(v)
            for k, v in data.get("banned_users", {}).items()
        }
        bot_data.group_states = {
            int(k): v for k, v in data.get("group_states", {}).items()
        }
        bot_data.chat_history = data.get("chat_history", [])
        
        # Load user stats
        user_stats_data = data.get("user_stats", {})
        for user_id_str, stats_data in user_stats_data.items():
            user_id = int(user_id_str)
            bot_data.user_stats[user_id] = UserStats(
                user_id=stats_data["user_id"],
                username=stats_data["username"],
                first_seen=datetime.fromisoformat(stats_data["first_seen"]),
                last_seen=datetime.fromisoformat(stats_data["last_seen"]),
                message_count=stats_data.get("message_count", 0),
                spam_score=stats_data.get("spam_score", 0),
                warnings=stats_data.get("warnings", 0),
                verification_status=stats_data.get("verification_status", "unverified"),
                last_spam_check=datetime.fromisoformat(stats_data["last_spam_check"]) if stats_data.get("last_spam_check") else None
            )
        
        # Load spam violations
        spam_violations_data = data.get("spam_violations", {})
        for user_id_str, violations in spam_violations_data.items():
            user_id = int(user_id_str)
            bot_data.spam_violations[user_id] = [
                datetime.fromisoformat(v) for v in violations
            ]
        
        bot_data.suspicious_users = set(data.get("suspicious_users", []))
        
        if data.get("session_start_time"):
            bot_data.session_start_time = datetime.fromisoformat(data["session_start_time"])
        
        if data.get("last_backup_time"):
            bot_data.last_backup_time = datetime.fromisoformat(data["last_backup_time"])
        
        return bot_data

def load_data() -> BotData:
    """Load bot data from file"""
    if os.path.exists(config.DATA_FILE):
        try:
            with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return BotData.from_dict(data)
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            # Create backup before returning new instance
            if os.path.exists(config.DATA_FILE):
                backup_file = f"{config.DATA_FILE}.error.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(config.DATA_FILE, backup_file)
                logger.info(f"Corrupted data file backed up as: {backup_file}")
    
    return BotData()

def save_data(bot_data: BotData):
    """Save bot data to file"""
    try:
        # Clean old data before saving
        bot_data.clean_old_data()
        
        # Create backup if file exists
        if os.path.exists(config.DATA_FILE):
            backup_file = f"{config.DATA_FILE}.backup"
            with open(config.DATA_FILE, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
        
        # Save data
        with open(config.DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(bot_data.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.debug("Bot data saved successfully")
        
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        raise
