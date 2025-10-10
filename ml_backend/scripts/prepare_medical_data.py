#!/usr/bin/env python3
"""
Medical Data Preparation Script

This script prepares and processes medical data for the RAG system.
It handles data cleaning, preprocessing, and vectorization for medical documents.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MedicalDataPreprocessor:
    """Handles preprocessing of medical data for RAG system."""

    def __init__(self, data_dir: str = "ml_backend/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize NLTK components
        self._download_nltk_data()
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))

        # Medical-specific stop words
        self.medical_stop_words = {
            'patient', 'patients', 'case', 'cases', 'study', 'studies',
            'treatment', 'therapy', 'medication', 'drug', 'medicine'
        }

    def _download_nltk_data(self):
        """Download required NLTK data."""
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
            nltk.data.find('corpora/wordnet')
        except LookupError:
            logger.info("Downloading NLTK data...")
            nltk.download('punkt')
            nltk.download('stopwords')
            nltk.download('wordnet')
            nltk.download('omw-1.4')

    def clean_text(self, text: str) -> str:
        """Clean and normalize medical text."""
        if not text or not isinstance(text, str):
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove special characters but keep medical abbreviations
        text = re.sub(r'[^\w\s\-\.]', ' ', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove numbers that are not part of medical terms
        text = re.sub(r'\b\d+\b', '', text)

        return text.strip()

    def tokenize_and_lemmatize(self, text: str) -> List[str]:
        """Tokenize and lemmatize medical text."""
        if not text:
            return []

        # Tokenize
        tokens = word_tokenize(text)

        # Remove stop words and lemmatize
        processed_tokens = []
        for token in tokens:
            if (len(token) > 2 and
                token not in self.stop_words and
                token not in self.medical_stop_words and
                    token.isalpha()):
                lemmatized = self.lemmatizer.lemmatize(token)
                processed_tokens.append(lemmatized)

        return processed_tokens

    def extract_medical_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract medical entities from text (simplified version)."""
        # This is a simplified version - in production, use spaCy with medical models
        entities = {
            'symptoms': [],
            'conditions': [],
            'medications': [],
            'procedures': []
        }

        # Common medical patterns (simplified)
        symptom_patterns = [
            r'\b(pain|ache|fever|nausea|fatigue|headache|dizziness)\b',
            r'\b(swelling|inflammation|rash|itching|burning)\b'
        ]

        condition_patterns = [
            r'\b(diabetes|hypertension|asthma|arthritis|depression)\b',
            r'\b(infection|cancer|pneumonia|bronchitis|gastritis)\b'
        ]

        medication_patterns = [
            r'\b(aspirin|ibuprofen|acetaminophen|insulin|metformin)\b',
            r'\b(antibiotic|antidepressant|analgesic|steroid)\b'
        ]

        # Extract entities using patterns
        for pattern in symptom_patterns:
            entities['symptoms'].extend(re.findall(pattern, text, re.IGNORECASE))

        for pattern in condition_patterns:
            entities['conditions'].extend(re.findall(pattern, text, re.IGNORECASE))

        for pattern in medication_patterns:
            entities['medications'].extend(re.findall(pattern, text, re.IGNORECASE))

        # Remove duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))

        return entities

    def prepare_medical_classification_data(self) -> Dict[str, Any]:
        """Prepare medical classification training data."""
        logger.info("Preparing medical classification data...")

        # Sample medical classification data
        classification_data = {
            'categories': [
                'cardiology', 'neurology', 'oncology', 'pediatrics',
                'psychiatry', 'dermatology', 'orthopedics', 'gastroenterology'
            ],
            'training_examples': [
                {
                    'text': 'chest pain shortness breath heart palpitations',
                    'category': 'cardiology',
                    'confidence': 0.95
                },
                {
                    'text': 'headache migraine seizure memory loss confusion',
                    'category': 'neurology',
                    'confidence': 0.92
                },
                {
                    'text': 'tumor cancer chemotherapy radiation oncology',
                    'category': 'oncology',
                    'confidence': 0.98
                },
                {
                    'text': 'child fever vaccination pediatric development',
                    'category': 'pediatrics',
                    'confidence': 0.89
                },
                {
                    'text': 'depression anxiety therapy mental health',
                    'category': 'psychiatry',
                    'confidence': 0.94
                },
                {
                    'text': 'skin rash dermatitis eczema acne treatment',
                    'category': 'dermatology',
                    'confidence': 0.91
                },
                {
                    'text': 'bone fracture joint pain arthritis surgery',
                    'category': 'orthopedics',
                    'confidence': 0.93
                },
                {
                    'text': 'stomach pain nausea digestive system gastritis',
                    'category': 'gastroenterology',
                    'confidence': 0.90
                }
            ]
        }

        # Save classification data
        output_file = self.data_dir / "medical_classification.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(classification_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Medical classification data saved to {output_file}")
        return classification_data

    def prepare_medical_similarity_data(self) -> Dict[str, Any]:
        """Prepare medical similarity and embedding data."""
        logger.info("Preparing medical similarity data...")

        # Sample medical documents for similarity
        medical_documents = [
            {
                'id': 'doc_001',
                'title': 'Cardiovascular Disease Prevention',
                'content': 'Regular exercise and healthy diet are crucial for preventing heart disease. Monitoring blood pressure and cholesterol levels helps identify risk factors early.',
                'category': 'cardiology',
                'keywords': ['heart', 'cardiovascular', 'prevention', 'exercise', 'diet']
            },
            {
                'id': 'doc_002',
                'title': 'Diabetes Management Guidelines',
                'content': 'Type 2 diabetes management involves blood glucose monitoring, medication adherence, and lifestyle modifications including diet and exercise.',
                'category': 'endocrinology',
                'keywords': ['diabetes', 'glucose', 'insulin', 'management', 'lifestyle']
            },
            {
                'id': 'doc_003',
                'title': 'Mental Health and Depression',
                'content': 'Depression is a common mental health condition that affects mood, thoughts, and daily activities. Treatment includes therapy and medication.',
                'category': 'psychiatry',
                'keywords': ['depression', 'mental health', 'therapy', 'mood', 'treatment']
            },
            {
                'id': 'doc_004',
                'title': 'Pediatric Vaccination Schedule',
                'content': 'Childhood vaccinations protect against serious diseases. Following the recommended schedule ensures optimal immunity development.',
                'category': 'pediatrics',
                'keywords': ['vaccination', 'children', 'immunity', 'schedule', 'protection']
            },
            {
                'id': 'doc_005',
                'title': 'Skin Cancer Prevention',
                'content': 'Sun protection and regular skin examinations are essential for preventing skin cancer. Early detection improves treatment outcomes.',
                'category': 'dermatology',
                'keywords': ['skin cancer', 'prevention', 'sun protection', 'examination', 'detection']
            }
        ]

        # Process documents for similarity calculation
        processed_docs = []
        for doc in medical_documents:
            cleaned_content = self.clean_text(doc['content'])
            tokens = self.tokenize_and_lemmatize(cleaned_content)
            entities = self.extract_medical_entities(cleaned_content)

            processed_doc = {
                **doc,
                'processed_content': ' '.join(tokens),
                'entities': entities,
                'token_count': len(tokens)
            }
            processed_docs.append(processed_doc)

        # Calculate similarity matrix
        contents = [doc['processed_content'] for doc in processed_docs]
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform(contents)
        similarity_matrix = cosine_similarity(tfidf_matrix)

        similarity_data = {
            'documents': processed_docs,
            'similarity_matrix': similarity_matrix.tolist(),
            'feature_names': vectorizer.get_feature_names_out().tolist(),
            'metadata': {
                'total_documents': len(processed_docs),
                'vocabulary_size': len(vectorizer.vocabulary_),
                'processing_date': pd.Timestamp.now().isoformat()
            }
        }

        # Save similarity data
        output_file = self.data_dir / "medical_similarity.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(similarity_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Medical similarity data saved to {output_file}")
        return similarity_data

    def generate_medical_qa_pairs(self) -> List[Dict[str, str]]:
        """Generate medical Q&A pairs for training."""
        qa_pairs = [
            {
                'question': 'What are the symptoms of diabetes?',
                'answer': 'Common symptoms of diabetes include frequent urination, excessive thirst, unexplained weight loss, fatigue, blurred vision, and slow-healing wounds.',
                'category': 'endocrinology'
            },
            {
                'question': 'How can I prevent heart disease?',
                'answer': 'Heart disease prevention includes regular exercise, healthy diet low in saturated fats, maintaining healthy weight, not smoking, limiting alcohol, and managing stress.',
                'category': 'cardiology'
            },
            {
                'question': 'What should I do for a severe headache?',
                'answer': 'For severe headaches, rest in a quiet dark room, apply cold compress, stay hydrated, and take over-the-counter pain relievers. Seek medical attention if symptoms persist or worsen.',
                'category': 'neurology'
            },
            {
                'question': 'When should children get vaccinated?',
                'answer': 'Children should follow the CDC vaccination schedule, starting at birth with Hepatitis B, then continuing with vaccines at 2, 4, 6, 12-15 months, and beyond according to pediatric guidelines.',
                'category': 'pediatrics'
            },
            {
                'question': 'How do I know if a mole is cancerous?',
                'answer': 'Watch for ABCDE signs: Asymmetry, Border irregularity, Color variation, Diameter larger than 6mm, and Evolving changes. Consult a dermatologist for suspicious moles.',
                'category': 'dermatology'
            }
        ]

        return qa_pairs

    def run_full_preparation(self):
        """Run the complete medical data preparation pipeline."""
        logger.info("Starting medical data preparation pipeline...")

        try:
            # Prepare classification data
            classification_data = self.prepare_medical_classification_data()

            # Prepare similarity data
            similarity_data = self.prepare_medical_similarity_data()

            # Generate Q&A pairs
            qa_pairs = self.generate_medical_qa_pairs()

            # Save Q&A pairs
            qa_file = self.data_dir / "medical_qa_pairs.json"
            with open(qa_file, 'w', encoding='utf-8') as f:
                json.dump(qa_pairs, f, indent=2, ensure_ascii=False)

            logger.info("Medical data preparation completed successfully!")

            # Print summary
            print("\n" + "="*50)
            print("MEDICAL DATA PREPARATION SUMMARY")
            print("="*50)
            print(f"Classification categories: {len(classification_data['categories'])}")
            print(f"Training examples: {len(classification_data['training_examples'])}")
            print(f"Medical documents: {len(similarity_data['documents'])}")
            print(f"Q&A pairs: {len(qa_pairs)}")
            print(f"Data directory: {self.data_dir.absolute()}")
            print("="*50)

        except Exception as e:
            logger.error(f"Error during data preparation: {str(e)}")
            raise


def main():
    """Main function to run medical data preparation."""
    try:
        preprocessor = MedicalDataPreprocessor()
        preprocessor.run_full_preparation()
    except Exception as e:
        logger.error(f"Failed to prepare medical data: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())