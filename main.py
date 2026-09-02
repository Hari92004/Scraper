"""
Main Entry Point for ScrapeAI Platform
Run Web Dashboard or Terminal CLI Scraper.
"""

import sys
import argparse
import uvicorn
from backend.scraper import UniversalScraper
from backend.rag_engine import RAGEngine
from backend.storage import save_scrape_session, export_to_csv, export_to_markdown


import os

def start_server(host=None, port=None):
    host = host or os.environ.get("HOST", "0.0.0.0")
    port = port or int(os.environ.get("PORT", 8000))
    is_prod = os.environ.get("RENDER") or os.environ.get("SPACE_ID")
    print("=" * 60)
    print(">> Starting ScrapeAI Web Dashboard & RAG Engine")
    print(f">> Server running on: http://{host}:{port}")
    print(f">> API Docs:          http://{host}:{port}/docs")
    print("=" * 60)
    uvicorn.run("backend.server:app", host=host, port=port, reload=not bool(is_prod))


def run_cli_scrape(url: str, query: str = None, export_fmt: str = None):
    print(f"[*] Scraping target URL: {url} ...")
    scraper = UniversalScraper()
    data = scraper.scrape(url)

    print("\n" + "=" * 50)
    print(f"📌 Title: {data['metadata']['title']}")
    print(f"📝 Words Extracted: {data['stats']['word_count']}")
    print(f"📊 Tables Extracted: {data['stats']['table_count']}")
    print(f"🔗 Links Extracted: {data['stats']['link_count']}")
    print("=" * 50)

    # Save session
    saved_file = save_scrape_session(data)
    print(f"[+] Dataset saved locally: data/{saved_file}")

    if export_fmt == "csv":
        csv_path = export_to_csv(data)
        print(f"[+] CSV Export saved: {csv_path}")
    elif export_fmt in ["markdown", "md"]:
        md_path = export_to_markdown(data)
        print(f"[+] Markdown Report saved: {md_path}")

    # RAG Query if asked
    if query:
        print(f"\n[*] Initializing RAG Query: '{query}' ...")
        rag = RAGEngine()
        rag.build_index(data['article']['text'], metadata={"title": data['metadata']['title'], "url": url})
        res = rag.query(query)
        print("\n🤖 AI Answer:")
        print(res["answer"])
        if res.get("citations"):
            print("\n📚 Citations:")
            for c in res["citations"]:
                print(f" - [Chunk {c['chunk_id']}] (Score: {c['score']}): {c['snippet']}")


def main():
    parser = argparse.ArgumentParser(description="ScrapeAI - Universal Web Scraper & Hugging Face RAG Platform")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode without launching the web server")
    parser.add_argument("--url", type=str, help="Target URL to scrape in CLI mode")
    parser.add_argument("--query", type=str, help="Question to ask about the scraped webpage using RAG")
    parser.add_argument("--export", choices=["csv", "markdown", "json"], help="Export format in CLI mode")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address for web server")
    parser.add_argument("--port", type=int, default=8000, help="Port number for web server")

    args = parser.parse_args()

    if args.cli or args.url:
        if not args.url:
            print("[!] Error: --url is required when running in CLI mode.")
            sys.exit(1)
        run_cli_scrape(args.url, query=args.query, export_fmt=args.export)
    else:
        start_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
