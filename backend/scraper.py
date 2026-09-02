"""
Universal Web Scraper Engine
Extracts clean content, metadata, tables, links, images, and custom selectors from any URL.
"""

import re
import urllib.parse
from typing import Dict, Any, List, Optional
import requests
from bs4 import BeautifulSoup
import trafilatura

# Realistic headers to prevent blocking
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}


class UniversalScraper:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch_html(self, url: str) -> str:
        """Fetch raw HTML from target URL with proper redirect & error handling."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
        response.raise_for_status()
        
        # Ensure encoding is properly detected
        if response.encoding is None or response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding or 'utf-8'
            
        return response.text, str(response.url)

    def extract_metadata(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Extract title, description, keywords, author, canonical URL, and OpenGraph tags."""
        meta = {
            "title": "",
            "description": "",
            "author": "",
            "site_name": "",
            "canonical_url": base_url,
            "language": soup.html.get("lang", "en") if soup.html else "en",
            "favicon": ""
        }

        # Title
        if soup.title and soup.title.string:
            meta["title"] = soup.title.string.strip()
        elif soup.find("meta", property="og:title"):
            meta["title"] = soup.find("meta", property="og:title").get("content", "").strip()

        # Description
        desc_el = soup.find("meta", attrs={"name": re.compile(r"description", re.I)}) or \
                  soup.find("meta", property="og:description")
        if desc_el and desc_el.get("content"):
            meta["description"] = desc_el["content"].strip()

        # Author / Site Name
        site_el = soup.find("meta", property="og:site_name")
        if site_el and site_el.get("content"):
            meta["site_name"] = site_el["content"].strip()
            
        author_el = soup.find("meta", attrs={"name": re.compile(r"author", re.I)})
        if author_el and author_el.get("content"):
            meta["author"] = author_el["content"].strip()

        # Favicon
        icon_el = soup.find("link", rel=re.compile(r"icon", re.I))
        if icon_el and icon_el.get("href"):
            meta["favicon"] = urllib.parse.urljoin(base_url, icon_el["href"])
        else:
            meta["favicon"] = urllib.parse.urljoin(base_url, "/favicon.ico")

        return meta

    def extract_clean_article(self, html: str, url: str) -> Dict[str, Any]:
        """Extract clean main content text and markdown using Trafilatura."""
        downloaded = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            include_images=True,
            include_links=True,
            output_format="json",
            with_metadata=True
        )

        if downloaded:
            import json
            data = json.loads(downloaded)
            return {
                "text": data.get("text", "") or "",
                "title": data.get("title", "") or "",
                "author": data.get("author", "") or "",
                "date": data.get("date", "") or "",
                "raw_text": data.get("raw_text", "") or data.get("text", "")
            }

        # Fallback to BeautifulSoup basic text extraction if trafilatura produces empty result
        return self._soup_fallback_text(html)

    def _soup_fallback_text(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "noscript", "svg", "header"]):
            tag.decompose()

        main_el = soup.find("main") or soup.find("article") or soup.find("body") or soup
        text = main_el.get_text(separator="\n", strip=True)
        return {
            "text": text,
            "title": soup.title.string.strip() if soup.title else "",
            "author": "",
            "date": "",
            "raw_text": text
        }

    def extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract H1, H2, H3 tags in outline order."""
        headings = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
            text = tag.get_text(strip=True)
            if text:
                headings.append({
                    "level": tag.name.upper(),
                    "text": text
                })
        return headings

    def extract_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract HTML tables into structured rows and column headers."""
        tables_data = []
        for idx, table in enumerate(soup.find_all("table")):
            headers = []
            rows = []
            
            # Extract header row
            thead = table.find("thead")
            if thead:
                for th in thead.find_all(["th", "td"]):
                    headers.append(th.get_text(strip=True))
            
            # If no thead, check first tr
            first_tr = table.find("tr")
            if not headers and first_tr:
                th_cells = first_tr.find_all(["th", "td"])
                if any(c.name == 'th' for c in th_cells) or len(first_tr.find_all("th")) > 0:
                    headers = [c.get_text(strip=True) for c in th_cells]

            # Extract data rows
            tbody = table.find("tbody") or table
            for tr in tbody.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                row_vals = [c.get_text(strip=True) for c in cells]
                # Skip if row matches headers exactly
                if row_vals and row_vals != headers:
                    rows.append(row_vals)

            if rows or headers:
                # Ensure headers exist
                if not headers and rows:
                    max_cols = max(len(r) for r in rows)
                    headers = [f"Col {i+1}" for i in range(max_cols)]
                
                tables_data.append({
                    "table_index": idx + 1,
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                    "col_count": len(headers)
                })

        return tables_data

    def extract_links(self, soup: BeautifulSoup, base_url: str, limit: int = 100) -> List[Dict[str, str]]:
        """Extract internal and external links."""
        links = []
        seen = set()
        base_domain = urllib.parse.urlparse(base_url).netloc

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(strip=True) or a.get("title", "") or "[No Anchor Text]"
            
            # Resolve relative URLs
            full_url = urllib.parse.urljoin(base_url, href)
            parsed = urllib.parse.urlparse(full_url)
            
            if parsed.scheme in ["http", "https"] and full_url not in seen:
                seen.add(full_url)
                is_internal = (parsed.netloc == base_domain)
                links.append({
                    "text": text[:100],
                    "url": full_url,
                    "type": "Internal" if is_internal else "External"
                })
                if len(links) >= limit:
                    break

        return links

    def extract_images(self, soup: BeautifulSoup, base_url: str, limit: int = 50) -> List[Dict[str, str]]:
        """Extract image sources, alt text, and dimensions."""
        images = []
        seen = set()

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("srcset", "").split()[0]
            if not src:
                continue

            full_src = urllib.parse.urljoin(base_url, src.strip())
            if full_src.startswith(("http://", "https://")) and full_src not in seen:
                seen.add(full_src)
                images.append({
                    "src": full_src,
                    "alt": img.get("alt", "").strip() or "Image",
                    "width": img.get("width", ""),
                    "height": img.get("height", "")
                })
                if len(images) >= limit:
                    break

        return images

    def extract_custom_selector(self, soup: BeautifulSoup, selector: str) -> List[Dict[str, Any]]:
        """Extract elements matching a custom CSS selector."""
        results = []
        try:
            elements = soup.select(selector)
            for idx, el in enumerate(elements[:100]):
                results.append({
                    "index": idx + 1,
                    "tag": el.name,
                    "text": el.get_text(strip=True),
                    "html": str(el)[:500],
                    "attributes": dict(el.attrs)
                })
        except Exception as e:
            results.append({"error": f"Invalid CSS selector: {str(e)}"})
        return results

    def scrape(self, url: str, custom_selector: Optional[str] = None) -> Dict[str, Any]:
        """Perform comprehensive scraping for the given URL."""
        html, final_url = self.fetch_html(url)
        soup = BeautifulSoup(html, "lxml")

        metadata = self.extract_metadata(soup, final_url)
        article = self.extract_clean_article(html, final_url)
        headings = self.extract_headings(soup)
        tables = self.extract_tables(soup)
        links = self.extract_links(soup, final_url)
        images = self.extract_images(soup, final_url)

        custom_data = []
        if custom_selector and custom_selector.strip():
            custom_data = self.extract_custom_selector(soup, custom_selector.strip())

        # Ensure we have good article text
        main_text = article.get("text") or metadata.get("description") or ""
        if len(main_text) < 100:
            fallback = self._soup_fallback_text(html)
            main_text = fallback.get("text", "")

        # Word & Char counts
        words = len(main_text.split())
        chars = len(main_text)

        return {
            "url": final_url,
            "metadata": metadata,
            "article": {
                "title": article.get("title") or metadata.get("title"),
                "text": main_text,
                "author": article.get("author") or metadata.get("author"),
                "date": article.get("date", "")
            },
            "stats": {
                "word_count": words,
                "character_count": chars,
                "table_count": len(tables),
                "link_count": len(links),
                "image_count": len(images),
                "heading_count": len(headings)
            },
            "headings": headings,
            "tables": tables,
            "links": links,
            "images": images,
            "custom_data": custom_data,
            "success": True
        }


if __name__ == "__main__":
    scraper = UniversalScraper()
    test_url = "https://en.wikipedia.org/wiki/Web_scraping"
    print(f"Testing scraper on {test_url}...")
    res = scraper.scrape(test_url)
    print(f"Title: {res['metadata']['title']}")
    print(f"Words extracted: {res['stats']['word_count']}")
    print(f"Tables extracted: {res['stats']['table_count']}")
