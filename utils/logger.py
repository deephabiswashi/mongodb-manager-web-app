"""
Structured logging setup for the application
"""
import logging
import sys
from datetime import datetime
import uuid


class StructuredLogger:
    """Custom logger with error IDs"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - [ERROR_ID:%(error_id)s] - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (optional - creates app.log)
        try:
            file_handler = logging.FileHandler('app.log')
            file_handler.setLevel(logging.ERROR)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except Exception:
            pass  # Skip file logging if not writable
    
    def _generate_error_id(self) -> str:
        """Generate a unique error ID"""
        return str(uuid.uuid4())[:8].upper()
    
    def info(self, message: str, error_id: str = None):
        """Log info message"""
        if not error_id:
            error_id = self._generate_error_id()
        self.logger.info(message, extra={'error_id': error_id})
        return error_id
    
    def warning(self, message: str, error_id: str = None):
        """Log warning message"""
        if not error_id:
            error_id = self._generate_error_id()
        self.logger.warning(message, extra={'error_id': error_id})
        return error_id
    
    def error(self, message: str, error_id: str = None, exc_info=None):
        """Log error message with optional exception info"""
        if not error_id:
            error_id = self._generate_error_id()
        self.logger.error(message, extra={'error_id': error_id}, exc_info=exc_info)
        return error_id
    
    def exception(self, message: str, error_id: str = None):
        """Log exception with traceback"""
        if not error_id:
            error_id = self._generate_error_id()
        self.logger.exception(message, extra={'error_id': error_id})
        return error_id


# Global logger instance
app_logger = StructuredLogger('mongodb_manager')

