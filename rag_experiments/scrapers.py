import asyncio
import aiohttp
import json
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"


@dataclass
class ScrapedMedicine:
    name: str
    price: Optional[float] = None
    currency: str = "RON"
    active_substance: str = ""
    description: str = ""
    category: str = ""
    prescription_required: bool = False
    manufacturer: str = ""
    url: str = ""
    image_url: str = ""
    source: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_document(self) -> Dict[str, Any]:
        rx_note = "⚠️ **Requires prescription**" if self.prescription_required else "Available without prescription"

        content = f"""# {self.name}

## Overview
- **Active substance**: {self.active_substance or 'Not specified'}
- **Category**: {self.category}
- **Manufacturer**: {self.manufacturer or 'Not specified'}
- **Prescription**: {rx_note}

## Description
{self.description or 'No description available.'}

## Purchase Information
- **Price**: {self.price} {self.currency} (as of {self.scraped_at[:10]})
- **Buy online**: [{self.source}]({self.url})
"""
        return {
            "content": content,
            "title": f"{self.name} - {self.source}",
            "source": self.source,
            "metadata": {
                "price": self.price,
                "currency": self.currency,
                "category": self.category,
                "prescription_required": self.prescription_required,
                "url": self.url,
                "active_substance": self.active_substance
            }
        }


class PharmacyScraper(ABC):
    name: str = "base"
    base_url: str = ""

    def __init__(self, max_products: int = 100, delay: float = 0.5):
        self.max_products = max_products
        self.delay = delay
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8"
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch(self, url: str) -> Optional[str]:
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    return await response.text()
                logger.warning(f"HTTP {response.status} for {url}")
                return None
        except Exception as e:
            logger.error(f"Fetch error for {url}: {e}")
            return None

    @abstractmethod
    async def get_category_urls(self) -> List[str]:
        pass

    @abstractmethod
    async def get_product_urls(self, category_url: str) -> List[str]:
        pass

    @abstractmethod
    async def parse_product(self, url: str) -> Optional[ScrapedMedicine]:
        pass

    async def scrape(self) -> List[ScrapedMedicine]:
        medicines = []
        seen_urls: Set[str] = set()

        logger.info(f"Starting {self.name} scraper (max: {self.max_products})")

        category_urls = await self.get_category_urls()
        logger.info(f"Found {len(category_urls)} categories")

        for cat_url in category_urls:
            if len(medicines) >= self.max_products:
                break

            product_urls = await self.get_product_urls(cat_url)
            logger.info(f"Found {len(product_urls)} products in {cat_url}")

            for prod_url in product_urls:
                if len(medicines) >= self.max_products:
                    break

                if prod_url in seen_urls:
                    continue
                seen_urls.add(prod_url)

                await asyncio.sleep(self.delay)
                medicine = await self.parse_product(prod_url)

                if medicine:
                    medicines.append(medicine)
                    logger.info(f"Scraped: {medicine.name} ({len(medicines)}/{self.max_products})")

        logger.info(f"Completed {self.name}: {len(medicines)} medicines")
        return medicines


