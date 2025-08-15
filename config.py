import os
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class BotConfig:
    """Bot configuration class with all settings"""
    
    # Bot credentials
    TOKEN: str = os.getenv("TELEGRAM_TOKEN", "YOUR BOT TOKEN")
    API_URL: str = "https://api.ryzumi.vip/api/ai/v2/chatgpt"
    OWNER_ID: int = YOUR TELEGRAM ID
    
    # File paths
    DATA_FILE: str = "alya_data.json"
    BACKUP_DIR: str = "backups"
    LOG_FILE: str = "bot.log"
    
    # Rate limiting settings
    MAX_MESSAGES_PER_MINUTE: int = 10
    MAX_MESSAGES_PER_HOUR: int = 100
    MAX_API_CALLS_PER_MINUTE: int = 5
    COOLDOWN_PERIOD: int = 60  # seconds
    
    # Anti-spam settings
    MAX_MESSAGE_LENGTH: int = 4000
    MAX_IDENTICAL_MESSAGES: int = 3
    SPAM_SCORE_THRESHOLD: int = 5
    AUTO_BAN_SPAM_SCORE: int = 10
    
    # Moderation settings
    ENABLE_PROFANITY_FILTER: bool = True
    ENABLE_LINK_FILTER: bool = True
    ENABLE_CAPS_FILTER: bool = True
    MAX_CAPS_PERCENTAGE: float = 0.7
    
    # Security settings
    ENABLE_USER_VERIFICATION: bool = True
    MIN_ACCOUNT_AGE_DAYS: int = 7
    ENABLE_CAPTCHA: bool = False
    SESSION_TIMEOUT_HOURS: int = 24
    
    # Backup settings
    AUTO_BACKUP_INTERVAL: int = 3600  # seconds (1 hour)
    MAX_BACKUP_FILES: int = 10
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    ENABLE_CONSOLE_LOGGING: bool = True
    ENABLE_FILE_LOGGING: bool = True
    
    # Spam patterns (regex patterns)
    SPAM_PATTERNS: List[str] = field(default_factory=lambda: [
        r'\b(viagra|cialis|casino|lottery|winner|congratulations)\b',
        r'\b(click here|free money|make money fast|get rich quick)\b',
        r'\b(bitcoin|crypto|investment|forex|trading)\b.*(guaranteed|profit|returns)\b',
        r'https?://(?:bit\.ly|tinyurl|t\.co|short\.link)/',  # Suspicious short links
        r'\b(join now|limited time|act now|urgent|hurry)\b',
    ])
    
    # Profanity filter words
    PROFANITY_WORDS: List[str] = field(default_factory=lambda: [
        # Add your profanity words here - keeping it minimal for example
        'spam', 'scam', 'fake'
    ])
    
    @classmethod
    def load_from_env(cls) -> 'BotConfig':
        """Load configuration from environment variables"""
        config = cls()
        
        # Override with environment variables if they exist
        config.TOKEN = os.getenv("TELEGRAM_TOKEN", config.TOKEN)
        config.API_URL = os.getenv("API_URL", config.API_URL)
        config.OWNER_ID = int(os.getenv("OWNER_ID", str(config.OWNER_ID)))
        
        # Rate limiting
        config.MAX_MESSAGES_PER_MINUTE = int(os.getenv("MAX_MESSAGES_PER_MINUTE", str(config.MAX_MESSAGES_PER_MINUTE)))
        config.MAX_MESSAGES_PER_HOUR = int(os.getenv("MAX_MESSAGES_PER_HOUR", str(config.MAX_MESSAGES_PER_HOUR)))
        
        # Security
        config.MIN_ACCOUNT_AGE_DAYS = int(os.getenv("MIN_ACCOUNT_AGE_DAYS", str(config.MIN_ACCOUNT_AGE_DAYS)))
        
        return config

# Global config instance
config = BotConfig.load_from_env()
