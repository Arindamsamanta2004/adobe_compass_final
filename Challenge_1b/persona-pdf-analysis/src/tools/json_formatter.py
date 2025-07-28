"""
JSON Output Formatter Tool

This tool formats ranked chunks into the final JSON response with schema validation.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..shared import (
    JSONFormatterInput,
    JSONFormatterOutput,
    ResponseJSON,
    ResponseMetadata,
    ExtractedSection,
    RankedChunk,
    ErrorCode,
    ProcessingError,
    timing_decorator,
    truncate_text
)

logger = logging.getLogger(__name__)


class JSONOutputFormatterTool:
    """
    Tool for formatting final JSON output with schema validation.
    Ensures 100% compliance with the specified JSON schema.
    """
    
    def __init__(self, max_sections: int = 50):
        """
        Initialize the JSON Output Formatter Tool.
        
        Args:
            max_sections: Maximum number of sections to include in output
        """
        self.max_sections = max_sections
        self.text_preview_length = 150

    def _create_extracted_sections(self, ranked_chunks: List[RankedChunk]) -> List[ExtractedSection]:
        """
        Create ExtractedSection objects from ranked chunks.
        
        Args:
            ranked_chunks: List of ranked text chunks
            
        Returns:
            List of ExtractedSection objects
        """
        extracted_sections = []
        
        # Take top sections up to max_sections limit
        top_chunks = ranked_chunks[:self.max_sections]
        
        for ranked_chunk in top_chunks:
            chunk = ranked_chunk.chunk
            
            # Create text preview with truncation
            text_preview = truncate_text(chunk.text, self.text_preview_length)
            
            # Ensure section title is not None
            section_title = chunk.section_title or "Untitled Section"
            
            # Create extracted section
            section = ExtractedSection(
                document=chunk.document_source,
                section_title=section_title,
                text_preview=text_preview,
                relevance_score=ranked_chunk.relevance_score,
                page_number=chunk.page_number
            )
            
            extracted_sections.append(section)
        
        logger.info(f"Created {len(extracted_sections)} extracted sections")
        return extracted_sections

    def _create_response_metadata(self, metadata: Dict[str, Any]) -> ResponseMetadata:
        """
        Create ResponseMetadata object from input metadata.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            ResponseMetadata object
        """
        # Extract required fields with defaults
        input_documents = metadata.get('input_documents', [])
        persona = metadata.get('persona', 'Unknown')
        job_to_be_done = metadata.get('job_to_be_done', 'Unknown')
        
        # Extract optional fields
        total_documents_processed = metadata.get('total_documents_processed', 0)
        total_chunks_extracted = metadata.get('total_chunks_extracted', 0)
        errors = metadata.get('errors', [])
        processing_time = metadata.get('processing_time_seconds')
        
        # Ensure timestamp is datetime object
        processing_timestamp = metadata.get('processing_timestamp')
        if not isinstance(processing_timestamp, datetime):
            processing_timestamp = datetime.utcnow()
        
        response_metadata = ResponseMetadata(
            input_documents=input_documents,
            persona=persona,
            job_to_be_done=job_to_be_done,
            processing_timestamp=processing_timestamp,
            total_documents_processed=total_documents_processed,
            total_chunks_extracted=total_chunks_extracted,
            errors=errors,
            processing_time_seconds=processing_time
        )
        
        return response_metadata

    def _validate_response_schema(self, response: ResponseJSON) -> bool:
        """
        Validate the response against the expected schema.
        
        Args:
            response: Response to validate
            
        Returns:
            True if valid
            
        Raises:
            ProcessingError: If validation fails
        """
        try:
            # Basic structure validation
            if not hasattr(response, 'metadata') or not hasattr(response, 'extracted_sections'):
                raise ProcessingError(
                    "Response missing required fields",
                    ErrorCode.E500_PROCESSING_FAILED
                )
            
            # Metadata validation
            metadata = response.metadata
            required_metadata_fields = [
                'input_documents', 'persona', 'job_to_be_done', 
                'processing_timestamp', 'total_documents_processed', 
                'total_chunks_extracted'
            ]
            
            for field in required_metadata_fields:
                if not hasattr(metadata, field):
                    raise ProcessingError(
                        f"Metadata missing required field: {field}",
                        ErrorCode.E500_PROCESSING_FAILED
                    )
            
            # Extracted sections validation
            sections = response.extracted_sections
            if not isinstance(sections, list):
                raise ProcessingError(
                    "extracted_sections must be a list",
                    ErrorCode.E500_PROCESSING_FAILED
                )
            
            # Validate each section
            for i, section in enumerate(sections):
                required_section_fields = [
                    'document', 'section_title', 'text_preview', 
                    'relevance_score', 'page_number'
                ]
                
                for field in required_section_fields:
                    if not hasattr(section, field):
                        raise ProcessingError(
                            f"Section {i} missing required field: {field}",
                            ErrorCode.E500_PROCESSING_FAILED
                        )
                
                # Validate field types and ranges
                if not isinstance(section.relevance_score, (int, float)):
                    raise ProcessingError(
                        f"Section {i} relevance_score must be numeric",
                        ErrorCode.E500_PROCESSING_FAILED
                    )
                
                if not (0.0 <= section.relevance_score <= 1.0):
                    raise ProcessingError(
                        f"Section {i} relevance_score must be between 0.0 and 1.0",
                        ErrorCode.E500_PROCESSING_FAILED
                    )
                
                if not isinstance(section.page_number, int) or section.page_number < 1:
                    raise ProcessingError(
                        f"Section {i} page_number must be positive integer",
                        ErrorCode.E500_PROCESSING_FAILED
                    )
                
                if len(section.text_preview) > self.text_preview_length:
                    raise ProcessingError(
                        f"Section {i} text_preview exceeds maximum length",
                        ErrorCode.E500_PROCESSING_FAILED
                    )
            
            logger.info("Response schema validation passed")
            return True
            
        except ProcessingError:
            raise
        except Exception as e:
            logger.error(f"Schema validation error: {str(e)}")
            raise ProcessingError(
                f"Schema validation failed: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )

    def _ensure_json_serializable(self, response: ResponseJSON) -> Dict[str, Any]:
        """
        Ensure the response is JSON serializable by converting to dictionary.
        
        Args:
            response: Response object
            
        Returns:
            JSON-serializable dictionary
        """
        try:
            # Convert to dictionary using Pydantic's dict() method
            response_dict = response.dict()
            
            # Ensure all timestamps are ISO format strings
            if 'metadata' in response_dict and 'processing_timestamp' in response_dict['metadata']:
                timestamp = response_dict['metadata']['processing_timestamp']
                if isinstance(timestamp, datetime):
                    response_dict['metadata']['processing_timestamp'] = timestamp.isoformat()
            
            # Ensure all numeric values are standard Python types
            if 'extracted_sections' in response_dict:
                for section in response_dict['extracted_sections']:
                    if 'relevance_score' in section:
                        section['relevance_score'] = float(section['relevance_score'])
                    if 'page_number' in section:
                        section['page_number'] = int(section['page_number'])
            
            return response_dict
            
        except Exception as e:
            logger.error(f"JSON serialization preparation failed: {str(e)}")
            raise ProcessingError(
                f"Failed to prepare JSON serializable response: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )

    @timing_decorator
    async def process(self, input_data: JSONFormatterInput) -> JSONFormatterOutput:
        """
        Process JSON formatting request.
        
        Args:
            input_data: JSON formatter input
            
        Returns:
            Formatted JSON response
        """
        try:
            ranked_chunks = input_data.ranked_chunks
            metadata = input_data.metadata
            
            # Validate input
            if not ranked_chunks:
                logger.warning("No ranked chunks provided for formatting")
                # Create empty response
                extracted_sections = []
            else:
                # Create extracted sections
                extracted_sections = self._create_extracted_sections(ranked_chunks)
            
            # Update metadata with actual counts
            if isinstance(metadata, dict):
                metadata = dict(metadata)  # Make a copy
                metadata['total_chunks_extracted'] = len(ranked_chunks) if ranked_chunks else 0
            
            # Create response metadata
            response_metadata = self._create_response_metadata(metadata)
            
            # Create final response
            response = ResponseJSON(
                metadata=response_metadata,
                extracted_sections=extracted_sections
            )
            
            # Validate schema compliance
            self._validate_response_schema(response)
            
            # Ensure JSON serializable
            serializable_response = self._ensure_json_serializable(response)
            
            logger.info(f"Successfully formatted response with {len(extracted_sections)} sections")
            
            return JSONFormatterOutput(
                response=response,
                status="success"
            )
            
        except ProcessingError as e:
            logger.error(f"JSON formatting failed: {e.message}")
            return JSONFormatterOutput(
                response=None,
                status="error",
                error_code=e.error_code
            )
        except Exception as e:
            logger.error(f"Unexpected error in JSON formatting: {str(e)}")
            return JSONFormatterOutput(
                response=None,
                status="error",
                error_code=ErrorCode.E500_PROCESSING_FAILED
            )


# Tool function for Kiro framework integration
async def json_output_formatter_tool(input_data: dict) -> dict:
    """
    Kiro tool function for JSON output formatting.
    
    Args:
        input_data: Dictionary with ranked_chunks and metadata
        
    Returns:
        Dictionary with formatted response
    """
    try:
        # Parse input - need to convert ranked chunks back to RankedChunk objects
        ranked_chunks_data = input_data.get('ranked_chunks', [])
        ranked_chunks = []
        
        for ranked_chunk_data in ranked_chunks_data:
            chunk_data = ranked_chunk_data['chunk']
            relevance_score = ranked_chunk_data['relevance_score']
            
            from ..shared.models import TextChunk
            chunk = TextChunk(**chunk_data)
            
            from ..shared.models import RankedChunk
            ranked_chunk = RankedChunk(
                chunk=chunk,
                relevance_score=relevance_score
            )
            ranked_chunks.append(ranked_chunk)
        
        formatter_input = JSONFormatterInput(
            ranked_chunks=ranked_chunks,
            metadata=input_data['metadata']
        )
        
        # Process
        tool = JSONOutputFormatterTool()
        result = await tool.process(formatter_input)
        
        # Convert result to dictionary format
        result_dict = result.dict()
        
        # Convert ResponseJSON to dictionary if present
        if result_dict.get('response'):
            result_dict['response'] = result.response.dict()
        
        return result_dict
        
    except Exception as e:
        logger.error(f"JSON output formatter tool error: {str(e)}")
        return {
            "response": None,
            "status": "error",
            "error_code": ErrorCode.E500_PROCESSING_FAILED
        }
