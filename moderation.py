import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from telegram import Update, ChatMember
from telegram.ext import CallbackContext
from config import config
from bot_data import BotData

logger = logging.getLogger(__name__)

class ModerationSystem:
    """Advanced moderation system for groups"""
    
    def __init__(self):
        self.auto_moderation_actions: Dict[int, List[str]] = {}  # {chat_id: [actions]}
        self.warning_counts: Dict[Tuple[int, int], int] = {}  # {(chat_id, user_id): count}
        self.muted_users: Dict[Tuple[int, int], datetime] = {}  # {(chat_id, user_id): unmute_time}
        
    async def handle_spam_violation(self, update: Update, context: CallbackContext, 
                                  bot_data: BotData, spam_score: int, reason: str):
        """Handle spam violation with appropriate moderation action"""
        user = update.effective_user
        chat = update.effective_chat
        
        if chat.type == 'private':
            return  # No moderation in private chats
        
        # Determine action based on spam score
        if spam_score >= config.AUTO_BAN_SPAM_SCORE:
            await self._ban_user(update, context, user.id, reason)
        elif spam_score >= config.SPAM_SCORE_THRESHOLD + 2:
            await self._mute_user(update, context, user.id, minutes=30, reason=reason)
        elif spam_score >= config.SPAM_SCORE_THRESHOLD:
            await self._warn_user(update, context, user.id, reason)
        
        # Delete the spam message
        try:
            await update.message.delete()
            logger.info(f"Deleted spam message from user {user.id} in chat {chat.id}")
        except Exception as e:
            logger.error(f"Failed to delete spam message: {e}")
    
    async def _warn_user(self, update: Update, context: CallbackContext, 
                        user_id: int, reason: str):
        """Issue a warning to user"""
        chat_id = update.effective_chat.id
        key = (chat_id, user_id)
        
        self.warning_counts[key] = self.warning_counts.get(key, 0) + 1
        warning_count = self.warning_counts[key]
        
        try:
            warning_msg = (
                f"⚠️ Peringatan #{warning_count} untuk pengguna ID {user_id}\n"
                f"Alasan: {reason}\n"
                f"Peringatan ke-3 akan mengakibatkan mute otomatis."
            )
            await update.effective_chat.send_message(warning_msg)
            
            # Auto-mute after 3 warnings
            if warning_count >= 3:
                await self._mute_user(update, context, user_id, minutes=60, 
                                    reason="3 peringatan spam")
        
        except Exception as e:
            logger.error(f"Failed to warn user {user_id}: {e}")
    
    async def _mute_user(self, update: Update, context: CallbackContext, 
                        user_id: int, minutes: int, reason: str):
        """Mute user for specified duration"""
        chat_id = update.effective_chat.id
        key = (chat_id, user_id)
        
        try:
            # Restrict user from sending messages
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions={
                    'can_send_messages': False,
                    'can_send_media_messages': False,
                    'can_send_other_messages': False,
                    'can_add_web_page_previews': False
                },
                until_date=datetime.now() + timedelta(minutes=minutes)
            )
            
            self.muted_users[key] = datetime.now() + timedelta(minutes=minutes)
            
            mute_msg = (
                f"🔇 Pengguna ID {user_id} di-mute selama {minutes} menit\n"
                f"Alasan: {reason}"
            )
            await update.effective_chat.send_message(mute_msg)
            
            logger.info(f"Muted user {user_id} in chat {chat_id} for {minutes} minutes")
            
        except Exception as e:
            logger.error(f"Failed to mute user {user_id}: {e}")
    
    async def _ban_user(self, update: Update, context: CallbackContext, 
                       user_id: int, reason: str):
        """Ban user from the group"""
        chat_id = update.effective_chat.id
        
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            
            ban_msg = (
                f"⛔ Pengguna ID {user_id} telah di-ban dari grup\n"
                f"Alasan: {reason}"
            )
            await update.effective_chat.send_message(ban_msg)
            
            logger.info(f"Banned user {user_id} from chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Failed to ban user {user_id}: {e}")
    
    async def unmute_user(self, update: Update, context: CallbackContext, 
                         user_id: int) -> bool:
        """Manually unmute a user"""
        chat_id = update.effective_chat.id
        key = (chat_id, user_id)
        
        try:
            # Restore normal permissions
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions={
                    'can_send_messages': True,
                    'can_send_media_messages': True,
                    'can_send_other_messages': True,
                    'can_add_web_page_previews': True
                }
            )
            
            if key in self.muted_users:
                del self.muted_users[key]
            
            logger.info(f"Unmuted user {user_id} in chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unmute user {user_id}: {e}")
            return False
    
    async def unban_user(self, update: Update, context: CallbackContext, 
                        user_id: int) -> bool:
        """Manually unban a user"""
        chat_id = update.effective_chat.id
        
        try:
            await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
            logger.info(f"Unbanned user {user_id} from chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unban user {user_id}: {e}")
            return False
    
    def clear_user_warnings(self, chat_id: int, user_id: int):
        """Clear warnings for a user in a specific chat"""
        key = (chat_id, user_id)
        if key in self.warning_counts:
            del self.warning_counts[key]
        
        logger.info(f"Cleared warnings for user {user_id} in chat {chat_id}")
    
    def get_user_warnings(self, chat_id: int, user_id: int) -> int:
        """Get warning count for a user in a specific chat"""
        key = (chat_id, user_id)
        return self.warning_counts.get(key, 0)
    
    def is_user_muted(self, chat_id: int, user_id: int) -> bool:
        """Check if user is currently muted"""
        key = (chat_id, user_id)
        if key not in self.muted_users:
            return False
        
        if self.muted_users[key] <= datetime.now():
            del self.muted_users[key]
            return False
        
        return True
    
    def get_mute_remaining(self, chat_id: int, user_id: int) -> Optional[int]:
        """Get remaining mute time in seconds"""
        key = (chat_id, user_id)
        if key not in self.muted_users:
            return None
        
        remaining = (self.muted_users[key] - datetime.now()).total_seconds()
        return max(0, int(remaining))
    
    async def cleanup_expired_restrictions(self, context: CallbackContext):
        """Clean up expired mutes and restrictions"""
        now = datetime.now()
        expired_mutes = [
            key for key, unmute_time in self.muted_users.items()
            if unmute_time <= now
        ]
        
        for (chat_id, user_id) in expired_mutes:
            try:
                # Restore permissions
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions={
                        'can_send_messages': True,
                        'can_send_media_messages': True,
                        'can_send_other_messages': True,
                        'can_add_web_page_previews': True
                    }
                )
                del self.muted_users[(chat_id, user_id)]
                logger.info(f"Auto-unmuted user {user_id} in chat {chat_id}")
                
            except Exception as e:
                logger.error(f"Failed to auto-unmute user {user_id}: {e}")
    
    def get_moderation_stats(self, chat_id: int) -> Dict[str, int]:
        """Get moderation statistics for a chat"""
        chat_warnings = sum(
            1 for (cid, uid), count in self.warning_counts.items()
            if cid == chat_id
        )
        
        chat_mutes = sum(
            1 for (cid, uid) in self.muted_users.keys()
            if cid == chat_id
        )
        
        return {
            "total_warnings": chat_warnings,
            "active_mutes": chat_mutes,
            "total_users_warned": len([
                (cid, uid) for (cid, uid) in self.warning_counts.keys()
                if cid == chat_id
            ])
        }

# Global moderation system instance
moderation = ModerationSystem()
