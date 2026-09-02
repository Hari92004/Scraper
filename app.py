"""
Hugging Face Spaces & Cloud Entry Point
FastAPI app instance exported directly for ASGI servers (Uvicorn, Gunicorn).
"""

import os
import uvicorn
from backend.server import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))  # 7860 is default for Hugging Face Spaces
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
