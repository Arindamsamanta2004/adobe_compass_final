# Adobe Compass - Persona-Driven PDF Analysis System

## 🎯 Project Overview

**Adobe Compass** (Codename: "Cogni-Extract") is an AI-powered PDF analysis system built for the **Adobe India Hackathon 2025**. The system processes large collections of PDF documents and extracts semantically relevant information based on user personas and specific job requirements, acting as an intelligent research assistant.

### 🏆 Challenge: "Connecting the Dots" 
**Rethink Reading. Rediscover Knowledge.**

Transform static PDFs into intelligent, interactive experiences that understand structure, surface insights, and respond like a trusted research companion.

### High-Level Architecture
<img width="4096" height="4218" alt="image" src="https://github.com/user-attachments/assets/f745aea6-cee6-4371-9feb-f52e8bdda1f1" />

---

## 📁 Project Structure

```
Adobe_Compass-base/
├── Adobe-India-Hackathon25-main/           # Main hackathon project
│   ├── Challenge_1a/                       # Basic PDF Processing
│   │   ├── sample_dataset/                 # Sample PDFs & expected outputs
│   │   │   ├── pdfs/                      # Input PDF files
│   │   │   ├── outputs/                   # Expected JSON outputs
│   │   │   └── schema/                    # Output schema definition
│   │   ├── Dockerfile                     # Docker container config
│   │   ├── process_pdfs.py               # Sample processing script
│   │   └── README.md                     # Challenge 1a documentation
│   │
│   └── Challenge_1b/                      # Advanced Persona Analysis
│       ├── Collection 1/                  # Travel Planning Scenario
│       │   ├── PDFs/                     # 7 South of France guides
│       │   ├── challenge1b_input.json    # Travel planner persona
│       │   └── challenge1b_output.json   # Expected analysis results
│       ├── Collection 2/                  # Adobe Acrobat Learning
│       │   ├── PDFs/                     # 15 Acrobat tutorials
│       │   ├── challenge1b_input.json    # HR professional persona
│       │   └── challenge1b_output.json   # Expected analysis results
│       ├── Collection 3/                  # Recipe Collection
│       │   ├── PDFs/                     # 9 cooking guides
│       │   ├── challenge1b_input.json    # Food contractor persona
│       │   └── challenge1b_output.json   # Expected analysis results
│       │
│       └── persona-pdf-analysis/          # 🎯 MAIN IMPLEMENTATION
│           ├── src/                       # Core source code
│           │   ├── orchestrator/          # Main coordination logic
│           │   ├── tools/                 # Processing microservices
│           │   └── shared/                # Common utilities & models
│           ├── docker/                    # Individual service containers
│           ├── docker-compose.yml         # Service orchestration
│           ├── Dockerfile                 # Main application container
│           ├── main.py                    # CLI entry point
│           ├── requirements*.txt          # Dependencies for each component
│           └── setup.sh                   # Automated setup script
│
└── README.md                              # This master documentation
```

---

## 🧠 System Architecture

### Core Components

#### 1. **PersonaQueryOrchestrator**
- **Purpose**: Main coordination agent that manages the entire workflow
- **Functions**: Request validation, tool orchestration, parallel processing, result compilation
- **Performance**: <10 seconds processing for 50-page collections

#### 2. **Microservices Architecture**
Each component runs as an independent Docker container:

##### 🔍 Query Formulation Tool
- **Technology**: Amazon Bedrock with Claude 3 Sonnet
- **Function**: Converts persona + job requirements → semantic search queries
- **Input**: User persona + job description
- **Output**: Optimized search queries

##### 📄 Document Processor Tool
- **Technology**: unstructured library + PyMuPDF + OCR
- **Function**: Extracts and intelligently chunks text from PDFs
- **Features**: Selective OCR, parallel processing, error handling
- **Performance**: Concurrent document processing

##### 🎯 Semantic Ranking Tool
- **Technology**: SBERT embeddings (all-MiniLM-L6-v2 model)
- **Function**: Ranks text chunks by relevance to user queries
- **Features**: Batch processing, CPU optimization
- **Output**: Relevance scores (0.0 to 1.0)

##### 📋 JSON Output Formatter Tool
- **Technology**: Pydantic validation
- **Function**: Formats results into schema-compliant JSON
- **Features**: 100% schema compliance, metadata inclusion

---

## 🚀 Key Features

