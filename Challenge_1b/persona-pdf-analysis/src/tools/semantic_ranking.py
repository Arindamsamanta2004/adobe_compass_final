"""
Semantic Ranking Tool

This tool ranks text chunks against semantic queries using SBERT embeddings
with optimized batch processing for CPU performance.
"""

import asyncio
import logging
import numpy as np
from typing import List, Optional
import time

from ..shared import (
    SemanticRankingInput,
    SemanticRankingOutput,
    TextChunk,
    RankedChunk,
    ErrorCode,
    ProcessingError,
    timing_decorator
)

logger = logging.getLogger(__name__)


class SemanticRankingTool:
    """
    Tool for ranking text chunks using semantic similarity.
    Uses all-MiniLM-L6-v2 model for efficient CPU-based embeddings.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", batch_size: int = 128):
        """
        Initialize the Semantic Ranking Tool.
        
        Args:
            model_name: SBERT model name
            batch_size: Batch size for embedding generation
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None
        self._device = "cpu"  # Force CPU for consistent performance
        
    def _load_model(self):
        """Lazy loading of the SBERT model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                
                logger.info(f"Loading SBERT model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name, device=self._device)
                
                # Verify model loaded correctly
                test_embedding = self._model.encode(["test"], show_progress_bar=False)
                if test_embedding is None or len(test_embedding) == 0:
                    raise ProcessingError(
                        "Model failed validation test",
                        ErrorCode.E500_PROCESSING_FAILED
                    )
                
                logger.info(f"SBERT model loaded successfully on {self._device}")
                
            except ImportError:
                raise ProcessingError(
                    "sentence-transformers library not available",
                    ErrorCode.E503_SERVICE_UNAVAILABLE
                )
            except Exception as e:
                logger.error(f"Failed to load SBERT model: {str(e)}")
                raise ProcessingError(
                    f"Model loading failed: {str(e)}",
                    ErrorCode.E503_SERVICE_UNAVAILABLE
                )
        
        return self._model

    def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts with batch processing.
        
        Args:
            texts: List of text strings
            
        Returns:
            NumPy array of embeddings
            
        Raises:
            ProcessingError: If embedding generation fails
        """
        try:
            model = self._load_model()
            
            # Generate embeddings in batches for optimal CPU performance
            logger.info(f"Generating embeddings for {len(texts)} texts with batch_size={self.batch_size}")
            
            embeddings = model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True  # Normalize for cosine similarity
            )
            
            if embeddings is None or embeddings.shape[0] != len(texts):
                raise ProcessingError(
                    "Embedding generation returned unexpected results",
                    ErrorCode.E500_PROCESSING_FAILED
                )
            
            logger.info(f"Generated embeddings shape: {embeddings.shape}")
            return embeddings
            
        except ProcessingError:
            raise
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise ProcessingError(
                f"Failed to generate embeddings: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )

    def _calculate_cosine_similarity(self, query_embedding: np.ndarray, chunk_embeddings: np.ndarray) -> np.ndarray:
        """
        Calculate cosine similarity between query and chunk embeddings.
        
        Args:
            query_embedding: Query embedding vector
            chunk_embeddings: Matrix of chunk embeddings
            
        Returns:
            Array of similarity scores
        """
        try:
            # Since embeddings are normalized, dot product = cosine similarity
            similarities = np.dot(chunk_embeddings, query_embedding.T).flatten()
            
            # Ensure scores are in [0, 1] range
            # Cosine similarity ranges from -1 to 1, normalize to 0 to 1
            normalized_scores = (similarities + 1) / 2
            
            # Clamp to ensure valid range
            normalized_scores = np.clip(normalized_scores, 0.0, 1.0)
            
            return normalized_scores
            
        except Exception as e:
            logger.error(f"Similarity calculation failed: {str(e)}")
            raise ProcessingError(
                f"Failed to calculate similarities: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )

    def _rank_chunks(self, chunks: List[TextChunk], similarity_scores: np.ndarray) -> List[RankedChunk]:
        """
        Create ranked chunks with similarity scores.
        
        Args:
            chunks: Original text chunks
            similarity_scores: Similarity scores for each chunk
            
        Returns:
            List of ranked chunks sorted by relevance
        """
        try:
            if len(chunks) != len(similarity_scores):
                raise ProcessingError(
                    "Mismatch between chunks and similarity scores",
                    ErrorCode.E500_PROCESSING_FAILED
                )
            
            # Create ranked chunks
            ranked_chunks = []
            for chunk, score in zip(chunks, similarity_scores):
                ranked_chunk = RankedChunk(
                    chunk=chunk,
                    relevance_score=float(score)  # Ensure it's a Python float
                )
                ranked_chunks.append(ranked_chunk)
            
            # Sort by relevance score (highest first)
            ranked_chunks.sort(key=lambda x: x.relevance_score, reverse=True)
            
            logger.info(f"Ranked {len(ranked_chunks)} chunks, top score: {ranked_chunks[0].relevance_score:.3f}")
            
            return ranked_chunks
            
        except ProcessingError:
            raise
        except Exception as e:
            logger.error(f"Chunk ranking failed: {str(e)}")
            raise ProcessingError(
                f"Failed to rank chunks: {str(e)}",
                ErrorCode.E500_PROCESSING_FAILED
            )

    def _validate_input(self, chunks: List[TextChunk], query: str) -> None:
        """
        Validate input parameters.
        
        Args:
            chunks: Text chunks to rank
            query: Semantic query
            
        Raises:
            ProcessingError: If validation fails
        """
        if not chunks:
            raise ProcessingError(
                "No chunks provided for ranking",
                ErrorCode.E400_INVALID_INPUT
            )
        
        if not query or len(query.strip()) < 3:
            raise ProcessingError(
                "Query is too short or empty",
                ErrorCode.E400_INVALID_INPUT
            )
        
        # Check for valid chunk content
        valid_chunks = [chunk for chunk in chunks if chunk.text and len(chunk.text.strip()) > 0]
        if len(valid_chunks) == 0:
            raise ProcessingError(
                "No chunks with valid text content",
                ErrorCode.E400_INVALID_INPUT
            )

    @timing_decorator
    async def process(self, input_data: SemanticRankingInput) -> SemanticRankingOutput:
        """
        Process semantic ranking request.
        
        Args:
            input_data: Semantic ranking input
            
        Returns:
            Ranked chunks with similarity scores
        """
        try:
            chunks = input_data.chunks
            query = input_data.query.strip()
            
            # Validate input
            self._validate_input(chunks, query)
            
            # Filter chunks with meaningful content
            valid_chunks = [chunk for chunk in chunks if chunk.text and len(chunk.text.strip()) > 0]
            
            if not valid_chunks:
                return SemanticRankingOutput(
                    ranked_chunks=[],
                    status="success"  # Empty but successful
                )
            
            # Prepare texts for embedding
            chunk_texts = [chunk.text for chunk in valid_chunks]
            all_texts = [query] + chunk_texts
            
            logger.info(f"Processing {len(valid_chunks)} chunks with query: '{query[:50]}...'")
            
            # Generate embeddings
            all_embeddings = self._generate_embeddings(all_texts)
            
            # Split query and chunk embeddings
            query_embedding = all_embeddings[0:1]  # Keep as 2D array
            chunk_embeddings = all_embeddings[1:]
            
            # Calculate similarity scores
            similarity_scores = self._calculate_cosine_similarity(query_embedding, chunk_embeddings)
            
            # Create ranked chunks
            ranked_chunks = self._rank_chunks(valid_chunks, similarity_scores)
            
            logger.info(f"Successfully ranked {len(ranked_chunks)} chunks")
            
            return SemanticRankingOutput(
                ranked_chunks=ranked_chunks,
                status="success"
            )
            
        except ProcessingError as e:
            logger.error(f"Semantic ranking failed: {e.message}")
            return SemanticRankingOutput(
                ranked_chunks=None,
                status="error",
                error_code=e.error_code
            )
        except Exception as e:
            logger.error(f"Unexpected error in semantic ranking: {str(e)}")
            return SemanticRankingOutput(
                ranked_chunks=None,
                status="error",
                error_code=ErrorCode.E500_PROCESSING_FAILED
            )


# Tool function for Kiro framework integration
async def semantic_ranking_tool(input_data: dict) -> dict:
    """
    Kiro tool function for semantic ranking.
    
    Args:
        input_data: Dictionary with chunks and query
        
    Returns:
        Dictionary with ranked_chunks and status
    """
    try:
        # Parse input - need to convert chunks back to TextChunk objects
        chunks_data = input_data.get('chunks', [])
        chunks = [TextChunk(**chunk_data) for chunk_data in chunks_data]
        
        ranking_input = SemanticRankingInput(
            chunks=chunks,
            query=input_data['query']
        )
        
        # Process
        tool = SemanticRankingTool()
        result = await tool.process(ranking_input)
        
        # Convert result to dictionary format
        result_dict = result.dict()
        
        # Convert RankedChunk objects to dictionaries if present
        if result_dict.get('ranked_chunks'):
            result_dict['ranked_chunks'] = [
                {
                    'chunk': ranked_chunk.chunk.dict(),
                    'relevance_score': ranked_chunk.relevance_score
                }
                for ranked_chunk in result.ranked_chunks
            ]
        
        return result_dict
        
    except Exception as e:
        logger.error(f"Semantic ranking tool error: {str(e)}")
        return {
            "ranked_chunks": None,
            "status": "error",
            "error_code": ErrorCode.E500_PROCESSING_FAILED
        }
