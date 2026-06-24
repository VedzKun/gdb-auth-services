"""
Centralized Error Logging Module for GDB Banking Services

This module provides comprehensive error logging functionality including:
- File-based logging with rotation
- Structured error logging with context
- Error categorization and severity levels
- Integration with existing service loggers

Author: GDB Architecture Team
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
import json
import traceback
from typing import Optional, Dict, Any


class ErrorLogger:
    """Centralized error logger with file rotation and structured logging."""
    
    def __init__(self, service_name: str, log_dir: str = "logs"):
        """
        Initialize error logger for a service.
        
        Args:
            service_name: Name of the service (e.g., 'accounts_service')
            log_dir: Directory to store log files
        """
        self.service_name = service_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(f"{service_name}.errors")
        self.logger.setLevel(logging.ERROR)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup file and console handlers with formatters."""
        
        # File handler with daily rotation
        error_log_file = self.log_dir / f"{self.service_name}_errors.log"
        file_handler = TimedRotatingFileHandler(
            error_log_file,
            when='midnight',
            interval=1,
            backupCount=30,  # Keep 30 days of logs
            encoding='utf-8'
        )
        file_handler.setLevel(logging.ERROR)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.ERROR)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        severity: str = "ERROR"
    ):
        """
        Log an error with structured context.
        
        Args:
            error: The exception that occurred
            context: Additional context information
            user_id: User ID if applicable
            endpoint: API endpoint where error occurred
            severity: Error severity (ERROR, CRITICAL, WARNING)
        """
        error_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
            "severity": severity,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "user_id": user_id,
            "endpoint": endpoint,
            "context": context or {}
        }
        
        # Log as JSON for easy parsing
        self.logger.error(json.dumps(error_data, indent=2))
    
    def log_validation_error(
        self,
        field: str,
        value: Any,
        message: str,
        user_id: Optional[str] = None
    ):
        """Log validation errors."""
        self.log_error(
            ValueError(f"Validation failed for {field}: {message}"),
            context={
                "field": field,
                "value": str(value),
                "validation_message": message
            },
            user_id=user_id,
            severity="WARNING"
        )
    
    def log_database_error(
        self,
        error: Exception,
        query: Optional[str] = None,
        params: Optional[Dict] = None
    ):
        """Log database-related errors."""
        self.log_error(
            error,
            context={
                "query": query,
                "params": params,
                "database_error": True
            },
            severity="CRITICAL"
        )
    
    def log_authentication_error(
        self,
        error: Exception,
        login_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log authentication/authorization errors."""
        self.log_error(
            error,
            context={
                "login_id": login_id,
                "ip_address": ip_address,
                "auth_error": True
            },
            severity="WARNING"
        )
    
    def log_business_logic_error(
        self,
        error: Exception,
        operation: str,
        user_id: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log business logic errors."""
        self.log_error(
            error,
            context={
                "operation": operation,
                "details": details or {},
                "business_logic_error": True
            },
            user_id=user_id,
            severity="ERROR"
        )


# Global error logger instances for each service
_error_loggers: Dict[str, ErrorLogger] = {}


def get_error_logger(service_name: str) -> ErrorLogger:
    """
    Get or create an error logger for a service.
    
    Args:
        service_name: Name of the service
        
    Returns:
        ErrorLogger instance
    """
    if service_name not in _error_loggers:
        _error_loggers[service_name] = ErrorLogger(service_name)
    return _error_loggers[service_name]


# Convenience functions for quick error logging
def log_error(service_name: str, error: Exception, **kwargs):
    """Quick error logging function."""
    logger = get_error_logger(service_name)
    logger.log_error(error, **kwargs)


def log_critical(service_name: str, error: Exception, **kwargs):
    """Log critical errors."""
    logger = get_error_logger(service_name)
    logger.log_error(error, severity="CRITICAL", **kwargs)
