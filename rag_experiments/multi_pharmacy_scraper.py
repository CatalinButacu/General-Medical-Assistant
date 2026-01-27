"""
Romanian Pharmacy Multi-Store Scrapers
Extended scrapers for all major Romanian online pharmacies
"""

import asyncio
import aiohttp
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"


@dataclass
class MedicineProduct:
    name: str
    price: Optional[float] = None
    currency: str = "RON"
    active_substance: str = ""
    description: str = ""
    indications: str = ""
    contraindications: str = ""
    side_effects: str = ""
    dosage: str = ""
    category: str = ""
    prescription_required: bool = False
    manufacturer: str = ""
    url: str = ""
    store: str = ""


PHARMACY_CONFIGS = {
    "catena": {
        "name": "Catena",
        "base_url": "https://www.catena.ro",
        "categories": [
            "/durere-febra",
            "/tuse-raceala-gripa",
            "/digestie",
            "/alergii",
            "/vitamine-minerale",
        ],
        "selectors": {
            "product_list": ".product-item a",
            "name": "h1.product-title",
            "price": ".product-price .price",
            "description": ".product-description",
        }
    },
    "ropharma": {
        "name": "Ropharma",
        "base_url": "https://ropharma.ro",
        "categories": [
            "/medicamente",
            "/suplimente-alimentare",
        ],
        "selectors": {
            "product_list": ".product-item a",
            "name": "h1",
            "price": ".price",
            "description": ".description",
        }
    },
    "drmax": {
        "name": "Dr. Max",
        "base_url": "https://www.drmax.ro",
        "categories": [
            "/medicamente",
            "/vitamine-suplimente",
        ],
        "selectors": {
            "product_list": ".product-item a",
            "name": "h1",
            "price": ".price",
            "description": ".description",
        }
    },
    "bebetei": {
        "name": "Bebe Tei",
        "base_url": "https://comenzi.bebetei.ro",
        "categories": [
            "/medicamente-copii",
            "/vitamine-copii",
        ],
        "selectors": {
            "product_list": "a[href*='/p/']",
            "name": "h1",
            "price": ".product-price",
            "description": ".product-description",
        }
    },
    "pharma_nord": {
        "name": "Pharma Nord",
        "base_url": "https://www.pharmanord.ro",
        "categories": [
            "/produse",
        ],
        "selectors": {
            "product_list": ".product a",
            "name": "h1",
            "price": ".price",
            "description": ".description",
        }
    },
    "botaniq": {
        "name": "Botaniq",
        "base_url": "https://www.botaniq.ro",
        "categories": [
            "/suplimente",
            "/plante-medicinale",
        ],
        "selectors": {
            "product_list": ".product-item a",
            "name": "h1",
            "price": ".price",
            "description": ".description",
        }
    },
    "delpharma": {
        "name": "Delpharma",
        "base_url": "https://www.farmaciadelpharma.ro",
        "categories": [
            "/medicamente",
        ],
        "selectors": {
            "product_list": ".product a",
            "name": "h1",
            "price": ".price",
            "description": ".description",
        }
    },
    "daciaplant": {
        "name": "Dacia Plant",
        "base_url": "https://www.daciaplant.ro",
        "categories": [
            "/produse",
        ],
        "selectors": {
            "product_list": ".product-item a",
            "name": "h1",
            "price": ".price",
            "description": ".description",
        }
    },
    "napofarm": {
        "name": "Napofarm",
        "base_url": "https://www.farmaciilenapofarm.ro",
        "categories": [
            "/medicamente",
        ],
        "selectors": {
            "product_list": ".product a",
            "name": "h1",
            "price": ".price",
            "description": ".description",
        }
    },
    "eumed": {
        "name": "EUmed",
        "base_url": "https://www.eumed.ro",
        "categories": [
            "/medicamente",
            "/suplimente-alimentare",
        ],
        "selectors": {
            "product_list": ".product-item a",
            "name": "h1",
            "price": ".price",
            "description": ".description",
        }
    },
    "elmafarm": {
        "name": "Elmafarm",
        "base_url": "https://www.elmafarm.ro",
        "categories": [
            "/medicamente",
        ],
        "selectors": {
            "product_list": ".product a",
            "name": "h1",
            "price": ".price",
            "description": ".description",
        }
    },
}


