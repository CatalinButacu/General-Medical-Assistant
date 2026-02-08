import logging
from typing import List, Dict, Any, Optional
from .loader import load_medicines_db, load_symptom_index

logger = logging.getLogger(__name__)

_medicines_cache = None
_symptom_index_cache = None

def _ensure_data_loaded():
    global _medicines_cache, _symptom_index_cache
    if _medicines_cache is None:
        _medicines_cache = load_medicines_db()
    if _symptom_index_cache is None:
        _symptom_index_cache = load_symptom_index()

def search_by_symptom(symptom, max_results=10, symptom_index=None):
    if symptom_index is None:
        _ensure_data_loaded()
        symptom_index = _symptom_index_cache
    
    if not symptom_index:
        return []
    
    symptom_lower = symptom.lower().strip()
    results = []
    
    for indexed_symptom, medicines in symptom_index.items():
        if symptom_lower in indexed_symptom.lower() or indexed_symptom.lower() in symptom_lower:
            results.extend(medicines)
    
    seen = set()
    unique = []
    for med in results:
        name = med.get("name", "")
        if name and name not in seen:
            seen.add(name)
            unique.append(med)
    
    return unique[:max_results]

def search_medicines(query, max_results=10, medicines_db=None):
    if medicines_db is None:
        _ensure_data_loaded()
        medicines_db = _medicines_cache
    
    if not medicines_db:
        return []
    
    query_lower = query.lower().strip()
    if not query_lower:
        return []
    
    results = []
    for med in medicines_db:
        score = 0
        title = med.get("title", "").lower()
        content = med.get("content", "").lower()
        metadata = med.get("metadata", {})
        
        if query_lower in title:
            score += 10
        if query_lower in metadata.get("active_substance", "").lower():
            score += 8
        if query_lower in metadata.get("category", "").lower():
            score += 5
        
        symptoms = metadata.get("symptoms", [])
        for symptom in symptoms:
            if query_lower in symptom.lower():
                score += 7
                break
        
        if query_lower in content:
            score += 3
        
        if score > 0:
            results.append((score, med))
    
    results.sort(key=lambda x: x[0], reverse=True)
    return [med for _, med in results[:max_results]]

def format_search_results(query, results):
    if not results:
        return f"No results found for '{query}'."
    
    output = f"Search results for: {query}\n\n"
    for item in results[:5]:
        if "metadata" in item:
            metadata = item.get("metadata", {})
            name = item.get("title", "Unknown Medicine").replace(" - Prospect Complet", "")
            price = metadata.get("price", "N/A")
            rx = metadata.get("prescription_required", False)
            url = metadata.get("url", "#")
        else:
            name = item.get("name", "Unknown Medicine")
            price = item.get("price", "N/A")
            rx = item.get("rx", False)
            url = item.get("url", "#")
        
        prescription = "Requires Prescription" if rx else "OTC"
        output += f"### {name}\nPrice: {price} RON | Status: {prescription}\n[Product]({url})\n\n---\n"
    
    return output

def combined_search(query, max_results=10, medicines_db=None, symptom_index=None):
    symptom_results = search_by_symptom(query, max_results, symptom_index)
    general_results = search_medicines(query, max_results, medicines_db)
    
    seen = set()
    combined = []
    for med in symptom_results + general_results:
        name = med.get("name") or med.get("title", "")
        if name and name not in seen:
            seen.add(name)
            combined.append(med)
    
    return {
        "query": query,
        "symptom_matches": symptom_results,
        "search_results": general_results,
        "combined": combined[:max_results],
        "formatted": format_search_results(query, combined[:max_results]),
    }
