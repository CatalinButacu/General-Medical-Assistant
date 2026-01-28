import gradio as gr
import json
from pathlib import Path

# Data paths relative to this file
DATA_PATH = Path("data/comprehensive_medicines.json")
INDEX_PATH = Path("data/comprehensive_symptom_index.json")

def load_json_data(path):
    if not path.exists():
        return [] if "medicines" in path.name else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# Load data on startup
medicines = load_json_data(DATA_PATH)
symptom_index = load_json_data(INDEX_PATH)

def search_medicines(query):
    query = query.lower().strip()
    if not query:
        return "Please enter a symptom or medicine name."

    results = []
    
    # 1. Check symptom index
    for symptom, meds in symptom_index.items():
        if query in symptom.lower():
            results.extend(meds)
    
    # 2. Check medicine titles, active substances, and content
    for med in medicines:
        title = med.get("title", "").lower()
        metadata = med.get("metadata", {})
        active = metadata.get("active_substance", "").lower()
        content = med.get("content", "").lower()
        
        if query in title or query in active or query in content:
            results.append({
                "name": med.get("title", "Unknown Medicine").replace(" - Prospect Complet", ""),
                "price": metadata.get("price", "N/A"),
                "url": metadata.get("url", "#"),
                "rx": metadata.get("prescription_required", False)
            })

    if not results:
        return f"No results found for '{query}'. Try searching for symptoms like 'febra' or 'tuse', or active substances like 'Paracetamol'."

    unique_results = {}
    for res in results:
        name = res["name"]
        if name not in unique_results:
            unique_results[name] = res

    output = f"Search results for: {query}\n\n"
    for item in list(unique_results.values())[:5]:
        prescription = "Requires Prescription" if item.get("rx") else "OTC (No prescription)"
        output += f"### {item['name']}\n"
        output += f"Price: {item.get('price')} RON | Status: {prescription}\n"
        output += f"[Link to Product]({item.get('url')})\n\n"
        output += "---\n"
    
    return output

# Using gr.Interface to automatically expose the /api/predict endpoint correctly
interface = gr.Interface(
    fn=search_medicines,
    inputs=gr.Textbox(label="Enter symptoms or medicine brand/name"),
    outputs=gr.Markdown(label="Search Results"),
    title="Pharma RAG Assistant",
    description="Search through a database of 1200+ medicines."
)

if __name__ == "__main__":
    interface.launch()
