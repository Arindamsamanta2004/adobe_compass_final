"""
Shared utilities and models for the Persona-Driven PDF Analysis Agent.
"""

from .models import (
    RequestJSON,
    ResponseJSON,
    TextChunk,
    RankedChunk,
    ErrorLog,
    ErrorCode,
    ERROR_MESSAGES,
    ProcessingResult,
    QueryFormulationInput,
    QueryFormulationOutput,
    DocumentProcessorInput,
    DocumentProcessorOutput,
    SemanticRankingInput,
    SemanticRankingOutput,
    JSONFormatterInput,
    JSONFormatterOutput,
    ResponseMetadata,
    ExtractedSection
)

from .utils import (
    ValidationError,
    ProcessingError,
    create_error_log,
    validate_file_path,
    validate_pdf_file,
    truncate_text,
    timing_decorator,
    safe_execute,
    format_processing_metadata,
    sanitize_filename,
    generate_chunk_id,
    is_text_meaningful
)

__all__ = [
    # Models
    "RequestJSON",
    "ResponseJSON", 
    "TextChunk",
    "RankedChunk",
    "ErrorLog",
    "ErrorCode",
    "ERROR_MESSAGES",
    "ProcessingResult",
    "QueryFormulationInput",
    "QueryFormulationOutput",
    "DocumentProcessorInput", 
    "DocumentProcessorOutput",
    "SemanticRankingInput",
    "SemanticRankingOutput",
    "JSONFormatterInput",
    "JSONFormatterOutput",
    "ResponseMetadata",
    "ExtractedSection",
    
    # Utilities
    "ValidationError",
    "ProcessingError",
    "create_error_log",
    "validate_file_path",
    "validate_pdf_file",
    "truncate_text",
    "timing_decorator",
    "safe_execute",
    "format_processing_metadata",
    "sanitize_filename",
    "generate_chunk_id",
    "is_text_meaningful"
]
