"""
Medical Data Preprocessing Pipeline
Custom data science pipeline for medical text processing and augmentation
"""

import numpy as np
import re
import nltk
import spacy
from typing import List, Dict, Any, Tuple, Optional
import logging
from pathlib import Path
import json
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from transformers import AutoTokenizer
from collections import Counter
import string

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
except Exception:
    pass


class MedicalTextPreprocessor:
    """
    Comprehensive medical text preprocessing pipeline
    """

    def __init__(self, language_model: str = "en_core_web_sm"):
        self.language_model = language_model
        self.nlp = None
        self.medical_abbreviations = self._load_medical_abbreviations()
        self.drug_name_patterns = self._compile_drug_patterns()

        # Initialize spaCy model
        try:
            self.nlp = spacy.load(language_model)
        except OSError:
            logger.warning(f"SpaCy model {language_model} not found. "
                           f"Using basic preprocessing.")
            self.nlp = None

    def _load_medical_abbreviations(self) -> Dict[str, str]:
        """Load common medical abbreviations and their expansions"""
        return {
            'mg': 'milligrams',
            'ml': 'milliliters',
            'mcg': 'micrograms',
            'bid': 'twice daily',
            'tid': 'three times daily',
            'qid': 'four times daily',
            'qd': 'once daily',
            'prn': 'as needed',
            'po': 'by mouth',
            'iv': 'intravenous',
            'im': 'intramuscular',
            'sc': 'subcutaneous',
            'od': 'right eye',
            'os': 'left eye',
            'ou': 'both eyes',
            'ad': 'right ear',
            'as': 'left ear',
            'au': 'both ears',
            'nsaid': 'nonsteroidal anti-inflammatory drug',
            'ace': 'angiotensin converting enzyme',
            'arb': 'angiotensin receptor blocker',
            'ssri': 'selective serotonin reuptake inhibitor',
            'snri': 'serotonin norepinephrine reuptake inhibitor',
            'maoi': 'monoamine oxidase inhibitor',
            'otc': 'over the counter',
            'rx': 'prescription',
            'dx': 'diagnosis',
            'hx': 'history',
            'sx': 'symptoms',
            'tx': 'treatment'
        }

    def _compile_drug_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for drug name recognition"""
        patterns = [
            re.compile(r'\b\w+cillin\b', re.IGNORECASE),  # Penicillins
            re.compile(r'\b\w+mycin\b', re.IGNORECASE),   # Mycins
            re.compile(r'\b\w+pril\b', re.IGNORECASE),    # ACE inhibitors
            re.compile(r'\b\w+sartan\b', re.IGNORECASE),  # ARBs
            re.compile(r'\b\w+olol\b', re.IGNORECASE),    # Beta blockers
            re.compile(r'\b\w+pine\b', re.IGNORECASE),    # Calcium channel blockers
            re.compile(r'\b\w+statin\b', re.IGNORECASE),  # Statins
            re.compile(r'\b\w+zole\b', re.IGNORECASE),    # Proton pump inhibitors
        ]
        return patterns

    def clean_text(self, text: str) -> str:
        """Basic text cleaning"""
        if not text or not isinstance(text, str):
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters but keep medical symbols
        text = re.sub(r'[^\w\s\-\.\,\;\:\(\)\[\]\/\%\+\=\<\>\&]', '', text)

        # Normalize case for abbreviations
        for abbrev, expansion in self.medical_abbreviations.items():
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)

        return text.strip()

    def extract_medical_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract medical entities using spaCy NER"""
        entities = {
            'drugs': [],
            'conditions': [],
            'dosages': [],
            'frequencies': []
        }

        if not self.nlp:
            return entities

        try:
            doc = self.nlp(text)

            # Extract named entities
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'ORG']:
                    # Might be drug names
                    entities['drugs'].append(ent.text)
                elif ent.label_ in ['QUANTITY', 'CARDINAL']:
                    # Might be dosages
                    entities['dosages'].append(ent.text)

            # Extract drug names using patterns
            for pattern in self.drug_name_patterns:
                matches = pattern.findall(text)
                entities['drugs'].extend(matches)

            # Extract dosage patterns
            dosage_patterns = [
                r'\d+\s*(?:mg|ml|mcg|g|units?)',
                r'\d+\s*(?:milligrams?|milliliters?|micrograms?|grams?)',
            ]

            for pattern in dosage_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                entities['dosages'].extend(matches)

            # Extract frequency patterns
            frequency_patterns = [
                r'(?:once|twice|three times?|four times?)\s*(?:daily|per day|a day)',
                r'(?:bid|tid|qid|qd|prn)',
                r'every\s*\d+\s*hours?'
            ]

            for pattern in frequency_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                entities['frequencies'].extend(matches)

        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")

        # Remove duplicates and clean
        for key in entities:
            entities[key] = list(set([item.strip() for item in entities[key] if item.strip()]))

        return entities

    def tokenize_medical_text(self, text: str,
                              tokenizer_name: str = "dmis-lab/biobert-base-cased-v1.1") -> Dict[str, Any]:
        """Tokenize medical text using BioBERT tokenizer"""
        try:
            tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

            # Clean text first
            cleaned_text = self.clean_text(text)

            # Tokenize
            tokens = tokenizer.tokenize(cleaned_text)
            token_ids = tokenizer.convert_tokens_to_ids(tokens)

            return {
                'original_text': text,
                'cleaned_text': cleaned_text,
                'tokens': tokens,
                'token_ids': token_ids,
                'token_count': len(tokens)
            }

        except Exception as e:
            logger.error(f"Tokenization failed: {str(e)}")
            return {
                'original_text': text,
                'cleaned_text': text,
                'tokens': [],
                'token_ids': [],
                'token_count': 0
            }

    def preprocess_dataset(self, texts: List[str],
                           labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Preprocess a dataset of medical texts"""
        processed_data = {
            'texts': [],
            'cleaned_texts': [],
            'entities': [],
            'statistics': {}
        }

        if labels:
            processed_data['labels'] = labels

        # Process each text
        for text in texts:
            cleaned = self.clean_text(text)
            entities = self.extract_medical_entities(cleaned)

            processed_data['texts'].append(text)
            processed_data['cleaned_texts'].append(cleaned)
            processed_data['entities'].append(entities)

        # Calculate statistics
        processed_data['statistics'] = self._calculate_dataset_statistics(processed_data)

        return processed_data

    def _calculate_dataset_statistics(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate dataset statistics"""
        texts = processed_data['cleaned_texts']
        entities_list = processed_data['entities']

        # Text length statistics
        text_lengths = [len(text.split()) for text in texts]

        # Entity statistics
        all_drugs = []
        all_conditions = []
        all_dosages = []

        for entities in entities_list:
            all_drugs.extend(entities.get('drugs', []))
            all_conditions.extend(entities.get('conditions', []))
            all_dosages.extend(entities.get('dosages', []))

        stats = {
            'total_texts': len(texts),
            'avg_text_length': np.mean(text_lengths) if text_lengths else 0,
            'min_text_length': min(text_lengths) if text_lengths else 0,
            'max_text_length': max(text_lengths) if text_lengths else 0,
            'total_unique_drugs': len(set(all_drugs)),
            'total_unique_conditions': len(set(all_conditions)),
            'total_unique_dosages': len(set(all_dosages)),
            'most_common_drugs': Counter(all_drugs).most_common(10),
            'most_common_conditions': Counter(all_conditions).most_common(10)
        }

        if 'labels' in processed_data:
            label_counts = Counter(processed_data['labels'])
            stats['label_distribution'] = dict(label_counts)
            stats['num_classes'] = len(label_counts)

        return stats


class MedicalDataAugmentor:
    """
    Data augmentation techniques for medical text
    """

    def __init__(self):
        self.synonym_dict = self._load_medical_synonyms()
        self.augmentation_techniques = [
            'synonym_replacement',
            'random_insertion',
            'random_swap',
            'random_deletion'
        ]

    def _load_medical_synonyms(self) -> Dict[str, List[str]]:
        """Load medical synonyms for augmentation"""
        return {
            'pain': ['ache', 'discomfort', 'soreness', 'hurt'],
            'medication': ['medicine', 'drug', 'pharmaceutical', 'remedy'],
            'treatment': ['therapy', 'intervention', 'care', 'management'],
            'doctor': ['physician', 'clinician', 'healthcare provider', 'medical professional'],
            'patient': ['individual', 'person', 'client', 'case'],
            'symptom': ['sign', 'indication', 'manifestation', 'feature'],
            'condition': ['disorder', 'disease', 'illness', 'ailment'],
            'severe': ['serious', 'acute', 'intense', 'extreme'],
            'mild': ['slight', 'minor', 'gentle', 'weak'],
            'chronic': ['persistent', 'long-term', 'ongoing', 'continuous'],
            'acute': ['sudden', 'sharp', 'severe', 'immediate']
        }

    def synonym_replacement(self, text: str, n: int = 1) -> str:
        """Replace n words with synonyms"""
        words = text.split()
        new_words = words.copy()

        # Find words that have synonyms
        replaceable_words = []
        for i, word in enumerate(words):
            word_lower = word.lower().strip(string.punctuation)
            if word_lower in self.synonym_dict:
                replaceable_words.append(i)

        # Replace n random words
        if replaceable_words:
            indices_to_replace = np.random.choice(
                replaceable_words,
                size=min(n, len(replaceable_words)),
                replace=False
            )

            for idx in indices_to_replace:
                word = words[idx].lower().strip(string.punctuation)
                synonyms = self.synonym_dict[word]
                new_word = np.random.choice(synonyms)
                new_words[idx] = new_word

        return ' '.join(new_words)

    def random_insertion(self, text: str, n: int = 1) -> str:
        """Insert n random synonyms"""
        words = text.split()

        for _ in range(n):
            # Choose a random word that has synonyms
            available_words = [w for w in words if w.lower().strip(string.punctuation) in self.synonym_dict]
            if available_words:
                word = np.random.choice(available_words)
                word_clean = word.lower().strip(string.punctuation)
                synonyms = self.synonym_dict[word_clean]
                synonym = np.random.choice(synonyms)

                # Insert at random position
                insert_idx = np.random.randint(0, len(words) + 1)
                words.insert(insert_idx, synonym)

        return ' '.join(words)

    def random_swap(self, text: str, n: int = 1) -> str:
        """Swap n pairs of words"""
        words = text.split()

        for _ in range(n):
            if len(words) >= 2:
                idx1, idx2 = np.random.choice(len(words), size=2, replace=False)
                words[idx1], words[idx2] = words[idx2], words[idx1]

        return ' '.join(words)

    def random_deletion(self, text: str, p: float = 0.1) -> str:
        """Delete words with probability p"""
        words = text.split()

        # Don't delete if text is too short
        if len(words) <= 3:
            return text

        new_words = []
        for word in words:
            if np.random.random() > p:
                new_words.append(word)

        # Ensure we don't delete everything
        if not new_words:
            return text

        return ' '.join(new_words)

    def augment_text(self, text: str, num_augmentations: int = 1, techniques: Optional[List[str]] = None) -> List[str]:
        """Generate augmented versions of text"""
        if techniques is None:
            techniques = self.augmentation_techniques

        augmented_texts = []

        for _ in range(num_augmentations):
            # Choose random technique
            technique = np.random.choice(techniques)

            if technique == 'synonym_replacement':
                augmented = self.synonym_replacement(text, n=np.random.randint(1, 4))
            elif technique == 'random_insertion':
                augmented = self.random_insertion(text, n=np.random.randint(1, 3))
            elif technique == 'random_swap':
                augmented = self.random_swap(text, n=np.random.randint(1, 3))
            elif technique == 'random_deletion':
                augmented = self.random_deletion(text, p=np.random.uniform(0.05, 0.15))
            else:
                augmented = text

            augmented_texts.append(augmented)

        return augmented_texts

    def augment_dataset(self, texts: List[str], labels: List[str], augmentation_factor: int = 2) -> Tuple[List[str], List[str]]:
        """Augment entire dataset"""
        augmented_texts = []
        augmented_labels = []

        for text, label in zip(texts, labels):
            # Keep original
            augmented_texts.append(text)
            augmented_labels.append(label)

            # Generate augmentations
            aug_texts = self.augment_text(text, num_augmentations=augmentation_factor)
            augmented_texts.extend(aug_texts)
            augmented_labels.extend([label] * len(aug_texts))

        return augmented_texts, augmented_labels


class MedicalDatasetBuilder:
    """
    Build training datasets for medical ML models
    """

    def __init__(self):
        self.preprocessor = MedicalTextPreprocessor()
        self.augmentor = MedicalDataAugmentor()

    def create_classification_dataset(self,
                                     raw_data: List[Dict[str, Any]],
                                     text_column: str = 'text',
                                     label_column: str = 'label',
                                     test_size: float = 0.2,
                                     augment: bool = True,
                                     augmentation_factor: int = 2) -> Dict[str, Any]:
        """Create classification dataset"""

        # Extract texts and labels
        texts = [item[text_column] for item in raw_data]
        labels = [item[label_column] for item in raw_data]

        # Preprocess
        processed_data = self.preprocessor.preprocess_dataset(texts, labels)

        # Split data
        train_texts, test_texts, train_labels, test_labels = train_test_split(
            processed_data['cleaned_texts'],
            processed_data['labels'],
            test_size=test_size,
            stratify=processed_data['labels'],
            random_state=42
        )

        # Augment training data
        if augment:
            train_texts, train_labels = self.augmentor.augment_dataset(
                train_texts, train_labels, augmentation_factor
            )

        # Encode labels
        label_encoder = LabelEncoder()
        train_labels_encoded = label_encoder.fit_transform(train_labels)
        test_labels_encoded = label_encoder.transform(test_labels)

        return {
            'train': {
                'texts': train_texts,
                'labels': train_labels,
                'labels_encoded': train_labels_encoded
            },
            'test': {
                'texts': test_texts,
                'labels': test_labels,
                'labels_encoded': test_labels_encoded
            },
            'label_encoder': label_encoder,
            'statistics': processed_data['statistics'],
            'num_classes': len(label_encoder.classes_),
            'class_names': label_encoder.classes_.tolist()
        }

    def create_similarity_dataset(self,
                                  texts: List[str],
                                  similarity_threshold: float = 0.7,
                                  num_pairs: int = 1000) -> List[Tuple[str, str, float]]:
        """Create similarity dataset from texts"""

        # Preprocess texts
        processed_data = self.preprocessor.preprocess_dataset(texts)
        clean_texts = processed_data['cleaned_texts']

        pairs = []

        # Generate positive pairs (similar)
        num_positive = num_pairs // 2
        for _ in range(num_positive):
            # Choose random text
            idx = np.random.randint(0, len(clean_texts))
            text1 = clean_texts[idx]

            # Create augmented version (should be similar)
            augmented = self.augmentor.augment_text(text1, num_augmentations=1)[0]
            similarity = np.random.uniform(similarity_threshold, 1.0)

            pairs.append((text1, augmented, similarity))

        # Generate negative pairs (dissimilar)
        num_negative = num_pairs - num_positive
        for _ in range(num_negative):
            # Choose two random different texts
            idx1, idx2 = np.random.choice(len(clean_texts), size=2, replace=False)
            text1 = clean_texts[idx1]
            text2 = clean_texts[idx2]

            similarity = np.random.uniform(0.0, similarity_threshold)
            pairs.append((text1, text2, similarity))

        return pairs

    def save_dataset(self, dataset: Dict[str, Any], save_path: str):
        """Save dataset to disk"""
        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)

        # Save as JSON
        with open(save_path / 'dataset.json', 'w') as f:
            # Convert numpy arrays to lists for JSON serialization
            dataset_copy = dataset.copy()
            if 'train' in dataset_copy:
                dataset_copy['train']['labels_encoded'] = (dataset_copy['train']['labels_encoded'].tolist())
            if 'test' in dataset_copy:
                dataset_copy['test']['labels_encoded'] = (dataset_copy['test']['labels_encoded'].tolist())

            json.dump(dataset_copy, f, indent=2)

        # Save label encoder separately
        if 'label_encoder' in dataset:
            import joblib
            joblib.dump(dataset['label_encoder'], save_path / 'label_encoder.pkl')

        logger.info(f"Dataset saved to {save_path}")

    def load_dataset(self, load_path: str) -> Dict[str, Any]:
        """Load dataset from disk"""
        load_path = Path(load_path)

        # Load JSON
        with open(load_path / 'dataset.json', 'r') as f:
            dataset = json.load(f)

        # Convert lists back to numpy arrays
        if 'train' in dataset:
            dataset['train']['labels_encoded'] = np.array(
                dataset['train']['labels_encoded']
            )
        if 'test' in dataset:
            dataset['test']['labels_encoded'] = np.array(
                dataset['test']['labels_encoded']
            )

        # Load label encoder
        label_encoder_path = load_path / 'label_encoder.pkl'
        if label_encoder_path.exists():
            import joblib
            dataset['label_encoder'] = joblib.load(label_encoder_path)

        logger.info(f"Dataset loaded from {load_path}")
        return dataset