class GenericPharmacyScraper:
    def __init__(self, config: dict, max_products: int = 20, delay: float = 1.0):
        self.config = config
        self.max_products = max_products
        self.delay = delay
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8"
        }

    @property
    def name(self) -> str:
        return self.config["name"]

    @property
    def base_url(self) -> str:
        return self.config["base_url"]

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def fetch(self, url: str) -> Optional[str]:
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    return await resp.text()
                logger.warning(f"HTTP {resp.status} for {url}")
        except Exception as e:
            logger.error(f"Fetch error {url}: {e}")
        return None

    async def scrape(self) -> List[MedicineProduct]:
        products = []
        seen = set()

        for cat_path in self.config["categories"]:
            if len(products) >= self.max_products:
                break

            cat_url = self.base_url + cat_path
            html = await self.fetch(cat_url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')
            selector = self.config["selectors"]["product_list"]

            for link in soup.select(selector)[:10]:
                if len(products) >= self.max_products:
                    break

                href = link.get('href', '')
                if not href:
                    continue

                product_url = urljoin(self.base_url, href)
                if product_url in seen:
                    continue
                seen.add(product_url)

                await asyncio.sleep(self.delay)
                product = await self.parse_product(product_url)
                if product:
                    products.append(product)
                    logger.info(f"[{self.name}] Scraped: {product.name}")

        return products

    async def parse_product(self, url: str) -> Optional[MedicineProduct]:
        html = await self.fetch(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        selectors = self.config["selectors"]

        name = self._extract_text(soup, selectors.get("name", "h1"))
        if not name:
            return None

        price = self._extract_price(soup, selectors.get("price", ".price"))
        description = self._extract_text(soup, selectors.get("description", ".description"))

        return MedicineProduct(
            name=name,
            price=price,
            description=description[:500] if description else "",
            url=url,
            store=self.name
        )

    def _extract_text(self, soup: BeautifulSoup, selector: str) -> str:
        elem = soup.select_one(selector)
        return elem.get_text(strip=True) if elem else ""

    def _extract_price(self, soup: BeautifulSoup, selector: str) -> Optional[float]:
        elem = soup.select_one(selector)
        if not elem:
            return None
        text = elem.get_text(strip=True).replace(',', '.')
        match = re.search(r'(\d+\.?\d*)', text)
        return float(match.group(1)) if match else None


async def scrape_pharmacy(pharmacy_id: str, max_products: int = 20) -> List[MedicineProduct]:
    if pharmacy_id not in PHARMACY_CONFIGS:
        logger.error(f"Unknown pharmacy: {pharmacy_id}")
        return []

    config = PHARMACY_CONFIGS[pharmacy_id]
    async with GenericPharmacyScraper(config, max_products) as scraper:
        return await scraper.scrape()


async def scrape_all_pharmacies(max_per_pharmacy: int = 10) -> List[MedicineProduct]:
    all_products = []

    for pharmacy_id in PHARMACY_CONFIGS:
        logger.info(f"Scraping {pharmacy_id}...")
        products = await scrape_pharmacy(pharmacy_id, max_per_pharmacy)
        all_products.extend(products)
        logger.info(f"Got {len(products)} from {pharmacy_id}")

    return all_products


def product_to_document(product: MedicineProduct) -> dict:
    return {
        "content": f"""# {product.name}

## Informații Produs
- **Magazin**: {product.store}
- **Preț**: {product.price} {product.currency}

## Descriere
{product.description or 'Descriere indisponibilă.'}

## Cumpărare
🛒 [Cumpără online]({product.url})
""",
        "title": f"{product.name} - {product.store}",
        "source": product.store,
        "metadata": {
            "price": product.price,
            "currency": product.currency,
            "url": product.url,
            "store": product.store
        }
    }


async def build_multi_pharmacy_database(max_per_pharmacy: int = 10) -> Path:
    products = await scrape_all_pharmacies(max_per_pharmacy)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_file = DATA_DIR / "multi_pharmacy.json"

    documents = [product_to_document(p) for p in products]
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(documents)} products to {output_file}")
    return output_file


if __name__ == "__main__":
    asyncio.run(build_multi_pharmacy_database(max_per_pharmacy=5))
