"""
Persona Query Orchestrator Agent

Main orchestration logic that coordinates all tools to process PDF collections
and extract persona-relevant information.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

from ..shared import (
    RequestJSON,
    ResponseJSON,
    TextChunk,
    RankedChunk,
    ErrorLog,
    ErrorCode,
    ProcessingResult,
    ValidationError,
    ProcessingError,
    timing_decorator,
    create_error_log,
    format_processing_metadata
)

from ..tools.query_formulation import QueryFormulationTool
from ..tools.document_processor import DocumentProcessorTool
from ..tools.semantic_ranking import SemanticRankingTool
from ..tools.json_formatter import JSONOutputFormatterTool

logger = logging.getLogger(__name__)


class PersonaQueryOrchestrator:
    """
    Main orchestrator agent that coordinates the persona-driven PDF analysis workflow.
    Implements parallel processing and comprehensive error handling.
    """
    
    def __init__(self, max_workers: int = 4, document_timeout: int = 15):
        """
        Initialize the orchestrator.
        
        Args:
            max_workers: Maximum number of parallel workers for document processing
            document_timeout: Timeout in seconds for processing each document
        """
        self.max_workers = max_workers
        self.document_timeout = document_timeout
        
        # Initialize tools
        self.query_formulation_tool = QueryFormulationTool()
        self.document_processor_tool = DocumentProcessorTool()
        self.semantic_ranking_tool = SemanticRankingTool()
        self.json_formatter_tool = JSONOutputFormatterTool()

    def _validate_request(self, request: RequestJSON) -> None:
        """
        Validate the input request.
        
        Args:
            request: Input request to validate
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Basic validation is handled by Pydantic models
            # Additional business logic validation here
            
            if len(request.documents) == 0:
                raise ValidationError(
                    "No documents provided in request",
                    ErrorCode.E400_INVALID_INPUT
                )
            
            if len(request.documents) > 100:  # Reasonable limit
                raise ValidationError(
                    "Too many documents (max 100 allowed)",
                    ErrorCode.E400_INVALID_INPUT
                )
            
            # Validate document filenames are unique
            filenames = [doc.filename for doc in request.documents]
            if len(filenames) != len(set(filenames)):
                raise ValidationError(
                    "Duplicate document filenames found",
                    ErrorCode.E400_INVALID_INPUT
                )
            
            logger.info(f"Request validation passed: {len(request.documents)} documents")
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Request validation error: {str(e)}")
            raise ValidationError(
                f"Request validation failed: {str(e)}",
                ErrorCode.E400_INVALID_INPUT
            )

    @timing_decorator
    async def _formulate_query(self, request: RequestJSON) -> str:
        """
        Formulate semantic query from persona and job description.
        
        Args:
            request: Input request
            
        Returns:
            Formulated semantic query
            
        Raises:
            ProcessingError: If query formulation fails
        """
        try:
            from ..shared.models import QueryFormulationInput
            
            query_input = QueryFormulationInput(
                persona=request.persona,
                job_to_be_done=request.job_to_be_done
            )
            
            result = await self.query_formulation_tool.process(query_input)
            
            if result.status != "success":
                raise ProcessingError(
                    f"Query formulation failed: {result.error_code}",
                    result.error_code or ErrorCode.E500_PROCESSING_FAILED
                )
            
            logger.info(f"Query formulated: {result.semantic_query}")
            return result.semantic_query
            
        except ProcessingError:
            raise
        except Exception as e:
            logger.error(f"Query formulation error: {str(e)}")
            raise ProcessingError(
                f"Failed to formulate query: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )

    async def _process_single_document(self, document_path: str, document_filename: str) -> ProcessingResult:
        """
        Process a single document and return result.
        
        Args:
            document_path: Path to the document
            document_filename: Filename of the document
            
        Returns:
            ProcessingResult with chunks or error
        """
        start_time = time.time()
        
        try:
            from ..shared.models import DocumentProcessorInput
            
            processor_input = DocumentProcessorInput(document_path=document_path)
            
            # Process with timeout
            result = await asyncio.wait_for(
                self.document_processor_tool.process(processor_input),
                timeout=self.document_timeout
            )
            
            processing_time = time.time() - start_time
            
            if result.status == "success" and result.chunks:
                logger.info(f"Successfully processed {document_filename}: {len(result.chunks)} chunks in {processing_time:.2f}s")
                return ProcessingResult(
                    success=True,
                    chunks=result.chunks,
                    error=None,
                    document_path=document_path,
                    processing_time=processing_time
                )
            else:
                error_log = create_error_log(
                    document_filename,
                    result.error_code or ErrorCode.E500_PROCESSING_FAILED,
                    result.error_message
                )
                
                logger.warning(f"Document processing failed for {document_filename}: {result.error_message}")
                return ProcessingResult(
                    success=False,
                    chunks=None,
                    error=error_log,
                    document_path=document_path,
                    processing_time=processing_time
                )
                
        except asyncio.TimeoutError:
            processing_time = time.time() - start_time
            error_log = create_error_log(
                document_filename,
                ErrorCode.E500_PROCESSING_FAILED,
                f"Document processing timed out after {self.document_timeout} seconds"
            )
            
            logger.error(f"Document processing timeout for {document_filename}")
            return ProcessingResult(
                success=False,
                chunks=None,
                error=error_log,
                document_path=document_path,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_log = create_error_log(
                document_filename,
                ErrorCode.E500_PROCESSING_FAILED,
                f"Unexpected error: {str(e)}"
            )
            
            logger.error(f"Unexpected error processing {document_filename}: {str(e)}")
            return ProcessingResult(
                success=False,
                chunks=None,
                error=error_log,
                document_path=document_path,
                processing_time=processing_time
            )

    @timing_decorator
    async def _process_documents_parallel(self, request: RequestJSON, base_path: str = "") -> Tuple[List[TextChunk], List[ErrorLog]]:
        """
        Process all documents in parallel.
        
        Args:
            request: Input request with documents
            base_path: Base path for document files
            
        Returns:
            Tuple of (successful_chunks, error_logs)
        """
        try:
            # Prepare document paths
            document_tasks = []
            for document in request.documents:
                document_path = os.path.join(base_path, document.filename)
                document_tasks.append((document_path, document.filename))
            
            logger.info(f"Starting parallel processing of {len(document_tasks)} documents with {self.max_workers} workers")
            
            # Process documents in parallel
            tasks = []
            for document_path, document_filename in document_tasks:
                task = self._process_single_document(document_path, document_filename)
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Aggregate results
            successful_chunks = []
            error_logs = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Handle exceptions from tasks
                    document_filename = document_tasks[i][1]
                    error_log = create_error_log(
                        document_filename,
                        ErrorCode.E500_PROCESSING_FAILED,
                        f"Task execution failed: {str(result)}"
                    )
                    error_logs.append(error_log)
                    logger.error(f"Task exception for {document_filename}: {str(result)}")
                    
                elif isinstance(result, ProcessingResult):
                    if result.success and result.chunks:
                        successful_chunks.extend(result.chunks)
                    elif result.error:
                        error_logs.append(result.error)
                else:
                    # Unexpected result type
                    document_filename = document_tasks[i][1] if i < len(document_tasks) else "unknown"
                    error_log = create_error_log(
                        document_filename,
                        ErrorCode.E500_PROCESSING_FAILED,
                        "Unexpected result type from document processing"
                    )
                    error_logs.append(error_log)
            
            logger.info(f"Parallel processing completed: {len(successful_chunks)} chunks, {len(error_logs)} errors")
            return successful_chunks, error_logs
            
        except Exception as e:
            logger.error(f"Parallel document processing failed: {str(e)}")
            raise ProcessingError(
                f"Document processing pipeline failed: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )

    @timing_decorator
    async def _rank_chunks(self, chunks: List[TextChunk], query: str) -> List[RankedChunk]:
        """
        Rank chunks using semantic similarity.
        
        Args:
            chunks: Text chunks to rank
            query: Semantic query
            
        Returns:
            Ranked chunks
            
        Raises:
            ProcessingError: If ranking fails
        """
        try:
            from ..shared.models import SemanticRankingInput
            
            ranking_input = SemanticRankingInput(
                chunks=chunks,
                query=query
            )
            
            result = await self.semantic_ranking_tool.process(ranking_input)
            
            if result.status != "success":
                raise ProcessingError(
                    f"Semantic ranking failed: {result.error_code}",
                    result.error_code or ErrorCode.E500_PROCESSING_FAILED
                )
            
            logger.info(f"Successfully ranked {len(result.ranked_chunks)} chunks")
            return result.ranked_chunks
            
        except ProcessingError:
            raise
        except Exception as e:
            logger.error(f"Chunk ranking error: {str(e)}")
            raise ProcessingError(
                f"Failed to rank chunks: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )

    @timing_decorator
    async def _format_response(self, ranked_chunks: List[RankedChunk], request: RequestJSON, 
                             errors: List[ErrorLog], processing_time: float) -> ResponseJSON:
        """
        Format the final response.
        
        Args:
            ranked_chunks: Ranked text chunks
            request: Original request
            errors: Processing errors
            processing_time: Total processing time
            
        Returns:
            Formatted response
            
        Raises:
            ProcessingError: If formatting fails
        """
        try:
            from ..shared.models import JSONFormatterInput
            
            # Prepare metadata
            metadata = format_processing_metadata(
                input_documents=[doc.filename for doc in request.documents],
                persona=request.persona.role,
                job_to_be_done=request.job_to_be_done.task,
                successful_chunks=len(ranked_chunks),
                total_documents=len([doc for doc in request.documents]) - len(errors),
                errors=errors,
                processing_time=processing_time
            )
            
            formatter_input = JSONFormatterInput(
                ranked_chunks=ranked_chunks,
                metadata=metadata
            )
            
            result = await self.json_formatter_tool.process(formatter_input)
            
            if result.status != "success":
                raise ProcessingError(
                    f"Response formatting failed: {result.error_code}",
                    result.error_code or ErrorCode.E500_PROCESSING_FAILED
                )
            
            logger.info("Response formatted successfully")
            return result.response
            
        except ProcessingError:
            raise
        except Exception as e:
            logger.error(f"Response formatting error: {str(e)}")
            raise ProcessingError(
                f"Failed to format response: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )

    @timing_decorator
    async def process_request(self, request: RequestJSON, documents_base_path: str = "") -> ResponseJSON:
        """
        Process the complete persona-driven PDF analysis request.
        
        Args:
            request: Input request
            documents_base_path: Base path where document files are located
            
        Returns:
            Analysis response
        """
        start_time = time.time()
        
        try:
            # Step 1: Validate request
            self._validate_request(request)
            
            # Step 2: Formulate semantic query
            semantic_query = await self._formulate_query(request)
            
            # Step 3: Process documents in parallel
            chunks, errors = await self._process_documents_parallel(request, documents_base_path)
            
            # Step 4: Check if we have any chunks to work with
            if not chunks:
                logger.warning("No text chunks extracted from any document")
                # Still format a response with errors
                ranked_chunks = []
            else:
                # Step 5: Rank chunks semantically
                ranked_chunks = await self._rank_chunks(chunks, semantic_query)
            
            # Step 6: Format final response
            total_processing_time = time.time() - start_time
            response = await self._format_response(ranked_chunks, request, errors, total_processing_time)
            
            logger.info(f"Request processing completed successfully in {total_processing_time:.2f} seconds")
            return response
            
        except (ValidationError, ProcessingError) as e:
            total_processing_time = time.time() - start_time
            logger.error(f"Request processing failed after {total_processing_time:.2f} seconds: {e.message}")
            
            # Create error response
            error_metadata = format_processing_metadata(
                input_documents=[doc.filename for doc in request.documents],
                persona=request.persona.role,
                job_to_be_done=request.job_to_be_done.task,
                errors=[create_error_log("system", e.error_code, e.message)],
                processing_time=total_processing_time
            )
            
            from ..shared.models import ResponseMetadata, ExtractedSection
            response_metadata = ResponseMetadata(**error_metadata)
            
            return ResponseJSON(
                metadata=response_metadata,
                extracted_sections=[]
            )
            
        except Exception as e:
            total_processing_time = time.time() - start_time
            logger.error(f"Unexpected error in request processing: {str(e)}")
            
            # Create error response for unexpected errors
            error_metadata = format_processing_metadata(
                input_documents=[doc.filename for doc in request.documents] if hasattr(request, 'documents') else [],
                persona=request.persona.role if hasattr(request, 'persona') else "Unknown",
                job_to_be_done=request.job_to_be_done.task if hasattr(request, 'job_to_be_done') else "Unknown",
                errors=[create_error_log("system", ErrorCode.E500_PROCESSING_FAILED, f"Unexpected error: {str(e)}")],
                processing_time=total_processing_time
            )
            
            from ..shared.models import ResponseMetadata
            response_metadata = ResponseMetadata(**error_metadata)
            
            return ResponseJSON(
                metadata=response_metadata,
                extracted_sections=[]
            )
