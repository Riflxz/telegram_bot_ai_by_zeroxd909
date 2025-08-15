import requests
import logging
from typing import Optional
from telegram import Update
from config import config

logger = logging.getLogger(__name__)

async def send_typing(update: Update):
    """Send typing action to show bot is processing"""
    try:
        await update.effective_chat.send_action(action="typing")
    except Exception as e:
        logger.error(f"Failed to send typing action: {e}")

async def get_ai_response(text: str, user_id: int, image_url: Optional[str] = None) -> str:
    """Get AI response with enhanced error handling"""
    try:
        params = {
            "text": text,
            "prompt": "Kamu adalah Alya, asisten virtual perempuan yang ramah, baik, peka, tulen, sedikit wibu dan helpful. kamu selalu menggunakan bahasa Indonesia yang gaul dan tidak suka basa basi.",
            "session": f"user_{user_id}",  # User-specific session
            "imageUrl": image_url
        }
        
        # Add timeout to prevent hanging
        response = requests.get(config.API_URL, params=params, timeout=30)
        response.raise_for_status()  # Raise exception for bad status codes
        
        data = response.json()
        ai_response = data.get('result', '')
        
        if not ai_response:
            return "❌ Aku sedang tidak bisa merespon. Coba lagi nanti ya!"
        
        # Validate response length
        if len(ai_response) > 4000:  # Telegram message limit
            ai_response = ai_response[:3950] + "... (pesan dipotong)"
        
        return ai_response
        
    except requests.exceptions.Timeout:
        logger.error("API request timeout")
        return "⏰ Respons API timeout. Coba lagi nanti ya!"
        
    except requests.exceptions.ConnectionError:
        logger.error("API connection error")
        return "🔌 Gagal terhubung ke API. Coba lagi nanti ya!"
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"API HTTP error: {e}")
        return "🚫 API sedang bermasalah. Coba lagi nanti ya!"
        
    except Exception as e:
        logger.error(f"Unexpected API error: {str(e)}")
        return "⚠️ Terjadi kesalahan sistem. Coba lagi nanti ya!"

def format_time_duration(seconds: int) -> str:
    """Format seconds into human readable duration"""
    if seconds < 60:
        return f"{seconds} detik"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} menit"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} jam {minutes} menit"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days} hari {hours} jam"

def sanitize_text(text: str) -> str:
    """Sanitize text for safe display"""
    # Remove potential HTML/markdown injection
    dangerous_chars = ['<', '>', '`', '*', '_', '[', ']', '\\']
    for char in dangerous_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def is_admin_user(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id == config.OWNER_ID

def get_user_display_name(user) -> str:
    """Get user display name safely"""
    if user.username:
        return f"@{user.username}"
    elif user.first_name:
        name = user.first_name
        if user.last_name:
            name += f" {user.last_name}"
        return name
    else:
        return f"User {user.id}"
