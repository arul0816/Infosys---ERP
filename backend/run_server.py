#!/usr/bin/env python
"""
Server startup wrapper script
"""
import sys
import os
import uvicorn

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    # Import the app after path is set
    from main import app
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False  # Disable reload in production
    )
