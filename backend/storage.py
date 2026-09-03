"""
Storage & Export Module
Saves scraped datasets, history, and exports to CSV, JSON, Markdown, and TXT.
"""

import os
import json
import csv
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")


def sanitize_filename(name: str) -> str:
    """Clean string to be safe as a filename."""
    name = re.sub(r'[\\/*?:"<>| ]', "_", name)
    return name[:50].strip("_") or "scrape_data"


def save_scrape_session(data: Dict[str, Any]) -> str:
    """Save full scrape result to a JSON file and append to history."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    title = data.get("metadata", {}).get("title", "page")
    safe_name = sanitize_filename(title)
    filename = f"{timestamp}_{safe_name}.json"
    filepath = os.path.join(DATA_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    append_to_history({
        "id": filename,
        "title": title,
        "url": data.get("url", ""),
        "timestamp": datetime.now().isoformat(),
        "word_count": data.get("stats", {}).get("word_count", 0),
        "tables_count": data.get("stats", {}).get("table_count", 0),
        "filepath": filepath
    })

    return filename


def save_batch_session(batch_data: Dict[str, Any]) -> str:
    """Save full batch scrape results to a JSON file and append to history."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    total = batch_data.get("total_urls", 0)
    filename = f"{timestamp}_batch_{total}_sites.json"
    filepath = os.path.join(DATA_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(batch_data, f, ensure_ascii=False, indent=2)

    append_to_history({
        "id": filename,
        "title": f"Batch Scrape ({batch_data.get('success_count', 0)}/{total} Sites)",
        "url": f"{total} target websites",
        "timestamp": datetime.now().isoformat(),
        "word_count": batch_data.get("stats", {}).get("total_words", 0),
        "tables_count": batch_data.get("stats", {}).get("total_tables", 0),
        "filepath": filepath
    })

    return filename


def append_to_history(entry: Dict[str, Any]):
    """Add item to history.json."""
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.insert(0, entry)
    history = history[:50]

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_history() -> List[Dict[str, Any]]:
    """Retrieve scraping history."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def export_to_csv(data: Dict[str, Any]) -> str:
    """Convert scraped tables or links to CSV."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = sanitize_filename(data.get("metadata", {}).get("title", "data"))
    filepath = os.path.join(DATA_DIR, f"{timestamp}_{safe_name}.csv")

    tables = data.get("tables", [])
    if tables:
        all_rows = []
        for t_idx, tbl in enumerate(tables):
            headers = tbl.get("headers", [])
            for row in tbl.get("rows", []):
                row_dict = {"Table": f"Table {t_idx+1}"}
                for h_idx, h in enumerate(headers):
                    val = row[h_idx] if h_idx < len(row) else ""
                    row_dict[h or f"Col_{h_idx+1}"] = val
                all_rows.append(row_dict)

        if all_rows:
            df = pd.DataFrame(all_rows)
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            return filepath

    links = data.get("links", [])
    if links:
        df = pd.DataFrame(links)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        return filepath

    meta = data.get("metadata", {})
    df = pd.DataFrame([meta])
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    return filepath


def export_batch_to_csv(batch_data: Dict[str, Any]) -> str:
    """Export consolidated multi-website data to CSV."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(DATA_DIR, f"{timestamp}_batch_export.csv")

    rows = []
    for item in batch_data.get("results", []):
        url = item.get("url", "")
        status = item.get("status", "")
        duration = item.get("duration", 0)
        proxy = item.get("proxy") or "Direct"
        data = item.get("data") or {}
        meta = data.get("metadata", {})
        article = data.get("article", {})
        stats = data.get("stats", {})

        rows.append({
            "Target_URL": url,
            "Status": status,
            "Duration_Seconds": duration,
            "Proxy_Used": proxy,
            "Title": meta.get("title") or article.get("title", ""),
            "Author": meta.get("author") or article.get("author", ""),
            "Words_Extracted": stats.get("word_count", 0),
            "Tables_Extracted": stats.get("table_count", 0),
            "Links_Extracted": stats.get("link_count", 0),
            "Images_Extracted": stats.get("image_count", 0),
            "Article_Excerpt": (article.get("text", "")[:300] + "...") if article.get("text") else "",
            "Error": item.get("error", "")
        })

    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    return filepath


def export_to_markdown(data: Dict[str, Any]) -> str:
    """Format full scrape data as a rich Markdown report."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    meta = data.get("metadata", {})
    safe_name = sanitize_filename(meta.get("title", "document"))
    filepath = os.path.join(DATA_DIR, f"{timestamp}_{safe_name}.md")

    md = []
    md.append(f"# {meta.get('title', 'Scraped Document')}\n")
    md.append(f"- **Source URL**: [{data.get('url', '')}]({data.get('url', '')})")
    md.append(f"- **Author**: {meta.get('author', 'Unknown')}")
    md.append(f"- **Scraped At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"- **Word Count**: {data.get('stats', {}).get('word_count', 0)}\n")

    if meta.get("description"):
        md.append(f"> {meta.get('description')}\n")

    md.append("## Article Content\n")
    md.append(data.get("article", {}).get("text", "") + "\n")

    tables = data.get("tables", [])
    if tables:
        md.append("## Extracted Tables\n")
        for idx, t in enumerate(tables):
            md.append(f"### Table {idx+1}\n")
            headers = t.get("headers", [])
            if headers:
                md.append("| " + " | ".join(headers) + " |")
                md.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for r in t.get("rows", []):
                md.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in r) + " |")
            md.append("\n")

    links = data.get("links", [])
    if links:
        md.append("## Extracted Links (First 30)\n")
        for l in links[:30]:
            md.append(f"- [{l.get('text', 'Link')}]({l.get('url', '')}) ({l.get('type', 'External')})")
        md.append("\n")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    return filepath
