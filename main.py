"""
Main Entry Point for ScrapeAI Platform
Run Web Dashboard or Terminal CLI Multi-Website Scraper with Proxy Rotation.
"""

import sys
import os
import argparse
import uvicorn
from backend.scraper import UniversalScraper, ProxyPool, mask_proxy
from backend.rag_engine import RAGEngine
from backend.storage import (
    save_scrape_session,
    save_batch_session,
    export_to_csv,
    export_to_markdown,
    export_batch_to_csv
)


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


def run_cli_scrape(
    urls: list,
    query: str = None,
    export_fmt: str = None,
    proxy: str = None,
    proxies: list = None,
    delay: float = 1.0,
    continuous: bool = False
):
    scraper = UniversalScraper()
    active_proxies = proxies or ([proxy] if proxy else None)

    if len(urls) == 1 and not continuous:
        target_url = urls[0]
        print(f"[*] Scraping target URL: {target_url} ...")
        if active_proxies:
            print(f"[*] Routing via proxy: {mask_proxy(active_proxies[0])}")
        
        data = scraper.scrape(target_url, proxy=active_proxies[0] if active_proxies else None)

        print("\n" + "=" * 50)
        print(f"📌 Title: {data['metadata']['title']}")
        print(f"📝 Words Extracted: {data['stats']['word_count']}")
        print(f"📊 Tables Extracted: {data['stats']['table_count']}")
        print(f"🔗 Links Extracted: {data['stats']['link_count']}")
        if data.get("proxy"):
            print(f"🛡️  Proxy Used: {data['proxy']}")
        print("=" * 50)

        saved_file = save_scrape_session(data)
        print(f"[+] Dataset saved locally: data/{saved_file}")

        if export_fmt == "csv":
            csv_path = export_to_csv(data)
            print(f"[+] CSV Export saved: {csv_path}")
        elif export_fmt in ["markdown", "md"]:
            md_path = export_to_markdown(data)
            print(f"[+] Markdown Report saved: {md_path}")

        if query:
            print(f"\n[*] Initializing RAG Query: '{query}' ...")
            rag = RAGEngine()
            rag.build_index(data['article']['text'], metadata={"title": data['metadata']['title'], "url": target_url})
            res = rag.query(query)
            print("\n🤖 AI Answer:")
            print(res["answer"])

    else:
        # Multi-Website Batch / Continuous Mode
        print(f"\n🚀 Starting Continuous Multi-Website Scraper on {len(urls)} URLs...")
        if active_proxies:
            print(f"🛡️  Rotating through {len(active_proxies)} proxies with {delay}s delay between requests.")
        
        def on_item_scraped(item):
            status_icon = "✅" if item["status"] == "success" else "❌"
            proxy_tag = f"[Proxy: {item['proxy']}]" if item.get("proxy") else "[Direct]"
            print(f"{status_icon} [{item['index']}/{item['total']}] {item['url']} {proxy_tag} ({item['duration']}s)")
            if item["status"] == "failed":
                print(f"   └─ Error: {item['error']}")

        batch_data = scraper.scrape_batch(
            urls=urls,
            proxies=active_proxies,
            delay=delay,
            on_progress=on_item_scraped
        )

        print("\n" + "=" * 50)
        print(f"🏁 Batch Summary: {batch_data['success_count']} Successful, {batch_data['fail_count']} Failed")
        print(f"📝 Total Words: {batch_data['stats']['total_words']}")
        print(f"📊 Total Tables: {batch_data['stats']['total_tables']}")
        print(f"🔗 Total Links: {batch_data['stats']['total_links']}")
        print("=" * 50)

        saved_file = save_batch_session(batch_data)
        print(f"[+] Batch Dataset saved locally: data/{saved_file}")

        if export_fmt == "csv":
            csv_path = export_batch_to_csv(batch_data)
            print(f"[+] Consolidated CSV Export saved: {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="ScrapeAI - Universal Multi-Website Web Scraper & Hugging Face RAG Platform")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode without launching the web server")
    parser.add_argument("--url", type=str, help="Single target URL or comma-separated URLs to scrape")
    parser.add_argument("--urls-file", type=str, help="Path to text file containing target URLs (one per line)")
    parser.add_argument("--proxy", type=str, help="Single Proxy URL (HTTP, HTTPS, or SOCKS5)")
    parser.add_argument("--proxies", type=str, help="Comma-separated list of proxies for rotation")
    parser.add_argument("--proxies-file", type=str, help="Path to text file containing proxies (one per line)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay in seconds between continuous requests (default: 1.0)")
    parser.add_argument("--continuous", action="store_true", help="Run in continuous multi-website batch mode")
    parser.add_argument("--query", type=str, help="Question to ask about the scraped webpage using RAG")
    parser.add_argument("--export", choices=["csv", "markdown", "json"], help="Export format in CLI mode")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address for web server")
    parser.add_argument("--port", type=int, default=8000, help="Port number for web server")

    args = parser.parse_args()

    # Collect URLs
    urls = []
    if args.url:
        urls.extend([u.strip() for u in args.url.split(",") if u.strip()])
    if args.urls_file and os.path.exists(args.urls_file):
        with open(args.urls_file, "r", encoding="utf-8") as f:
            urls.extend([line.strip() for line in f if line.strip() and not line.startswith("#")])

    # Collect Proxies
    proxies = []
    if args.proxy:
        proxies.append(args.proxy.strip())
    if args.proxies:
        proxies.extend([p.strip() for p in args.proxies.split(",") if p.strip()])
    if args.proxies_file and os.path.exists(args.proxies_file):
        with open(args.proxies_file, "r", encoding="utf-8") as f:
            proxies.extend([line.strip() for line in f if line.strip() and not line.startswith("#")])

    if args.cli or urls:
        if not urls:
            print("[!] Error: Provide at least one URL via --url or --urls-file when running in CLI mode.")
            sys.exit(1)
        run_cli_scrape(
            urls=urls,
            query=args.query,
            export_fmt=args.export,
            proxies=proxies,
            delay=args.delay,
            continuous=args.continuous or len(urls) > 1
        )
    else:
        start_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
