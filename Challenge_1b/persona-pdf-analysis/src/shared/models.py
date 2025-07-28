"""
Core data models for the Persona-Driven PDF Analysis Agent.
Implements all required data structures with Pydantic validation.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for the system."""
    E404_FILE_NOT_FOUND = "E404_FILE_NOT_FOUND"
    E415_UNSUPPORTED_FORMAT = "E415_UNSUPPORTED_FORMAT"  
    E423_FILE_ENCRYPTED = "E423_FILE_ENCRYPTED"
    E500_PROCESSING_FAILED = "E500_PROCESSING_FAILED"
    E400_INVALID_INPUT = "E400_INVALID_INPUT"
    E503_SERVICE_UNAVAILABLE = "E503_SERVICE_UNAVAILABLE"


ERROR_MESSAGES = {
    ErrorCode.E404_FILE_NOT_FOUND: "Document file not accessible",
    ErrorCode.E415_UNSUPPORTED_FORMAT: "Invalid PDF format",
    ErrorCode.E423_FILE_ENCRYPTED: "Password-protected PDF",
    ErrorCode.E500_PROCESSING_FAILED: "Unexpected processing error",
    ErrorCode.E400_INVALID_INPUT: "Invalid input format",
    ErrorCode.E503_SERVICE_UNAVAILABLE: "External service unavailable"
}


# Input Models
class ChallengeInfo(BaseModel):
    """Challenge information from the input request."""
    challenge_id: str = Field(..., description="Unique identifier for the challenge")
    test_case_name: str = Field(..., description="Name of the test case")
    description: str = Field(..., description="Description of the challenge")


class Document(BaseModel):
    """Document information in the input request."""
    filename: str = Field(..., description="Name of the PDF file")
    title: str = Field(..., description="Human-readable title of the document")
    
    @validator('filename')
    def validate_filename(cls, v):
        if not v.endswith('.pdf'):
            raise ValueError('Document filename must end with .pdf')
        return v


class Persona(BaseModel):
    """User persona information."""
    role: str = Field(..., description="Professional role of the user")
    
    @validator('role')
    def validate_role(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Role cannot be empty')
        return v.strip()


class JobToBeDone(BaseModel):
    """Job to be done information."""
    task: str = Field(..., description="Specific task to be accomplished")
    
    @validator('task')
    def validate_task(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Task cannot be empty')
        return v.strip()


class RequestJSON(BaseModel):
    """Main input request model."""
    challenge_info: ChallengeInfo
    documents: List[Document] = Field(..., min_items=1, description="List of documents to process")
    persona: Persona
    job_to_be_done: JobToBeDone
    
    @validator('documents')
    def validate_documents(cls, v):
        if len(v) == 0:
            raise ValueError('At least one document must be provided')
        return v


# Processing Models
class TextChunk(BaseModel):
    """Extracted text chunk with metadata."""
    text: str = Field(..., description="Extracted text content")
    page_number: int = Field(..., ge=1, description="Page number (1-indexed)")
    section_title: Optional[str] = Field(None, description="Section title if available")
    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    document_source: str = Field(..., description="Source document filename")
    
    @validator('text')
    def validate_text(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Text chunk cannot be empty')
        return v.strip()


class RankedChunk(BaseModel):
    """Text chunk with relevance scoring."""
    chunk: TextChunk
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score from 0.0 to 1.0")


class ErrorLog(BaseModel):
    """Error information for failed processing."""
    document: str = Field(..., description="Document that failed to process")
    error_code: ErrorCode = Field(..., description="Standard error code")
    reason: str = Field(..., description="Human-readable error description")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the error occurred")


# Output Models
class ExtractedSection(BaseModel):
    """Extracted section in the final output."""
    document: str = Field(..., description="Source document filename")
    section_title: str = Field(..., description="Title of the extracted section")
    text_preview: str = Field(..., max_length=150, description="Preview of the text content")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    page_number: int = Field(..., ge=1, description="Page number")
    
    @validator('text_preview')
    def validate_text_preview(cls, v):
        if len(v) > 150:
            return v[:147] + "..."
        return v


class ResponseMetadata(BaseModel):
    """Metadata for the response."""
    input_documents: List[str] = Field(..., description="List of input document filenames")
    persona: str = Field(..., description="User persona role")
    job_to_be_done: str = Field(..., description="User's task description")
    processing_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")
    total_documents_processed: int = Field(..., ge=0, description="Number of documents successfully processed")
    total_chunks_extracted: int = Field(..., ge=0, description="Total number of text chunks extracted")
    errors: Optional[List[ErrorLog]] = Field(default=None, description="Processing errors if any")
    processing_time_seconds: Optional[float] = Field(None, ge=0.0, description="Total processing time")


class ResponseJSON(BaseModel):
    """Main output response model."""
    metadata: ResponseMetadata
    extracted_sections: List[ExtractedSection] = Field(..., description="Ranked extracted sections")


# Tool Interface Models
class QueryFormulationInput(BaseModel):
    """Input for Query Formulation Tool."""
    persona: Persona
    job_to_be_done: JobToBeDone


class QueryFormulationOutput(BaseModel):
    """Output from Query Formulation Tool."""
    semantic_query: str = Field(..., description="Formulated semantic query")
    status: str = Field(..., description="Processing status")
    error_code: Optional[ErrorCode] = Field(None, description="Error code if failed")


class DocumentProcessorInput(BaseModel):
    """Input for Document Processor Tool."""
    document_path: str = Field(..., description="Absolute path to the PDF document")


class DocumentProcessorOutput(BaseModel):
    """Output from Document Processor Tool."""
    chunks: Optional[List[TextChunk]] = Field(None, description="Extracted text chunks")
    status: str = Field(..., description="Processing status")
    error_code: Optional[ErrorCode] = Field(None, description="Error code if failed")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class SemanticRankingInput(BaseModel):
    """Input for Semantic Ranking Tool."""
    chunks: List[TextChunk] = Field(..., description="Text chunks to rank")
    query: str = Field(..., description="Semantic query for ranking")


class SemanticRankingOutput(BaseModel):
    """Output from Semantic Ranking Tool."""
    ranked_chunks: Optional[List[RankedChunk]] = Field(None, description="Ranked text chunks")
    status: str = Field(..., description="Processing status")
    error_code: Optional[ErrorCode] = Field(None, description="Error code if failed")


class JSONFormatterInput(BaseModel):
    """Input for JSON Output Formatter Tool."""
    ranked_chunks: List[RankedChunk] = Field(..., description="Ranked chunks to format")
    metadata: Dict[str, Any] = Field(..., description="Metadata for the response")


class JSONFormatterOutput(BaseModel):
    """Output from JSON Output Formatter Tool."""
    response: Optional[ResponseJSON] = Field(None, description="Formatted response")
    status: str = Field(..., description="Processing status")
    error_code: Optional[ErrorCode] = Field(None, description="Error code if failed")


# Processing Result Models
class ProcessingResult(BaseModel):
    """Result from processing a single document."""
    success: bool = Field(..., description="Whether processing was successful")
    chunks: Optional[List[TextChunk]] = Field(None, description="Extracted chunks if successful")
    error: Optional[ErrorLog] = Field(None, description="Error information if failed")
    document_path: str = Field(..., description="Path to the processed document")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
