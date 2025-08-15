import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext
)

# Import our modules
from config import config
from bot_data import BotData, load_data, save_data
from rate_limiter import rate_limiter
from anti_spam import anti_spam
from moderation import moderation
from security import security
from handlers import handle_text, handle_image, error_handler, check_access
from utils import get_user_display_name, format_time_duration, is_admin_user
from backup import backup_system

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE) if config.ENABLE_FILE_LOGGING else logging.NullHandler(),
        logging.StreamHandler() if config.ENABLE_CONSOLE_LOGGING else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global bot data
bot_data = load_data()

def print_status():
    """Print current bot status"""
    print("\n" + "="*50)
    print("           ALYA BOT STATUS")
    print("="*50)
    print(f"Session ID: {bot_data.session_id}")
    print(f"Approved Users: {len(bot_data.approved_users)}")
    print(f"Banned Users: {len(bot_data.banned_users)}")
    print(f"Active Groups: {sum(bot_data.group_states.values())}")
    print(f"Total Messages: {len(bot_data.chat_history)}")
    print(f"Suspicious Users: {len(security.suspicious_users)}")
    print(f"Session Start: {bot_data.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50 + "\n")

# ===== COMMAND HANDLERS =====

async def start(update: Update, context: CallbackContext):
    """Enhanced start command with security info"""
    user = update.effective_user
    
    # Verify user account
    is_verified, reason = security.verify_user_account(user)
    verification_status = "✅ Terverifikasi" if is_verified else f"⚠️ {reason}"
    
    welcome_msg = (
        f"🤖 Selamat datang {user.first_name}!\n\n"
        f"Saya Alya, asisten virtual yang telah ditingkatkan dengan:\n"
        f"🛡️ Anti-spam protection\n"
        f"⏰ Rate limiting\n"
        f"🔒 Enhanced security\n"
        f"🛠️ Advanced moderation\n\n"
        f"Status Akun: {verification_status}\n"
        f"Session ID: {bot_data.session_id}\n\n"
        f"Cara Penggunaan:\n"
        f"• Di grup: Mulai pesan dengan 'Alya'\n"
        f"• Private chat: Langsung kirim pesan\n\n"
        f"Gunakan /help untuk bantuan lengkap"
    )
    
    await update.message.reply_text(welcome_msg)
    logger.info(f"START - User: {user.id} ({get_user_display_name(user)})")

async def help_command(update: Update, context: CallbackContext):
    """Enhanced help command with new features"""
    user = update.effective_user
    is_admin = is_admin_user(user.id)
    
    help_text = (
        "🆘 BANTUAN ALYA BOT v2.0\n\n"
        "Perintah Umum:\n"
        "/start - Info bot dan status\n"
        "/help - Bantuan lengkap\n"
        "/status - Status pribadi\n\n"
    )
    
    if is_admin:
        help_text += (
            "Perintah Admin:\n"
            "/on - Aktifkan di grup\n"
            "/off - Nonaktifkan di grup\n"
            "/akses [ID] - Beri akses user\n"
            "/hapus_akses [ID] - Cabut akses\n"
            "/ban [ID] [HARI] - Ban user\n"
            "/unban [ID] - Hapus ban\n"
            "/mute [ID] [MENIT] - Mute user di grup\n"
            "/unmute [ID] - Unmute user\n"
            "/resetlimit [ID] - Reset rate limit\n"
            "/marksafe [ID] - Tandai user aman\n"
            "/changeid - Ganti session ID\n"
            "/backup - Buat backup manual\n"
            "/adminstatus - Status lengkap admin\n\n"
        )
    
    help_text += (
        "Fitur Keamanan:\n"
        "• Anti-spam otomatis\n"
        "• Rate limiting per user\n"
        "• Verifikasi akun otomatis\n"
        "• Filter konten berbahaya\n"
        "• Sistem moderasi grup\n\n"
        "Tips:\n"
        "• Hindari spam untuk mencegah pembatasan\n"
        "• Laporkan user mencurigakan ke admin\n"
        "• Gunakan bot dengan bijak"
    )
    
    await update.message.reply_text(help_text)

async def user_status(update: Update, context: CallbackContext):
    """Show user's personal status"""
    user = update.effective_user
    user_stats = bot_data.get_user_stats(user.id, get_user_display_name(user))
    rate_stats = rate_limiter.get_user_stats(user.id)
    
    status_msg = (
        f"📊 Status Anda\n\n"
        f"ID: {user.id}\n"
        f"Username: {get_user_display_name(user)}\n"
        f"Total Pesan: {user_stats.message_count}\n"
        f"Skor Spam: {user_stats.spam_score}\n"
        f"Peringatan: {user_stats.warnings}\n"
        f"Status Verifikasi: {user_stats.verification_status}\n\n"
        f"Rate Limiting:\n"
        f"• Pesan/menit: {rate_stats['messages_last_minute']}/{config.MAX_MESSAGES_PER_MINUTE}\n"
        f"• Pesan/jam: {rate_stats['messages_last_hour']}/{config.MAX_MESSAGES_PER_HOUR}\n"
        f"• Cooldown: {rate_stats['cooldown_remaining']} detik\n\n"
        f"Bergabung: {user_stats.first_seen.strftime('%Y-%m-%d')}\n"
        f"Terakhir aktif: {user_stats.last_seen.strftime('%Y-%m-%d %H:%M')}"
    )
    
    await update.message.reply_text(status_msg, parse_mode='Markdown')

# ===== ADMIN COMMANDS =====

async def admin_status(update: Update, context: CallbackContext):
    """Comprehensive admin status"""
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("❌ Hanya admin yang dapat menggunakan perintah ini")
        return
    
    # Get system statistics
    security_stats = security.get_security_stats()
    spam_stats = anti_spam.get_spam_stats()
    backups = backup_system.list_backups()
    
    status_msg = (
        f"🔧 ADMIN STATUS - ALYA BOT v2.0\n\n"
        f"Session Info:\n"
        f"• Session ID: {bot_data.session_id}\n"
        f"• Start Time: {bot_data.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"• Uptime: {format_time_duration(int((datetime.now() - bot_data.session_start_time).total_seconds()))}\n\n"
        f"Users:\n"
        f"• Approved: {len(bot_data.approved_users)}\n"
        f"• Banned: {len(bot_data.banned_users)}\n"
        f"• Suspicious: {security_stats['suspicious_users']}\n"
        f"• Active Sessions: {security_stats['active_sessions']}\n\n"
        f"Groups:\n"
        f"• Total: {len(bot_data.group_states)}\n"
        f"• Active: {sum(bot_data.group_states.values())}\n\n"
        f"Security:\n"
        f"• Spam Patterns: {spam_stats['spam_patterns_count']}\n"
        f"• Failed Verifications: {security_stats['total_verification_failures']}\n\n"
        f"Backups:\n"
        f"• Available: {len(backups)}\n"
        f"• Last Backup: {bot_data.last_backup_time.strftime('%Y-%m-%d %H:%M') if bot_data.last_backup_time else 'Never'}\n\n"
        f"Messages:\n"
        f"• Total Processed: {len(bot_data.chat_history)}\n"
        f"• Spam Violations: {sum(len(v) for v in bot_data.spam_violations.values())}"
    )
    
    await update.message.reply_text(status_msg)

async def toggle_group_state(update: Update, state: bool):
    """Toggle group state with admin check"""
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("❌ Hanya admin yang dapat menggunakan perintah ini")
        return
    
    bot_data.group_states[update.effective_chat.id] = state
    save_data(bot_data)
    status = "diaktifkan" if state else "dinonaktifkan"
    await update.message.reply_text(f"✅ Bot {status} di grup ini")
    print_status()

async def turn_on(update: Update, context: CallbackContext):
    """Turn on bot in group"""
    await toggle_group_state(update, True)

async def turn_off(update: Update, context: CallbackContext):
    """Turn off bot in group"""
    await toggle_group_state(update, False)

async def grant_access(update: Update, context: CallbackContext):
    """Grant access to user"""
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("❌ Hanya admin yang dapat menggunakan perintah ini")
        return
    
    try:
        user_id = int(context.args[0])
        bot_data.approved_users.add(user_id)
        
        # Remove from banned and suspicious lists
        if user_id in bot_data.banned_users:
            del bot_data.banned_users[user_id]
        security.mark_user_safe(user_id)
        
        save_data(bot_data)
        await update.message.reply_text(f"✅ Akses diberikan ke user ID: {user_id}")
        logger.info(f"ACCESS GRANTED - User ID: {user_id}")
        print_status()
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Format: /akses [USER_ID]")

async def revoke_access(update: Update, context: CallbackContext):
    """Revoke user access"""
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("❌ Hanya admin yang dapat menggunakan perintah ini")
        return
    
    try:
        user_id = int(context.args[0])
        bot_data.approved_users.discard(user_id)
        save_data(bot_data)
        await update.message.reply_text(f"❌ Akses dicabut dari user ID: {user_id}")
        logger.info(f"ACCESS REVOKED - User ID: {user_id}")
        print_status()
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Format: /hapus_akses [USER_ID]")

async def ban_user(update: Update, context: CallbackContext):
    """Ban user with duration"""
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("❌ Hanya admin yang dapat menggunakan perintah ini")
        return
    
    try:
        user_id = int(context.args[0])
        duration = int(context.args[1]) if len(context.args) > 1 else 0
        
        if duration > 0:
            ban_end = datetime.now() + timedelta(days=duration)
            bot_data.banned_users[user_id] = ban_end
            msg = f"⛔ User ID {user_id} dibanned selama {duration} hari"
        else:
            bot_data.banned_users[user_id] = datetime.max
            msg = f"⛔ User ID {user_id} dibanned permanen"
        
        save_data(bot_data)
        await update.message.reply_text(msg)
        logger.info(f"BANNED - User ID: {user_id} | Duration: {duration} days")
        print_status()
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Format: /ban [USER_ID] [DAYS] (0=permanent)")

async def unban_user(update: Update, context: CallbackContext):
    """Unban user"""
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("❌ Hanya admin yang dapat menggunakan perintah ini")
        return
    
    try:
        user_id = int(context.args[0])
        if user_id in bot_data.banned_users:
            del bot_data.banned_users[user_id]
            save_data(bot_data)
            await update.message.reply_text(f"✅ User ID {user_id} diunban")
            logger.info(f"UNBANNED - User ID: {user_id}")
            print_status()
        else:
            await update.message.reply_text(f"ℹ️ User ID {user_id} tidak dalam status banned")
            
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Format: /unban [USER_ID]")

async def mute_user_cmd(update: Update, context: CallbackContext):
    """Mute user in group"""
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("❌ Hanya admin yang dapat menggunakan perintah ini")
        return
    
    if update.effective_chat.type == 'private':
        await update.message.reply_text("❌ Perintah ini hanya bisa digunakan di grup")
        return
    
    try:
        user_id = int(context.args[0])
        minutes = int(context.args[1]) if len(context.args) > 1 else 60
        
        await moderation._mute_user(update, context, user_id, minutes, "Admin command")
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Format: /mute [USER_ID] [MINUTES]")

async def unmute_user_cmd(update: Update, context: CallbackContext):
    """Unmute user in group"""
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("❌ Hanya admin yang dapat menggunakan perintah ini")
        return
    
    if update.effective_chat.type == 'private':
        await update.message.reply_text("❌ Perintah ini hanya bisa digunakan di grup")
        return
    
    try:
        user_id = int(context.args[0])
        success = await moderation.unmute_user(update, context, user_id)
        
        if success:
            await update.message.reply_text(f"✅ User ID {user_id} berhasil di-unmute")
        else:
            await update.message.reply_text(f"❌ Gagal unmute user ID {user_id}")
            
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Format: /unmute [USER_ID]")

async def reset_user_limits(update: Update, context: CallbackContext):
    """Reset rate limits for user"""
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("❌ Hanya admin yang dapat menggunakan perintah ini")
        return
    
    try:
        user_id = int(context.args[0])
        rate_limiter.reset_user_limits(user_id)
        anti_spam.reset_user_spam_data(user_id)
        
        await update.message.reply_text(f"✅ Rate limit dan spam data direset untuk user ID {user_id}")
        logger.info(f"LIMITS RESET - User ID: {user_id}")
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Format: /resetlimit [USER_ID]")

async def mark_user_safe(update: Update, context: CallbackContext):
    """Mark user as safe"""
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("❌ Hanya admin yang dapat menggunakan perintah ini")
        return
    
    try:
        user_id = int(context.args[0])
        security.mark_user_safe(user_id)
        
        # Reset spam data
        if user_id in bot_data.user_stats:
            bot_data.user_stats[user_id].spam_score = 0
            bot_data.user_stats[user_id].warnings = 0
            bot_data.user_stats[user_id].verification_status = "verified"
        
        save_data(bot_data)
        await update.message.reply_text(f"✅ User ID {user_id} ditandai sebagai aman")
        logger.info(f"MARKED SAFE - User ID: {user_id}")
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Format: /marksafe [USER_ID]")

async def create_backup_cmd(update: Update, context: CallbackContext):
    """Create manual backup"""
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("❌ Hanya admin yang dapat menggunakan perintah ini")
        return
    
    backup_path = backup_system.create_backup(bot_data, "manual")
    if backup_path:
        filename = os.path.basename(backup_path)
        await update.message.reply_text(f"✅ Backup berhasil dibuat: {filename}")
        logger.info(f"MANUAL BACKUP CREATED: {backup_path}")
    else:
        await update.message.reply_text("❌ Gagal membuat backup")

async def change_session_id(update: Update, context: CallbackContext):
    """Change session ID"""
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("❌ Hanya admin yang dapat menggunakan perintah ini")
        return
    
    old_id = bot_data.session_id
    import random
    bot_data.session_id = str(random.randint(100000, 999999))
    save_data(bot_data)
    
    await update.message.reply_text(
        f"✅ Session ID diperbarui\n\n"
        f"Lama: {old_id}\n"
        f"Baru: {bot_data.session_id}"
    )
    logger.info(f"CHANGED SESSION - New ID: {bot_data.session_id}")
    print_status()

# ===== MESSAGE HANDLERS =====

async def handle_text_message(update: Update, context: CallbackContext):
    """Handle text messages"""
    await handle_text(update, context, bot_data)

async def handle_photo_message(update: Update, context: CallbackContext):
    """Handle photo messages"""
    await handle_image(update, context, bot_data)

# ===== BACKGROUND TASKS =====

async def cleanup_task(context: CallbackContext):
    """Periodic cleanup task"""
    try:
        # Clean old data
        bot_data.clean_old_data()
        
        # Clean up expired sessions
        security.cleanup_old_sessions()
        
        # Clean up expired restrictions
        await moderation.cleanup_expired_restrictions(context)
        
        # Auto backup if needed
        if backup_system.auto_backup_needed(bot_data):
            backup_path = backup_system.create_backup(bot_data, "auto")
            if backup_path:
                logger.info(f"AUTO BACKUP CREATED: {backup_path}")
        
        # Save data
        save_data(bot_data)
        
        logger.debug("Cleanup task completed")
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")

# ===== MAIN APPLICATION =====

def main():
    """Main application entry point"""
    print(f"🚀 Starting Alya Bot v2.0...")
    print(f"📝 Config loaded: {config.TOKEN[:10]}...")
    print_status()
    
    # Create application
    application = Application.builder().token(config.TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", user_status))
    
    # Admin commands
    application.add_handler(CommandHandler("adminstatus", admin_status))
    application.add_handler(CommandHandler("on", turn_on))
    application.add_handler(CommandHandler("off", turn_off))
    application.add_handler(CommandHandler("akses", grant_access))
    application.add_handler(CommandHandler("hapus_akses", revoke_access))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("mute", mute_user_cmd))
    application.add_handler(CommandHandler("unmute", unmute_user_cmd))
    application.add_handler(CommandHandler("resetlimit", reset_user_limits))
    application.add_handler(CommandHandler("marksafe", mark_user_safe))
    application.add_handler(CommandHandler("backup", create_backup_cmd))
    application.add_handler(CommandHandler("changeid", change_session_id))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Add cleanup job
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(cleanup_task, interval=300, first=60)  # Every 5 minutes
    else:
        logger.warning("JobQueue not available - cleanup tasks will not run automatically")
    
    # Start bot
    logger.info("🤖 Alya Bot v2.0 started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
