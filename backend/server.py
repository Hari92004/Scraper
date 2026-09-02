"""
FastAPI Server for Universal Web Scraper & Hugging Face RAG Chatbot
Exposes REST APIs and serves the frontend dashboard.
"""

import os
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from backend.scraper import UniversalScraper
from backend.rag_engine import RAGEngine
from backend.storage import (
    save_scrape_session,
    get_history,
    export_to_csv,
    export_to_markdown,
    DATA_DIR
)

app = FastAPI(
    title="Universal Web Scraper & RAG AI API",
    description="Extract clean data from any URL and query it interactively with Hugging Face RAG.",
    version="1.0.0"
)

# Enable CORS for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Instances
scraper = UniversalScraper(timeout=20)
rag_engine = RAGEngine()
current_scraped_data: Optional[Dict[str, Any]] = None


# Request Models
class ScrapeRequest(BaseModel):
    url: str = Field(..., description="Target website URL to scrape")
    custom_selector: Optional[str] = Field(None, description="Optional CSS selector")
    hf_token: Optional[str] = Field(None, description="Hugging Face API Token")
    model_name: Optional[str] = Field("Qwen/Qwen2.5-7B-Instruct", description="HF Model Name")


class ChatRequest(BaseModel):
    question: str = Field(..., description="User question about the scraped content")
    hf_token: Optional[str] = Field(None, description="Hugging Face API Token")
    model_name: Optional[str] = Field("Qwen/Qwen2.5-7B-Instruct", description="HF Model Name")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt instructions")


class ExportRequest(BaseModel):
    format: str = Field("json", description="Export format: json, csv, markdown, txt")


# --- API Routes ---

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "Universal Web Scraper & RAG Engine",
        "has_active_scrape": current_scraped_data is not None,
        "indexed_chunks": len(rag_engine.chunks)
    }


@app.get("/api/config")
def get_config():
    return {
        "supported_models": [
            {"id": "Qwen/Qwen2.5-7B-Instruct", "name": "Qwen 2.5 (7B Instruct) - Recommended"},
            {"id": "meta-llama/Llama-3.2-3B-Instruct", "name": "Llama 3.2 (3B Instruct) - Fast"},
            {"id": "mistralai/Mistral-7B-Instruct-v0.3", "name": "Mistral (7B Instruct)"},
            {"id": "HuggingFaceH4/zephyr-7b-beta", "name": "Zephyr (7B Beta)"},
            {"id": "google/gemma-2-2b-it", "name": "Google Gemma 2 (2B IT)"}
        ],
        "default_model": "Qwen/Qwen2.5-7B-Instruct",
        "has_env_token": bool(os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY"))
    }


@app.post("/api/scrape")
def scrape_endpoint(req: ScrapeRequest):
    global current_scraped_data
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    try:
        data = scraper.scrape(req.url, custom_selector=req.custom_selector)
        current_scraped_data = data

        # Update HF config if provided
        if req.hf_token:
            rag_engine.set_hf_token(req.hf_token)
        if req.model_name:
            rag_engine.set_model_name(req.model_name)

        # Build RAG Index over the scraped article text
        article_text = data.get("article", {}).get("text", "")
        rag_engine.build_index(
            article_text,
            metadata={
                "title": data.get("metadata", {}).get("title", ""),
                "url": data.get("url", "")
            }
        )

        # Auto-save session
        saved_file = save_scrape_session(data)
        data["saved_filename"] = saved_file
        data["indexed_chunks"] = len(rag_engine.chunks)

        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if req.hf_token:
        rag_engine.set_hf_token(req.hf_token)
    if req.model_name:
        rag_engine.set_model_name(req.model_name)
    if req.system_prompt:
        rag_engine.set_system_prompt(req.system_prompt)

    res = rag_engine.query(req.question.strip())
    return res


@app.post("/api/export")
def export_endpoint(req: ExportRequest):
    global current_scraped_data
    if not current_scraped_data:
        raise HTTPException(status_code=400, detail="No active scraped data to export. Please scrape a URL first.")

    fmt = req.format.lower().strip()
    if fmt == "csv":
        path = export_to_csv(current_scraped_data)
        return FileResponse(path, media_type="text/csv", filename=os.path.basename(path))
    elif fmt == "markdown" or fmt == "md":
        path = export_to_markdown(current_scraped_data)
        return FileResponse(path, media_type="text/markdown", filename=os.path.basename(path))
    elif fmt == "txt":
        text = current_scraped_data.get("article", {}).get("text", "")
        return PlainTextResponse(text, headers={"Content-Disposition": 'attachment; filename="scraped_article.txt"'})
    else:  # json
        return JSONResponse(
            content=current_scraped_data,
            headers={"Content-Disposition": 'attachment; filename="scraped_data.json"'}
        )


@app.get("/api/history")
def history_endpoint():
    return {"history": get_history()}


# Mount Frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_frontend_index():
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend index.html not found."}


if __name__ == "__main__":
    import uvicorn
    print("Starting Universal Web Scraper & Hugging Face RAG Server on http://localhost:8000 ...")
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=True)