class FarmaciaTeiScraper(PharmacyScraper):
    name = "Farmacia Tei"
    base_url = "https://comenzi.farmaciatei.ro"

    CATEGORIES = [
        "/medicamente-otc/durere-febra/",
        "/medicamente-otc/afectiuni-digestive/",
        "/medicamente-otc/afectiuni-respiratorii/",
        "/medicamente-otc/afectiuni-circulatorii/",
        "/medicamente-otc/vitamine-minerale/",
        "/medicamente-otc/afectiuni-dermatologice/",
        "/medicamente-otc/afectiuni-oftalmologice/",
        "/medicamente-otc/afectiuni-urologice/",
        "/suplimente-alimentare/sistemul-imunitar/",
        "/suplimente-alimentare/sistemul-digestiv/",
    ]

    async def get_category_urls(self) -> List[str]:
        return [self.base_url + cat for cat in self.CATEGORIES]

    async def get_product_urls(self, category_url: str) -> List[str]:
        urls = []

        for page in range(1, 6):
            page_url = f"{category_url}?page={page}" if page > 1 else category_url
            html = await self.fetch(page_url)

            if not html:
                break

            soup = BeautifulSoup(html, 'html.parser')
            product_links = soup.select('a.product-name, a.product-link, .product-item a[href*="/p/"]')

            if not product_links:
                product_links = soup.select('a[href*="/p/"]')

            for link in product_links:
                href = link.get('href', '')
                if '/p/' in href or '/produs/' in href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)

            if len(urls) >= 20:
                break

        return urls[:20]

    async def parse_product(self, url: str) -> Optional[ScrapedMedicine]:
        html = await self.fetch(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        name = ""
        name_elem = soup.select_one('h1, .product-name, .product-title')
        if name_elem:
            name = name_elem.get_text(strip=True)

        if not name:
            return None

        price = None
        price_elem = soup.select_one('.product-price, .price, [class*="price"]')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_match = re.search(r'(\d+[.,]?\d*)', price_text.replace(',', '.'))
            if price_match:
                price = float(price_match.group(1))

        description = ""
        desc_elem = soup.select_one('.product-description, .description, [class*="description"]')
        if desc_elem:
            description = desc_elem.get_text(strip=True)[:500]

        active_substance = ""
        substance_elem = soup.find(text=re.compile(r'substan.*activ', re.I))
        if substance_elem:
            parent = substance_elem.find_parent()
            if parent:
                active_substance = parent.get_text(strip=True)

        prescription = False
        rx_indicators = soup.find_text(text=re.compile(r'rețetă|prescripție|rx', re.I)) if hasattr(soup, 'find_text') else None
        if soup.find(text=re.compile(r'rețetă|prescripție', re.I)):
            prescription = True

        category = ""
        breadcrumb = soup.select_one('.breadcrumb, nav[aria-label="breadcrumb"]')
        if breadcrumb:
            crumbs = breadcrumb.select('a, span')
            if len(crumbs) > 1:
                category = crumbs[-2].get_text(strip=True) if len(crumbs) >= 2 else ""

        return ScrapedMedicine(
            name=name,
            price=price,
            description=description,
            active_substance=active_substance,
            category=category,
            prescription_required=prescription,
            url=url,
            source=self.name
        )


class HelpNetScraper(PharmacyScraper):
    name = "HelpNet"
    base_url = "https://www.helpnet.ro"

    CATEGORIES = [
        "/medicamente-fara-reteta/",
        "/suplimente-alimentare/",
        "/ingrijire-personala/",
    ]

    async def get_category_urls(self) -> List[str]:
        return [self.base_url + cat for cat in self.CATEGORIES]

    async def get_product_urls(self, category_url: str) -> List[str]:
        urls = []
        html = await self.fetch(category_url)

        if not html:
            return urls

        soup = BeautifulSoup(html, 'html.parser')
        product_links = soup.select('a[href*="/produs/"], a.product-link, .product-item a')

        for link in product_links:
            href = link.get('href', '')
            if href and '/produs/' in href:
                full_url = urljoin(self.base_url, href)
                if full_url not in urls:
                    urls.append(full_url)

        return urls[:20]

    async def parse_product(self, url: str) -> Optional[ScrapedMedicine]:
        html = await self.fetch(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        name = ""
        name_elem = soup.select_one('h1, .product-name')
        if name_elem:
            name = name_elem.get_text(strip=True)

        if not name:
            return None

        price = None
        price_elem = soup.select_one('.price, [class*="price"]')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_match = re.search(r'(\d+[.,]?\d*)', price_text.replace(',', '.'))
            if price_match:
                price = float(price_match.group(1))

        description = ""
        desc_elem = soup.select_one('.description, .product-description')
        if desc_elem:
            description = desc_elem.get_text(strip=True)[:500]

        return ScrapedMedicine(
            name=name,
            price=price,
            description=description,
            url=url,
            source=self.name
        )


class EumedScraper(PharmacyScraper):
    name = "EUmed"
    base_url = "https://www.eumed.ro"

    CATEGORIES = [
        "/medicamente/",
        "/suplimente-alimentare/",
    ]

    async def get_category_urls(self) -> List[str]:
        return [self.base_url + cat for cat in self.CATEGORIES]

    async def get_product_urls(self, category_url: str) -> List[str]:
        urls = []
        html = await self.fetch(category_url)

        if not html:
            return urls

        soup = BeautifulSoup(html, 'html.parser')
        product_links = soup.select('a[href*="/produs/"], a.product-link')

        for link in product_links:
            href = link.get('href', '')
            if href:
                full_url = urljoin(self.base_url, href)
                if full_url not in urls:
                    urls.append(full_url)

        return urls[:20]

    async def parse_product(self, url: str) -> Optional[ScrapedMedicine]:
        html = await self.fetch(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        name = ""
        name_elem = soup.select_one('h1')
        if name_elem:
            name = name_elem.get_text(strip=True)

        if not name:
            return None

        price = None
        price_elem = soup.select_one('.price, [class*="price"]')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_match = re.search(r'(\d+[.,]?\d*)', price_text.replace(',', '.'))
            if price_match:
                price = float(price_match.group(1))

        return ScrapedMedicine(
            name=name,
            price=price,
            url=url,
            source=self.name
        )


SCRAPERS = {
    "farmaciatei": FarmaciaTeiScraper,
    "helpnet": HelpNetScraper,
    "eumed": EumedScraper,
}


async def scrape_all_pharmacies(
    max_per_pharmacy: int = 50,
    pharmacies: Optional[List[str]] = None
) -> List[ScrapedMedicine]:
    all_medicines = []
    pharmacy_names = pharmacies or list(SCRAPERS.keys())

    for name in pharmacy_names:
        if name not in SCRAPERS:
            logger.warning(f"Unknown pharmacy: {name}")
            continue

        scraper_class = SCRAPERS[name]
        async with scraper_class(max_products=max_per_pharmacy) as scraper:
            medicines = await scraper.scrape()
            all_medicines.extend(medicines)

    return all_medicines


def save_medicines(medicines: List[ScrapedMedicine], filename: str = "ro_medicines.json") -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_file = DATA_DIR / filename

    documents = [m.to_document() for m in medicines]

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(documents)} medicines to {output_file}")
    return output_file


async def build_pharmacy_knowledge_base(max_per_pharmacy: int = 50) -> Path:
    medicines = await scrape_all_pharmacies(max_per_pharmacy)
    return save_medicines(medicines)


if __name__ == "__main__":
    asyncio.run(build_pharmacy_knowledge_base(max_per_pharmacy=30))
