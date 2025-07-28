"""
Utility functions for error handling, validation, and common operations.
"""

import logging
import time
from typing import Optional, Any, Dict
from functools import wraps
from datetime import datetime

from .models import ErrorCode, ERROR_MESSAGES, ErrorLog


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.E400_INVALID_INPUT):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class ProcessingError(Exception):
    """Custom exception for processing errors."""
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.E500_PROCESSING_FAILED):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


def create_error_log(document: str, error_code: ErrorCode, custom_reason: Optional[str] = None) -> ErrorLog:
    """
    Create a standardized error log entry.
    
    Args:
        document: Name of the document that failed
        error_code: Standard error code
        custom_reason: Optional custom reason, defaults to standard message
    
    Returns:
        ErrorLog instance
    """
    reason = custom_reason or ERROR_MESSAGES.get(error_code, "Unknown error")
    return ErrorLog(
        document=document,
        error_code=error_code,
        reason=reason,
        timestamp=datetime.utcnow()
    )


def validate_file_path(file_path: str) -> bool:
    """
    Validate that a file path exists and is accessible.
    
    Args:
        file_path: Path to validate
        
    Returns:
        True if valid, False otherwise
    """
    import os
    try:
        return os.path.exists(file_path) and os.path.isfile(file_path)
    except (OSError, TypeError):
        return False


def validate_pdf_file(file_path: str) -> bool:
    """
    Validate that a file is a valid PDF.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        True if valid PDF, False otherwise
    """
    if not validate_file_path(file_path):
        return False
    
    try:
        import PyMuPDF as fitz
        doc = fitz.open(file_path)
        doc.close()
        return True
    except Exception:
        return False


def truncate_text(text: str, max_length: int = 150) -> str:
    """
    Truncate text to specified length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including ellipsis
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def timing_decorator(func):
    """
    Decorator to measure execution time of functions.
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            end_time = time.time()
            logger.info(f"{func.__name__} completed in {end_time - start_time:.3f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            logger.error(f"{func.__name__} failed after {end_time - start_time:.3f} seconds: {str(e)}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            logger.info(f"{func.__name__} completed in {end_time - start_time:.3f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            logger.error(f"{func.__name__} failed after {end_time - start_time:.3f} seconds: {str(e)}")
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def safe_execute(func, *args, default_return=None, log_errors=True, **kwargs):
    """
    Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        *args: Function arguments
        default_return: Default return value on error
        log_errors: Whether to log errors
        **kwargs: Function keyword arguments
        
    Returns:
        Function result or default_return on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Error executing {func.__name__}: {str(e)}")
        return default_return


def format_processing_metadata(
    input_documents: list,
    persona: str,
    job_to_be_done: str,
    successful_chunks: int = 0,
    total_documents: int = 0,
    errors: Optional[list] = None,
    processing_time: Optional[float] = None
) -> Dict[str, Any]:
    """
    Format metadata for response.
    
    Args:
        input_documents: List of input document filenames
        persona: User persona
        job_to_be_done: User's task
        successful_chunks: Number of successfully extracted chunks
        total_documents: Number of successfully processed documents
        errors: List of errors
        processing_time: Total processing time
        
    Returns:
        Formatted metadata dictionary
    """
    return {
        "input_documents": input_documents,
        "persona": persona,
        "job_to_be_done": job_to_be_done,
        "processing_timestamp": datetime.utcnow(),
        "total_documents_processed": total_documents,
        "total_chunks_extracted": successful_chunks,
        "errors": errors or [],
        "processing_time_seconds": processing_time
    }


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to remove potentially harmful characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    # Remove or replace potentially dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')
    return sanitized if sanitized else "unknown_file"


def generate_chunk_id(document: str, page: int, chunk_index: int) -> str:
    """
    Generate a unique identifier for a text chunk.
    
    Args:
        document: Source document name
        page: Page number
        chunk_index: Index of chunk on the page
        
    Returns:
        Unique chunk identifier
    """
    import hashlib
    # Create a hash-based ID for uniqueness
    content = f"{document}_{page}_{chunk_index}_{int(time.time())}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def is_text_meaningful(text: str, min_length: int = 10) -> bool:
    """
    Check if text content is meaningful (not just whitespace, special chars, etc.).
    
    Args:
        text: Text to check
        min_length: Minimum length for meaningful text
        
    Returns:
        True if text is meaningful
    """
    import re
    # Remove whitespace and common non-meaningful characters
    cleaned = re.sub(r'[\s\-_=\.\,\;\:\!\?\(\)\[\]\{\}]+', '', text)
    
    # Check if remaining text has sufficient alphabetic content
    alpha_chars = len(re.findall(r'[a-zA-Z]', cleaned))
    total_chars = len(cleaned)
    
    return (
        len(cleaned) >= min_length and
        total_chars > 0 and
        (alpha_chars / total_chars) > 0.3  # At least 30% alphabetic
    )
