# Challenge 1b: Persona-Driven PDF Analysis System

## 📋 Overview
Challenge 1b implements an advanced AI-powered PDF analysis system that processes multiple document collections and extracts relevant content based on specific user personas and job requirements. The system uses microservices architecture with Docker containerization.

## 🎯 Challenge Requirements
- **Persona-Based Analysis**: Extract content relevant to specific user roles
- **Multi-Collection Processing**: Handle multiple document sets simultaneously
- **Performance**: <10 seconds processing for document collections
- **AI Integration**: Semantic understanding and content ranking
- **Schema Compliance**: Structured JSON output format

## 📁 Project Structure
```
Challenge_1b/
├── Collection 1/                           # Travel Planning Scenario
│   ├── PDFs/                              # 7 South of France travel guides
│   │   ├── South of France - Cities.pdf
│   │   ├── South of France - Cuisine.pdf
│   │   ├── South of France - History.pdf
│   │   ├── South of France - Restaurants and Hotels.pdf
│   │   ├── South of France - Things to Do.pdf
│   │   ├── South of France - Tips and Tricks.pdf
│   │   └── South of France - Traditions and Culture.pdf
│   ├── challenge1b_input.json             # Travel planner persona input
│   └── challenge1b_output.json            # Expected analysis results
│
├── Collection 2/                           # Adobe Acrobat Learning
│   ├── PDFs/                              # 15 Acrobat tutorial documents
│   │   ├── Learn Acrobat - Create and Convert_1.pdf
│   │   ├── Learn Acrobat - Edit_1.pdf
│   │   ├── Learn Acrobat - Fill and Sign.pdf
│   │   ├── Learn Acrobat - Generative AI_1.pdf
│   │   └── ... (11 more Acrobat guides)
│   ├── challenge1b_input.json             # HR professional persona input
│   └── challenge1b_output.json            # Expected analysis results
│
├── Collection 3/                           # Recipe Collection
│   ├── PDFs/                              # 9 cooking and recipe guides
│   │   ├── Breakfast Ideas.pdf
│   │   ├── Dinner Ideas - Mains_1.pdf
│   │   ├── Lunch Ideas.pdf
│   │   └── ... (6 more recipe guides)
│   ├── challenge1b_input.json             # Food contractor persona input
│   └── challenge1b_output.json            # Expected analysis results
│
├── output/                                 # Generated Results
│   ├── collection1_output.json            # Travel planner analysis
│   ├── collection2_output.json            # HR professional analysis
│   └── collection3_output.json            # Food contractor analysis
│
├── persona-pdf-analysis/                   # 🎯 MAIN IMPLEMENTATION
│   ├── src/                               # Core source code
│   │   ├── orchestrator/                  # Main coordination logic
│   │   │   ├── persona_query_orchestrator.py  # Primary orchestrator
│   │   │   └── __init__.py
│   │   ├── tools/                         # Processing microservices
│   │   │   ├── document_processor.py      # PDF text extraction
│   │   │   ├── query_formulation.py       # AI query generation
│   │   │   ├── semantic_ranking.py        # Content relevance scoring
│   │   │   ├── json_formatter.py          # Output formatting
│   │   │   └── __init__.py
│   │   ├── shared/                        # Common utilities
│   │   │   ├── models.py                  # Data models & schemas
│   │   │   ├── utils.py                   # Utility functions
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── docker/                            # Individual service containers
│   │   ├── Dockerfile.document-processor  # PDF processing container
│   │   ├── Dockerfile.query-formulation   # AI query container
│   │   ├── Dockerfile.semantic-ranking    # Ranking service container
│   │   └── Dockerfile.json-formatter      # Output formatting container
│   ├── docker-compose.yml                 # Service orchestration
│   ├── Dockerfile                         # Main application container
│   ├── main.py                            # CLI entry point
│   ├── requirements.txt                   # All dependencies
│   ├── requirements-minimal.txt           # Basic testing dependencies
│   ├── requirements-document-processor.txt # PDF processing only
│   ├── requirements-semantic-ranking.txt  # AI ranking only
│   ├── requirements-query-formulation.txt # Query generation only
│   ├── requirements-json-formatter.txt    # Output formatting only
│   ├── setup.sh                          # Automated environment setup
│   └── README.md                         # Implementation documentation
│
└── README.md                              # This documentation
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose (optional)
- 8-core CPU / 16GB RAM (recommended)

### Option 1: Local Python Setup (Fastest)
```bash
# Navigate to implementation directory
cd Challenge_1b/persona-pdf-analysis

# Install minimal dependencies
pip install -r requirements-minimal.txt

