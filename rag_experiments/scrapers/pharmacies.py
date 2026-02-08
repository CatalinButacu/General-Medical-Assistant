"""
Pharmacy scraper implementations for Romanian pharmacies.
"""
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import PharmacyScraper, ScrapedMedicine

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


class FarmaciaTeiScraper(PharmacyScraper):
    """Scraper for Farmacia Tei online pharmacy."""
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
    """Scraper for HelpNet online pharmacy."""
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
    """Scraper for EUmed online pharmacy."""
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


# Registry of available scrapers
SCRAPERS = {
    "farmaciatei": FarmaciaTeiScraper,
    "helpnet": HelpNetScraper,
    "eumed": EumedScraper,
}


async def scrape_all_pharmacies(
    max_per_pharmacy: int = 50,
    pharmacies: Optional[List[str]] = None
) -> List[ScrapedMedicine]:
    """
    Scrape medicines from multiple pharmacies.
    
    Args:
        max_per_pharmacy: Maximum products per pharmacy
        pharmacies: List of pharmacy keys to scrape (defaults to all)
        
    Returns:
        List of scraped medicines
    """
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
    """
    Save scraped medicines to a JSON file.
    
    Args:
        medicines: List of ScrapedMedicine objects
        filename: Output filename
        
    Returns:
        Path to the saved file
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_file = DATA_DIR / filename

    documents = [m.to_document() for m in medicines]

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(documents)} medicines to {output_file}")
    return output_file


async def build_pharmacy_knowledge_base(max_per_pharmacy: int = 50) -> Path:
    """Build a knowledge base by scraping all pharmacies."""
    medicines = await scrape_all_pharmacies(max_per_pharmacy)
    return save_medicines(medicines)


if __name__ == "__main__":
    asyncio.run(build_pharmacy_knowledge_base(max_per_pharmacy=30))
