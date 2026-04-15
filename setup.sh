#!/bin/bash
# setup.sh
# Installs all required dependencies for the resume-tailor skill.
# Run this script once before using the skill on a new machine.

echo "Setting up dependencies for Resume Tailor..."

# Detect OS
OS="$(uname)"
if [ "$OS" = "Darwin" ]; then
    echo "macOS detected. Using Homebrew..."
    
    # Check for Homebrew
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Please install Homebrew first: https://brew.sh/"
        exit 1
    fi
    
    # Install system packages
    echo "Installing system packages (pandoc, libreoffice, poppler)..."
    brew install pandoc poppler
    brew list --cask libreoffice &>/dev/null || brew install --cask libreoffice
    
    # Check for Node
    if ! command -v node &> /dev/null; then
        echo "Node.js not found. Installing Node..."
        brew install node
    fi

    # Check for Python 3
    if ! command -v python3 &> /dev/null; then
        echo "Python 3 not found. Installing Python..."
        brew install python
    fi

elif [ "$OS" = "Linux" ]; then
    echo "Linux detected. Using apt..."
    
    # Check for apt
    if ! command -v apt &> /dev/null; then
        echo "apt not found. Please install dependencies manually (see references/environment_setup.md)."
        exit 1
    fi
    
    echo "Installing system packages..."
    sudo apt update
    sudo apt install -y pandoc libreoffice poppler-utils nodejs npm python3
else
    echo "Unsupported OS: $OS. Please install dependencies manually (see references/environment_setup.md)."
    exit 1
fi

# Install global npm packages
echo "Installing npm packages (docx)..."
npm install -g docx

echo "====================================="
echo "Setup complete! Verifying installations:"
echo "-------------------------------------"
echo -n "pandoc: " && command -v pandoc || echo "MISSING"
echo -n "python3: " && command -v python3 || echo "MISSING"
echo -n "node: " && command -v node || echo "MISSING"
echo -n "libreoffice: " && command -v libreoffice || echo "MISSING"
echo -n "pdfinfo: " && command -v pdfinfo || echo "MISSING"
echo -n "docx (npm): " && npm list -g docx | grep docx || echo "MISSING"
echo "====================================="
echo "If any are MISSING, check the logs above."
