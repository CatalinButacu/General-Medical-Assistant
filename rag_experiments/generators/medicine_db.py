"""
Medicine Database Generator for RAG Pharma.
Consolidated from comprehensive_db.py, leaflets_db.py, and ro_medicines_db.py.

This module generates synthetic medicine entries for testing and development.
For production, use scraped data from the scrapers module.
"""
import json
import random
from pathlib import Path
from typing import List, Dict, Any

DATA_DIR = Path(__file__).parent.parent / "data"

# Medical categories with symptoms and active substances
CATEGORIES = {
    "durere_febra": {
        "name": "Durere și Febră",
        "symptoms": ["durere de cap", "migrena", "febra", "dureri musculare", "dureri articulare", "dureri dentare"],
        "substances": [
            ("Ibuprofen", "AINS pentru durere și inflamație"),
            ("Paracetamol", "Analgezic și antipiretic"),
            ("Acid acetilsalicilic", "Analgezic, antipiretic, antiinflamator"),
            ("Metamizol", "Analgezic puternic"),
            ("Naproxen", "AINS cu durată lungă de acțiune"),
            ("Diclofenac", "AINS pentru dureri articulare"),
        ]
    },
    "digestiv": {
        "name": "Afecțiuni Digestive",
        "symptoms": ["arsuri gastrice", "reflux", "dureri stomac", "diaree", "constipatie", "balonare", "greata"],
        "substances": [
            ("Omeprazol", "Inhibitor de pompă protonică"),
            ("Pantoprazol", "IPP pentru protecție gastrică"),
            ("Diosmectită", "Protector intestinal"),
            ("Loperamidă", "Antidiareic"),
            ("Drotaverină", "Antispastic"),
            ("Simeticonă", "Antiflatulent"),
        ]
    },
    "respirator": {
        "name": "Afecțiuni Respiratorii",
        "symptoms": ["tuse", "raceala", "gripa", "nas infundat", "sinuzita", "durere in gat"],
        "substances": [
            ("Acetilcisteină", "Mucolitc pentru tuse productivă"),
            ("Ambroxol", "Expectorant"),
            ("Xilometazolină", "Decongestionant nazal"),
            ("Dextrometorfan", "Antitusiv"),
            ("Benzidamină", "Antiinflamator pentru gât"),
        ]
    },
    "alergii": {
        "name": "Alergii",
        "symptoms": ["alergie", "rinita alergica", "urticarie", "mancarimi", "ochi rosii"],
        "substances": [
            ("Loratadină", "Antihistaminic non-sedativ"),
            ("Cetirizină", "Antihistaminic"),
            ("Levocetirizină", "Antihistaminic puternic"),
            ("Fexofenadină", "Antihistaminic non-sedativ"),
        ]
    },
    "vitamine": {
        "name": "Vitamine și Minerale",
        "symptoms": ["oboseala", "imunitate scazuta", "anemie", "crampe musculare"],
        "substances": [
            ("Vitamina D3", "Colecalciferol"),
            ("Vitamina C", "Acid ascorbic"),
            ("Magneziu", "Mineral esențial"),
            ("Zinc", "Mineral pentru imunitate"),
            ("Fier", "Mineral pentru anemie"),
        ]
    },
}

# Brand prefixes for generating medicine names
BRAND_PREFIXES = [
    "Zentiva", "Terapia", "Biofarm", "Sandoz", "Krka", "Stada",
    "Naturalis", "Hofigal", "Alevia", "Himalaya", "Solgar"
]

# Pharmacy sources for purchase links
PHARMACIES = [
    ("Catena", "https://www.catena.ro"),
    ("Farmacia Tei", "https://comenzi.farmaciatei.ro"),
    ("HelpNet", "https://www.helpnet.ro"),
    ("Dr. Max", "https://www.drmax.ro"),
]

# Pharmaceutical forms
FORMS = [
    "comprimate", "capsule", "tablete", "comprimate filmate",
    "sirop", "picături", "cremă", "gel", "spray"
]


def generate_medicine_entry(
    category_key: str,
    substance_data: tuple,
    index: int = 0
) -> Dict[str, Any]:
    """
    Generate a single medicine entry.
    
    Args:
        category_key: Key of the category in CATEGORIES
        substance_data: Tuple of (substance_name, mechanism)
        index: Optional index for uniqueness
        
    Returns:
        Dictionary with medicine data
    """
    category = CATEGORIES[category_key]
    substance, mechanism = substance_data
    
    brand = random.choice(BRAND_PREFIXES)
    pharmacy_name, pharmacy_url = random.choice(PHARMACIES)
    form = random.choice(FORMS)
    
    doses = ["50mg", "100mg", "200mg", "400mg", "500mg", "10mg", "20mg"]
    dose = random.choice(doses)
    
    name = f"{substance} {brand} {dose}"
    if random.random() > 0.5:
        name = f"{brand} {substance} {dose}"
    
    price = round(random.uniform(8.0, 100.0), 2)
    symptoms = random.sample(category["symptoms"], min(3, len(category["symptoms"])))
    
    url_slug = name.lower().replace(" ", "-").replace("+", "-")
    url = f"{pharmacy_url}/p/{url_slug}"
    
    rx = category_key in ["antibiotice", "neurologie", "diabet", "cardiovascular"]
    
    return {
        "name": name,
        "active": substance,
        "mechanism": mechanism,
        "category": category["name"],
        "category_key": category_key,
        "form": form,
        "rx": rx,
        "price": price,
        "currency": "RON",
        "symptoms": symptoms,
        "manufacturer": brand,
        "pharmacy": pharmacy_name,
        "url": url,
    }


