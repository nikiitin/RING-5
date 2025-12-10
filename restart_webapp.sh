#!/bin/bash
# Force restart Streamlit with cache clearing

echo "Stopping any running Streamlit processes..."
pkill -f "streamlit run" 2>/dev/null

echo "Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

echo "Clearing Streamlit cache..."
rm -rf ~/.streamlit/cache 2>/dev/null

echo "Starting Streamlit with fresh cache..."
source python_venv/bin/activate
streamlit run app.py --server.runOnSave=true
