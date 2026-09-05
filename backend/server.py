"""
FastAPI Server for Universal Web Scraper & Hugging Face RAG Chatbot
Exposes REST APIs for single-URL and continuous multi-website batch scraping with rotating proxies.
"""

import os
import time
from typing import Optional, Dict, Any, List, Union
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from backend.scraper import UniversalScraper, ProxyPool, normalize_proxy_url, mask_proxy
from backend.rag_engine import RAGEngine
from backend.storage import (
    save_scrape_session,
    save_batch_session,
    get_history,
    export_to_csv,
    export_to_markdown,
    export_batch_to_csv,
    DATA_DIR
)

app = FastAPI(
    title="Universal Web Scraper & RAG AI API",
    description="Extract clean data from any URL and query it interactively with Hugging Face RAG.",
    version="1.1.0"
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
current_batch_data: Optional[Dict[str, Any]] = None


# Request Models
class ScrapeRequest(BaseModel):
    url: str = Field(..., description="Target website URL to scrape")
    custom_selector: Optional[str] = Field(None, description="Optional CSS selector")
    proxy: Optional[str] = Field(None, description="Optional HTTP/HTTPS/SOCKS5 proxy URL")
    hf_token: Optional[str] = Field(None, description="Hugging Face API Token")
    model_name: Optional[str] = Field("Qwen/Qwen2.5-7B-Instruct", description="HF Model Name")


class BatchScrapeRequest(BaseModel):
    urls: List[str] = Field(..., description="List of target website URLs to scrape continuously")
    proxies: Optional[Union[List[str], str]] = Field(None, description="Proxy list or multiline string")
    proxy_rotation: Optional[str] = Field("round-robin", description="Rotation strategy: 'round-robin' or 'random'")
    delay_seconds: Optional[float] = Field(1.0, description="Delay between requests in seconds")
    custom_selector: Optional[str] = Field(None, description="Optional CSS selector")
    hf_token: Optional[str] = Field(None, description="Hugging Face API Token")
    model_name: Optional[str] = Field("Qwen/Qwen2.5-7B-Instruct", description="HF Model Name")


class ProxyTestRequest(BaseModel):
    proxy: Optional[str] = Field(None, description="Proxy URL to test (e.g. http://127.0.0.1:8080 or socks5://...)")


class ChatRequest(BaseModel):
    question: str = Field(..., description="User question about the scraped content")
    hf_token: Optional[str] = Field(None, description="Hugging Face API Token")
    model_name: Optional[str] = Field("Qwen/Qwen2.5-7B-Instruct", description="HF Model Name")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt instructions")


class ExportRequest(BaseModel):
    format: str = Field("json", description="Export format: json, csv, markdown, txt")
    is_batch: Optional[bool] = Field(False, description="Whether to export current batch dataset")


# --- API Routes ---

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "Universal Web Scraper & RAG Engine",
        "has_active_scrape": current_scraped_data is not None or current_batch_data is not None,
        "indexed_chunks": len(rag_engine.chunks)
    }


