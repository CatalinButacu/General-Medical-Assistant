# 💊 MedAssist: AI Pharmacist Demo

> [!IMPORTANT]
> **Educational Demo Purposes Only**: This project is a prototype developed for educational and research purposes. The information provided by the AI assistant is NOT medical advice. Always consult a healthcare professional.

Asistent medical bazat pe AI pentru recomandări de medicamente din România.

## 🏗️ Arhitectură

```
RAG-Pharma/
├── src/                    # React Frontend (GitHub Pages)
├── huggingface_space/      # Gradio Backend (Hugging Face Spaces)
├── rag_experiments/        # RAG Logic & Medicine Database
│   └── data/               # 1200+ medicamente, 107 simptome
├── docs/                   # Documentation
└── scripts/                # Utility scripts
```

## 🚀 Deployment

### Frontend (GitHub Pages)

```bash
npm run build
# Push to gh-pages branch or /docs folder
```

### Backend (Hugging Face Spaces)

```bash
# Push huggingface_space/ to HF Space repo
cd huggingface_space
git push hf main
```

## 💻 Local Development

```bash
# Frontend
npm install
npm run dev

# Backend (Gradio)
pip install gradio
python huggingface_space/app.py
# Open http://localhost:7860
```

## 📊 Features

- 🔍 Căutare după simptome
- 💊 1200+ medicamente indexate
- 🏥 20 categorii medicale
- 🛒 Link-uri directe către farmacii (Catena, Farmacia Tei, HelpNet, etc.)

## ⚠️ Disclaimer

Acest asistent oferă informații generale. Pentru diagnostic și tratament, consultați un medic.

## 📝 License

MIT
