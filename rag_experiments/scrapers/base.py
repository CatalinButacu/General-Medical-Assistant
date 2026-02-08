"""
Base scraper class for pharmacy websites.
"""
import asyncio
import aiohttp
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ScrapedMedicine:
    """
    Medicine data scraped from pharmacy websites.
    """
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
        """Convert to document format for storage."""
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
    """
    Abstract base class for pharmacy scrapers.
    Provides common functionality for scraping product information.
    """
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
        """Fetch HTML content from a URL."""
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
        """Get list of category URLs to scrape."""
        pass

    @abstractmethod
    async def get_product_urls(self, category_url: str) -> List[str]:
        """Get product URLs from a category page."""
        pass

    @abstractmethod
    async def parse_product(self, url: str) -> Optional[ScrapedMedicine]:
        """Parse a product page and return medicine data."""
        pass

    async def scrape(self) -> List[ScrapedMedicine]:
        """Run the scraper and collect medicines."""
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
