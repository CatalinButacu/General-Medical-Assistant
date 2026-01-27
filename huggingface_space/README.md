---
title: RAG Pharma Assistant
emoji: 💊
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
---

# RAG Pharma Assistant

Asistent medical bazat pe AI pentru recomandări de medicamente din România.

## Features

- 🔍 Căutare după simptome
- 💊 1200+ medicamente indexate
- 🏥 20 categorii medicale
- 🛒 Link-uri directe către farmacii

## API Usage

Pentru integrare cu frontend-ul de pe GitHub Pages:

```javascript
const response = await fetch('https://your-space.hf.space/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'durere de cap' })
});
const data = await response.json();
```

## Disclaimer

Acest asistent oferă informații generale. Pentru diagnostic și tratament, consultați un medic.
