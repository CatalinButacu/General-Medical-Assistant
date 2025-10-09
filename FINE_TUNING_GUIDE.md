# 🧬 BioBERT Fine-Tuning Guide for Medical RAG System

## 📋 Overview

This guide walks you through fine-tuning your custom BioBERT model for medical text understanding. Our system uses three custom embedding approaches:

1. **BioBERT Fine-tuning** - Domain-specific medical text classification and similarity
2. **Sentence-BERT** - Medical sentence embeddings
3. **Word2Vec** - Medical vocabulary embeddings

## 🚀 Quick Start

### Step 1: Prepare Your Medical Data

```bash
# Navigate to ML backend
cd ml_backend

# Create sample medical datasets
python scripts/prepare_medical_data.py
```

This creates:
- `./data/medical_classification.json` - For classification fine-tuning
- `./data/medical_similarity.json` - For similarity learning

### Step 2: Fine-tune BioBERT for Classification

```python
from ml.fine_tuning import BioBERTFineTuner
import json

# Load your medical data
with open('./data/medical_classification.json', 'r') as f:
    data = json.load(f)

# Extract texts and labels
texts = [item['text'] for item in data]
labels = [item['label'] for item in data]

# Initialize fine-tuner
fine_tuner = BioBERTFineTuner(
    model_name='dmis-lab/biobert-base-cased-v1.2',
    task_type='classification',
    num_labels=len(set(labels))  # Number of unique labels
)

# Fine-tune the model
fine_tuner.fine_tune_classification(
    texts=texts,
    labels=labels,
    epochs=3,
    batch_size=16,
    learning_rate=2e-5,
    experiment_name="medical_classification_v1"
)

# Save the fine-tuned model
fine_tuner.save_model('./models/biobert_medical_classifier')
```

### Step 3: Fine-tune for Medical Similarity

```python
# Load similarity data
with open('./data/medical_similarity.json', 'r') as f:
    sim_data = json.load(f)

# Extract text pairs and similarities
text_pairs = [(item['text1'], item['text2']) for item in sim_data]
similarities = [item['similarity'] for item in sim_data]

# Initialize similarity fine-tuner
similarity_tuner = BioBERTFineTuner(
    model_name='dmis-lab/biobert-base-cased-v1.2',
    task_type='similarity'
)

# Fine-tune for similarity
similarity_tuner.fine_tune_similarity(
    text_pairs=text_pairs,
    similarities=similarities,
    epochs=5,
    batch_size=8,
    learning_rate=1e-5,
    experiment_name="medical_similarity_v1"
)

# Save the model
similarity_tuner.save_model('./models/biobert_medical_similarity')
```

## 📊 Using Your Custom Embeddings

### Load and Use Fine-tuned BioBERT

```python
from ml.custom_embeddings import CustomBioBERTEmbeddings

# Load your fine-tuned model
embeddings = CustomBioBERTEmbeddings(
    model_path='./models/biobert_medical_classifier',
    device='cuda'  # or 'cpu'
)

# Encode medical texts
medical_texts = [
    "Patient has chest pain and shortness of breath",
    "Prescribed ibuprofen for inflammation"
]

# Get embeddings
text_embeddings = embeddings.encode_text(medical_texts)
print(f"Embeddings shape: {text_embeddings.shape}")

# Compute similarity between texts
similarity = embeddings.compute_similarity(
    text_embeddings[0], 
    text_embeddings[1]
)
print(f"Similarity: {similarity:.3f}")
```

### Use with Custom Vector Database

```python
from ml.vector_database import CustomFAISSDatabase

# Initialize vector database
vector_db = CustomFAISSDatabase(
    embedding_dim=768,  # BioBERT dimension
    index_type='IVF'
)

# Add medical documents
documents = [
    "Ibuprofen is a nonsteroidal anti-inflammatory drug",
    "Common side effects include nausea and dizziness",
    "Contraindicated in severe renal impairment"
]

# Get embeddings and add to database
embeddings_list = embeddings.encode_text(documents)
vector_db.add_vectors(embeddings_list, documents)

# Search for similar content
query = "What are the side effects of NSAIDs?"
query_embedding = embeddings.encode_single(query)
results = vector_db.search(query_embedding, k=2)

for doc, score in results:
    print(f"Score: {score:.3f} - {doc}")
```

