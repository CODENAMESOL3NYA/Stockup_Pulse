"""
South African Live Retail Scraper
---------------------------------
Asynchronous scraper for public SA retail product listings (Makro, Shoprite, Checkers, Pick n Pay, Woolworths).
Extracts product_name, price_zar, retailer, and availability using JSON-LD and CSS selectors.
Features aggressive error handling for Cloudflare blocks (401, 403, 429).
Returns [] gracefully on blocking without crashing the system.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, List, Optional
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from stockup_pulse.core.db import upsert_scraped_product

logger = logging.getLogger(__name__)

USER_AGENT = (
    "StockUpPulseResearchBot/1.0 "
    "(sample product data collection; spaza-retail-research@stockup_pulse.co.za)"
)
TIMEOUT_SECONDS = 15.0
REQUEST_DELAY_SECONDS = 1.5

SEARCH_URLS = {
    "makro": "https://www.makro.co.za/search/?text={query}",
    "shoprite": "https://www.shoprite.co.za/search/all?text={query}",
    "checkers": "https://www.checkers.co.za/search/all?text={query}",
    "picknpay": "https://www.pnp.co.za/search/?text={query}",
    "woolworths": "https://www.woolworths.co.za/cat?Ntt={query}",
}

CSS_SELECTORS = {
    "product": [
        "[data-testid*='product']",
        ".product-item",
        ".product-card",
        ".product",
        "article",
    ],
    "name": [
        "[itemprop='name']",
        "[data-testid*='product-title']",
        ".product-title",
        ".product-name",
        "h2",
        "h3",
    ],
    "price": [
        "[itemprop='price']",
        "[data-testid*='price']",
        ".price",
        ".product-price",
        "[class*='price']",
    ],
    "image": [
        "img[itemprop='image']",
        "img[data-src]",
        "img[src]",
    ],
}

@dataclass
class ProductRecord:
    retailer: str
    query: str
    product_name: str
    price_zar: float | None
    currency: str
    product_url: str
    image_url: str
    sku_or_gtin: str
    availability: str
    source_type: str
    scraped_at_utc: str

    def to_dict(self) -> dict:
        return asdict(self)

def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()

def parse_price(value: Any) -> float | None:
    """Parse common South African price strings such as 'R 24,99' or 'R1,299.00'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        price = float(value)
        return round(price, 2) if math.isfinite(price) and price > 0 else None

    text = clean_text(value).replace("\u00a0", " ")
    if re.search(r"(?<!\w)-\s*\d", text):
        return None
    match = re.search(r"(?<!\w)(?:R\s*)?([0-9][0-9 ,.]*)", text, flags=re.I)
    if not match:
        return None

    number = match.group(1).strip().replace(" ", "")
    if "," in number and "." in number:
        number = number.replace(",", "")
    elif "," in number:
        tail = number.rsplit(",", 1)[-1]
        if len(tail) == 2:
            number = number.replace(".", "").replace(",", ".")
        else:
            number = number.replace(",", "")
    try:
        price = float(number)
        return round(price, 2) if math.isfinite(price) and price > 0 else None
    except ValueError:
        return None

def first_text(node, selectors: list[str]) -> str:
    for selector in selectors:
        found = node.select_one(selector)
        if found:
            value = found.get("content") or found.get_text(" ", strip=True)
            value = clean_text(value)
            if value:
                return value
    return ""

def first_image(node, base_url: str) -> str:
    for selector in CSS_SELECTORS["image"]:
        img = node.select_one(selector)
        if img:
            src = img.get("data-src") or img.get("src") or img.get("content")
            if src:
                return urljoin(base_url, src.strip())
    return ""

