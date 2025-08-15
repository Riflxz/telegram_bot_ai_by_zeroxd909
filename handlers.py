import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import CallbackContext
from config import config
from bot_data import BotData, save_data
from rate_limiter import rate_limiter
from anti_spam import anti_spam
from moderation import moderation
from security import security
from utils import send_typing, get_ai_response

logger = logging.getLogger(__name__)

async def check_access(update: Update, bot_data: BotData) -> bool:
    """Enhanced access control with security checks"""
    user = update.effective_user
    
    # Owner always has access
    if user.id == config.OWNER_ID:
        return True
    
    # Check if user is banned
    if user.id in bot_data.banned_users:
        ban_end = bot_data.banned_users[user.id]
        if ban_end > datetime.now():
            remaining = ban_end - datetime.now()
            await update.message.reply_text(
                f"⛔ Anda dibanned dari menggunakan bot ini\n"
                f"Sisa waktu ban: {remaining.days} hari, {remaining.seconds//3600} jam"
            )
            return False
        else:
            # Ban expired, remove it
            del bot_data.banned_users[user.id]
            save_data(bot_data)
    
    # Check rate limiting
    if rate_limiter.is_rate_limited(user.id):
        cooldown = rate_limiter.get_cooldown_remaining(user.id)
        if cooldown:
            await update.message.reply_text(
                f"⏰ Anda terkena rate limit. Coba lagi dalam {cooldown} detik."
            )
        else:
            await update.message.reply_text(
                "⏰ Anda mengirim pesan terlalu cepat. Harap tunggu sebentar."
            )
        return False
    
    # Check if user is suspicious
    if security.is_user_suspicious(user.id):
        await update.message.reply_text(
            "🔒 Akun Anda ditandai sebagai mencurigakan. Hubungi admin untuk verifikasi."
        )
        return False
    
    # For private chats, check if user is approved
    if update.effective_chat.type == 'private' and user.id not in bot_data.approved_users:
        # Verify user account
        is_verified, reason = security.verify_user_account(user)
        if not is_verified:
            security.add_failed_verification(user.id)
            await update.message.reply_text(
                f"❌ Verifikasi akun gagal: {reason}\n"
                "Hubungi admin untuk mendapat akses."
            )
            return False
        
        # Auto-approve verified users if enabled
        if config.ENABLE_USER_VERIFICATION:
            bot_data.approved_users.add(user.id)
            save_data(bot_data)
            await update.message.reply_text(
                "✅ Akun berhasil diverifikasi otomatis!"
            )
        else:
            await update.message.reply_text(
                "❌ Anda belum mendapat akses. Hubungi admin."
            )
            return False
    
    return True

async def handle_text(update: Update, context: CallbackContext, bot_data: BotData):
    """Enhanced text message handler with anti-spam"""
    if not await check_access(update, bot_data):
        return
    
    chat = update.effective_chat
    user = update.effective_user
    text = update.message.text or ""
    
    # Security input validation
    is_valid, validation_reason = security.validate_input(text)
    if not is_valid:
        await update.message.reply_text(
            f"❌ Input tidak valid: {validation_reason}"
        )
        return
    
    # Group chat requires "Alya" prefix
    if chat.type in ['group', 'supergroup']:
        if not bot_data.group_states.get(chat.id, False):
            return
        if not text.lower().startswith('alya'):
            return
        text = text[4:].strip()  # Remove trigger word
    
    if not text:
        return
    
    # Anti-spam check
    is_spam, spam_reason, spam_score = anti_spam.check_spam(update, bot_data)
    if is_spam:
        await moderation.handle_spam_violation(
            update, context, bot_data, spam_score, spam_reason
        )
        return
    
    # Add to rate limiter
    rate_limiter.add_request(user.id, "message")
    
    # Update user stats
    user_stats = bot_data.get_user_stats(user.id, user.username or user.first_name)
    user_stats.message_count += 1
    bot_data.increment_user_message_count(user.id)
    
    # Log interaction
    interaction = {
        "user_id": user.id,
        "username": user.username or user.first_name,
        "chat_type": chat.type,
        "chat_title": chat.title if hasattr(chat, 'title') else None,
        "timestamp": datetime.now().isoformat(),
        "message": text[:100] + "..." if len(text) > 100 else text,
        "spam_score": spam_score
    }
    bot_data.chat_history.append(interaction)
    save_data(bot_data)
    
    logger.info(f"CHAT - User: {user.id} | Chat: {chat.title or 'Private'} | Spam Score: {spam_score}")
    
    # Check API rate limit
    if rate_limiter.is_rate_limited(user.id, "api"):
        await update.message.reply_text(
            "⏰ Terlalu banyak permintaan API. Coba lagi nanti."
        )
        return
    
    # Add API call to rate limiter
    rate_limiter.add_request(user.id, "api")
    
    await send_typing(update)
    response = await get_ai_response(text, user.id)
    await update.message.reply_text(response)

async def handle_image(update: Update, context: CallbackContext, bot_data: BotData):
    """Enhanced image handler with security checks"""
    if not await check_access(update, bot_data):
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Group chat requires "Alya" prefix in caption
    if chat.type in ['group', 'supergroup']:
        if not bot_data.group_states.get(chat.id, False):
            return
        if update.message.caption and not update.message.caption.lower().startswith('alya'):
            return
    
    # Rate limiting for images (more restrictive)
    if rate_limiter.is_rate_limited(user.id, "api"):
        await update.message.reply_text(
            "⏰ Terlalu banyak permintaan gambar. Coba lagi nanti."
        )
        return
    
    # Add to rate limiter
    rate_limiter.add_request(user.id, "message")
    rate_limiter.add_request(user.id, "api")
    
    # Update user stats
    user_stats = bot_data.get_user_stats(user.id, user.username or user.first_name)
    user_stats.message_count += 1
    
    # Log interaction
    interaction = {
        "user_id": user.id,
        "username": user.username or user.first_name,
        "chat_type": chat.type,
        "chat_title": chat.title if hasattr(chat, 'title') else None,
        "timestamp": datetime.now().isoformat(),
        "message": "[PHOTO]" + (f" - {update.message.caption[:100]}" if update.message.caption else ""),
        "spam_score": 0
    }
    bot_data.chat_history.append(interaction)
    save_data(bot_data)
    
    logger.info(f"IMAGE - User: {user.id} | Chat: {chat.title or 'Private'}")
    
    await send_typing(update)
    
    try:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        response = await get_ai_response("Deskripsikan gambar ini", user.id, file.file_path)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await update.message.reply_text(
            "❌ Maaf, terjadi kesalahan saat memproses gambar."
        )

async def error_handler(update: Update, context: CallbackContext):
    """Enhanced error handler with detailed logging"""
    error_message = str(context.error)
    
    # Handle specific errors
    if "Conflict" in error_message and "getUpdates" in error_message:
        logger.warning("Bot conflict detected - another instance may be running")
        return
    
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message and "Can't parse entities" not in error_message:
            await update.effective_message.reply_text(
                "❌ Terjadi kesalahan sistem. Tim teknis telah diberitahu."
            )
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")
