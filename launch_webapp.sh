#!/bin/bash
# RING-5 Quick Launch Script
# Launches the interactive web application

echo "RING-5 Interactive Web Application"
echo "======================"
echo ""

# Check if virtual environment exists
if [ ! -d "python_venv" ]; then
    echo "Virtual environment not found!"
    echo "Run: make build"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source python_venv/bin/activate

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "Installing Streamlit..."
    pip install streamlit openpyxl -q
fi

echo "Environment ready!"
echo ""
echo "Starting web application..."
echo "URL: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop"
echo "======================"
echo ""

# Launch Streamlit
streamlit run app.py --server.headless true

echo ""
echo "Application stopped."
