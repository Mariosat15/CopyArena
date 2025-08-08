#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server on the port provided by Render
uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} 