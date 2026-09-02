"""
Hugging Face Spaces Entry Point
Serves the FastAPI ScrapeAI Dashboard and RAG Assistant directly.
"""

import os
import uvicorn
from backend.server import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f">> Launching ScrapeAI on Hugging Face Spaces (Port: {port})...")
    uvicorn.run(app, host="0.0.0.0", port=port)