def build_document(med: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a medicine entry to document format for the RAG system.
    
    Args:
        med: Medicine dictionary
        
    Returns:
        Document dictionary with content, title, and metadata
    """
    rx_status = "⚠️ **NECESITĂ REȚETĂ**" if med["rx"] else "✅ Fără rețetă"
    symptoms_text = ", ".join(med["symptoms"])
    
    content = f"""# {med["name"]}

## Informații Produs
- **Substanță activă**: {med["active"]}
- **Formă farmaceutică**: {med["form"]}
- **Categorie**: {med["category"]}
- **Producător**: {med["manufacturer"]}
- **Status**: {rx_status}
- **Preț**: {med["price"]} {med["currency"]}

## Mecanism de Acțiune
{med["mechanism"]}

## Simptome Tratate
{symptoms_text}

## Cumpărare Online
🛒 [Cumpără de la {med["pharmacy"]}]({med["url"]})
"""
    return {
        "content": content,
        "title": f"{med['name']} - Prospect Complet",
        "source": med["pharmacy"],
        "metadata": {
            "active_substance": med["active"],
            "category": med["category"],
            "category_key": med["category_key"],
            "form": med["form"],
            "prescription_required": med["rx"],
            "price": med["price"],
            "symptoms": med["symptoms"],
            "manufacturer": med["manufacturer"],
            "url": med["url"]
        }
    }


def generate_medicine_database(target_count: int = 500) -> List[Dict[str, Any]]:
    """
    Generate a database of medicine entries.
    
    Args:
        target_count: Target number of medicine entries
        
    Returns:
        List of medicine dictionaries
    """
    medicines = []
    index = 0
    
    # Distribute evenly across categories
    per_category = max(5, target_count // len(CATEGORIES))
    
    for category_key, category_data in CATEGORIES.items():
        substances = category_data["substances"]
        
        for substance_data in substances:
            variants = max(1, per_category // len(substances))
            for _ in range(variants):
                med = generate_medicine_entry(category_key, substance_data, index)
                medicines.append(med)
                index += 1
                
                if len(medicines) >= target_count:
                    break
            if len(medicines) >= target_count:
                break
        if len(medicines) >= target_count:
            break
    
    # Fill remaining slots with random entries
    while len(medicines) < target_count:
        category_key = random.choice(list(CATEGORIES.keys()))
        substance_data = random.choice(CATEGORIES[category_key]["substances"])
        med = generate_medicine_entry(category_key, substance_data, index)
        medicines.append(med)
        index += 1
    
    return medicines


def build_symptom_index(medicines: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Build an index mapping symptoms to medicines.
    
    Args:
        medicines: List of medicine dictionaries
        
    Returns:
        Dictionary mapping symptom names to lists of medicine info
    """
    index = {}
    for med in medicines:
        for symptom in med.get("symptoms", []):
            symptom_lower = symptom.lower()
            if symptom_lower not in index:
                index[symptom_lower] = []
            index[symptom_lower].append({
                "name": med["name"],
                "active": med["active"],
                "category": med["category"],
                "rx": med["rx"],
                "price": med["price"],
                "url": med["url"]
            })
    return index


def build_comprehensive_database(target_count: int = 500) -> Path:
    """
    Generate and save a comprehensive medicine database.
    
    Args:
        target_count: Target number of medicine entries
        
    Returns:
        Path to the saved documents file
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {target_count} medicine entries...")
    medicines = generate_medicine_database(target_count)
    
    # Save documents
    documents = [build_document(med) for med in medicines]
    docs_file = DATA_DIR / "comprehensive_medicines.json"
    with open(docs_file, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(documents)} documents to {docs_file}")
    
    # Save symptom index
    symptom_index = build_symptom_index(medicines)
    index_file = DATA_DIR / "comprehensive_symptom_index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(symptom_index, f, indent=2, ensure_ascii=False)
    print(f"Saved symptom index ({len(symptom_index)} symptoms) to {index_file}")
    
    return docs_file


if __name__ == "__main__":
    build_comprehensive_database(500)