### 🎭 Persona-Driven Analysis
- **Travel Planner**: Extracts itinerary, attractions, cultural experiences
- **HR Professional**: Focuses on forms, compliance, onboarding processes
- **Food Contractor**: Identifies recipes, ingredients, dietary requirements

### ⚡ Performance Optimized
- **Speed**: <10 seconds for 50-page document collections
- **Parallel Processing**: Concurrent document handling with configurable worker pools
- **Resource Efficient**: Optimized for 8-core CPU / 16GB RAM systems

### 🔧 Technical Excellence
- **Error Resilience**: Graceful degradation when services fail
- **Schema Compliance**: 100% adherence to specified JSON output format
- **Containerized**: Each tool runs in isolated Docker containers
- **Local Capable**: Can run completely offline with fallback modes

### 🎯 Use Cases

#### Challenge 1a: Basic PDF Processing
- **Constraint**: ≤10 seconds execution, ≤200MB models, CPU-only, no internet
- **Function**: Extract structured outlines from PDFs → JSON output
- **Architecture**: Single Docker container processing
- **Output**: Structured JSON matching defined schema

#### Challenge 1b: Advanced Persona Analysis
- **Input**: User persona + job description + document collection
- **Process**: AI-powered semantic analysis and ranking
- **Output**: Ranked, relevant sections with metadata and importance scores

---

## 📊 Sample Scenarios

### Scenario 1: Travel Planning (Collection 1)
```json
{
  "persona": {"role": "Travel Planner"},
  "job_to_be_done": {"task": "Plan a 4-day trip for 10 college friends to South of France"},
  "documents": ["South of France - Cities.pdf", "South of France - Cuisine.pdf", ...]
}
```
**Result**: Extracts itineraries, cultural experiences, group-friendly activities

### Scenario 2: HR Professional (Collection 2)
```json
{
  "persona": {"role": "HR Professional"},
  "job_to_be_done": {"task": "Create and manage fillable forms for onboarding"},
  "documents": ["Learn Acrobat - Fill and Sign.pdf", "Learn Acrobat - Edit_1.pdf", ...]
}
```
**Result**: Focuses on form creation, e-signatures, compliance workflows

### Scenario 3: Food Contractor (Collection 3)
```json
{
  "persona": {"role": "Food Contractor"},
  "job_to_be_done": {"task": "Prepare vegetarian buffet menu for corporate gathering"},
  "documents": ["Breakfast Ideas.pdf", "Dinner Ideas - Mains_1.pdf", ...]
}
```
**Result**: Extracts vegetarian recipes, buffet-style preparations, dietary info

---

## 🛠️ Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- 8-core CPU / 16GB RAM (recommended)
- AWS credentials (for full functionality)

### 1. Installation
```bash
# Clone the repository
git clone <repository-url>
cd Adobe_Compass-base/Adobe-India-Hackathon25-main/Challenge_1b/persona-pdf-analysis

# Install dependencies
pip install -r requirements.txt

# Setup environment (automated)
./setup.sh
```

### 2. Configuration
```bash
# Configure AWS credentials for Bedrock
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

### 3. Running the System

#### Docker Compose (Recommended)
```bash
# Build and start all microservices
docker-compose up --build

# Run in background
docker-compose up -d --build
```

#### Command Line Usage
```bash
# Process a collection with persona analysis
python main.py ../Collection\ 1/challenge1b_input.json ../Collection\ 1/ -o result.json

