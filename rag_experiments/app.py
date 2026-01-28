import gradio as gr
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import uvicorn
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data paths
DATA_PATH = Path("data/comprehensive_medicines.json")
INDEX_PATH = Path("data/comprehensive_symptom_index.json")

def load_json_data(path):
    if not path.exists():
        return [] if "medicines" in path.name else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

medicines = load_json_data(DATA_PATH)
symptom_index = load_json_data(INDEX_PATH)

def search_medicines(query):
    query = (query or "").lower().strip()
    if not query:
        return "Please enter a symptom or medicine name."
    results = []
    for symptom, meds in symptom_index.items():
        if query in symptom.lower():
            results.extend(meds)
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
        return f"No results found for '{query}'."
    unique_results = {}
    for res in results:
        name = res["name"]
        if name not in unique_results:
            unique_results[name] = res
    output = f"Search results for: {query}\n\n"
    for item in list(unique_results.values())[:5]:
        prescription = "Requires Prescription" if item.get("rx") else "OTC"
        output += f"### {item['name']}\nPrice: {item.get('price')} RON | Status: {prescription}\n[Product]({item.get('url')})\n\n---\n"
    return output

# --- FastAPI App Setup ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoint (Defined BEFORE Gradio mounting)
@app.post("/api/v1/search")
async def api_search(request: Request):
    try:
        data = await request.json()
        query = data.get("data", [""])[0] if "data" in data else data.get("query", "")
        return {"data": [search_medicines(query)]}
    except Exception as e:
        return {"error": str(e), "data": ["Error"]}

@app.get("/health")
async def health():
    return {"status": "ok"}

# Redirect root to Gradio if needed, but we'll mount Gradio at /
@app.get("/ui")
async def ui_redirect():
    return RedirectResponse(url="/")

# --- Gradio UI Setup ---
io = gr.Interface(
    fn=search_medicines,
    inputs=gr.Textbox(label="Search"),
    outputs=gr.Markdown(),
    title="Pharma RAG"
)

# Mount Gradio at root
# NOTE: mounting at root last ensures FastAPI routes are checked first
app = gr.mount_gradio_app(app, io, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
