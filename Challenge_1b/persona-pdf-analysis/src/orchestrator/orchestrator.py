"""
Persona Query Orchestrator

The main orchestration agent that coordinates all tools to process
PDF document collections based on user personas and job requirements.
"""

import asyncio
import logging
import time
import os
from typing import List, Optional, Dict, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from ..shared import (
    RequestJSON,
    ResponseJSON,
    TextChunk,
    RankedChunk,
    ProcessingResult,
    ErrorLog,
    ErrorCode,
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
    Main orchestrator agent for persona-driven PDF analysis.
    
    Coordinates all tools following the execution algorithm:
    1. Validate input and formulate semantic query
    2. Process documents in parallel 
    3. Aggregate results and handle errors
    4. Rank chunks semantically
    5. Format final JSON output
    """
    
    def __init__(self, max_workers: int = 4, document_timeout: int = 15):
        """
        Initialize the orchestrator.
        
        Args:
            max_workers: Maximum parallel workers for document processing
            document_timeout: Timeout per document in seconds
        """
        self.max_workers = max_workers
        self.document_timeout = document_timeout
        
        # Initialize tools
        self.query_formulation_tool = QueryFormulationTool()
        self.document_processor_tool = DocumentProcessorTool()
        self.semantic_ranking_tool = SemanticRankingTool()
        self.json_formatter_tool = JSONOutputFormatterTool()
        
        # State tracking
        self.current_query = None
        self.processing_errors = []
        self.successful_chunks = []
    
    def _validate_request(self, request: RequestJSON) -> None:
        """
        Validate the incoming request.
        
        Args:
            request: The request to validate
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Basic validation is handled by Pydantic models
            # Additional business logic validation here
            
            if len(request.documents) == 0:
                raise ValidationError(
                    "At least one document must be provided",
                    ErrorCode.E400_INVALID_INPUT
                )
            
            if len(request.persona.role.strip()) == 0:
                raise ValidationError(
                    "Persona role cannot be empty",
                    ErrorCode.E400_INVALID_INPUT
                )
            
            if len(request.job_to_be_done.task.strip()) == 0:
                raise ValidationError(
                    "Job to be done task cannot be empty",
                    ErrorCode.E400_INVALID_INPUT
                )
            
            logger.info(f"Request validation passed: {len(request.documents)} documents")
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Request validation failed: {str(e)}")
            raise ValidationError(
                f"Request validation error: {str(e)}",
                ErrorCode.E400_INVALID_INPUT
            )

    async def _formulate_query(self, request: RequestJSON) -> str:
        """
        Formulate semantic query from persona and job description.
        
        Args:
            request: The request containing persona and job info
            
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
            
            logger.info("Formulating semantic query...")
            result = await self.query_formulation_tool.process(query_input)
            
            if result.status != "success" or not result.semantic_query:
                error_code = result.error_code or ErrorCode.E500_PROCESSING_FAILED
                raise ProcessingError(
                    "Query formulation failed",
                    error_code
                )
            
            self.current_query = result.semantic_query
            logger.info(f"Query formulated: '{self.current_query[:100]}...'")
            
            return self.current_query
            
        except ProcessingError:
            raise
        except Exception as e:
            logger.error(f"Query formulation error: {str(e)}")
            raise ProcessingError(
                f"Failed to formulate query: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )

    def _resolve_document_path(self, document_filename: str, base_path: str) -> str:
        """
        Resolve full path to document file.
        
        Args:
            document_filename: Name of the document file
            base_path: Base directory containing documents
            
        Returns:
            Full path to document
        """
        # Try different path combinations
        possible_paths = [
            os.path.join(base_path, document_filename),
            os.path.join(base_path, "PDFs", document_filename),
            os.path.join(base_path, "pdfs", document_filename),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # If not found, return the first option for error reporting
        return possible_paths[0]

    async def _process_single_document(self, document_filename: str, base_path: str) -> ProcessingResult:
        """
        Process a single document with timeout handling.
        
        Args:
            document_filename: Name of the document to process
            base_path: Base path containing documents
            
        Returns:
            Processing result with chunks or error
        """
        document_path = self._resolve_document_path(document_filename, base_path)
        
        try:
            from ..shared.models import DocumentProcessorInput
            
            processor_input = DocumentProcessorInput(document_path=document_path)
            
            logger.info(f"Processing document: {document_filename}")
            
            # Process with timeout
            result = await asyncio.wait_for(
                self.document_processor_tool.process(processor_input),
                timeout=self.document_timeout
            )
            
            if result.status == "success" and result.chunks:
                logger.info(f"Successfully processed {document_filename}: {len(result.chunks)} chunks")
                return ProcessingResult(
                    success=True,
                    chunks=result.chunks,
                    error=None,
                    document_path=document_path
                )
            else:
                # Document processing failed
                error_code = result.error_code or ErrorCode.E500_PROCESSING_FAILED
                error_message = result.error_message or "Document processing failed"
                
                error_log = create_error_log(document_filename, error_code, error_message)
                
                return ProcessingResult(
                    success=False,
                    chunks=None,
                    error=error_log,
                    document_path=document_path
                )
            
        except asyncio.TimeoutError:
            logger.warning(f"Document processing timeout for {document_filename}")
            error_log = create_error_log(
                document_filename,
                ErrorCode.E500_PROCESSING_FAILED,
                f"Processing timeout ({self.document_timeout}s)"
            )
            return ProcessingResult(
                success=False,
                chunks=None,
                error=error_log,
                document_path=document_path
            )
            
        except Exception as e:
            logger.error(f"Document processing error for {document_filename}: {str(e)}")
            error_log = create_error_log(
                document_filename,
                ErrorCode.E500_PROCESSING_FAILED,
                f"Processing failed: {str(e)}"
            )
            return ProcessingResult(
                success=False,
                chunks=None,
                error=error_log,
                document_path=document_path
            )

    async def _process_documents_parallel(self, request: RequestJSON, base_path: str) -> List[ProcessingResult]:
        """
        Process all documents in parallel using worker pool.
        
        Args:
            request: The request containing documents to process
            base_path: Base path containing documents
            
        Returns:
            List of processing results
        """
        logger.info(f"Starting parallel processing of {len(request.documents)} documents")
        
        # Create tasks for parallel processing
        tasks = []
        for document in request.documents:
            task = self._process_single_document(document.filename, base_path)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processing_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Document processing exception: {str(result)}")
                error_log = create_error_log(
                    request.documents[i].filename,
                    ErrorCode.E500_PROCESSING_FAILED,
                    f"Unexpected error: {str(result)}"
                )
                processing_results.append(ProcessingResult(
                    success=False,
                    chunks=None,
                    error=error_log,
                    document_path=""
                ))
            else:
                processing_results.append(result)
        
        # Log summary
        successful = sum(1 for r in processing_results if r.success)
        failed = len(processing_results) - successful
        total_chunks = sum(len(r.chunks) for r in processing_results if r.chunks)
        
        logger.info(f"Document processing completed: {successful} successful, {failed} failed, {total_chunks} total chunks")
        
        return processing_results

    def _aggregate_results(self, processing_results: List[ProcessingResult]) -> tuple[List[TextChunk], List[ErrorLog]]:
        """
        Aggregate successful chunks and error logs from processing results.
        
        Args:
            processing_results: List of processing results
            
        Returns:
            Tuple of (successful_chunks, error_logs)
        """
        successful_chunks = []
        error_logs = []
        
        for result in processing_results:
            if result.success and result.chunks:
                successful_chunks.extend(result.chunks)
            elif result.error:
                error_logs.append(result.error)
        
        logger.info(f"Aggregated {len(successful_chunks)} chunks and {len(error_logs)} errors")
        
        return successful_chunks, error_logs

    async def _rank_chunks_semantically(self, chunks: List[TextChunk], query: str) -> List[RankedChunk]:
        """
        Rank text chunks using semantic similarity.
        
        Args:
            chunks: List of text chunks to rank
            query: Semantic query for ranking
            
        Returns:
            List of ranked chunks
            
        Raises:
            ProcessingError: If ranking fails
        """
        if not chunks:
            logger.warning("No chunks to rank")
            return []
        
        try:
            from ..shared.models import SemanticRankingInput
            
            ranking_input = SemanticRankingInput(
                chunks=chunks,
                query=query
            )
            
            logger.info(f"Ranking {len(chunks)} chunks against query...")
            result = await self.semantic_ranking_tool.process(ranking_input)
            
            if result.status != "success" or not result.ranked_chunks:
                error_code = result.error_code or ErrorCode.E500_PROCESSING_FAILED
                raise ProcessingError(
                    "Semantic ranking failed",
                    error_code
                )
            
            ranked_chunks = result.ranked_chunks
            logger.info(f"Ranking completed: {len(ranked_chunks)} chunks ranked")
            
            return ranked_chunks
            
        except ProcessingError:
            raise
        except Exception as e:
            logger.error(f"Ranking error: {str(e)}")
            raise ProcessingError(
                f"Failed to rank chunks: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )

    async def _format_final_response(
        self, 
        ranked_chunks: List[RankedChunk], 
        request: RequestJSON,
        error_logs: List[ErrorLog],
        processing_time: float
    ) -> ResponseJSON:
        """
        Format the final JSON response.
        
        Args:
            ranked_chunks: Ranked text chunks
            request: Original request
            error_logs: Processing errors
            processing_time: Total processing time
            
        Returns:
            Final formatted response
            
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
                total_documents=len([chunk for chunk in ranked_chunks]),  # Approximate
                errors=error_logs,
                processing_time=processing_time
            )
            
            formatter_input = JSONFormatterInput(
                ranked_chunks=ranked_chunks,
                metadata=metadata
            )
            
            logger.info("Formatting final JSON response...")
            result = await self.json_formatter_tool.process(formatter_input)
            
            if result.status != "success" or not result.response:
                error_code = result.error_code or ErrorCode.E500_PROCESSING_FAILED
                raise ProcessingError(
                    "JSON formatting failed",
                    error_code
                )
            
            logger.info("Response formatting completed successfully")
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
    async def process_request(self, request: RequestJSON, documents_base_path: str) -> ResponseJSON:
        """
        Main processing function that orchestrates the complete workflow.
        
        Args:
            request: The JSON request to process
            documents_base_path: Base path where documents are located
            
        Returns:
            Complete response with ranked extracted sections
            
        Raises:
            ValidationError: If input validation fails
            ProcessingError: If processing fails
        """
        start_time = time.time()
        
        try:
            # Step 1: Validate input
            logger.info("Starting persona-driven PDF analysis workflow")
            self._validate_request(request)
            
            # Step 2: Formulate semantic query
            query = await self._formulate_query(request)
            
            # Step 3: Process documents in parallel
            processing_results = await self._process_documents_parallel(request, documents_base_path)
            
            # Step 4: Aggregate results
            successful_chunks, error_logs = self._aggregate_results(processing_results)
            
            # Check if we have any successful chunks
            if not successful_chunks:
                logger.warning("No text chunks were successfully extracted")
                # Still create a response with empty results
                ranked_chunks = []
            else:
                # Step 5: Rank chunks semantically
                ranked_chunks = await self._rank_chunks_semantically(successful_chunks, query)
            
            # Step 6: Format final response
            processing_time = time.time() - start_time
            response = await self._format_final_response(
                ranked_chunks, 
                request, 
                error_logs, 
                processing_time
            )
            
            logger.info(f"Workflow completed successfully in {processing_time:.2f} seconds")
            
            return response
            
        except (ValidationError, ProcessingError):
            # Re-raise known errors
            raise
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Workflow failed after {processing_time:.2f} seconds: {str(e)}")
            raise ProcessingError(
                f"Orchestration failed: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )
