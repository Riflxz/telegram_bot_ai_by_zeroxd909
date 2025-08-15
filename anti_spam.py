import re
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from telegram import Update, User
from config import config
from bot_data import BotData

logger = logging.getLogger(__name__)

class AntiSpam:
    """Advanced anti-spam detection system"""
    
    def __init__(self):
        # Compile regex patterns for better performance with IGNORECASE flag
        self.spam_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in config.SPAM_PATTERNS]
        self.profanity_words = set(word.lower() for word in config.PROFANITY_WORDS)
        
        # Tracking duplicate messages
        self.message_hashes: Dict[str, List[Tuple[int, datetime]]] = {}
        
        # Tracking user behavior patterns
        self.user_message_intervals: Dict[int, List[datetime]] = {}
        
    def check_spam(self, update: Update, bot_data: BotData) -> Tuple[bool, str, int]:
        """
        Check if message is spam
        Returns: (is_spam, reason, spam_score)
        """
        if not update.message or not update.message.text:
            return False, "", 0
        
        user = update.effective_user
        message_text = update.message.text
        spam_score = 0
        reasons = []
        
        # Check message length
        if len(message_text) > config.MAX_MESSAGE_LENGTH:
            spam_score += 2
            reasons.append("message_too_long")
        
        # Check for spam patterns
        pattern_matches = self._check_spam_patterns(message_text)
        if pattern_matches:
            spam_score += len(pattern_matches) * 2
            reasons.extend(pattern_matches)
        
        # Check for profanity
        if self._contains_profanity(message_text):
            spam_score += 1
            reasons.append("profanity")
        
        # Check for excessive caps
        if self._check_excessive_caps(message_text):
            spam_score += 1
            reasons.append("excessive_caps")
        
        # Check for duplicate messages
        duplicate_score = self._check_duplicate_message(user.id, message_text)
        if duplicate_score > 0:
            spam_score += duplicate_score
            reasons.append("duplicate_message")
        
        # Check for suspicious links
        if self._check_suspicious_links(message_text):
            spam_score += 3
            reasons.append("suspicious_links")
        
        # Check message frequency (rapid fire)
        if self._check_rapid_messaging(user.id):
            spam_score += 2
            reasons.append("rapid_messaging")
        
        # Check user account age (if available)
        account_age_score = self._check_account_age(user)
        if account_age_score > 0:
            spam_score += account_age_score
            reasons.append("new_account")
        
        # Update user spam score in bot data
        user_stats = bot_data.get_user_stats(user.id, user.username or user.first_name)
        user_stats.last_spam_check = datetime.now()
        
        is_spam = spam_score >= config.SPAM_SCORE_THRESHOLD
        reason_str = ", ".join(reasons) if reasons else ""
        
        if is_spam:
            logger.warning(f"Spam detected from user {user.id}: score={spam_score}, reasons={reason_str}")
            bot_data.add_spam_violation(user.id, reason_str)
        
        return is_spam, reason_str, spam_score
    
    def _check_spam_patterns(self, text: str) -> List[str]:
        """Check for spam patterns using regex"""
        matches = []
        for i, pattern in enumerate(self.spam_patterns):
            if pattern.search(text):
                matches.append(f"spam_pattern_{i}")
        return matches
    
    def _contains_profanity(self, text: str) -> bool:
        """Check for profanity words"""
        if not config.ENABLE_PROFANITY_FILTER:
            return False
        
        words = text.lower().split()
        return any(word in self.profanity_words for word in words)
    
    def _check_excessive_caps(self, text: str) -> bool:
        """Check for excessive capital letters"""
        if not config.ENABLE_CAPS_FILTER or len(text) < 10:
            return False
        
        caps_count = sum(1 for c in text if c.isupper())
        caps_percentage = caps_count / len(text)
        
        return caps_percentage > config.MAX_CAPS_PERCENTAGE
    
    def _check_duplicate_message(self, user_id: int, message: str) -> int:
        """Check for duplicate messages"""
        # Create hash of the message
        message_hash = hashlib.md5(message.encode()).hexdigest()
        now = datetime.now()
        
        if message_hash not in self.message_hashes:
            self.message_hashes[message_hash] = []
        
        # Clean old entries (older than 1 hour)
        hour_ago = now - timedelta(hours=1)
        self.message_hashes[message_hash] = [
            (uid, timestamp) for uid, timestamp in self.message_hashes[message_hash]
            if timestamp > hour_ago
        ]
        
        # Count duplicates from this user
        user_duplicates = [
            timestamp for uid, timestamp in self.message_hashes[message_hash]
            if uid == user_id
        ]
        
        # Add current message
        self.message_hashes[message_hash].append((user_id, now))
        
        if len(user_duplicates) >= config.MAX_IDENTICAL_MESSAGES:
            return len(user_duplicates) - config.MAX_IDENTICAL_MESSAGES + 1
        
        return 0
    
    def _check_suspicious_links(self, text: str) -> bool:
        """Check for suspicious links"""
        if not config.ENABLE_LINK_FILTER:
            return False
        
        # Pattern for suspicious short URLs
        suspicious_url_pattern = r'https?://(?:bit\.ly|tinyurl|t\.co|short\.link|goo\.gl)/'
        return bool(re.search(suspicious_url_pattern, text, re.IGNORECASE))
    
    def _check_rapid_messaging(self, user_id: int) -> bool:
        """Check for rapid messaging (potential bot behavior)"""
        now = datetime.now()
        
        if user_id not in self.user_message_intervals:
            self.user_message_intervals[user_id] = []
        
        # Add current message time
        self.user_message_intervals[user_id].append(now)
        
        # Keep only last 10 messages
        self.user_message_intervals[user_id] = self.user_message_intervals[user_id][-10:]
        
        # Check if user sent 5+ messages in last 30 seconds
        thirty_seconds_ago = now - timedelta(seconds=30)
        recent_messages = [
            timestamp for timestamp in self.user_message_intervals[user_id]
            if timestamp > thirty_seconds_ago
        ]
        
        return len(recent_messages) >= 5
    
    def _check_account_age(self, user: User) -> int:
        """Check account age (basic heuristic based on user ID)"""
        if not config.ENABLE_USER_VERIFICATION:
            return 0
        
        # Very basic heuristic: newer user IDs are likely newer accounts
        # This is not perfect but provides some protection
        if user.id > 5000000000:  # Very high user ID suggests recent account
            return 1
        
        return 0
    
    def should_auto_ban(self, bot_data: BotData, user_id: int) -> bool:
        """Check if user should be automatically banned"""
        user_stats = bot_data.user_stats.get(user_id)
        if not user_stats:
            return False
        
        return user_stats.spam_score >= config.AUTO_BAN_SPAM_SCORE
    
    def reset_user_spam_data(self, user_id: int):
        """Reset spam data for a user (admin function)"""
        # Clear message intervals
        if user_id in self.user_message_intervals:
            del self.user_message_intervals[user_id]
        
        # Clear message hashes for this user
        for message_hash in list(self.message_hashes.keys()):
            self.message_hashes[message_hash] = [
                (uid, timestamp) for uid, timestamp in self.message_hashes[message_hash]
                if uid != user_id
            ]
            if not self.message_hashes[message_hash]:
                del self.message_hashes[message_hash]
        
        logger.info(f"Spam data reset for user {user_id}")
    
    def get_spam_stats(self) -> Dict[str, int]:
        """Get general spam statistics"""
        return {
            "tracked_message_hashes": len(self.message_hashes),
            "tracked_users": len(self.user_message_intervals),
            "spam_patterns_count": len(self.spam_patterns),
            "profanity_words_count": len(self.profanity_words)
        }

# Global anti-spam instance
anti_spam = AntiSpam()
