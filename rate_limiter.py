import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from telegram import Update
from config import config

logger = logging.getLogger(__name__)

class RateLimiter:
    """Advanced rate limiting system"""
    
    def __init__(self):
        self.user_requests: Dict[int, List[datetime]] = defaultdict(list)
        self.api_requests: Dict[int, List[datetime]] = defaultdict(list)
        self.cooldown_users: Dict[int, datetime] = {}
        self.warning_counts: Dict[int, int] = defaultdict(int)
        
    def is_rate_limited(self, user_id: int, request_type: str = "message") -> bool:
        """Check if user is rate limited"""
        now = datetime.now()
        
        # Check if user is in cooldown
        if user_id in self.cooldown_users:
            if self.cooldown_users[user_id] > now:
                return True
            else:
                del self.cooldown_users[user_id]
        
        # Clean old requests
        self._clean_old_requests(user_id, now)
        
        if request_type == "message":
            return self._check_message_rate_limit(user_id, now)
        elif request_type == "api":
            return self._check_api_rate_limit(user_id, now)
        
        return False
    
    def _clean_old_requests(self, user_id: int, now: datetime):
        """Remove old requests from tracking"""
        # Clean message requests older than 1 hour
        hour_ago = now - timedelta(hours=1)
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if req_time > hour_ago
        ]
        
        # Clean API requests older than 1 minute
        minute_ago = now - timedelta(minutes=1)
        self.api_requests[user_id] = [
            req_time for req_time in self.api_requests[user_id]
            if req_time > minute_ago
        ]
    
    def _check_message_rate_limit(self, user_id: int, now: datetime) -> bool:
        """Check message rate limits"""
        minute_ago = now - timedelta(minutes=1)
        recent_messages = [
            req_time for req_time in self.user_requests[user_id]
            if req_time > minute_ago
        ]
        
        # Check per-minute limit
        if len(recent_messages) >= config.MAX_MESSAGES_PER_MINUTE:
            self._apply_cooldown(user_id, "message_flood")
            return True
        
        # Check per-hour limit
        hour_ago = now - timedelta(hours=1)
        hourly_messages = [
            req_time for req_time in self.user_requests[user_id]
            if req_time > hour_ago
        ]
        
        if len(hourly_messages) >= config.MAX_MESSAGES_PER_HOUR:
            self._apply_cooldown(user_id, "message_abuse")
            return True
        
        return False
    
    def _check_api_rate_limit(self, user_id: int, now: datetime) -> bool:
        """Check API call rate limits"""
        minute_ago = now - timedelta(minutes=1)
        recent_api_calls = [
            req_time for req_time in self.api_requests[user_id]
            if req_time > minute_ago
        ]
        
        if len(recent_api_calls) >= config.MAX_API_CALLS_PER_MINUTE:
            self._apply_cooldown(user_id, "api_abuse")
            return True
        
        return False
    
    def _apply_cooldown(self, user_id: int, violation_type: str):
        """Apply cooldown to user"""
        now = datetime.now()
        self.warning_counts[user_id] += 1
        
        # Progressive cooldown based on warning count
        cooldown_minutes = min(self.warning_counts[user_id] * 5, 60)  # Max 1 hour
        self.cooldown_users[user_id] = now + timedelta(minutes=cooldown_minutes)
        
        logger.warning(
            f"Rate limit cooldown applied to user {user_id}: "
            f"{violation_type}, cooldown: {cooldown_minutes} minutes"
        )
    
    def add_request(self, user_id: int, request_type: str = "message"):
        """Add a request to tracking"""
        now = datetime.now()
        
        if request_type == "message":
            self.user_requests[user_id].append(now)
        elif request_type == "api":
            self.api_requests[user_id].append(now)
    
    def get_cooldown_remaining(self, user_id: int) -> Optional[int]:
        """Get remaining cooldown time in seconds"""
        if user_id not in self.cooldown_users:
            return None
        
        remaining = (self.cooldown_users[user_id] - datetime.now()).total_seconds()
        return max(0, int(remaining))
    
    def reset_user_limits(self, user_id: int):
        """Reset all limits for a user (admin function)"""
        self.user_requests[user_id] = []
        self.api_requests[user_id] = []
        if user_id in self.cooldown_users:
            del self.cooldown_users[user_id]
        self.warning_counts[user_id] = 0
        
        logger.info(f"Rate limits reset for user {user_id}")
    
    def get_user_stats(self, user_id: int) -> Dict[str, int]:
        """Get rate limit statistics for a user"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        
        messages_last_minute = len([
            req for req in self.user_requests[user_id]
            if req > minute_ago
        ])
        
        messages_last_hour = len([
            req for req in self.user_requests[user_id]
            if req > hour_ago
        ])
        
        api_calls_last_minute = len([
            req for req in self.api_requests[user_id]
            if req > minute_ago
        ])
        
        return {
            "messages_last_minute": messages_last_minute,
            "messages_last_hour": messages_last_hour,
            "api_calls_last_minute": api_calls_last_minute,
            "warning_count": self.warning_counts[user_id],
            "cooldown_remaining": self.get_cooldown_remaining(user_id) or 0
        }

# Global rate limiter instance
rate_limiter = RateLimiter()
