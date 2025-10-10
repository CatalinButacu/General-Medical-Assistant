"""
BioBERT Fine-tuning Pipeline
Custom implementation for fine-tuning BioBERT on medical datasets
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer, AutoModel, AutoConfig,
    get_linear_schedule_with_warmup,
    AdamW
)
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from typing import Dict, List, Tuple, Optional, Any
import logging
import mlflow
import mlflow.pytorch
from pathlib import Path
from tqdm import tqdm
import time
import matplotlib.pyplot as plt

from .data_preprocessing import MedicalTextPreprocessor, MedicalDatasetBuilder

logger = logging.getLogger(__name__)


class MedicalBERTDataset(Dataset):
    """
    Dataset class for medical BERT fine-tuning
    """

    def __init__(self,
                 texts: List[str],
                 labels: List[int],
                 tokenizer: AutoTokenizer,
                 max_length: int = 512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]

        # Tokenize
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


class MedicalSimilarityDataset(Dataset):
    """
    Dataset for medical text similarity fine-tuning
    """

    def __init__(self,
                 text_pairs: List[Tuple[str, str]],
                 similarities: List[float],
                 tokenizer: AutoTokenizer,
                 max_length: int = 512):
        self.text_pairs = text_pairs
        self.similarities = similarities
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.text_pairs)

    def __getitem__(self, idx):
        text1, text2 = self.text_pairs[idx]
        similarity = self.similarities[idx]

        # Tokenize both texts
        encoding1 = self.tokenizer(
            text1,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )

        encoding2 = self.tokenizer(
            text2,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )

        return {
            'input_ids_1': encoding1['input_ids'].flatten(),
            'attention_mask_1': encoding1['attention_mask'].flatten(),
            'input_ids_2': encoding2['input_ids'].flatten(),
            'attention_mask_2': encoding2['attention_mask'].flatten(),
            'similarity': torch.tensor(similarity, dtype=torch.float)
        }


class MedicalBERTClassifier(nn.Module):
    """
    BioBERT-based classifier for medical text classification
    """

    def __init__(self,
                 model_name: str = "dmis-lab/biobert-base-cased-v1.1",
                 num_classes: int = 2,
                 dropout_rate: float = 0.3,
                 freeze_bert: bool = False):
        super(MedicalBERTClassifier, self).__init__()

        self.model_name = model_name
        self.num_classes = num_classes

        # Load BioBERT
        self.config = AutoConfig.from_pretrained(model_name)
        self.bert = AutoModel.from_pretrained(model_name, config=self.config)

        # Freeze BERT parameters if specified
        if freeze_bert:
            for param in self.bert.parameters():
                param.requires_grad = False

        # Classification head
        self.dropout = nn.Dropout(dropout_rate)
        self.classifier = nn.Linear(self.config.hidden_size, num_classes)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize classifier weights"""
        nn.init.xavier_uniform_(self.classifier.weight)
        nn.init.zeros_(self.classifier.bias)

    def forward(self, input_ids, attention_mask):
        # Get BERT outputs
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        # Use [CLS] token representation
        pooled_output = outputs.pooler_output

        # Apply dropout and classify
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)

        return logits


