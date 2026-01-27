import json
import logging
from pathlib import Path
from typing import List, Optional

from .base import Document
from .data_sources import DATA_DIR, create_sample_knowledge_base

logger = logging.getLogger(__name__)


def load_documents(source_file: Optional[Path] = None) -> List[Document]:
    if source_file is None:
        source_file = DATA_DIR / "eu_medicines.json"

    if not source_file.exists():
        logger.info("Knowledge base not found, creating sample...")
        create_sample_knowledge_base()

    with open(source_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    documents = []
    for entry in data:
        doc = Document(
            content=entry["content"],
            title=entry["title"],
            source=entry.get("source", "unknown"),
            metadata=entry.get("metadata", {})
        )
        documents.append(doc)

    logger.info(f"Loaded {len(documents)} documents from {source_file}")
    return documents


def load_leaflets() -> List[Document]:
    leaflet_file = DATA_DIR / "ro_leaflets.json"
    if leaflet_file.exists():
        return load_documents(leaflet_file)
    return []


def load_romanian_medicines() -> List[Document]:
    ro_file = DATA_DIR / "ro_medicines_100.json"
    if ro_file.exists():
        return load_documents(ro_file)
    return []


def load_all_knowledge_bases() -> List[Document]:
    all_docs = []
    
    leaflets = load_leaflets()
    if leaflets:
        all_docs.extend(leaflets)
        logger.info(f"Loaded {len(leaflets)} medicine leaflets")
    
    ro_meds = load_romanian_medicines()
    if ro_meds:
        all_docs.extend(ro_meds)
        logger.info(f"Loaded {len(ro_meds)} Romanian medicines")
    
    eu_meds = load_documents()
    if eu_meds:
        all_docs.extend(eu_meds)
        logger.info(f"Loaded {len(eu_meds)} EU medicines")
    
    logger.info(f"Total: {len(all_docs)} documents loaded")
    return all_docs


def load_symptom_index() -> dict:
    index_file = DATA_DIR / "symptom_index.json"
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def search_by_symptom(symptom: str) -> List[dict]:
    index = load_symptom_index()
    symptom_lower = symptom.lower()
    
    results = []
    for indexed_symptom, medicines in index.items():
        if symptom_lower in indexed_symptom or indexed_symptom in symptom_lower:
            results.extend(medicines)
    
    seen = set()
    unique = []
    for med in results:
        if med["name"] not in seen:
            seen.add(med["name"])
            unique.append(med)
    
    return unique


def load_from_directory(directory: Path) -> List[Document]:
    documents = []

    for file_path in directory.glob("*.md"):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        doc = Document(
            content=content,
            title=file_path.stem.replace("_", " ").title(),
            source=str(file_path)
        )
        documents.append(doc)

    for file_path in directory.glob("*.txt"):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        doc = Document(
            content=content,
            title=file_path.stem.replace("_", " ").title(),
            source=str(file_path)
        )
        documents.append(doc)

    for file_path in directory.glob("*.json"):
        try:
            docs = load_documents(file_path)
            documents.extend(docs)
        except Exception as e:
            logger.warning(f"Failed to load {file_path}: {e}")

    logger.info(f"Loaded {len(documents)} documents from {directory}")
    return documents
