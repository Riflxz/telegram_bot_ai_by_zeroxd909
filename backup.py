import os
import json
import shutil
import logging
from datetime import datetime
from typing import Optional
from config import config
from bot_data import BotData

logger = logging.getLogger(__name__)

class BackupSystem:
    """Backup and restore system for bot data"""
    
    def __init__(self):
        self.ensure_backup_directory()
    
    def ensure_backup_directory(self):
        """Ensure backup directory exists"""
        if not os.path.exists(config.BACKUP_DIR):
            os.makedirs(config.BACKUP_DIR)
            logger.info(f"Created backup directory: {config.BACKUP_DIR}")
    
    def create_backup(self, bot_data: BotData, backup_type: str = "manual") -> Optional[str]:
        """Create a backup of bot data"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"alya_backup_{backup_type}_{timestamp}.json"
            backup_path = os.path.join(config.BACKUP_DIR, backup_filename)
            
            # Create backup data
            backup_data = {
                "backup_info": {
                    "timestamp": datetime.now().isoformat(),
                    "type": backup_type,
                    "version": "2.0"
                },
                "bot_data": bot_data.to_dict()
            }
            
            # Write backup
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            # Update bot data with backup info
            bot_data.last_backup_time = datetime.now()
            
            logger.info(f"Backup created: {backup_path}")
            
            # Clean old backups
            self.cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def restore_backup(self, backup_path: str) -> Optional[BotData]:
        """Restore bot data from backup"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return None
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Validate backup format
            if "bot_data" not in backup_data:
                logger.error("Invalid backup format")
                return None
            
            # Restore bot data
            bot_data = BotData.from_dict(backup_data["bot_data"])
            
            logger.info(f"Backup restored from: {backup_path}")
            return bot_data
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return None
    
    def list_backups(self) -> list:
        """List available backups"""
        try:
            backups = []
            if os.path.exists(config.BACKUP_DIR):
                for filename in os.listdir(config.BACKUP_DIR):
                    if filename.startswith("alya_backup_") and filename.endswith(".json"):
                        filepath = os.path.join(config.BACKUP_DIR, filename)
                        stat = os.stat(filepath)
                        backups.append({
                            "filename": filename,
                            "path": filepath,
                            "size": stat.st_size,
                            "created": datetime.fromtimestamp(stat.st_ctime)
                        })
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x["created"], reverse=True)
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    def cleanup_old_backups(self):
        """Remove old backup files"""
        try:
            backups = self.list_backups()
            
            if len(backups) > config.MAX_BACKUP_FILES:
                # Remove oldest backups
                backups_to_remove = backups[config.MAX_BACKUP_FILES:]
                
                for backup in backups_to_remove:
                    os.remove(backup["path"])
                    logger.info(f"Removed old backup: {backup['filename']}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
    
    def get_backup_info(self, backup_path: str) -> Optional[dict]:
        """Get information about a backup file"""
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            return backup_data.get("backup_info", {})
            
        except Exception as e:
            logger.error(f"Failed to get backup info: {e}")
            return None
    
    def auto_backup_needed(self, bot_data: BotData) -> bool:
        """Check if automatic backup is needed"""
        if not bot_data.last_backup_time:
            return True
        
        time_since_backup = datetime.now() - bot_data.last_backup_time
        return time_since_backup.total_seconds() >= config.AUTO_BACKUP_INTERVAL
    
    def emergency_backup(self, bot_data: BotData) -> Optional[str]:
        """Create emergency backup (e.g., before critical operations)"""
        return self.create_backup(bot_data, "emergency")

# Global backup system instance
backup_system = BackupSystem()
