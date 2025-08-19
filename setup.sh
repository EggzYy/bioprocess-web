#!/bin/bash

# Bioprocess Web Application Setup Script
# This script sets up the development environment

set -e  # Exit on error

echo "========================================="
echo "Bioprocess Web Application Setup"
echo "========================================="

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "Error: Python $required_version or higher is required (found $python_version)"
    exit 1
fi
echo "✓ Python $python_version found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating directory structure..."
mkdir -p logs
mkdir -p data
mkdir -p exports
mkdir -p configs
mkdir -p temp

# Copy original calculation modules if they exist
if [ -f "../fermentation_capacity_calculator.py" ]; then
    echo "Copying fermentation_capacity_calculator.py..."
    cp ../fermentation_capacity_calculator.py bioprocess/
    echo "✓ Copied fermentation_capacity_calculator.py"
fi

if [ -f "../pricing_integrated.py" ]; then
    echo "Copying pricing_integrated.py as reference..."
    cp ../pricing_integrated.py bioprocess/pricing_integrated_original.py
    echo "✓ Copied pricing_integrated.py"
fi

# Create __init__.py files
echo "Creating package initialization files..."
touch bioprocess/__init__.py
touch api/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py

# Set executable permissions
chmod +x setup.sh

echo ""
echo "========================================="
echo "✓ Setup completed successfully!"
echo "========================================="
echo ""
echo "To start developing:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Start the development server:"
echo "   uvicorn api.main:app --reload"
echo ""
echo "3. Open your browser to:"
echo "   http://localhost:8000"
echo ""
echo "For API documentation, visit:"
echo "   http://localhost:8000/docs"
echo "========================================="
