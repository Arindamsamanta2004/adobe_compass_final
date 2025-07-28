# Challenge 1a: Basic PDF Processing Solution

## 📋 Overview
Challenge 1a implements a containerized PDF processing solution that extracts structured data from PDF documents and outputs JSON files according to Adobe Hackathon 2025 specifications.

## 🎯 Challenge Requirements
- **Execution Time**: ≤ 10 seconds for a 50-page PDF
- **Model Size**: ≤ 200MB (if using ML models)
- **Network**: No internet access during runtime
- **Runtime**: CPU-only (AMD64) with 8 CPUs, 16GB RAM
- **Architecture**: Must work on AMD64, not ARM-specific

## 📁 Project Structure
```
Challenge_1a/
├── sample_dataset/                 # Test data and reference outputs
│   ├── pdfs/                      # Input PDF files for testing
│   │   ├── AgriRec_Manuscript_finalized.pdf
│   │   ├── ArewechefbyprofessionorGastronomist.pdf
│   │   └── file05.pdf
│   ├── outputs/                   # Expected JSON outputs
│   │   ├── AgriRec_Manuscript_finalized.json
│   │   ├── ArewechefbyprofessionorGastronomist.json
│   │   └── file05.json
│   └── schema/                    # Output format specification
│       └── output_schema.json     # Required JSON schema
├── Dockerfile                     # Docker container configuration
├── process_pdfs.py               # Main processing script
└── README.md                     # This documentation
```

## 🚀 Quick Start

### Prerequisites
- Docker installed and running
- AMD64 architecture support

### Build Docker Image
```bash
# Navigate to Challenge_1a directory
cd Challenge_1a

# Build the Docker image
docker build --platform linux/amd64 -t pdf-processor .
```

### Run Processing
```bash
# Process PDFs using Docker (production mode)
docker run --rm \
  -v $(pwd)/sample_dataset/pdfs:/app/input:ro \
  -v $(pwd)/sample_dataset/outputs:/app/output \
  --network none \
  pdf-processor

# For local testing with Python
python process_pdfs.py
```

## 📊 Input/Output Format

### Input
- **Location**: `/app/input` directory (read-only)
- **Format**: PDF files (any valid PDF document)
- **Processing**: Automatic discovery of all `*.pdf` files

### Output
- **Location**: `/app/output` directory
- **Format**: JSON files (`filename.json` for each `filename.pdf`)
- **Schema**: Must conform to `sample_dataset/schema/output_schema.json`

### Expected JSON Structure
```json
{
  "outline": [
    {
      "title": "Section Title",
      "level": 1,
      "page_number": 1,
      "subsections": [
        {
          "title": "Subsection Title",
          "level": 2,
          "page_number": 2
        }
      ]
    }
  ],
  "metadata": {
    "total_pages": 10,
    "processing_time_seconds": 5.2,
    "extraction_method": "automated"
  }
}
```

## 🛠️ Implementation Details

### Current Implementation
The `process_pdfs.py` script includes:
- **PDF Discovery**: Automatic scanning of input directory
- **Batch Processing**: Handles multiple PDFs simultaneously
- **Error Handling**: Graceful failure for corrupted/invalid PDFs
- **Schema Compliance**: Outputs match required JSON format

### Performance Optimizations
- **Memory Efficient**: Processes PDFs sequentially to manage memory
- **Fast Processing**: Optimized for <10 second constraint
- **Resource Aware**: Designed for 8-core/16GB systems

## 🧪 Testing

### Validation Checklist
- [ ] All PDFs in input directory processed
- [ ] JSON output files generated for each PDF
- [ ] Output format matches schema requirements
- [ ] Processing completes within 10 seconds
- [ ] Works without internet access
- [ ] Memory usage stays within 16GB limit
- [ ] Compatible with AMD64 architecture

### Test Commands
```bash
# Test with sample data
python process_pdfs.py

# Validate output format
python -c "import json; print(json.load(open('sample_dataset/outputs/file05.json')))"

# Check processing time
time python process_pdfs.py
```

## 🔧 Docker Configuration

### Dockerfile Features
- **Base Image**: Python 3.10 on linux/amd64
- **Dependencies**: Minimal PDF processing libraries
- **Working Directory**: `/app`
- **Entry Point**: Automatic PDF processing on container start
- **Network**: Disabled for security compliance

### Build Arguments
```dockerfile
# Example Dockerfile structure
FROM --platform=linux/amd64 python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY process_pdfs.py .
CMD ["python", "process_pdfs.py"]
```

## 📈 Performance Metrics

### Target Performance
- **Processing Speed**: <10 seconds for 50-page PDF
- **Memory Usage**: <16GB RAM
- **CPU Utilization**: Efficient use of 8 cores
- **Output Accuracy**: 100% schema compliance

### Optimization Strategies
- **Parallel Processing**: Multi-threaded PDF handling
- **Memory Management**: Efficient garbage collection
- **I/O Optimization**: Minimized disk read/write operations
- **Error Recovery**: Robust handling of edge cases

## 🚨 Common Issues & Solutions

### Build Issues
```bash
# Platform compatibility
docker build --platform linux/amd64 -t pdf-processor .

# Permission issues
sudo docker run --rm -v $(pwd)/input:/app/input:ro ...
```

### Runtime Issues
```bash
# Memory constraints
# Reduce batch size or implement streaming processing

# Timeout issues  
# Optimize PDF parsing algorithms
```

## 📝 Development Notes

### Adding New Features
1. Update `process_pdfs.py` with new functionality
2. Test with sample dataset
3. Verify schema compliance
4. Update Docker configuration if needed
5. Validate performance constraints

### Code Standards
- **Language**: Python 3.10+
- **Style**: PEP 8 compliance
- **Documentation**: Inline comments and docstrings
- **Testing**: Unit tests for core functions

## 🎯 Success Criteria

### Technical Requirements
- ✅ **Containerized**: Docker image builds and runs successfully
- ✅ **Performance**: Meets 10-second processing constraint
- ✅ **Compliance**: Outputs match required JSON schema
- ✅ **Robustness**: Handles various PDF formats gracefully

### Hackathon Submission
- ✅ **Repository**: Complete code with working Dockerfile
- ✅ **Documentation**: Clear README with usage instructions
- ✅ **Testing**: Validated with provided sample dataset
- ✅ **Architecture**: AMD64 compatible, no internet dependency

---

**Built for Adobe India Hackathon 2025 - Challenge 1a**

*Efficient, containerized PDF processing with structured data extraction.*
