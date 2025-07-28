"""
Main entry point for the Persona-Driven PDF Analysis Agent.
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.shared.models import RequestJSON, ResponseJSON
from src.orchestrator.persona_query_orchestrator import PersonaQueryOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('persona_pdf_analysis.log')
    ]
)

logger = logging.getLogger(__name__)


async def process_request_file(input_file_path: str, documents_base_path: str, output_file_path: str = None):
    """
    Process a request from a JSON file.
    
    Args:
        input_file_path: Path to input JSON file
        documents_base_path: Base path for PDF documents
        output_file_path: Path for output JSON file (optional)
    """
    try:
        # Load request
        logger.info(f"Loading request from {input_file_path}")
        with open(input_file_path, 'r', encoding='utf-8') as f:
            request_data = json.load(f)
        
        # Parse request
        request = RequestJSON(**request_data)
        logger.info(f"Parsed request: {len(request.documents)} documents, persona: {request.persona.role}")
        
        # Process request
        orchestrator = PersonaQueryOrchestrator()
        response = await orchestrator.process_request(request, documents_base_path)
        
        # Convert response to dictionary (using new Pydantic v2 method)
        response_dict = response.model_dump()
        
        # Ensure datetime serialization
        if 'metadata' in response_dict and 'processing_timestamp' in response_dict['metadata']:
            timestamp = response_dict['metadata']['processing_timestamp']
            if hasattr(timestamp, 'isoformat'):
                response_dict['metadata']['processing_timestamp'] = timestamp.isoformat()
        
        # Custom JSON encoder for datetime objects
        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        # Output response
        if output_file_path:
            logger.info(f"Writing response to {output_file_path}")
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(response_dict, f, indent=2, ensure_ascii=False, default=json_serial)
        else:
            print(json.dumps(response_dict, indent=2, ensure_ascii=False, default=json_serial))
        
        logger.info("Processing completed successfully")
        
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise


async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Persona-Driven PDF Analysis Agent')
    parser.add_argument('input_file', help='Input JSON file with request')
    parser.add_argument('documents_path', help='Base path to PDF documents')
    parser.add_argument('-o', '--output', help='Output JSON file (optional)')
    
    args = parser.parse_args()
    
    # Validate paths
    if not os.path.exists(args.input_file):
        logger.error(f"Input file not found: {args.input_file}")
        return 1
    
    if not os.path.exists(args.documents_path):
        logger.error(f"Documents path not found: {args.documents_path}")
        return 1
    
    try:
        await process_request_file(args.input_file, args.documents_path, args.output)
        return 0
    except Exception as e:
        logger.error(f"Application failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
