from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class Medicine:
    name: str
    active_substance: str = ""
    category: str = ""
    price: Optional[float] = None
    currency: str = "RON"
    prescription_required: bool = False
    symptoms: List[str] = field(default_factory=list)
    description: str = ""
    warnings: str = ""
    interactions: str = ""
    url: str = ""
    source: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "active_substance": self.active_substance,
            "category": self.category,
            "price": self.price,
            "currency": self.currency,
            "rx": self.prescription_required,
            "symptoms": self.symptoms,
            "description": self.description,
            "warnings": self.warnings,
            "interactions": self.interactions,
            "url": self.url,
            "source": self.source,
        }

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
        content_parts = [
            f"Medicament: {self.name}",
            f"Substanță activă: {self.active_substance}" if self.active_substance else "",
            f"Descriere: {self.description}" if self.description else "",
            f"Preț: {self.price} {self.currency}" if self.price else "",
            f"Necesită rețetă: {'Da' if self.prescription_required else 'Nu'}",
        ]
        content = "\n".join(filter(None, content_parts))

        return {
            "title": self.name,
            "content": content,
            "metadata": {
                "source": self.source,
                "url": self.url,
                "price": self.price,
                "currency": self.currency,
                "active_substance": self.active_substance,
                "category": self.category,
                "prescription_required": self.prescription_required,
                "manufacturer": self.manufacturer,
                "image_url": self.image_url,
                "scraped_at": self.scraped_at,
            }
        }

@dataclass
class DrugInfo:
    name: str
    active_substance: str = ""
    therapeutic_area: str = ""
    indication: str = ""
    administration_route: str = ""
    authorization_status: str = ""
    marketing_holder: str = ""
    side_effects: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)
    interactions: List[str] = field(default_factory=list)
    dosage_info: str = ""
    source: str = "EMA"

    def to_document(self) -> Dict[str, Any]:
        content_parts = [
            f"Medicament: {self.name}",
            f"Substanță activă: {self.active_substance}",
            f"Zonă terapeutică: {self.therapeutic_area}" if self.therapeutic_area else "",
            f"Indicație: {self.indication}" if self.indication else "",
            f"Cale de administrare: {self.administration_route}" if self.administration_route else "",
            "",
            "Efecte adverse:" if self.side_effects else "",
            *[f"  - {effect}" for effect in self.side_effects],
            "",
            "Contraindicații:" if self.contraindications else "",
            *[f"  - {contra}" for contra in self.contraindications],
            "",
            "Interacțiuni:" if self.interactions else "",
            *[f"  - {inter}" for inter in self.interactions],
            "",
            f"Dozaj: {self.dosage_info}" if self.dosage_info else "",
        ]
        content = "\n".join(filter(lambda x: x is not None, content_parts))

        return {
            "title": self.name,
            "content": content,
            "metadata": {
                "source": self.source,
                "active_substance": self.active_substance,
                "therapeutic_area": self.therapeutic_area,
                "indication": self.indication,
                "administration_route": self.administration_route,
                "authorization_status": self.authorization_status,
                "marketing_holder": self.marketing_holder,
                "side_effects": self.side_effects,
                "contraindications": self.contraindications,
                "interactions": self.interactions,
            }
        }
