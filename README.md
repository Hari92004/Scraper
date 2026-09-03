---
title: Scraper
emoji: 🕷️
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: 4.44.0
python_version: '3.10'
app_file: app.py
pinned: false
license: mit
short_description: Universal Web Scraper & Hugging Face RAG Chatbot
---

# 🕷️ ScrapeAI • Universal Web Scraper & Hugging Face RAG Chatbot

An end-to-end, production-ready Web Scraping & RAG (Retrieval-Augmented Generation) platform. Extract clean text, metadata, structured tables, links, and media from **any website URL**, explore data in a modern glassmorphic dashboard, export to CSV/JSON/Markdown, and interactively query the scraped content using an embedded **Hugging Face RAG AI Assistant**.

---

## ✨ Key Features

- **🌐 Universal Web Scraping Engine**:
  - Extracts clean article text (boilerplate & ad removal with Trafilatura).
  - Extracts structured HTML tables into interactive grids and downloadable CSV datasets.
  - Extracts internal & external links, image galleries, and OpenGraph metadata.
  - Supports optional custom CSS selectors for targeted scraping.
- **🤖 Hugging Face RAG Chatbot**:
  - Text chunking & vector indexing for semantic similarity search.
  - Multi-model support: **Qwen 2.5 (7B)**, **Llama 3.2 (3B)**, **Mistral 7B**, **Zephyr 7B**, **Google Gemma 2**.
  - Ground-truth citations & text snippets highlighting exactly where facts came from.
  - Customizable System Prompt persona.
  - **Offline Zero-Key Fallback Mode** (works even without an API key!).
- **🎨 Luxury Glassmorphic UI**:
  - Modern dark carbon aesthetic with violet & cyan neon accents.
  - Dynamic expandable sidebar with quick navigation.
  - Interactive table explorer with search and sorting.
  - 1-click Export to **CSV**, **JSON**, **Markdown**, and **TXT**.
  - Presets for Wikipedia, tech news, python docs, and blogs.
  - Scrape history tracking.
- **🚀 Multi-Platform Deployment Ready**:
  - Ready for **Hugging Face Spaces** (Docker template).
  - Ready for **Render / Railway / Koyeb** (`render.yaml`, `Procfile`, `Dockerfile`).
  - Ready for **Vercel / Netlify** (`vercel.json`, `netlify.toml`).
  - Full CLI support for terminal workflows.

---

## 🏗️ Project Architecture

```
Scraper/
├── frontend/
│   ├── index.html        # Modern semantic HTML5 interface
│   ├── style.css         # Glassmorphism dark mode design system
│   └── app.js            # Client controller, tab routing, RAG chat stream
├── backend/
│   ├── __init__.py
│   ├── server.py         # FastAPI backend exposing REST endpoints
│   ├── scraper.py        # Universal scraping engine (BeautifulSoup + Trafilatura)
│   ├── rag_engine.py     # Hugging Face RAG pipeline (Chunking + Vector Indexing + QA)
│   └── storage.py        # Persistence & multi-format exporter
├── data/                 # Saved scrapes, datasets & history
├── app.py                # Hugging Face Spaces / ASGI entrypoint
├── main.py               # Top-level CLI and server launcher
├── Dockerfile            # Container deployment configuration
├── requirements.txt      # Python dependencies
├── render.yaml           # Render deployment configuration
├── Procfile              # Railway / Render start command
├── vercel.json           # Vercel deployment configuration
├── netlify.toml          # Netlify deployment configuration
├── .gitignore
└── README.md
```

---

## ⚡ Quick Start (Local Setup)

### 1. Clone & Install Dependencies
Make sure you have **Python 3.9+** installed:

```bash
# Clone the repository
git clone https://github.com/Hari92004/Scraper.git
cd Scraper

# Create virtual environment (Optional but recommended)
python -m venv venv
venv\Scripts\activate      # On Windows
# source venv/bin/activate # On macOS/Linux

# Install requirements
pip install -r requirements.txt
```

### 2. Launch the Web Application
```bash
python main.py
```
Open your browser and visit: **`http://localhost:8000`**

---

## 💻 CLI Mode (Terminal Usage)

You can scrape single websites or continuous batches with rotating proxies directly from your terminal:

```bash
# 1. Scrape a single URL with an optional proxy
python main.py --cli --url "https://en.wikipedia.org/wiki/Web_scraping" --proxy "http://127.0.0.1:8080"

# 2. Continuous Multi-Website Batch Scraping with Rotating Proxy Pool
python main.py --cli --urls "https://en.wikipedia.org/wiki/Web_scraping,https://news.ycombinator.com" --proxies "http://127.0.0.1:8080,socks5://127.0.0.1:9050" --delay 1.5 --export csv

# 3. Batch Scrape from URLs file and Proxies file
python main.py --cli --urls-file urls.txt --proxies-file proxies.txt --continuous --export csv

# 4. Scrape and ask a question directly using RAG
python main.py --cli --url "https://en.wikipedia.org/wiki/Web_scraping" --query "What are common techniques in web scraping?"
```

---

## 🛡️ Proxy Configuration & Supported Formats

ScrapeAI supports **HTTP, HTTPS, SOCKS4, and SOCKS5** proxies with automatic rotation:
- **Single Proxy / Gateway format**: `http://username:password@ip_or_host:port` or `socks5://127.0.0.1:9050`
- **Proxy Pool List**: Supply multiple proxies (one per line) via Web UI or `--proxies` / `--proxies-file`.
- **Live Proxy Testing**: Click **Test** in the Web UI or send `POST /api/proxy/test` to verify public IP and latency.
- **Environment Variable Fallback**: Set `SCRAPER_PROXY` or `SCRAPER_PROXIES` in your environment.

---

## 🔑 Hugging Face API Configuration

1. Visit [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) and generate a free **User Access Token** (Read permission).
2. Click **AI Models** or **Settings** in the web interface and paste your token.
3. Choose your preferred model (e.g. `Qwen/Qwen2.5-7B-Instruct` or `meta-llama/Llama-3.2-3B-Instruct`).
4. *Note: If you leave the token empty, the system will automatically run in local offline semantic mode without any errors.*

---

## 🚀 Deployment Guide (100% Free)

### Option 1: Deploy to Hugging Face Spaces (Recommended for AI Apps)
1. Go to [Hugging Face Spaces](https://huggingface.co/spaces) and click **Create new Space**.
2. Name your space (e.g. `scrape-ai`).
3. Select **Docker** $\rightarrow$ **Blank** template.
4. Push this repository to your Hugging Face Space:
   ```bash
   git remote add space https://huggingface.co/spaces/YOUR_USERNAME/scrape-ai.git
   git push space main
   ```
5. Hugging Face will automatically detect the `Dockerfile` and start the server on port `7860`.
6. Your app is live with a permanent URL like: `https://YOUR_USERNAME-scrape-ai.hf.space`!

### Option 2: Deploy to Render.com (Full-Stack Free Cloud)
1. Go to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** $\rightarrow$ **Web Service** $\rightarrow$ Select your GitHub repo: `Hari92004/Scraper`.
3. Set configurations:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.server:app --host 0.0.0.0 --port $PORT`
4. (Optional) Add Environment Variable: `HF_TOKEN` = `your_huggingface_token`.
5. Click **Create Web Service**! Render will provide your free live URL (e.g. `https://scrape-ai.onrender.com`).

### Option 3: Deploy to Railway / Koyeb
- Connect your GitHub repo to Railway or Koyeb, and it will automatically deploy using the included `Dockerfile` and `Procfile`.

---

## 🛡️ License
MIT License. Built for universal web scraping and conversational AI research.