## 🔧 Advanced Configuration

### Custom Training Parameters

```python
# Advanced fine-tuning configuration
fine_tuner = BioBERTFineTuner(
    model_name='dmis-lab/biobert-base-cased-v1.2',
    task_type='classification',
    num_labels=8,
    max_length=512,
    dropout_rate=0.1
)

# Custom training with advanced options
fine_tuner.fine_tune_classification(
    texts=texts,
    labels=labels,
    epochs=5,
    batch_size=16,
    learning_rate=2e-5,
    weight_decay=0.01,
    warmup_steps=100,
    gradient_accumulation_steps=2,
    experiment_name="medical_advanced_v1",
    save_steps=500,
    eval_steps=100
)
```

### Monitor Training with MLflow

```bash
# Start MLflow UI to monitor training
mlflow ui --host 0.0.0.0 --port 5000
```

Visit `http://localhost:5000` to see:
- Training loss curves
- Validation metrics
- Model parameters
- Experiment comparisons

## 📈 Evaluation and Testing

### Evaluate Model Performance

```python
# Evaluate classification model
from sklearn.metrics import classification_report, accuracy_score

# Load test data
test_texts = ["Patient diagnosed with hypertension"]
test_labels = ["diagnosis"]

# Get predictions
predictions = fine_tuner.predict(test_texts)
accuracy = accuracy_score(test_labels, predictions)

print(f"Accuracy: {accuracy:.3f}")
print(classification_report(test_labels, predictions))
```

### Test Embedding Quality

```python
# Test embedding similarity
test_pairs = [
    ("chest pain", "thoracic discomfort"),
    ("medication", "pharmaceutical drug"),
    ("allergy", "hypersensitivity")
]

for text1, text2 in test_pairs:
    emb1 = embeddings.encode_single(text1)
    emb2 = embeddings.encode_single(text2)
    sim = embeddings.compute_similarity(emb1, emb2)
    print(f"{text1} <-> {text2}: {sim:.3f}")
```

## 🎯 Best Practices

### 1. Data Preparation
- **Clean your medical texts**: Remove PHI, normalize terminology
- **Balance your dataset**: Ensure equal representation of classes
- **Validate annotations**: Use medical experts for labeling

### 2. Training Tips
- **Start with small learning rates**: 1e-5 to 5e-5 for BioBERT
- **Use gradient accumulation**: For larger effective batch sizes
- **Monitor overfitting**: Use validation sets and early stopping

### 3. Evaluation
- **Use medical-specific metrics**: Consider domain relevance
- **Test on real scenarios**: Use actual medical queries
- **Cross-validate**: Ensure model generalization

## 🔄 Production Deployment

### Save Production Model

```python
# Save optimized model for production
fine_tuner.save_model(
    './models/production/biobert_medical_v1',
    optimize_for_inference=True
)
```

### Load in Production

```python
# Production loading
embeddings = CustomBioBERTEmbeddings(
    model_path='./models/production/biobert_medical_v1',
    device='cuda'
)

# Optimize for inference
embeddings.model.eval()
torch.set_grad_enabled(False)
```

## 📚 Your Custom Models

After fine-tuning, you'll have:

1. **`./models/biobert_medical_classifier/`** - Classification model
2. **`./models/biobert_medical_similarity/`** - Similarity model  
3. **`./models/sentence_bert_medical/`** - Sentence embeddings
4. **`./models/word2vec_medical/`** - Word embeddings

## 🚀 Next Steps

1. **Expand your dataset** with more medical texts
2. **Fine-tune on your specific domain** (cardiology, oncology, etc.)
3. **Integrate with the RAG pipeline** for enhanced retrieval
4. **Deploy to production** with the deployment guide

## 🆘 Troubleshooting

### Common Issues

**CUDA Out of Memory:**
```python
# Reduce batch size
batch_size = 8  # or smaller

# Use gradient accumulation
gradient_accumulation_steps = 4
```

**Poor Performance:**
- Check data quality and balance
- Increase training epochs
- Adjust learning rate
- Add more training data

**Slow Training:**
- Use mixed precision training
- Optimize data loading
- Use multiple GPUs if available

---

🎉 **Congratulations!** You now have a custom fine-tuned BioBERT model for your medical RAG system!