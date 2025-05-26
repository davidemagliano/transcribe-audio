#!/bin/bash
# Deployment script for Audio Transcription App

set -e

echo "🚀 Audio Transcription App Deployment"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.12 or higher."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.12"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)"; then
    print_error "Python $required_version or higher is required. Current version: $python_version"
    exit 1
fi

print_success "Python $python_version detected"

# Check if uv is installed, if not use pip
if command -v uv &> /dev/null; then
    print_status "Using uv for dependency management"
    PACKAGE_MANAGER="uv"
else
    print_warning "uv not found, using pip"
    PACKAGE_MANAGER="pip"
fi

# Install dependencies
print_status "Installing dependencies..."
if [ "$PACKAGE_MANAGER" = "uv" ]; then
    # Just install dependencies without trying to install the project itself
    if [ "$1" = "--dev" ]; then
        uv sync --extra dev --no-install-project
        print_status "Development dependencies installed"
    else
        uv sync --no-install-project
    fi
else
    python3 -m pip install openai pydub python-dotenv streamlit
    if [ "$1" = "--dev" ]; then
        python3 -m pip install pytest pytest-mock black ruff
        print_status "Development dependencies installed"
    fi
fi

print_success "Dependencies installed successfully"

# Check for .env file
if [ ! -f ".env" ]; then
    print_warning ".env file not found"
    if [ -f ".env.example" ]; then
        print_status "Copying .env.example to .env"
        cp .env.example .env
        print_warning "Please edit .env file and add your OpenAI API key"
    else
        print_warning "Please create a .env file with your OpenAI API key"
        echo "OPENAI_API_KEY=your_key_here" > .env
    fi
fi

# Run tests if in dev mode
if [ "$1" = "--dev" ]; then
    print_status "Running tests..."
    python3 -m pytest tests/ -v
    print_success "Tests completed"
fi

# Check if port is available
PORT=${PORT:-8501}
if lsof -i:$PORT >/dev/null 2>&1; then
    print_warning "Port $PORT is already in use"
    print_status "You can specify a different port with: PORT=8502 $0"
fi

print_success "Setup completed successfully!"
echo ""
print_status "To run the application:"
echo "  streamlit run app_improved.py --server.port $PORT"
echo ""
print_status "Or use the original version:"
echo "  streamlit run app.py --server.port $PORT"
echo ""
print_status "Environment variables can be set in .env file"

# Option to start the app immediately
if [ "$2" = "--run" ]; then
    print_status "Starting application..."
    streamlit run app_improved.py --server.port $PORT
fi 