class MedicalBERTSimilarity(nn.Module):
    """
    BioBERT-based model for medical text similarity
    """

    def __init__(self,
                 model_name: str = "dmis-lab/biobert-base-cased-v1.1",
                 dropout_rate: float = 0.3,
                 freeze_bert: bool = False):
        super(MedicalBERTSimilarity, self).__init__()

        self.model_name = model_name

        # Load BioBERT
        self.config = AutoConfig.from_pretrained(model_name)
        self.bert = AutoModel.from_pretrained(model_name, config=self.config)

        # Freeze BERT parameters if specified
        if freeze_bert:
            for param in self.bert.parameters():
                param.requires_grad = False

        # Similarity head
        self.dropout = nn.Dropout(dropout_rate)
        self.similarity_head = nn.Sequential(
            # The input is a concatenation of the two embeddings, their absolute difference,
            # and their element-wise product.
            nn.Linear(self.config.hidden_size * 4, 256),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize similarity head weights"""
        for module in self.similarity_head:
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)

    def forward(self, input_ids_1, attention_mask_1, input_ids_2, attention_mask_2):
        # Get embeddings for both texts
        outputs1 = self.bert(input_ids=input_ids_1, attention_mask=attention_mask_1)
        outputs2 = self.bert(input_ids=input_ids_2, attention_mask=attention_mask_2)

        # Use [CLS] token representations
        emb1 = outputs1.pooler_output
        emb2 = outputs2.pooler_output

        # Apply dropout
        emb1 = self.dropout(emb1)
        emb2 = self.dropout(emb2)

        # Create similarity features
        concat_emb = torch.cat([emb1, emb2], dim=1)
        abs_diff = torch.abs(emb1 - emb2)
        element_wise = emb1 * emb2

        # Combine features
        combined = torch.cat([concat_emb, abs_diff, element_wise], dim=1)

        # Predict similarity
        similarity = self.similarity_head(combined)

        return similarity.squeeze()


class BioBERTFineTuner:
    """
    Main class for fine-tuning BioBERT models
    """

    def __init__(self,
                 model_name: str = "dmis-lab/biobert-base-cased-v1.1",
                 device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Initialize components
        self.preprocessor = MedicalTextPreprocessor()
        self.dataset_builder = MedicalDatasetBuilder()

        logger.info(f"BioBERT Fine-tuner initialized with device: {self.device}")

    def fine_tune_classifier(self,
                           train_texts: List[str],
                           train_labels: List[int],
                           val_texts: List[str],
                           val_labels: List[int],
                           num_classes: int,
                           config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fine-tune BioBERT for classification
        """

        # Start MLflow run
        with mlflow.start_run(run_name=f"biobert_classification_{int(time.time())}"):

            # Log parameters
            mlflow.log_params(config)

            # Create datasets
            train_dataset = MedicalBERTDataset(
                train_texts, train_labels, self.tokenizer, config['max_length']
            )
            val_dataset = MedicalBERTDataset(
                val_texts, val_labels, self.tokenizer, config['max_length']
            )

            # Create data loaders
            train_loader = DataLoader(
                train_dataset,
                batch_size=config['batch_size'],
                shuffle=True,
                num_workers=0  # Set to 0 for Windows compatibility
            )
            val_loader = DataLoader(
                val_dataset,
                batch_size=config['batch_size'],
                shuffle=False,
                num_workers=0
            )

            # Initialize model
            model = MedicalBERTClassifier(
                model_name=self.model_name,
                num_classes=num_classes,
                dropout_rate=config.get('dropout_rate', 0.3),
                freeze_bert=config.get('freeze_bert', False)
            ).to(self.device)

            # Initialize optimizer and scheduler
            optimizer = AdamW(
                model.parameters(),
                lr=config['learning_rate'],
                weight_decay=config.get('weight_decay', 0.01)
            )

            total_steps = len(train_loader) * config['num_epochs']
            scheduler = get_linear_schedule_with_warmup(
                optimizer,
                num_warmup_steps=int(0.1 * total_steps),
                num_training_steps=total_steps
            )

            # Loss function
            criterion = nn.CrossEntropyLoss()

            # Training loop
            best_val_acc = 0
            training_history = {
                'train_loss': [],
                'train_acc': [],
                'val_loss': [],
                'val_acc': []
            }

            for epoch in range(config['num_epochs']):
                logger.info(f"Epoch {epoch + 1}/{config['num_epochs']}")

                # Training phase
                train_loss, train_acc = self._train_epoch(
                    model, train_loader, optimizer, scheduler, criterion
                )

                # Validation phase
                val_loss, val_acc = self._validate_epoch(
                    model, val_loader, criterion
                )

                # Log metrics
                mlflow.log_metrics({
                    'train_loss': train_loss,
                    'train_acc': train_acc,
                    'val_loss': val_loss,
                    'val_acc': val_acc
                }, step=epoch)

                # Save history
                training_history['train_loss'].append(train_loss)
                training_history['train_acc'].append(train_acc)
                training_history['val_loss'].append(val_loss)
                training_history['val_acc'].append(val_acc)

                # Save best model
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    self._save_model(model, 'best_classifier.pth')
                    mlflow.log_metric('best_val_acc', best_val_acc)

                logger.info(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}")
                logger.info(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")

            # Final evaluation
            final_metrics = self._evaluate_classifier(model, val_loader, val_labels)
            mlflow.log_metrics(final_metrics)

            # Log model
            mlflow.pytorch.log_model(model, "model")

            # Plot training curves
            self._plot_training_curves(training_history)

            return {
                'model': model,
                'training_history': training_history,
                'final_metrics': final_metrics,
                'best_val_acc': best_val_acc
            }

    def fine_tune_similarity(self,
                           text_pairs: List[Tuple[str, str]],
                           similarities: List[float],
                           val_pairs: List[Tuple[str, str]],
                           val_similarities: List[float],
                           config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fine-tune BioBERT for similarity prediction
        """

        with mlflow.start_run(run_name=f"biobert_similarity_{int(time.time())}"):

            # Log parameters
            mlflow.log_params(config)

            # Create datasets
            train_dataset = MedicalSimilarityDataset(
                text_pairs, similarities, self.tokenizer, config['max_length']
            )
            val_dataset = MedicalSimilarityDataset(
                val_pairs, val_similarities, self.tokenizer, config['max_length']
            )

            # Create data loaders
            train_loader = DataLoader(
                train_dataset,
                batch_size=config['batch_size'],
                shuffle=True,
                num_workers=0
            )
            val_loader = DataLoader(
                val_dataset,
                batch_size=config['batch_size'],
                shuffle=False,
                num_workers=0
            )

            # Initialize model
            model = MedicalBERTSimilarity(
                model_name=self.model_name,
                dropout_rate=config.get('dropout_rate', 0.3),
                freeze_bert=config.get('freeze_bert', False)
            ).to(self.device)

            # Initialize optimizer and scheduler
            optimizer = AdamW(
                model.parameters(),
                lr=config['learning_rate'],
                weight_decay=config.get('weight_decay', 0.01)
            )

            total_steps = len(train_loader) * config['num_epochs']
            scheduler = get_linear_schedule_with_warmup(
                optimizer,
                num_warmup_steps=int(0.1 * total_steps),
                num_training_steps=total_steps
            )

            # Loss function
            criterion = nn.MSELoss()

            # Training loop
            best_val_loss = float('inf')
            training_history = {
                'train_loss': [],
                'val_loss': [],
                'val_correlation': []
            }

            for epoch in range(config['num_epochs']):
                logger.info(f"Epoch {epoch + 1}/{config['num_epochs']}")

                # Training phase
                train_loss = self._train_similarity_epoch(
                    model, train_loader, optimizer, scheduler, criterion
                )

                # Validation phase
                val_loss, val_correlation = self._validate_similarity_epoch(
                    model, val_loader, criterion
                )

                # Log metrics
                mlflow.log_metrics({
                    'train_loss': train_loss,
                    'val_loss': val_loss,
                    'val_correlation': val_correlation
                }, step=epoch)

                # Save history
                training_history['train_loss'].append(train_loss)
                training_history['val_loss'].append(val_loss)
                training_history['val_correlation'].append(val_correlation)

                # Save best model
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    self._save_model(model, 'best_similarity.pth')
                    mlflow.log_metric('best_val_loss', best_val_loss)

                logger.info(f"Train Loss: {train_loss:.4f}")
                logger.info(f"Val Loss: {val_loss:.4f}, "
                            f"Val Correlation: {val_correlation:.4f}")

            # Log model
            mlflow.pytorch.log_model(model, "model")

            return {
                'model': model,
                'training_history': training_history,
                'best_val_loss': best_val_loss
            }

    def _train_epoch(self, model, train_loader, optimizer, scheduler, criterion):
        """Train for one epoch"""
        model.train()
        total_loss = 0
        correct_predictions = 0
        total_predictions = 0

        progress_bar = tqdm(train_loader, desc="Training")

        for batch in progress_bar:
            # Move to device
            input_ids = batch['input_ids'].to(self.device)
            attention_mask = batch['attention_mask'].to(self.device)
            labels = batch['labels'].to(self.device)

            # Forward pass
            optimizer.zero_grad()
            logits = model(input_ids, attention_mask)
            loss = criterion(logits, labels)

            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            # Calculate accuracy
            predictions = torch.argmax(logits, dim=1)
            correct_predictions += (predictions == labels).sum().item()
            total_predictions += labels.size(0)

            total_loss += loss.item()

            # Update progress bar
            progress_bar.set_postfix({
                'loss': loss.item(),
                'acc': correct_predictions / total_predictions
            })

        avg_loss = total_loss / len(train_loader)
        accuracy = correct_predictions / total_predictions

        return avg_loss, accuracy

    def _validate_epoch(self, model, val_loader, criterion):
        """Validate for one epoch"""
        model.eval()
        total_loss = 0
        correct_predictions = 0
        total_predictions = 0

        with torch.no_grad():
            for batch in val_loader:
                # Move to device
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)

                # Forward pass
                logits = model(input_ids, attention_mask)
                loss = criterion(logits, labels)

                # Calculate accuracy
                predictions = torch.argmax(logits, dim=1)
                correct_predictions += (predictions == labels).sum().item()
                total_predictions += labels.size(0)

                total_loss += loss.item()

        avg_loss = total_loss / len(val_loader)
        accuracy = correct_predictions / total_predictions

        return avg_loss, accuracy

    def _train_similarity_epoch(self, model, train_loader, optimizer, scheduler, criterion):
        """Train similarity model for one epoch"""
        model.train()
        total_loss = 0

        progress_bar = tqdm(train_loader, desc="Training Similarity")

        for batch in progress_bar:
            # Move to device
            input_ids_1 = batch['input_ids_1'].to(self.device)
            attention_mask_1 = batch['attention_mask_1'].to(self.device)
            input_ids_2 = batch['input_ids_2'].to(self.device)
            attention_mask_2 = batch['attention_mask_2'].to(self.device)
            similarities = batch['similarity'].to(self.device)

            # Forward pass
            optimizer.zero_grad()
            predicted_similarities = model(
                input_ids_1, attention_mask_1,
                input_ids_2, attention_mask_2
            )
            loss = criterion(predicted_similarities, similarities)

            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()

            # Update progress bar
            progress_bar.set_postfix({'loss': loss.item()})

        avg_loss = total_loss / len(train_loader)
        return avg_loss

    def _validate_similarity_epoch(self, model, val_loader, criterion):
        """Validate similarity model for one epoch"""
        model.eval()
        total_loss = 0
        predictions = []
        targets = []

        with torch.no_grad():
            for batch in val_loader:
                # Move to device
                input_ids_1 = batch['input_ids_1'].to(self.device)
                attention_mask_1 = batch['attention_mask_1'].to(self.device)
                input_ids_2 = batch['input_ids_2'].to(self.device)
                attention_mask_2 = batch['attention_mask_2'].to(self.device)
                similarities = batch['similarity'].to(self.device)

                # Forward pass
                predicted_similarities = model(
                    input_ids_1, attention_mask_1,
                    input_ids_2, attention_mask_2
                )
                loss = criterion(predicted_similarities, similarities)

                total_loss += loss.item()

                # Collect predictions and targets
                predictions.extend(predicted_similarities.cpu().numpy())
                targets.extend(similarities.cpu().numpy())

        avg_loss = total_loss / len(val_loader)

        # Calculate correlation
        correlation = np.corrcoef(predictions, targets)[0, 1]
        if np.isnan(correlation):
            correlation = 0.0

        return avg_loss, correlation

    def _evaluate_classifier(self, model, val_loader, true_labels):
        """Comprehensive evaluation of classifier"""
        model.eval()
        all_predictions = []
        all_probabilities = []

        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)

                logits = model(input_ids, attention_mask)
                probabilities = torch.softmax(logits, dim=1)
                predictions = torch.argmax(logits, dim=1)

                all_predictions.extend(predictions.cpu().numpy())
                all_probabilities.extend(probabilities.cpu().numpy())

        # Calculate metrics
        accuracy = accuracy_score(true_labels, all_predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            true_labels, all_predictions, average='weighted'
        )

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1
        }

    def _save_model(self, model, filename):
        """Save model checkpoint"""
        save_path = Path('models') / filename
        save_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), save_path)
        logger.info(f"Model saved to {save_path}")

    def _plot_training_curves(self, history):
        """Plot training curves"""
        fig, axes = plt.subplots(1, 2, figsize=(15, 5))

        # Loss curves
        axes[0].plot(history['train_loss'], label='Train Loss')
        axes[0].plot(history['val_loss'], label='Validation Loss')
        axes[0].set_title('Training and Validation Loss')
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Loss')
        axes[0].legend()
        axes[0].grid(True)

        # Accuracy curves (if available)
        if 'train_acc' in history:
            axes[1].plot(history['train_acc'], label='Train Accuracy')
            axes[1].plot(history['val_acc'], label='Validation Accuracy')
            axes[1].set_title('Training and Validation Accuracy')
            axes[1].set_xlabel('Epoch')
            axes[1].set_ylabel('Accuracy')
            axes[1].legend()
            axes[1].grid(True)

        plt.tight_layout()
        plt.savefig('training_curves.png', dpi=300, bbox_inches='tight')
        mlflow.log_artifact('training_curves.png')
        plt.close()


def create_default_config() -> Dict[str, Any]:
    """Create default training configuration"""
    return {
        'batch_size': 16,
        'learning_rate': 2e-5,
        'num_epochs': 3,
        'max_length': 512,
        'dropout_rate': 0.3,
        'weight_decay': 0.01,
        'freeze_bert': False,
        'warmup_ratio': 0.1
    }
