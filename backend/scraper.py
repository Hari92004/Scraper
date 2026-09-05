"""
Universal Web Scraper Engine with Continuous Multi-Website Scraping & Proxy Rotation
Extracts clean content, metadata, tables, links, images, and custom selectors from any URL.
"""

import os
import re
import time
import random
import gzip
import zlib
import urllib.parse
from typing import Dict, Any, List, Optional, Union, Generator, Callable, Tuple
import requests
from bs4 import BeautifulSoup
import trafilatura

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def get_random_headers() -> Dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    }


def normalize_proxy_url(proxy: str) -> str:
    """Ensure proxy URL has a valid protocol prefix (http, https, socks4, socks5)."""
    proxy = proxy.strip()
    if not proxy:
        return ""
    if not re.match(r"^(https?|socks4|socks5|socks5h)://", proxy, re.IGNORECASE):
        # Default to http:// if no protocol is given
        proxy = f"http://{proxy}"
    return proxy


def format_proxies(proxy: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Format single proxy string into requests dict."""
    if not proxy:
        return None
    normalized = normalize_proxy_url(proxy)
    if not normalized:
        return None
    return {
        "http": normalized,
        "https": normalized
    }


def mask_proxy(proxy_url: Optional[str]) -> Optional[str]:
    """Mask credentials in proxy URL for safe display and logging."""
    if not proxy_url:
        return None
    try:
        parsed = urllib.parse.urlsplit(proxy_url)
        if parsed.username or parsed.password:
            hostname = parsed.hostname or ""
            port = f":{parsed.port}" if parsed.port else ""
            return f"{parsed.scheme}://***:***@{hostname}{port}"
        return proxy_url
    except Exception:
        return "***"


class ProxyPool:
    """
    Manages a pool of proxies with automatic rotation, health tracking, and failover.
    Supports HTTP, HTTPS, SOCKS4, and SOCKS5 proxies.
    """
    def __init__(self, proxies: Optional[Union[List[str], str]] = None, strategy: str = "round-robin"):
        self.strategy = strategy.lower()  # 'round-robin' or 'random'
        self.proxies: List[str] = []
        self.stats: Dict[str, Dict[str, Any]] = {}
        self.current_idx = 0
        
        if proxies:
            self.add_proxies(proxies)
        else:
            # Fall back to env variables
            env_proxies = os.getenv("SCRAPER_PROXIES") or os.getenv("SCRAPER_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
            if env_proxies:
                self.add_proxies(env_proxies)

    def add_proxies(self, proxies_input: Union[List[str], str]):
        """Add proxies from list, comma-separated string, or multiline text."""
        raw_list = []
        if isinstance(proxies_input, str):
            for line in re.split(r'[\r\n,;]+', proxies_input):
                cleaned = line.strip()
                if cleaned and not cleaned.startswith('#'):
                    raw_list.append(cleaned)
        elif isinstance(proxies_input, (list, tuple, set)):
            for p in proxies_input:
                if isinstance(p, str) and p.strip():
                    raw_list.append(p.strip())

        for raw in raw_list:
            norm = normalize_proxy_url(raw)
            if norm and norm not in self.proxies:
                self.proxies.append(norm)
                self.stats[norm] = {
                    "raw": raw,
                    "masked": mask_proxy(norm),
                    "success_count": 0,
                    "fail_count": 0,
                    "consecutive_fails": 0,
                    "last_used": None,
                    "is_active": True
                }

    def has_proxies(self) -> bool:
        return len(self.proxies) > 0

    def get_proxy(self) -> Optional[str]:
        """Get the next proxy based on configured strategy."""
        if not self.proxies:
            return None

        active = [p for p in self.proxies if self.stats[p]["is_active"]]
        if not active:
            # Revive all proxies if pool exhausted
            for p in self.proxies:
                self.stats[p]["is_active"] = True
                self.stats[p]["consecutive_fails"] = 0
            active = self.proxies

        if self.strategy == "random":
            selected = random.choice(active)
        else:
            selected = active[self.current_idx % len(active)]
            self.current_idx = (self.current_idx + 1) % len(active)

        self.stats[selected]["last_used"] = time.time()
        return selected

    def report_success(self, proxy: str):
        """Record a successful request through this proxy."""
        if proxy in self.stats:
            self.stats[proxy]["success_count"] += 1
            self.stats[proxy]["consecutive_fails"] = 0
            self.stats[proxy]["is_active"] = True

    def report_failure(self, proxy: str, max_consecutive_fails: int = 3):
        """Record a failed request and temporarily disable if too many fails."""
        if proxy in self.stats:
            self.stats[proxy]["fail_count"] += 1
            self.stats[proxy]["consecutive_fails"] += 1
            if self.stats[proxy]["consecutive_fails"] >= max_consecutive_fails:
                self.stats[proxy]["is_active"] = False

    def get_status_summary(self) -> List[Dict[str, Any]]:
        """Return status information for all proxies in the pool."""
        return [
            {
                "proxy": self.stats[p]["masked"],
                "is_active": self.stats[p]["is_active"],
                "successes": self.stats[p]["success_count"],
                "failures": self.stats[p]["fail_count"],
                "consecutive_fails": self.stats[p]["consecutive_fails"]
            }
            for p in self.proxies
        ]


class UniversalScraper:
    def __init__(self, timeout: int = 15, default_proxy: Optional[str] = None):
        self.timeout = timeout
        self.default_proxy = default_proxy
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        if self.default_proxy:
            proxies = format_proxies(self.default_proxy)
            if proxies:
                self.session.proxies.update(proxies)

    def fetch_html(self, url: str, proxy: Optional[str] = None) -> Tuple[str, str, Optional[str]]:
        """Fetch raw HTML from target URL with proper redirect, proxy, decompression & error handling."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        effective_proxies = format_proxies(proxy) if proxy else format_proxies(self.default_proxy)
        active_proxy_str = (proxy or self.default_proxy) if effective_proxies else None

        headers = get_random_headers()
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                proxies=effective_proxies,
                headers=headers
            )
            response.raise_for_status()
            content_bytes = response.content
            final_url = str(response.url)
            encoding = response.encoding
            apparent_encoding = response.apparent_encoding
        except requests.HTTPError as e:
            # Fallback to resilient fetcher if requests hits 429 (Too Many Requests) or 403 (Forbidden)
            if e.response is not None and e.response.status_code in (403, 429):
                html_traf = trafilatura.fetch_url(url)
                if html_traf:
                    return html_traf, url, mask_proxy(active_proxy_str)
            raise

        # Handle potential compressed raw content (gzip, deflate, brotli)
        if content_bytes.startswith(b'\x1f\x8b'):  # Gzip magic number
            try:
                content_bytes = gzip.decompress(content_bytes)
            except Exception:
                pass
        elif content_bytes.startswith((b'\x78\x9c', b'\x78\x01', b'\x78\xda')):  # Zlib deflate
            try:
                content_bytes = zlib.decompress(content_bytes)
            except Exception:
                pass
        else:
            try:
                import brotli
                content_bytes = brotli.decompress(content_bytes)
            except Exception:
                pass

        # Determine best encoding
        if not encoding or encoding.lower() in ('iso-8859-1', 'windows-1252'):
            encoding = apparent_encoding or 'utf-8'

        try:
            html_text = content_bytes.decode(encoding, errors='replace')
        except Exception:
            html_text = content_bytes.decode('utf-8', errors='replace')
            
        return html_text, final_url, mask_proxy(active_proxy_str)

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

        if soup.title and soup.title.string:
            meta["title"] = soup.title.string.strip()
        elif soup.find("meta", property="og:title"):
            meta["title"] = soup.find("meta", property="og:title").get("content", "").strip()

        desc_el = soup.find("meta", attrs={"name": re.compile(r"description", re.I)}) or \
                  soup.find("meta", property="og:description")
        if desc_el and desc_el.get("content"):
            meta["description"] = desc_el["content"].strip()

        site_el = soup.find("meta", property="og:site_name")
        if site_el and site_el.get("content"):
            meta["site_name"] = site_el["content"].strip()
            
        author_el = soup.find("meta", attrs={"name": re.compile(r"author", re.I)})
        if author_el and author_el.get("content"):
            meta["author"] = author_el["content"].strip()

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
            
            thead = table.find("thead")
            if thead:
                for th in thead.find_all(["th", "td"]):
                    headers.append(th.get_text(strip=True))
            
            first_tr = table.find("tr")
            if not headers and first_tr:
                th_cells = first_tr.find_all(["th", "td"])
                if any(c.name == 'th' for c in th_cells) or len(first_tr.find_all("th")) > 0:
                    headers = [c.get_text(strip=True) for c in th_cells]

            tbody = table.find("tbody") or table
            for tr in tbody.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                row_vals = [c.get_text(strip=True) for c in cells]
                if row_vals and row_vals != headers:
                    rows.append(row_vals)

            if rows or headers:
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

    def scrape(
        self,
        url: str,
        custom_selector: Optional[str] = None,
        proxy: Optional[str] = None,
        proxy_pool: Optional[ProxyPool] = None,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Perform comprehensive scraping for the given URL with automatic proxy failover and retries.
        """
        last_error = None
        attempts = 0
        total_attempts = max_retries + 1 if (proxy or (proxy_pool and proxy_pool.has_proxies())) else 1

        while attempts < total_attempts:
            attempts += 1
            current_proxy = proxy
            if not current_proxy and proxy_pool and proxy_pool.has_proxies():
                current_proxy = proxy_pool.get_proxy()

            try:
                html, final_url, used_proxy = self.fetch_html(url, proxy=current_proxy)
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

                main_text = article.get("text") or metadata.get("description") or ""
                if len(main_text) < 100:
                    fallback = self._soup_fallback_text(html)
                    main_text = fallback.get("text", "")

                words = len(main_text.split())
                chars = len(main_text)

                if current_proxy and proxy_pool:
                    proxy_pool.report_success(current_proxy)

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
                    "proxy": used_proxy,
                    "headings": headings,
                    "tables": tables,
                    "links": links,
                    "images": images,
                    "custom_data": custom_data,
                    "success": True,
                    "attempts": attempts
                }

            except Exception as e:
                last_error = e
                if current_proxy and proxy_pool:
                    proxy_pool.report_failure(current_proxy)
                if attempts < total_attempts:
                    time.sleep(0.5)
                    continue
                else:
                    break

        raise last_error or Exception(f"Failed to scrape {url}")

    def scrape_batch_stream(
        self,
        urls: List[str],
        custom_selector: Optional[str] = None,
        proxies: Optional[Union[List[str], str]] = None,
        proxy_rotation: str = "round-robin",
        delay: float = 1.0,
        max_retries: int = 2
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream scraped results URL by URL continuously across multiple websites with rotating proxies.
        Yields a dict per URL with status, metrics, and data.
        """
        pool = ProxyPool(proxies=proxies, strategy=proxy_rotation) if proxies else None
        total = len(urls)

        for idx, url in enumerate(urls):
            start_t = time.time()
            clean_url = url.strip()
            if not clean_url:
                continue

            item_result = {
                "index": idx + 1,
                "total": total,
                "url": clean_url,
                "status": "pending",
                "duration": 0.0,
                "data": None,
                "proxy": None,
                "error": None
            }

            try:
                data = self.scrape(
                    clean_url,
                    custom_selector=custom_selector,
                    proxy_pool=pool,
                    max_retries=max_retries
                )
                duration = round(time.time() - start_t, 2)
                item_result.update({
                    "status": "success",
                    "duration": duration,
                    "data": data,
                    "proxy": data.get("proxy")
                })
            except Exception as e:
                duration = round(time.time() - start_t, 2)
                item_result.update({
                    "status": "failed",
                    "duration": duration,
                    "error": str(e),
                    "proxy": mask_proxy(pool.get_proxy()) if pool and pool.has_proxies() else None
                })

            yield item_result

            if idx < total - 1 and delay > 0:
                time.sleep(delay)

    def scrape_batch(
        self,
        urls: List[str],
        custom_selector: Optional[str] = None,
        proxies: Optional[Union[List[str], str]] = None,
        proxy_rotation: str = "round-robin",
        delay: float = 1.0,
        max_retries: int = 2,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Batch scrape multiple websites continuously with proxy rotation.
        Returns complete aggregated batch results.
        """
        results = []
        success_count = 0
        fail_count = 0
        total_words = 0
        total_tables = 0
        total_links = 0
        total_images = 0
        combined_texts = []

        pool = ProxyPool(proxies=proxies, strategy=proxy_rotation) if proxies else None

        for item in self.scrape_batch_stream(
            urls=urls,
            custom_selector=custom_selector,
            proxies=proxies,
            proxy_rotation=proxy_rotation,
            delay=delay,
            max_retries=max_retries
        ):
            results.append(item)
            if on_progress:
                on_progress(item)

            if item["status"] == "success" and item["data"]:
                success_count += 1
                stats = item["data"].get("stats", {})
                total_words += stats.get("word_count", 0)
                total_tables += stats.get("table_count", 0)
                total_links += stats.get("link_count", 0)
                total_images += stats.get("image_count", 0)
                
                article = item["data"].get("article", {})
                title = article.get("title") or item["url"]
                text = article.get("text", "")
                if text:
                    combined_texts.append(f"--- SOURCE: {title} ({item['url']}) ---\n{text}\n")
            else:
                fail_count += 1

        return {
            "total_urls": len(urls),
            "success_count": success_count,
            "fail_count": fail_count,
            "stats": {
                "total_words": total_words,
                "total_tables": total_tables,
                "total_links": total_links,
                "total_images": total_images
            },
            "proxy_pool_status": pool.get_status_summary() if pool else [],
            "combined_text": "\n".join(combined_texts),
            "results": results
        }


if __name__ == "__main__":
    scraper = UniversalScraper()
    test_urls = [
        "https://en.wikipedia.org/wiki/Web_scraping",
        "https://news.ycombinator.com",
    ]
    print(f"Testing batch scraper on {len(test_urls)} websites...")
    res = scraper.scrape_batch(test_urls, delay=0.5)
    print(f"Batch completed: {res['success_count']} successes, {res['fail_count']} failures")
    print(f"Total words: {res['stats']['total_words']}")