# Challenge 1a basic processing
cd ../../Challenge_1a
docker build --platform linux/amd64 -t pdf-processor .
docker run --rm -v $(pwd)/sample_dataset/pdfs:/app/input:ro -v $(pwd)/output:/app/output --network none pdf-processor
```

---

## 📈 Performance & Constraints

### Challenge 1a Constraints
- **Execution Time**: ≤ 10 seconds for 50-page PDF
- **Model Size**: ≤ 200MB (if using ML models)
- **Network**: No internet access during runtime
- **Runtime**: CPU-only (AMD64) with 8 CPUs, 16GB RAM
- **Output**: Schema-compliant JSON for each input PDF

### Challenge 1b Performance
- **Processing Speed**: <10 seconds for 50-page collections
- **Parallel Workers**: Configurable based on system resources
- **Memory Management**: Efficient chunking and batch processing
- **Error Handling**: Graceful degradation with comprehensive logging

---

## 🔧 Technical Implementation

### Data Flow
1. **Input Validation** → Parse persona + job requirements
2. **Query Generation** → AI-powered semantic query formulation
3. **Document Processing** → Parallel PDF text extraction & chunking
4. **Semantic Ranking** → SBERT-based relevance scoring
5. **Output Formatting** → Schema-compliant JSON generation

### API Reference

#### Input Format
```json
{
  "challenge_info": {
    "challenge_id": "round_1b_XXX",
    "test_case_name": "scenario_name"
  },
  "documents": [{"filename": "doc.pdf", "title": "Title"}],
  "persona": {"role": "User Persona"},
  "job_to_be_done": {"task": "Specific task description"}
}
```

#### Output Format
```json
{
  "metadata": {
    "input_documents": ["list"],
    "persona": "User Persona",
    "job_to_be_done": "Task description",
    "processing_timestamp": "2025-07-27T15:31:22",
    "total_documents_processed": 5,
    "total_chunks_extracted": 127,
    "processing_time_seconds": 8.5
  },
  "extracted_sections": [
    {
      "document": "source.pdf",
      "section_title": "Title",
      "text_preview": "Content preview...",
      "relevance_score": 0.92,
      "page_number": 1
    }
  ]
}
```

---

## 🧪 Testing & Validation

### Automated Testing
```bash
# Run unit tests
python -m pytest tests/ -v

# Integration testing
python tests/integration_test.py

# Performance benchmarking (validates <10s constraint)
python tests/performance_test.py
```

### Manual Testing
```bash
# Test with all sample collections
for collection in {1..3}; do
  python main.py ../Collection\ $collection/challenge1b_input.json ../Collection\ $collection/ -o test_output_$collection.json
done
```

---

## 🚀 Deployment Options

### Local Development
- **Minimal Setup**: Basic PDF processing with PyMuPDF
- **Full Setup**: Complete AI pipeline with all microservices
- **Fallback Mode**: Offline operation without external AI services

### Production Deployment
- **Container Registry**: Push images to your registry
- **Kubernetes**: Use provided manifests for scaling
- **Cloud Integration**: AWS Bedrock, S3 compatibility, ECS/EKS support

---

## 🎯 Future Roadmap

### Round 2: Interactive Web Application
- **Technology**: Adobe PDF Embed API
- **Goal**: Beautiful, intuitive reading webapp
- **Features**: Interactive PDF experience with AI-powered insights

### Enhancements
- **Multi-language Support**: Extend beyond English documents
- **Custom Model Integration**: Support for specialized domain models
- **Real-time Processing**: Streaming analysis for large document sets

---

## 🤝 Team Collaboration

### Git Workflow
```bash
# Start working on a feature
git checkout -b feature/your-feature-name
git add .
git commit -m "Add: Description of changes"
git push origin feature/your-feature-name

# Create Pull Request → Review → Merge
```

### Development Guidelines
- **Code Standards**: Follow Python PEP 8
- **Documentation**: Add docstrings and comments
- **Testing**: Include unit tests for new features
- **Branch Naming**: `feature/`, `bugfix/`, `docs/`

---

## 📞 Support & Contributing

### Getting Help
- Check specifications in project documentation
- Create GitHub issues for bugs
- Use team communication channels
- Review sample implementations

### Contributing
1. Fork the repository
2. Create feature branch
3. Add tests and documentation
4. Submit pull request
5. Participate in code review

---

## 🏆 Hackathon Success Metrics

### Technical Excellence
- ✅ **Performance**: Sub-10 second processing
- ✅ **Accuracy**: Relevant content extraction
- ✅ **Scalability**: Handle multiple document collections
- ✅ **Reliability**: Error resilience and graceful degradation

### Innovation Points
- ✅ **AI Integration**: Semantic understanding with SBERT + Bedrock
- ✅ **Microservices**: Scalable, containerized architecture
- ✅ **Persona-Driven**: Context-aware analysis
- ✅ **Production-Ready**: Complete Docker orchestration

---

**Built for Adobe India Hackathon 2025 - "Connecting the Dots" Challenge**

*Transform static PDFs into intelligent, interactive experiences that understand, analyze, and respond with human-like intelligence.*

---

## 📄 License

This project is licensed under the MIT License. Built using open-source technologies:
- **AI Models**: Sentence Transformers, Amazon Bedrock
- **PDF Processing**: unstructured, PyMuPDF, Tesseract OCR
- **Infrastructure**: Docker, Python, Pydantic

**© 2025 Adobe Compass Team - Revolutionizing PDF Intelligence**
