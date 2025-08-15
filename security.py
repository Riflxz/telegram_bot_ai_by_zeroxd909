import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Set, Optional, Tuple
from telegram import Update, User
from config import config

logger = logging.getLogger(__name__)

class SecuritySystem:
    """Enhanced security system for bot protection"""
    
    def __init__(self):
        self.suspicious_users: Set[int] = set()
        self.failed_verifications: Dict[int, int] = {}
        self.user_sessions: Dict[int, str] = {}  # {user_id: session_token}
        self.session_timestamps: Dict[int, datetime] = {}
        self.ip_tracking: Dict[str, List[datetime]] = {}  # Basic IP tracking
        
    def generate_session_token(self, user_id: int) -> str:
        """Generate a secure session token for user"""
        token = secrets.token_urlsafe(32)
        self.user_sessions[user_id] = token
        self.session_timestamps[user_id] = datetime.now()
        return token
    
    def validate_session(self, user_id: int, token: str = None) -> bool:
        """Validate user session"""
        if not config.ENABLE_USER_VERIFICATION:
            return True
        
        # Check if session exists
        if user_id not in self.user_sessions:
            return False
        
        # Check session timeout
        if user_id in self.session_timestamps:
            session_age = datetime.now() - self.session_timestamps[user_id]
            if session_age > timedelta(hours=config.SESSION_TIMEOUT_HOURS):
                self.invalidate_session(user_id)
                return False
        
        # If token provided, validate it
        if token and self.user_sessions[user_id] != token:
            return False
        
        return True
    
    def invalidate_session(self, user_id: int):
        """Invalidate user session"""
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        if user_id in self.session_timestamps:
            del self.session_timestamps[user_id]
        
        logger.info(f"Session invalidated for user {user_id}")
    
    def verify_user_account(self, user: User) -> Tuple[bool, str]:
        """Verify user account based on various criteria"""
        if not config.ENABLE_USER_VERIFICATION:
            return True, "verification_disabled"
        
        verification_score = 0
        issues = []
        
        # Check if user has username
        if not user.username:
            verification_score += 1
            issues.append("no_username")
        
        # Check if user has profile photo (basic check)
        # Note: This requires additional API call in practice
        
        # Basic user ID analysis (heuristic for account age)
        if user.id > 5000000000:  # Very high user ID
            verification_score += 2
            issues.append("potentially_new_account")
        
        # Check for suspicious username patterns
        if user.username and self._is_suspicious_username(user.username):
            verification_score += 2
            issues.append("suspicious_username")
        
        # Check first name for suspicious patterns
        if self._is_suspicious_name(user.first_name):
            verification_score += 1
            issues.append("suspicious_name")
        
        is_verified = verification_score < 3
        reason = ", ".join(issues) if issues else "verified"
        
        if not is_verified:
            self.suspicious_users.add(user.id)
            logger.warning(f"User {user.id} failed verification: {reason}")
        
        return is_verified, reason
    
    def _is_suspicious_username(self, username: str) -> bool:
        """Check if username follows suspicious patterns"""
        username_lower = username.lower()
        
        # Check for common bot patterns
        suspicious_patterns = [
            'bot', 'spam', 'fake', 'test', 'promo', 'ad', 'marketing'
        ]
        
        for pattern in suspicious_patterns:
            if pattern in username_lower:
                return True
        
        # Check for excessive numbers
        digit_count = sum(c.isdigit() for c in username)
        if len(username) > 0 and digit_count / len(username) > 0.5:
            return True
        
        return False
    
    def _is_suspicious_name(self, name: str) -> bool:
        """Check if first name is suspicious"""
        if not name:
            return True
        
        # Check for excessive emojis or special characters
        special_char_count = sum(1 for c in name if not c.isalnum() and not c.isspace())
        if len(name) > 0 and special_char_count / len(name) > 0.3:
            return True
        
        # Check for promotional words
        promo_words = ['free', 'win', 'prize', 'money', 'bitcoin', 'crypto']
        name_lower = name.lower()
        
        return any(word in name_lower for word in promo_words)
    
    def add_failed_verification(self, user_id: int):
        """Add failed verification attempt"""
        self.failed_verifications[user_id] = self.failed_verifications.get(user_id, 0) + 1
        
        if self.failed_verifications[user_id] >= 3:
            self.suspicious_users.add(user_id)
            logger.warning(f"User {user_id} marked as suspicious after {self.failed_verifications[user_id]} failed verifications")
    
    def is_user_suspicious(self, user_id: int) -> bool:
        """Check if user is marked as suspicious"""
        return user_id in self.suspicious_users
    
    def mark_user_safe(self, user_id: int):
        """Mark user as safe (admin function)"""
        self.suspicious_users.discard(user_id)
        if user_id in self.failed_verifications:
            del self.failed_verifications[user_id]
        
        logger.info(f"User {user_id} marked as safe")
    
    def generate_secure_hash(self, data: str) -> str:
        """Generate secure hash for data"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def validate_input(self, text: str, max_length: int = 4000) -> Tuple[bool, str]:
        """Validate user input for security issues"""
        if not text:
            return False, "empty_input"
        
        if len(text) > max_length:
            return False, "input_too_long"
        
        # Check for potential injection attempts
        dangerous_patterns = [
            '<script', '<?php', '<?', 'javascript:', 'eval(',
            'system(', 'exec(', 'shell_exec(', 'passthru('
        ]
        
        text_lower = text.lower()
        for pattern in dangerous_patterns:
            if pattern in text_lower:
                return False, "potentially_malicious_input"
        
        return True, "valid"
    
    def cleanup_old_sessions(self):
        """Clean up expired sessions"""
        now = datetime.now()
        expired_users = []
        
        for user_id, timestamp in self.session_timestamps.items():
            if now - timestamp > timedelta(hours=config.SESSION_TIMEOUT_HOURS):
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self.invalidate_session(user_id)
        
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired sessions")
    
    def get_security_stats(self) -> Dict[str, int]:
        """Get security system statistics"""
        return {
            "suspicious_users": len(self.suspicious_users),
            "active_sessions": len(self.user_sessions),
            "failed_verifications": len(self.failed_verifications),
            "total_verification_failures": sum(self.failed_verifications.values())
        }

# Global security system instance
security = SecuritySystem()