class LiveRetailScraper:
    """
    Asynchronous scraper utilizing httpx.AsyncClient to collect South African retail prices.
    Catches 401/403/429 (Cloudflare) gracefully and returns [] without crashing.
    """
    def __init__(self, timeout: float = TIMEOUT_SECONDS):
        self.timeout = timeout
        self.headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-ZA,en-GB;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    async def fetch_page(self, client: httpx.AsyncClient, url: str) -> tuple[BeautifulSoup | None, str]:
        try:
            response = await client.get(url, timeout=self.timeout, follow_redirects=True)
            
            # Aggressive error handling for Cloudflare / anti-bot status codes
            if response.status_code in (401, 403, 429):
                logger.warning(
                    "LiveRetailScraper: Access denied or rate limited (%d) by Cloudflare/retailer on %s. Failing gracefully.",
                    response.status_code,
                    url
                )
                return None, url

            if response.status_code >= 400:
                logger.warning(
                    "LiveRetailScraper: HTTP error %d on %s. Returning empty gracefully.",
                    response.status_code,
                    url
                )
                return None, url

            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                logger.warning("LiveRetailScraper: Non-HTML response from %s; skipping.", url)
                return None, url

            soup = BeautifulSoup(response.text, "html.parser")
            return soup, str(response.url)

        except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as exc:
            logger.warning("LiveRetailScraper: Connection failure for %s (%s). Graceful fallback active.", url, exc)
            return None, url
        except Exception as exc:
            logger.error("LiveRetailScraper: Unexpected fetch error for %s (%s). Returning empty.", url, exc)
            return None, url

    def parse_jsonld_products(self, soup: BeautifulSoup, retailer: str, query: str, page_url: str) -> list[ProductRecord]:
        results: list[ProductRecord] = []

        def walk(obj):
            if isinstance(obj, list):
                for item in obj:
                    walk(item)
            elif isinstance(obj, dict):
                typ = obj.get("@type", "")
                types = typ if isinstance(typ, list) else [typ]
                if any(t in {"Product", "ProductGroup"} for t in types):
                    name = clean_text(obj.get("name"))
                    if name:
                        offers = obj.get("offers", {})
                        if isinstance(offers, list):
                            offers = offers[0] if offers else {}
                        if not isinstance(offers, dict):
                            offers = {}
                        price = parse_price(offers.get("price") or offers.get("lowPrice"))
                        availability = clean_text(offers.get("availability", "")).rsplit("/", 1)[-1] or "InStock"
                        image = obj.get("image", "")
                        if isinstance(image, list):
                            image = image[0] if image else ""
                        results.append(ProductRecord(
                            retailer=retailer.capitalize(),
                            query=query,
                            product_name=name,
                            price_zar=price,
                            currency=clean_text(offers.get("priceCurrency") or "ZAR").upper(),
                            product_url=urljoin(page_url, clean_text(obj.get("url"))),
                            image_url=urljoin(page_url, clean_text(image)),
                            sku_or_gtin=clean_text(obj.get("sku") or obj.get("gtin13") or obj.get("gtin")),
                            availability=availability,
                            source_type="json-ld",
                            scraped_at_utc=datetime.now(timezone.utc).isoformat(),
                        ))
                for key, value in obj.items():
                    if key != "offers" and isinstance(value, (dict, list)):
                        walk(value)

        for script in soup.select("script[type='application/ld+json']"):
            raw = script.string or script.get_text()
            if not raw:
                continue
            try:
                walk(json.loads(raw))
            except (json.JSONDecodeError, TypeError):
                continue

        unique = {}
        for row in results:
            if row.price_zar is not None:
                key = (row.product_url, row.product_name, row.price_zar)
                unique[key] = row
        return list(unique.values())

    def parse_html_products(self, soup: BeautifulSoup, retailer: str, query: str, page_url: str) -> list[ProductRecord]:
        results: list[ProductRecord] = []
        seen = set()

        for selector in CSS_SELECTORS["product"]:
            nodes = soup.select(selector)
            for node in nodes:
                name = first_text(node, CSS_SELECTORS["name"])
                price_text = first_text(node, CSS_SELECTORS["price"])
                price = parse_price(price_text)
                if not name or price is None:
                    continue

                link = node.select_one("a[href]")
                product_url = urljoin(page_url, link.get("href", "")) if link else ""
                image_url = first_image(node, page_url)
                key = (name.casefold(), price, product_url)
                if key in seen:
                    continue
                seen.add(key)

                sku = clean_text(
                    node.get("data-sku") or node.get("data-product-id") or node.get("data-id")
                )
                availability = clean_text(
                    node.get("data-availability")
                    or first_text(node, ["[itemprop='availability']", ".availability", "[class*='stock']"])
                ) or "InStock"

                results.append(ProductRecord(
                    retailer=retailer.capitalize(),
                    query=query,
                    product_name=name,
                    price_zar=price,
                    currency="ZAR",
                    product_url=product_url,
                    image_url=image_url,
                    sku_or_gtin=sku,
                    availability=availability,
                    source_type="html-selector",
                    scraped_at_utc=datetime.now(timezone.utc).isoformat(),
                ))
            if results:
                break

        return results

    async def scrape_retailer(
        self,
        client: httpx.AsyncClient,
        retailer: str,
        query: str,
        max_pages: int = 1
    ) -> list[ProductRecord]:
        template = SEARCH_URLS.get(retailer.lower())
        if not template:
            logger.warning("LiveRetailScraper: No configured search URL for retailer '%s'; skipping.", retailer)
            return []

        encoded_query = quote_plus(query)
        records: list[ProductRecord] = []
        seen_urls = set()

        for page_num in range(1, max_pages + 1):
            url = template.format(query=encoded_query, page=page_num)
            if url in seen_urls:
                break
            seen_urls.add(url)

            soup, final_url = await self.fetch_page(client, url)
            if soup is None:
                # Graceful exit on block / error
                break

            page_records = self.parse_jsonld_products(soup, retailer, query, final_url)
            if not page_records:
                page_records = self.parse_html_products(soup, retailer, query, final_url)

            records.extend(page_records)
            if "{page}" not in template or not page_records:
                break
            await asyncio.sleep(REQUEST_DELAY_SECONDS)

        # Deduplicate
        unique = {}
        for row in records:
            print(row)
            key = (row.product_url, row.product_name, row.price_zar)
            unique[key] = row
        return list(unique.values())

    async def scrape_staples_and_sync(
        self,
        queries: Optional[list[str]] = None,
        retailers: Optional[list[str]] = None
    ) -> list[ProductRecord]:
        """
        Scrapes a predefined list of staple queries across SA retailers and upserts
        results into the live_market_prices SQLite database.
        """
        target_queries = queries or ["maize meal", "cooking oil", "sugar", "rice", "soft drink", "brown bread"]
        target_retailers = retailers or ["shoprite", "checkers", "makro", "picknpay"]

        all_records: list[ProductRecord] = []

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            for query in target_queries:
                for retailer in target_retailers:
                    try:
                        records = await self.scrape_retailer(client, retailer, query, max_pages=1)
                        for r in records:
                            upsert_scraped_product(r.to_dict())
                        all_records.extend(records)
                    except Exception as e:
                        logger.warning(
                            "LiveRetailScraper: Error scraping %s for '%s': %s (continuing gracefully)",
                            retailer, query, e
                        )
                    await asyncio.sleep(0.5)

        return all_records

live_retail_scraper = LiveRetailScraper()
