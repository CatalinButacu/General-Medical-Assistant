"""
Medical Dataset Preparation Script
Prepare your medical text data for BioBERT fine-tuning
"""

import pandas as pd
import json
import os
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalDataPreparator:
    """Prepare medical datasets for fine-tuning"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def prepare_classification_data(self, texts: List[str], labels: List[str]) -> str:
        """
        Prepare data for medical text classification
        
        Args:
            texts: List of medical texts
            labels: List of corresponding labels (e.g., 'medication', 'symptom', 'diagnosis')
        
        Returns:
            Path to prepared dataset file
        """
        # Create classification dataset
        data = []
        for text, label in zip(texts, labels):
            data.append({
                'text': text.strip(),
                'label': label.strip(),
                'length': len(text.split())
            })
        
        # Save as JSON
        output_path = os.path.join(self.data_dir, 'medical_classification.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Classification dataset saved: {output_path}")
        logger.info(f"Total samples: {len(data)}")
        
        return output_path
    
    def prepare_similarity_data(self, text_pairs: List[Tuple[str, str]], 
                              similarities: List[float]) -> str:
        """
        Prepare data for medical text similarity learning
        
        Args:
            text_pairs: List of (text1, text2) tuples
            similarities: List of similarity scores (0.0 to 1.0)
        
        Returns:
            Path to prepared dataset file
        """
        data = []
        for (text1, text2), similarity in zip(text_pairs, similarities):
            data.append({
                'text1': text1.strip(),
                'text2': text2.strip(),
                'similarity': float(similarity),
                'length1': len(text1.split()),
                'length2': len(text2.split())
            })
        
        # Save as JSON
        output_path = os.path.join(self.data_dir, 'medical_similarity.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Similarity dataset saved: {output_path}")
        logger.info(f"Total pairs: {len(data)}")
        
        return output_path
    
    def create_sample_medical_data(self):
        """Create sample medical data for demonstration"""
        
        # Sample medical texts for classification
        medical_texts = [
            "Patient presents with acute chest pain and shortness of breath",
            "Prescribed ibuprofen 400mg twice daily for inflammation",
            "Contraindicated in patients with severe renal impairment",
            "Common side effects include nausea, dizziness, and headache",
            "Diagnosed with type 2 diabetes mellitus and hypertension",
            "Administer epinephrine 0.3mg intramuscularly for anaphylaxis",
            "Patient allergic to penicillin and sulfonamides",
            "Symptoms improved after 48 hours of antibiotic therapy"
        ]
        
        labels = [
            "symptom", "medication", "contraindication", "side_effect",
            "diagnosis", "medication", "allergy", "treatment"
        ]
        
        # Sample similarity pairs
        similarity_pairs = [
            ("chest pain", "thoracic discomfort"),
            ("ibuprofen", "nonsteroidal anti-inflammatory drug"),
            ("diabetes", "hyperglycemia"),
            ("allergy", "hypersensitivity reaction"),
            ("headache", "cephalgia")
        ]
        
        similarities = [0.9, 0.8, 0.85, 0.9, 0.95]
        
        # Prepare datasets
        class_path = self.prepare_classification_data(medical_texts, labels)
        sim_path = self.prepare_similarity_data(similarity_pairs, similarities)
        
        return class_path, sim_path

if __name__ == "__main__":
    # Example usage
    preparator = MedicalDataPreparator()
    
    # Create sample data
    class_file, sim_file = preparator.create_sample_medical_data()
    
    print(f"✅ Sample datasets created:")
    print(f"📋 Classification: {class_file}")
    print(f"🔗 Similarity: {sim_file}")
    print(f"\n🚀 Ready for fine-tuning!")