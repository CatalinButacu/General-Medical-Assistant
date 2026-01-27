"""
RAG Pharma Assistant - Hugging Face Spaces Backend
Gradio API for medicine recommendations based on symptoms
"""

import gradio as gr
import json
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load medicine database
DATA_FILE = Path(__file__).parent / "data" / "comprehensive_medicines.json"
SYMPTOM_INDEX_FILE = Path(__file__).parent / "data" / "comprehensive_symptom_index.json"

medicines_db: List[Dict] = []
symptom_index: Dict[str, List[Dict]] = {}


def load_data():
    global medicines_db, symptom_index
    
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            medicines_db = json.load(f)
        logger.info(f"Loaded {len(medicines_db)} medicines")
    
    if SYMPTOM_INDEX_FILE.exists():
        with open(SYMPTOM_INDEX_FILE, 'r', encoding='utf-8') as f:
            symptom_index = json.load(f)
        logger.info(f"Loaded {len(symptom_index)} symptoms")


def search_by_symptom(symptom: str, max_results: int = 10) -> List[Dict]:
    symptom_lower = symptom.lower().strip()
    results = []
    
    for indexed_symptom, medicines in symptom_index.items():
        if symptom_lower in indexed_symptom or indexed_symptom in symptom_lower:
            results.extend(medicines)
    
    seen = set()
    unique = []
    for med in results:
        if med["name"] not in seen:
            seen.add(med["name"])
            unique.append(med)
    
    return unique[:max_results]


def search_medicines(query: str, max_results: int = 10) -> List[Dict]:
    query_lower = query.lower().strip()
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
        
        if query_lower in content:
            score += 3
        
        if score > 0:
            results.append((score, med))
    
    results.sort(key=lambda x: x[0], reverse=True)
    return [med for _, med in results[:max_results]]


def format_medicine_card(med: Dict) -> str:
    metadata = med.get("metadata", {})
    rx = "⚠️ Rețetă" if metadata.get("prescription_required") else "✅ OTC"
    price = metadata.get("price", "N/A")
    url = metadata.get("url", "#")
    
    return f"""### {med.get('title', 'Unknown')}
**Preț**: {price} RON | **Status**: {rx}

[🛒 Cumpără online]({url})

---"""


def chat_response(message: str, history: List[Tuple[str, str]]) -> str:
    if not message.strip():
        return "Te rog să îmi spui ce simptome ai sau ce medicament cauți."
    
    symptom_results = search_by_symptom(message, max_results=5)
    
    if symptom_results:
        response = f"## 💊 Medicamente recomandate pentru: *{message}*\n\n"
        for med in symptom_results:
            rx = "⚠️ Rețetă" if med.get("rx") else "✅ Fără rețetă"
            response += f"- **{med['name']}** ({med.get('category', 'N/A')}) - {med.get('price', 'N/A')} RON - {rx}\n"
            response += f"  - [Cumpără]({med.get('url', '#')})\n\n"
        
        response += "\n⚠️ *Acestea sunt recomandări generale. Consultați medicul sau farmacistul pentru sfaturi personalizate.*"
        return response
    
    search_results = search_medicines(message, max_results=5)
    
    if search_results:
        response = f"## 🔍 Rezultate pentru: *{message}*\n\n"
        for med in search_results:
            response += format_medicine_card(med)
        
        response += "\n⚠️ *Consultați medicul sau farmacistul pentru sfaturi personalizate.*"
        return response
    
    return f"""Nu am găsit medicamente pentru "{message}".

Încearcă să cauți după:
- **Simptome**: durere de cap, febră, tuse, diaree, alergie
- **Categorie**: vitamine, antibiotice, digestiv
- **Nume medicament**: Nurofen, Paracetamol, Omeprazol

Sau descrie ce simptome ai și îți voi recomanda medicamente potrivite."""


def get_categories() -> str:
    categories = set()
    for med in medicines_db:
        cat = med.get("metadata", {}).get("category", "")
        if cat:
            categories.add(cat)
    
    return "\n".join(f"- {cat}" for cat in sorted(categories))


def get_symptoms() -> str:
    return "\n".join(f"- {sym}" for sym in sorted(symptom_index.keys())[:50])


# Load data on startup
load_data()

# Gradio Interface
with gr.Blocks(
    title="RAG Pharma Assistant",
) as demo:
    gr.Markdown("""
    # 💊 RAG Pharma Assistant
    ### Asistent medical bazat pe baza de date cu 1200+ medicamente din România
    
    Întreabă-mă despre simptome sau medicamente și îți voi recomanda opțiuni potrivite.
    """)
    
    chatbot = gr.Chatbot(
        label="Conversație",
        height=400,
    )
    
    msg = gr.Textbox(
        label="Mesajul tău",
        placeholder="Ex: Am durere de cap și febră...",
        lines=2
    )
    
    with gr.Row():
        submit = gr.Button("🔍 Caută", variant="primary")
        clear = gr.Button("🗑️ Șterge conversația")
    
    with gr.Accordion("📋 Categorii disponibile", open=False):
        gr.Markdown(get_categories())
    
    with gr.Accordion("🏥 Simptome indexate (primele 50)", open=False):
        gr.Markdown(get_symptoms())
    
    gr.Markdown(f"""
    ---
    **📊 Statistici bază de date:**
    - {len(medicines_db)} medicamente
    - {len(symptom_index)} simptome indexate
    - Surse: Catena, Farmacia Tei, HelpNet, Dr. Max, și altele
    
    ⚠️ *Acest asistent oferă informații generale. Pentru diagnostic și tratament, consultați un medic.*
    """)
    
    def respond(message, chat_history):
        bot_message = chat_response(message, chat_history)
        chat_history.append((message, bot_message))
        return "", chat_history
    
    msg.submit(respond, [msg, chatbot], [msg, chatbot])
    submit.click(respond, [msg, chatbot], [msg, chatbot])


# API endpoint for external use (GitHub Pages frontend)
def api_search(query: str) -> Dict:
    """API endpoint for external frontend"""
    symptom_results = search_by_symptom(query, max_results=10)
    search_results = search_medicines(query, max_results=10)
    
    return {
        "query": query,
        "symptom_matches": symptom_results,
        "search_results": [
            {
                "title": med.get("title"),
                "content": med.get("content", "")[:500],
                "metadata": med.get("metadata", {})
            }
            for med in search_results
        ]
    }


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