# Run with Collection 1 (Travel Planning)
python main.py "../Collection 1/challenge1b_input.json" "../Collection 1/PDFs" -o "../output/collection1_output.json"

# Run with Collection 2 (HR Professional)
python main.py "../Collection 2/challenge1b_input.json" "../Collection 2/PDFs" -o "../output/collection2_output.json"

# Run with Collection 3 (Food Contractor)
python main.py "../Collection 3/challenge1b_input.json" "../Collection 3/PDFs" -o "../output/collection3_output.json"
```

### Option 2: Full Installation (All Features)
```bash
cd Challenge_1b/persona-pdf-analysis

# Install all dependencies
pip install -r requirements.txt

# Configure AWS credentials for Bedrock (optional)
aws configure

# Run with enhanced AI capabilities
python main.py "../Collection 1/challenge1b_input.json" "../Collection 1/PDFs" -o "../output/result.json"
```

### Option 3: Docker Microservices (Production)
```bash
cd Challenge_1b/persona-pdf-analysis

# Build and start all services
docker-compose up --build

# Services will be available for API calls
```

## 📊 Input/Output Format

### Input JSON Structure
```json
{
  "challenge_info": {
    "challenge_id": "round_1b_002",
    "test_case_name": "travel_planner",
    "description": "France Travel"
  },
  "documents": [
    {"filename": "South of France - Cities.pdf", "title": "Cities Guide"}
  ],
  "persona": {
    "role": "Travel Planner"
  },
  "job_to_be_done": {
    "task": "Plan a trip of 4 days for a group of 10 college friends."
  }
}
```

### Output JSON Structure
```json
{
  "metadata": {
    "input_documents": ["South of France - Cities.pdf"],
    "persona": "Travel Planner",
    "job_to_be_done": "Plan a trip of 4 days for a group of 10 college friends.",
    "processing_timestamp": "2025-07-28T17:53:45.175335",
    "total_documents_processed": 7,
    "total_chunks_extracted": 142,
    "processing_time_seconds": 8.5,
    "errors": []
  },
  "extracted_sections": [
    {
      "document": "South of France - Cities.pdf",
      "section_title": "Best Cities for Groups",
      "text_preview": "Nice and Cannes offer excellent group accommodations...",
      "relevance_score": 0.92,
      "importance_rank": 1,
      "page_number": 3
    }
  ],
  "subsection_analysis": [
    {
      "document": "South of France - Things to Do.pdf",
      "refined_text": "Group activities include beach volleyball, wine tasting tours...",
      "relevance_score": 0.87,
      "page_number": 8
    }
  ]
}
```

## 🧠 System Architecture

### Core Components

#### 1. PersonaQueryOrchestrator
- **Purpose**: Main coordination agent
- **Functions**: Request validation, tool orchestration, parallel processing
- **Location**: `src/orchestrator/persona_query_orchestrator.py`

#### 2. Microservices Tools

##### Document Processor Tool
- **Technology**: unstructured + PyMuPDF + OCR
- **Function**: PDF text extraction and intelligent chunking
- **Container**: `docker/Dockerfile.document-processor`

##### Query Formulation Tool
- **Technology**: Amazon Bedrock with Claude 3 Sonnet
- **Function**: Converts persona + job → semantic search queries
- **Container**: `docker/Dockerfile.query-formulation`

##### Semantic Ranking Tool
- **Technology**: SBERT embeddings (all-MiniLM-L6-v2)
- **Function**: Ranks text chunks by relevance using AI
- **Container**: `docker/Dockerfile.semantic-ranking`

##### JSON Output Formatter Tool
- **Technology**: Pydantic validation
- **Function**: Schema-compliant response formatting
- **Container**: `docker/Dockerfile.json-formatter`

## 🎭 Persona Scenarios

### Collection 1: Travel Planner
- **Persona**: Travel planning professional
- **Task**: Plan 4-day trip for 10 college friends to South of France
- **Documents**: 7 travel guides covering cities, cuisine, culture, history
- **Focus**: Group activities, budget options, cultural experiences

### Collection 2: HR Professional
- **Persona**: Human resources professional
- **Task**: Create and manage fillable forms for onboarding and compliance
- **Documents**: 15 Adobe Acrobat tutorials and guides
- **Focus**: Form creation, e-signatures, document management, compliance workflows

### Collection 3: Food Contractor
- **Persona**: Food service contractor
- **Task**: Prepare vegetarian buffet-style dinner menu for corporate gathering
- **Documents**: 9 cooking and recipe guides
- **Focus**: Vegetarian recipes, buffet preparation, dietary requirements, scaling

## ⚡ Performance Features

### Speed Optimizations
- **Parallel Processing**: Concurrent document handling
- **Intelligent Chunking**: Optimized text segmentation
- **Batch Processing**: Efficient AI model utilization
- **Memory Management**: Streaming and garbage collection

### AI Capabilities
- **Semantic Understanding**: Context-aware content analysis
- **Relevance Scoring**: 0.0-1.0 confidence ratings
- **Query Optimization**: Persona-specific search enhancement
- **Error Resilience**: Graceful degradation when AI services fail

## 🧪 Testing & Validation

### Performance Testing
```bash
# Test all collections
cd Challenge_1b/persona-pdf-analysis