@app.get("/api/config")
def get_config():
    env_proxy = os.getenv("SCRAPER_PROXIES") or os.getenv("SCRAPER_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    return {
        "supported_models": [
            {"id": "Qwen/Qwen2.5-7B-Instruct", "name": "Qwen 2.5 (7B Instruct) - Recommended"},
            {"id": "meta-llama/Llama-3.2-3B-Instruct", "name": "Llama 3.2 (3B Instruct) - Fast"},
            {"id": "mistralai/Mistral-7B-Instruct-v0.3", "name": "Mistral (7B Instruct)"},
            {"id": "HuggingFaceH4/zephyr-7b-beta", "name": "Zephyr (7B Beta)"},
            {"id": "google/gemma-2-2b-it", "name": "Google Gemma 2 (2B IT)"}
        ],
        "default_model": "Qwen/Qwen2.5-7B-Instruct",
        "has_env_token": bool(os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")),
        "has_env_proxy": bool(env_proxy),
        "env_proxy_masked": mask_proxy(env_proxy) if env_proxy else None
    }


@app.post("/api/proxy/test")
def test_proxy_endpoint(req: ProxyTestRequest):
    """Test proxy connectivity by checking public IP."""
    import requests
    target_proxy = req.proxy or os.getenv("SCRAPER_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    proxies_dict = None
    if target_proxy:
        norm = normalize_proxy_url(target_proxy)
        proxies_dict = {"http": norm, "https": norm}

    test_urls = ["https://httpbin.org/ip", "https://api.ipify.org?format=json"]
    last_err = None

    for t_url in test_urls:
        try:
            start_t = time.time()
            resp = requests.get(t_url, proxies=proxies_dict, timeout=10)
            resp.raise_for_status()
            latency = round(time.time() - start_t, 2)
            data = resp.json()
            origin_ip = data.get("origin") or data.get("ip") or "Unknown"
            return {
                "success": True,
                "ip": origin_ip,
                "latency_seconds": latency,
                "proxy_tested": mask_proxy(target_proxy) if target_proxy else "Direct (No Proxy)",
                "message": f"Connected successfully via {mask_proxy(target_proxy) or 'Direct'} in {latency}s!"
            }
        except Exception as e:
            last_err = e

    return {
        "success": False,
        "proxy_tested": mask_proxy(target_proxy),
        "error": str(last_err),
        "message": f"Proxy connection failed: {str(last_err)}"
    }


@app.post("/api/scrape")
def scrape_endpoint(req: ScrapeRequest):
    """Scrape a single target URL with optional proxy."""
    global current_scraped_data
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    try:
        data = scraper.scrape(req.url, custom_selector=req.custom_selector, proxy=req.proxy)
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


@app.post("/api/scrape/batch")
def batch_scrape_endpoint(req: BatchScrapeRequest):
    """
    Continuous Multi-Website Scraping with Proxy Pool Rotation.
    Scrapes a list of target URLs sequentially/continuously with proxy rotation & delay.
    """
    global current_batch_data, current_scraped_data
    urls = [u.strip() for u in req.urls if u.strip()]
    if not urls:
        raise HTTPException(status_code=400, detail="URLs list cannot be empty")

    try:
        batch_result = scraper.scrape_batch(
            urls=urls,
            custom_selector=req.custom_selector,
            proxies=req.proxies,
            proxy_rotation=req.proxy_rotation or "round-robin",
            delay=req.delay_seconds if req.delay_seconds is not None else 1.0
        )

        current_batch_data = batch_result

        # Index combined scraped corpus into RAG AI
        if batch_result.get("combined_text"):
            if req.hf_token:
                rag_engine.set_hf_token(req.hf_token)
            if req.model_name:
                rag_engine.set_model_name(req.model_name)

            rag_engine.build_index(
                batch_result["combined_text"],
                metadata={
                    "title": f"Batch Scrape ({batch_result['success_count']} Sites)",
                    "url": f"{len(urls)} URLs"
                }
            )
            batch_result["indexed_chunks"] = len(rag_engine.chunks)

        # Auto-save batch session
        saved_file = save_batch_session(batch_result)
        batch_result["saved_filename"] = saved_file

        return batch_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch scraping failed: {str(e)}")


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    """Interactive Chatbot / RAG querying over scraped content."""
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
    """Export single or batch scraped datasets."""
    global current_scraped_data, current_batch_data

    fmt = req.format.lower().strip()

    # Batch export
    if req.is_batch:
        if not current_batch_data:
            raise HTTPException(status_code=400, detail="No active batch scrape data to export.")
        
        if fmt == "csv":
            path = export_batch_to_csv(current_batch_data)
            return FileResponse(path, media_type="text/csv", filename=os.path.basename(path))
        elif fmt == "markdown" or fmt == "md":
            text = current_batch_data.get("combined_text", "")
            return PlainTextResponse(text, headers={"Content-Disposition": 'attachment; filename="batch_scraped_report.md"'})
        elif fmt == "txt":
            text = current_batch_data.get("combined_text", "")
            return PlainTextResponse(text, headers={"Content-Disposition": 'attachment; filename="batch_scraped_corpus.txt"'})
        else:  # json
            return JSONResponse(
                content=current_batch_data,
                headers={"Content-Disposition": 'attachment; filename="batch_scraped_data.json"'}
            )

    # Single item export
    if not current_scraped_data:
        raise HTTPException(status_code=400, detail="No active scraped data to export. Please scrape a URL first.")

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
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")

    @app.get("/")
    def serve_frontend_index():
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend index.html not found."}

    @app.get("/style.css")
    def serve_frontend_css():
        return FileResponse(os.path.join(FRONTEND_DIR, "style.css"))

    @app.get("/app.js")
    def serve_frontend_js():
        return FileResponse(os.path.join(FRONTEND_DIR, "app.js"))


if __name__ == "__main__":
    import uvicorn
    print("Starting Universal Web Scraper & Hugging Face RAG Server on http://localhost:8000 ...")
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=True)
