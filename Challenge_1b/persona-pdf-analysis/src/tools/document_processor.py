"""
Document Processor Tool

This tool processes PDF documents and extracts structured text chunks 
using the unstructured library with intelligent chunking and selective OCR.
"""

import asyncio
import logging
import os
from typing import List, Optional, Tuple
import time

from ..shared import (
    DocumentProcessorInput,
    DocumentProcessorOutput,
    TextChunk,
    ErrorCode,
    ProcessingError,
    timing_decorator,
    safe_execute,
    validate_file_path,
    validate_pdf_file,
    generate_chunk_id,
    is_text_meaningful,
    sanitize_filename
)

logger = logging.getLogger(__name__)


class DocumentProcessorTool:
    """
    Tool for processing PDF documents with intelligent text extraction.
    Uses unstructured library with performance optimizations and selective OCR.
    """
    
    def __init__(self):
        """Initialize the Document Processor Tool."""
        self.ocr_threshold = 0.3  # Ratio of images to text for OCR decision
        self.max_chunk_size = 2000  # Maximum characters per chunk
        self.min_chunk_size = 100   # Minimum characters per meaningful chunk
        
    def _check_pdf_accessibility(self, file_path: str) -> Tuple[bool, Optional[ErrorCode]]:
        """
        Check if PDF is accessible and processable.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Tuple of (is_accessible, error_code)
        """
        # Check file existence
        if not validate_file_path(file_path):
            return False, ErrorCode.E404_FILE_NOT_FOUND
        
        # Check if it's a valid PDF
        if not validate_pdf_file(file_path):
            return False, ErrorCode.E415_UNSUPPORTED_FORMAT
        
        # Check for encryption
        try:
            import PyMuPDF as fitz
            doc = fitz.open(file_path)
            
            if doc.needs_pass:
                doc.close()
                return False, ErrorCode.E423_FILE_ENCRYPTED
            
            # Try to access first page to check for corruption
            if doc.page_count > 0:
                page = doc[0]
                _ = page.get_text()  # This will fail if severely corrupted
            
            doc.close()
            return True, None
            
        except Exception as e:
            logger.error(f"PDF accessibility check failed for {file_path}: {str(e)}")
            return False, ErrorCode.E415_UNSUPPORTED_FORMAT

    def _should_use_ocr(self, file_path: str) -> bool:
        """
        Determine if OCR should be used based on content heuristics.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            True if OCR should be used
        """
        try:
            import PyMuPDF as fitz
            
            doc = fitz.open(file_path)
            
            # Sample first few pages for analysis
            pages_to_check = min(3, doc.page_count)
            total_text_length = 0
            total_images = 0
            
            for page_num in range(pages_to_check):
                page = doc[page_num]
                
                # Get text length
                text = page.get_text()
                total_text_length += len(text.strip())
                
                # Count images
                image_list = page.get_images()
                total_images += len(image_list)
            
            doc.close()
            
            # If very little text but many images, likely needs OCR
            if total_text_length < 100 and total_images > 2:
                logger.info(f"OCR recommended for {file_path}: low text ({total_text_length}), many images ({total_images})")
                return True
            
            # If ratio of images to text suggests scanned document
            if total_images > 0 and total_text_length / max(total_images, 1) < 50:
                logger.info(f"OCR recommended for {file_path}: high image-to-text ratio")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"OCR heuristic analysis failed for {file_path}: {str(e)}")
            # Default to OCR if we can't determine
            return True

    def _extract_with_unstructured(self, file_path: str, use_ocr: bool = False) -> List[dict]:
        """
        Extract document structure using unstructured library.
        
        Args:
            file_path: Path to PDF file
            use_ocr: Whether to use OCR
            
        Returns:
            List of structured elements
            
        Raises:
            ProcessingError: If extraction fails
        """
        try:
            from unstructured.partition.pdf import partition_pdf
            
            # Configure extraction strategy
            strategy = "fast"  # Optimize for performance
            
            # OCR configuration
            ocr_languages = ["eng"] if use_ocr else None
            infer_table_structure = True
            
            logger.info(f"Processing {file_path} with strategy='{strategy}', OCR={use_ocr}")
            
            # Extract elements
            elements = partition_pdf(
                filename=file_path,
                strategy=strategy,
                ocr_languages=ocr_languages,
                infer_table_structure=infer_table_structure,
                extract_images_in_pdf=use_ocr,
                chunking_strategy="by_title",  # Smart chunking
                max_characters=self.max_chunk_size,
                combine_text_under_n_chars=self.min_chunk_size
            )
            
            logger.info(f"Extracted {len(elements)} elements from {file_path}")
            return elements
            
        except ImportError:
            raise ProcessingError(
                "unstructured library not available",
                ErrorCode.E500_PROCESSING_FAILED
            )
        except Exception as e:
            logger.error(f"Unstructured extraction failed for {file_path}: {str(e)}")
            raise ProcessingError(
                f"Document parsing failed: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )

    def _associate_titles_with_content(self, elements: List[dict]) -> List[dict]:
        """
        Associate section titles with following content paragraphs.
        
        Args:
            elements: Raw extracted elements
            
        Returns:
            Elements with title associations
        """
        processed_elements = []
        current_title = None
        
        for element in elements:
            element_type = getattr(element, 'category', 'Unknown')
            text = str(element).strip()
            
            if not text or not is_text_meaningful(text):
                continue
            
            # Track current section title
            if element_type in ['Title', 'Header']:
                current_title = text
                processed_elements.append({
                    'text': text,
                    'type': element_type,
                    'title': text,
                    'metadata': getattr(element, 'metadata', {})
                })
            else:
                # Associate content with current title
                processed_elements.append({
                    'text': text,
                    'type': element_type,
                    'title': current_title,
                    'metadata': getattr(element, 'metadata', {})
                })
        
        return processed_elements

    def _create_text_chunks(self, elements: List[dict], document_filename: str) -> List[TextChunk]:
        """
        Create TextChunk objects from processed elements.
        
        Args:
            elements: Processed elements with title associations
            document_filename: Source document filename
            
        Returns:
            List of TextChunk objects
        """
        chunks = []
        chunk_index = 0
        
        for element in elements:
            text = element['text']
            title = element.get('title')
            metadata = element.get('metadata', {})
            
            # Extract page number from metadata
            page_number = 1  # Default
            if 'page_number' in metadata:
                page_number = metadata['page_number']
            elif hasattr(metadata, 'page_number'):
                page_number = metadata.page_number
            
            # Ensure page number is valid
            if not isinstance(page_number, int) or page_number < 1:
                page_number = 1
            
            # Generate unique chunk ID
            chunk_id = generate_chunk_id(document_filename, page_number, chunk_index)
            
            # Create chunk
            chunk = TextChunk(
                text=text,
                page_number=page_number,
                section_title=title,
                chunk_id=chunk_id,
                document_source=document_filename
            )
            
            chunks.append(chunk)
            chunk_index += 1
        
        logger.info(f"Created {len(chunks)} text chunks from {document_filename}")
        return chunks

    def _fallback_extraction(self, file_path: str) -> List[TextChunk]:
        """
        Fallback extraction using PyMuPDF when unstructured fails.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of TextChunk objects
        """
        logger.warning(f"Using fallback extraction for {file_path}")
        
        try:
            import PyMuPDF as fitz
            
            doc = fitz.open(file_path)
            chunks = []
            document_filename = os.path.basename(file_path)
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                
                # Split into smaller chunks if too large
                if len(text) > self.max_chunk_size:
                    # Simple sentence-based splitting
                    sentences = text.split('. ')
                    current_chunk = ""
                    chunk_index = 0
                    
                    for sentence in sentences:
                        if len(current_chunk + sentence) > self.max_chunk_size:
                            if current_chunk and is_text_meaningful(current_chunk):
                                chunk_id = generate_chunk_id(document_filename, page_num + 1, chunk_index)
                                chunks.append(TextChunk(
                                    text=current_chunk.strip(),
                                    page_number=page_num + 1,
                                    section_title=None,
                                    chunk_id=chunk_id,
                                    document_source=document_filename
                                ))
                                chunk_index += 1
                            current_chunk = sentence
                        else:
                            current_chunk += ". " + sentence if current_chunk else sentence
                    
                    # Add remaining chunk
                    if current_chunk and is_text_meaningful(current_chunk):
                        chunk_id = generate_chunk_id(document_filename, page_num + 1, chunk_index)
                        chunks.append(TextChunk(
                            text=current_chunk.strip(),
                            page_number=page_num + 1,
                            section_title=None,
                            chunk_id=chunk_id,
                            document_source=document_filename
                        ))
                else:
                    # Single chunk for the page
                    if text and is_text_meaningful(text):
                        chunk_id = generate_chunk_id(document_filename, page_num + 1, 0)
                        chunks.append(TextChunk(
                            text=text.strip(),
                            page_number=page_num + 1,
                            section_title=None,
                            chunk_id=chunk_id,
                            document_source=document_filename
                        ))
            
            doc.close()
            logger.info(f"Fallback extraction created {len(chunks)} chunks from {document_filename}")
            return chunks
            
        except Exception as e:
            logger.error(f"Fallback extraction failed for {file_path}: {str(e)}")
            raise ProcessingError(
                f"All extraction methods failed: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )

    @timing_decorator
    async def process(self, input_data: DocumentProcessorInput) -> DocumentProcessorOutput:
        """
        Process a PDF document and extract text chunks.
        
        Args:
            input_data: Document processor input
            
        Returns:
            Document processing output with chunks or error
        """
        file_path = input_data.document_path
        document_filename = os.path.basename(file_path)
        
        try:
            # Check PDF accessibility
            is_accessible, error_code = self._check_pdf_accessibility(file_path)
            if not is_accessible:
                return DocumentProcessorOutput(
                    chunks=None,
                    status="error",
                    error_code=error_code,
                    error_message=f"Document not accessible: {error_code.value}"
                )
            
            # Determine OCR usage
            use_ocr = self._should_use_ocr(file_path)
            
            # Extract with unstructured
            try:
                elements = self._extract_with_unstructured(file_path, use_ocr)
                processed_elements = self._associate_titles_with_content(elements)
                chunks = self._create_text_chunks(processed_elements, document_filename)
                
            except ProcessingError as e:
                # Fall back to PyMuPDF if unstructured fails
                logger.warning(f"Unstructured extraction failed, using fallback: {e.message}")
                chunks = self._fallback_extraction(file_path)
            
            # Validate results
            if not chunks:
                return DocumentProcessorOutput(
                    chunks=None,
                    status="error",
                    error_code=ErrorCode.E500_PROCESSING_FAILED,
                    error_message="No meaningful text extracted from document"
                )
            
            logger.info(f"Successfully processed {document_filename}: {len(chunks)} chunks")
            
            return DocumentProcessorOutput(
                chunks=chunks,
                status="success"
            )
            
        except ProcessingError as e:
            logger.error(f"Document processing failed for {document_filename}: {e.message}")
            return DocumentProcessorOutput(
                chunks=None,
                status="error",
                error_code=e.error_code,
                error_message=e.message
            )
        except Exception as e:
            logger.error(f"Unexpected error processing {document_filename}: {str(e)}")
            return DocumentProcessorOutput(
                chunks=None,
                status="error",
                error_code=ErrorCode.E500_PROCESSING_FAILED,
                error_message=f"Unexpected processing error: {str(e)}"
            )


# Tool function for Kiro framework integration
async def document_processor_tool(input_data: dict) -> dict:
    """
    Kiro tool function for document processing.
    
    Args:
        input_data: Dictionary with document_path
        
    Returns:
        Dictionary with chunks and status
    """
    try:
        # Parse input
        processor_input = DocumentProcessorInput(**input_data)
        
        # Process
        tool = DocumentProcessorTool()
        result = await tool.process(processor_input)
        
        # Convert result to dictionary format
        result_dict = result.dict()
        
        # Convert TextChunk objects to dictionaries if present
        if result_dict.get('chunks'):
            result_dict['chunks'] = [chunk.dict() for chunk in result.chunks]
        
        return result_dict
        
    except Exception as e:
        logger.error(f"Document processor tool error: {str(e)}")
        return {
            "chunks": None,
            "status": "error",
            "error_code": ErrorCode.E500_PROCESSING_FAILED,
            "error_message": f"Tool execution error: {str(e)}"
        }