# Collection 1 - Travel Planning
time python main.py "../Collection 1/challenge1b_input.json" "../Collection 1/PDFs" -o "../output/test1.json"

# Collection 2 - HR Professional  
time python main.py "../Collection 2/challenge1b_input.json" "../Collection 2/PDFs" -o "../output/test2.json"

# Collection 3 - Food Contractor
time python main.py "../Collection 3/challenge1b_input.json" "../Collection 3/PDFs" -o "../output/test3.json"
```

### Output Validation
```bash
# Check output format compliance
python -c "
import json
with open('../output/collection1_output.json') as f:
    data = json.load(f)
    print(f'Documents: {len(data[\"metadata\"][\"input_documents\"])}')
    print(f'Sections: {len(data[\"extracted_sections\"])}')
    print(f'Processing time: {data[\"metadata\"][\"processing_time_seconds\"]}s')
"
```

## 🐳 Docker Deployment

### Individual Services
```bash
# Build individual containers
docker build -f docker/Dockerfile.document-processor -t doc-processor .
docker build -f docker/Dockerfile.semantic-ranking -t semantic-ranking .
docker build -f docker/Dockerfile.query-formulation -t query-formulation .
docker build -f docker/Dockerfile.json-formatter -t json-formatter .
```

### Full System
```bash
# Launch complete system
docker-compose up --build

# Background deployment
docker-compose up -d --build

# Check service health
docker-compose ps
docker-compose logs
```

## 🔧 Configuration Options

### Environment Variables
```bash
# AWS Bedrock configuration
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1

# Performance tuning
export MAX_WORKERS=8
export BATCH_SIZE=256
export DOCUMENT_TIMEOUT=15
```

### Performance Tuning
```python
# Orchestrator settings
orchestrator = PersonaQueryOrchestrator(
    max_workers=8,        # Parallel processing workers
    document_timeout=15   # Timeout per document (seconds)
)

# Semantic ranking optimization
ranking_tool = SemanticRankingTool(
    model_name="all-MiniLM-L6-v2",
    batch_size=256       # Optimize for your CPU cores
)
```

## 📈 Results Analysis

### Generated Outputs
All processed results are saved in `Challenge_1b/output/`:
- **collection1_output.json**: Travel planning analysis (2,488 bytes)
- **collection2_output.json**: HR professional analysis (4,833 bytes)  
- **collection3_output.json**: Food contractor analysis (2,931 bytes)

### Performance Metrics
- **Processing Speed**: 2-8 seconds per collection
- **Document Coverage**: 7-15 documents per collection
- **Memory Usage**: <4GB RAM in minimal mode
- **Error Handling**: Graceful degradation with detailed error codes

## 🚨 Troubleshooting

### Common Issues
```bash
# Dependency conflicts
pip install -r requirements-minimal.txt  # Use minimal setup

# Memory issues
# Reduce max_workers or batch_size in configuration

# PDF processing errors
pip install -r requirements-document-processor.txt  # Install full PDF support

# AWS/AI service errors
# Check credentials and fallback to minimal mode
```

### Debug Mode
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
python main.py [args] 2>&1 | tee debug.log
```

## 🎯 Success Criteria

### Technical Requirements
- ✅ **Persona-Driven**: Content analysis based on user roles
- ✅ **Multi-Collection**: Handles 3 different document sets
- ✅ **Performance**: <10 second processing per collection
- ✅ **Schema Compliance**: JSON output matches specification
- ✅ **Error Resilience**: Graceful handling of processing failures

### Hackathon Submission
- ✅ **Microservices Architecture**: Independent, scalable components
- ✅ **AI Integration**: Semantic understanding and ranking
- ✅ **Docker Support**: Complete containerization
- ✅ **Production Ready**: Comprehensive error handling and monitoring

---

**Built for Adobe India Hackathon 2025 - Challenge 1b**

*AI-powered persona-driven PDF analysis with microservices architecture.*
