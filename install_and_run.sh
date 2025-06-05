#!/bin/bash

echo "----------------------------------------------"
echo "MetaStream Aggregator - Installation and Setup"
echo "----------------------------------------------"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed or not in PATH."
    echo "Please install Python 3.9 or higher:"
    echo "  - Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  - macOS: brew install python3 (using Homebrew)"
    echo "  - Or download from https://www.python.org/downloads/"
    exit 1
fi

# Check Python version (need 3.9+)
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo "Python 3.9 or higher is required. You have Python $PYTHON_VERSION."
    exit 1
fi

echo "Python $PYTHON_VERSION detected."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment."
        exit 1
    fi
fi

# Activate virtual environment and install dependencies
echo "Activating virtual environment and installing dependencies..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Failed to activate virtual environment."
    exit 1
fi

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing requirements from requirements.txt..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install requirements."
        deactivate
        exit 1
    fi
else
    echo "Installing required packages..."
    pip install Flask requests beautifulsoup4 lxml google-api-python-client
    if [ $? -ne 0 ]; then
        echo "Failed to install required packages."
        deactivate
        exit 1
    fi
fi

# Create sample files if they don't exist
if [ ! -f "sites.json" ]; then
    if [ -f "sites.example.json" ]; then
        echo "Creating sites.json from example..."
        cp sites.example.json sites.json
    else
        echo "Warning: sites.example.json not found. You will need to create sites.json manually."
    fi
fi

if [ ! -f "settings.json" ]; then
    if [ -f "settings.example.json" ]; then
        echo "Creating settings.json from example..."
        cp settings.example.json settings.json
    else
        echo "Warning: settings.example.json not found. You will need to create settings.json manually."
    fi
fi

# Create cache directory if it doesn't exist
if [ ! -d "cache" ]; then
    mkdir cache
fi

# Make this script executable
chmod +x "$0"

echo ""
echo "---------------------------------------------------"
echo "Installation complete! Starting MetaStream Aggregator..."
echo "---------------------------------------------------"
echo ""
echo "The application will be available at: http://127.0.0.1:8001"
echo "Press Ctrl+C to stop the server when you're done."
echo ""

# Start the Flask application
python3 app.py

# Deactivate virtual environment when the application exits
deactivate