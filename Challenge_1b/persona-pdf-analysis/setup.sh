#!/bin/bash

# Setup script for Persona-Driven PDF Analysis Agent
# This script installs dependencies and sets up the environment

set -e

echo "=========================================="
echo "Persona-Driven PDF Analysis Agent Setup"
echo "=========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.9"

if [[ $(echo "$python_version >= $required_version" | bc -l) -eq 0 ]]; then
    echo "Error: Python 3.9 or higher is required. Found: $python_version"
    exit 1
fi

echo "✓ Python version check passed ($python_version)"

# Install system dependencies
echo ""
echo "Installing system dependencies..."

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux (Ubuntu/Debian)
    echo "Detected Linux system"
    sudo apt-get update
    sudo apt-get install -y \
        tesseract-ocr \
        tesseract-ocr-eng \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        poppler-utils \
        build-essential \
        python3-dev
    echo "✓ System dependencies installed"

elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "Detected macOS system"
    if command -v brew &> /dev/null; then
        brew install tesseract poppler
        echo "✓ System dependencies installed via Homebrew"
    else
        echo "Warning: Homebrew not found. Please install Tesseract manually:"
        echo "  brew install tesseract poppler"
    fi

else
    echo "Warning: Unsupported OS. Please install Tesseract OCR manually."
fi

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "✓ Virtual environment created and activated"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip
echo "✓ Pip upgraded"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Python dependencies installed"

# Download SBERT model
echo ""
echo "Pre-downloading SBERT model..."
python3 -c "
from sentence_transformers import SentenceTransformer
print('Downloading all-MiniLM-L6-v2 model...')
model = SentenceTransformer('all-MiniLM-L6-v2')
print('Model downloaded successfully')
" 2>/dev/null || echo "Warning: Could not pre-download SBERT model (will download on first use)"

# Check AWS credentials
echo ""
echo "Checking AWS configuration..."
if command -v aws &> /dev/null; then
    if aws sts get-caller-identity &> /dev/null; then
        echo "✓ AWS credentials configured"
    else
        echo "Warning: AWS credentials not configured. Set up with:"
        echo "  aws configure"
        echo "  or set environment variables:"
        echo "  export AWS_ACCESS_KEY_ID=your_key"
        echo "  export AWS_SECRET_ACCESS_KEY=your_secret"
        echo "  export AWS_REGION=us-east-1"
    fi
else
    echo "Warning: AWS CLI not found. Install with:"
    echo "  pip install awscli"
fi

# Check Docker
echo ""
echo "Checking Docker installation..."
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        echo "✓ Docker is available"
        
        if command -v docker-compose &> /dev/null; then
            echo "✓ Docker Compose is available"
        else
            echo "Warning: Docker Compose not found. Install with:"
            echo "  pip install docker-compose"
        fi
    else
        echo "Warning: Docker daemon not running. Start with:"
        echo "  sudo systemctl start docker  # Linux"
        echo "  # or start Docker Desktop    # macOS/Windows"
    fi
else
    echo "Warning: Docker not found. Install from https://docker.com"
fi

# Run tests
echo ""
echo "Running quick validation tests..."
python3 -c "
import sys
sys.path.insert(0, 'src')

try:
    from src.shared.models import RequestJSON, ResponseJSON
    print('✓ Core models import successfully')
except ImportError as e:
    print(f'✗ Model import failed: {e}')
    
try:
    from src.shared.utils import create_error_log, ErrorCode
    print('✓ Utilities import successfully')
except ImportError as e:
    print(f'✗ Utilities import failed: {e}')

try:
    from src.tools.query_formulation import QueryFormulationTool
    print('✓ Query formulation tool available')
except ImportError as e:
    print(f'✗ Query formulation tool failed: {e}')
    
try:
    from src.tools.semantic_ranking import SemanticRankingTool
    print('✓ Semantic ranking tool available')
except ImportError as e:
    print(f'✗ Semantic ranking tool failed: {e}')
"

echo ""
echo "=========================================="
echo "Setup completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Configure AWS credentials (if not done):"
echo "   aws configure"
echo ""
echo "3. Test with sample data:"
echo "   python main.py ../Collection\\ 1/challenge1b_input.json ../Collection\\ 1/ -o test_output.json"
echo ""
echo "4. Run with Docker:"
echo "   docker-compose up --build"
echo ""
echo "For more information, see README.md"
