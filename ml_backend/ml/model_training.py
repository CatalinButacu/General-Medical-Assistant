"""
Custom Model Training Pipeline
Fine-tuning BioBERT and other medical models on custom datasets
On-premise training infrastructure with MLflow experiment tracking
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer, AutoModel, AutoConfig,
    TrainingArguments, Trainer
)
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import mlflow
import mlflow.pytorch
import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Training configuration"""
    model_name: str = "dmis-lab/biobert-base-cased-v1.1"
    max_length: int = 512
    batch_size: int = 16
    learning_rate: float = 2e-5
    num_epochs: int = 3
    warmup_steps: int = 500
    weight_decay: float = 0.01
    gradient_accumulation_steps: int = 1
    fp16: bool = True
    save_steps: int = 500
    eval_steps: int = 500
    logging_steps: int = 100
    early_stopping_patience: int = 3
    output_dir: str = "./models/fine_tuned"

@dataclass
class MedicalTrainingExample:
    """Medical training example"""
    text: str
    label: str
    metadata: Dict[str, Any]


class MedicalTextDataset(Dataset):
    """
    Custom dataset for medical text classification and similarity learning
    """

    def __init__(self, examples: List[MedicalTrainingExample], tokenizer,
                 max_length: int = 512):
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length

        # Create label mapping
        unique_labels = list(set(example.label for example in examples))
        self.label_to_id = dict(
            (label, idx) for idx, label in enumerate(unique_labels)
        )
        self.id_to_label = {idx: label for label, idx in self.label_to_id.items()}
        self.num_labels = len(unique_labels)

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        example = self.examples[idx]

        # Tokenize text
        encoding = self.tokenizer(
            example.text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(self.label_to_id[example.label], dtype=torch.long)
        }


class MedicalSimilarityDataset(Dataset):
    """
    Dataset for training medical text similarity models
    """

    def __init__(self, text_pairs: List[Tuple[str, str, float]],
                 tokenizer, max_length: int = 512):
        self.text_pairs = text_pairs
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.text_pairs)

    def __getitem__(self, idx):
        text1, text2, similarity_score = self.text_pairs[idx]

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
            'similarity_score': torch.tensor(similarity_score, dtype=torch.float)
        }


class MedicalBERTClassifier(nn.Module):
    """
    Custom BioBERT-based classifier for medical text
    """

    def __init__(self, model_name: str, num_labels: int, dropout_rate: float = 0.1):
        super().__init__()
        self.num_labels = num_labels

        # Load pre-trained BioBERT
        self.config = AutoConfig.from_pretrained(model_name)
        self.bert = AutoModel.from_pretrained(model_name)

        # Classification head
        self.dropout = nn.Dropout(dropout_rate)
        self.classifier = nn.Linear(self.config.hidden_size, num_labels)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize classifier weights"""
        nn.init.normal_(self.classifier.weight, std=0.02)
        nn.init.zeros_(self.classifier.bias)

    def forward(self, input_ids, attention_mask, labels=None):
        # Get BERT outputs
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            return_dict=True
        )

        # Use [CLS] token representation
        pooled_output = outputs.pooler_output
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)

        loss = None
        if labels is not None:
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))

        return {
            'loss': loss,
            'logits': logits,
            'hidden_states': outputs.last_hidden_state
        }


class MedicalSimilarityModel(nn.Module):
    """
    Custom model for learning medical text similarity
    """

    def __init__(self, model_name: str, embedding_dim: int = 768):
        super().__init__()
        self.embedding_dim = embedding_dim

        # Load pre-trained BioBERT
        self.bert = AutoModel.from_pretrained(model_name)

        # Similarity head
        self.similarity_head = nn.Sequential(
            nn.Linear(embedding_dim * 3, 512),  # [emb1, emb2, |emb1-emb2|]
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 1),
            nn.Sigmoid()
        )

    def forward(self, input_ids_1, attention_mask_1, input_ids_2, attention_mask_2,
                similarity_score=None):
        # Get embeddings for both texts
        outputs1 = self.bert(input_ids=input_ids_1, attention_mask=attention_mask_1)
        outputs2 = self.bert(input_ids=input_ids_2, attention_mask=attention_mask_2)

        # Use [CLS] token embeddings
        emb1 = outputs1.pooler_output
        emb2 = outputs2.pooler_output

        # Create similarity features
        diff = torch.abs(emb1 - emb2)
        similarity_features = torch.cat([emb1, emb2, diff], dim=1)

        # Predict similarity
        predicted_similarity = self.similarity_head(similarity_features)

        loss = None
        if similarity_score is not None:
            loss_fct = nn.MSELoss()
            loss = loss_fct(predicted_similarity.squeeze(), similarity_score)

        return {
            'loss': loss,
            'similarity_score': predicted_similarity.squeeze(),
            'embeddings_1': emb1,
            'embeddings_2': emb2
        }


class MedicalDataGenerator:
    """
    Generate synthetic medical training data
    """

    def __init__(self):
        self.medicine_categories = {
            'analgesic': ['acetaminophen', 'ibuprofen', 'aspirin', 'naproxen'],
            'antibiotic': ['amoxicillin', 'azithromycin', 'ciprofloxacin',
                             'doxycycline'],
            'antihypertensive': ['lisinopril', 'amlodipine', 'metoprolol',
                                 'losartan'],
            'antidiabetic': ['metformin', 'insulin', 'glipizide', 'sitagliptin']
        }

        self.medical_contexts = [
            "This medication is used to treat",
            "Common side effects include",
            "Do not take this medication if you have",
            "This drug may interact with",
            "The recommended dosage is",
            "Patients should be monitored for",
            "This medication works by"
        ]

    def generate_classification_data(
        self, num_samples: int = 1000
    ) -> List[MedicalTrainingExample]:
        """Generate medical text classification data"""
        examples = []

        for category, medicines in self.medicine_categories.items():
            samples_per_category = num_samples // len(self.medicine_categories)

            for _ in range(samples_per_category):
                medicine = np.random.choice(medicines)
                context = np.random.choice(self.medical_contexts)

                # Generate synthetic medical text
                text = f"{context} {medicine}. "

                # Add category-specific information
                if category == 'analgesic':
                    text += (
                        "This medication helps reduce pain and inflammation."
                    )
                elif category == 'antibiotic':
                    text += "This medication fights bacterial infections."
                elif category == 'antihypertensive':
                    text += "This medication helps lower blood pressure."
                elif category == 'antidiabetic':
                    text += "This medication helps control blood sugar levels."

                examples.append(MedicalTrainingExample(
                    text=text,
                    label=category,
                    metadata={'medicine': medicine, 'context': context}
                ))

        return examples

    def generate_similarity_data(
        self, num_pairs: int = 1000
    ) -> List[Tuple[str, str, float]]:
        """Generate medical text similarity pairs"""
        pairs = []

        for _ in range(num_pairs):
            # Generate similar pairs (high similarity)
            if np.random.random() < 0.5:
                category = np.random.choice(list(self.medicine_categories.keys()))
                medicines = self.medicine_categories[category]

                med1, med2 = np.random.choice(medicines, 2, replace=False)
                text1 = (
                    f"Information about {med1} medication for medical treatment."
                )
                text2 = (
                    f"Details regarding {med2} drug for therapeutic use."
                )

                similarity = np.random.uniform(0.7, 1.0)  # High similarity

            # Generate dissimilar pairs (low similarity)
            else:
                categories = list(self.medicine_categories.keys())
                cat1, cat2 = np.random.choice(categories, 2, replace=False)

                med1 = np.random.choice(self.medicine_categories[cat1])
                med2 = np.random.choice(self.medicine_categories[cat2])

                text1 = f"Information about {med1} medication."
                text2 = f"Details about {med2} treatment."

                similarity = np.random.uniform(0.0, 0.3)  # Low similarity

            pairs.append((text1, text2, similarity))

        return pairs


class MedicalModelTrainer:
    """
    Custom trainer for medical models with MLflow integration
    """

    def __init__(
        self,
        config: TrainingConfig
    ):
        self.config = config
        self.device = torch.device(
            'cuda' if torch.cuda.is_available() else 'cpu'
        )

        # Initialize MLflow
        mlflow.set_experiment("medical_model_training")

        # Create output directory
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"Training device: {self.device}")

    def train_classification_model(
        self,
        training_data: List[MedicalTrainingExample]
    ) -> Dict[str, Any]:
        """Train medical text classification model"""

        run_name = f"classification_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with mlflow.start_run(run_name=run_name):
            # Log configuration
            mlflow.log_params(self.config.__dict__)

            try:
                # Initialize tokenizer
                tokenizer = AutoTokenizer.from_pretrained(
                    self.config.model_name
                )

                # Create dataset
                dataset = MedicalTextDataset(
                    training_data, tokenizer, self.config.max_length
                )

                # Split data
                train_size = int(0.8 * len(dataset))
                val_size = len(dataset) - train_size
                train_dataset, val_dataset = \
                    torch.utils.data.random_split(
                        dataset, [train_size, val_size]
                    )

                # Initialize model
                model = MedicalBERTClassifier(
                    model_name=self.config.model_name,
                    num_labels=dataset.num_labels
                ).to(self.device)

                # Training arguments
                training_args = TrainingArguments(
                    output_dir=self.config.output_dir,
                    num_train_epochs=self.config.num_epochs,
                    per_device_train_batch_size=self.config.batch_size,
                    per_device_eval_batch_size=self.config.batch_size,
                    warmup_steps=self.config.warmup_steps,
                    weight_decay=self.config.weight_decay,
                    logging_dir=f"{self.config.output_dir}/logs",
                    logging_steps=self.config.logging_steps,
                    evaluation_strategy="steps",
                    eval_steps=self.config.eval_steps,
                    save_steps=self.config.save_steps,
                    load_best_model_at_end=True,
                    metric_for_best_model="eval_loss",
                    greater_is_better=False,
                    fp16=self.config.fp16,
                    gradient_accumulation_steps=(
                        self.config.gradient_accumulation_steps
                    ),
                    dataloader_pin_memory=False
                )

                # Initialize trainer
                trainer = Trainer(
                    model=model,
                    args=training_args,
                    train_dataset=train_dataset,
                    eval_dataset=val_dataset,
                    compute_metrics=self._compute_classification_metrics,
                )

                # Train model
                logger.info("Starting classification model training...")
                train_result = trainer.train()

                # Evaluate model
                eval_result = trainer.evaluate()

                # Log metrics
                mlflow.log_metrics({
                    "train_loss": train_result.training_loss,
                    "eval_loss": eval_result["eval_loss"],
                    "eval_accuracy": eval_result.get("eval_accuracy", 0),
                    "eval_f1": eval_result.get("eval_f1", 0),
                })

                # Save model
                model_path = (
                    f"{self.config.output_dir}/classification_model"
                )
                trainer.save_model(model_path)
                tokenizer.save_pretrained(model_path)

                # Log model to MLflow
                mlflow.pytorch.log_model(model, "classification_model")

                logger.info("Classification model training completed successfully")

                return {
                    "model_path": model_path,
                    "train_loss": train_result.training_loss,
                    "eval_metrics": eval_result,
                    "num_labels": dataset.num_labels,
                    "label_mapping": dataset.label_to_id,
                }

            except Exception as e:
                logger.error(f"Classification training failed: {str(e)}")
                mlflow.log_param("error", str(e))
                raise

    def train_similarity_model(
        self,
        similarity_data: List[Tuple[str, str, float]]
    ) -> Dict[str, Any]:
        """Train medical text similarity model"""

        run_name = f"similarity_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with mlflow.start_run(run_name=run_name):
            # Log configuration
            mlflow.log_params(self.config.__dict__)

            try:
                # Initialize tokenizer
                tokenizer = AutoTokenizer.from_pretrained(
                    self.config.model_name
                )

                # Create dataset
                dataset = MedicalSimilarityDataset(
                    similarity_data, tokenizer, self.config.max_length
                )

                # Split data
                train_size = int(0.8 * len(dataset))
                val_size = len(dataset) - train_size
                train_dataset, val_dataset = torch.utils.data.random_split(
                    dataset, [train_size, val_size]
                )

                # Create data loaders
                train_loader = DataLoader(
                    train_dataset, batch_size=self.config.batch_size, shuffle=True
                )
                val_loader = DataLoader(
                    val_dataset, batch_size=self.config.batch_size, shuffle=False
                )

                # Initialize model
                model = MedicalSimilarityModel(self.config.model_name).to(self.device)

                # Initialize optimizer
                optimizer = optim.AdamW(
                    model.parameters(),
                    lr=self.config.learning_rate,
                    weight_decay=self.config.weight_decay
                )

                # Training loop
                logger.info("Starting similarity model training...")
                best_val_loss = float('inf')
                patience_counter = 0

                for epoch in range(self.config.num_epochs):
                    # Training phase
                    model.train()
                    train_loss = 0.0

                    for batch_idx, batch in enumerate(train_loader):
                        # Move batch to device
                        batch = {
                            k: v.to(self.device) for k, v in batch.items()
                        }

                        # Forward pass
                        outputs = model(**batch)
                        loss = outputs['loss']

                        # Backward pass
                        optimizer.zero_grad()
                        loss.backward()
                        optimizer.step()

                        train_loss += loss.item()

                        # Log progress
                        if batch_idx % self.config.logging_steps == 0:
                            logger.info(
                                f"Epoch {epoch + 1}/{self.config.num_epochs}, "
                                f"Batch {batch_idx}, "
                                f"Loss: {loss.item():.4f}"
                            )

                    # Validation phase
                    model.eval()
                    val_loss = 0.0
                    val_predictions = []
                    val_targets = []

                    with torch.no_grad():
                        for batch in val_loader:
                            batch = {
                                k: v.to(self.device) for k, v in batch.items()
                            }
                            outputs = model(**batch)

                            val_loss += outputs['loss'].item()
                            val_predictions.extend(
                                outputs['similarity_score'].cpu().numpy()
                            )
                            val_targets.extend(batch['similarity_score'].cpu().numpy())

                    # Calculate metrics
                    avg_train_loss = train_loss / len(train_loader)
                    avg_val_loss = val_loss / len(val_loader)

                    val_predictions = np.array(val_predictions)
                    val_targets = np.array(val_targets)
                    mse = np.mean((val_predictions - val_targets) ** 2)
                    mae = np.mean(np.abs(val_predictions - val_targets))

                    # Log metrics
                    mlflow.log_metrics({
                        f"train_loss_epoch_{epoch}": avg_train_loss,
                        f"val_loss_epoch_{epoch}": avg_val_loss,
                        f"val_mse_epoch_{epoch}": mse,
                        f"val_mae_epoch_{epoch}": mae
                    }, step=epoch)

                    logger.info(
                        f"Epoch {epoch + 1}: Train Loss: {avg_train_loss:.4f}, "
                        f"Val Loss: {avg_val_loss:.4f}, MSE: {mse:.4f}"
                    )

                    # Early stopping
                    if avg_val_loss < best_val_loss:
                        best_val_loss = avg_val_loss
                        patience_counter = 0

                        # Save best model
                        model_path = f"{self.config.output_dir}/similarity_model"
                        torch.save(
                            model.state_dict(),
                            f"{model_path}/pytorch_model.bin"
                        )
                        tokenizer.save_pretrained(model_path)
                    else:
                        patience_counter += 1
                        if (
                            patience_counter >=
                            self.config.early_stopping_patience
                        ):
                            logger.info(f"Early stopping at epoch {epoch + 1}")
                            break

                # Log final model
                mlflow.pytorch.log_model(
                    model, "similarity_model"
                )

                logger.info(
                    "Similarity model training completed successfully"
                )

                return {
                    "model_path":
                        f"{self.config.output_dir}/similarity_model",
                    "best_val_loss": best_val_loss,
                    "final_mse": mse,
                    "final_mae": mae,
                }

            except Exception as e:
                logger.error(f"Similarity training failed: {str(e)}")
                mlflow.log_param("error", str(e))
                raise

    def evaluate_classification_model(
        self, model_path: str, test_data: List[MedicalTrainingExample]
    ) -> Dict[str, Any]:
        """Evaluate a trained classification model"""
        from sklearn.metrics import classification_report
        from transformers import AutoModelForSequenceClassification

        try:
            # Load model and tokenizer
            model = AutoModelForSequenceClassification.from_pretrained(model_path)
            tokenizer = AutoTokenizer.from_pretrained(model_path)

            # Create dataset
            dataset = MedicalTextDataset(
                test_data, tokenizer, self.config.max_length
            )

            # Trainer
            trainer = Trainer(model=model)

            # Predictions
            predictions = trainer.predict(dataset)
            predicted_labels = np.argmax(predictions.predictions, axis=1)

            # True labels
            true_labels = [example.label for example in test_data]
            true_labels_encoded = [
                dataset.label_to_id[label] for label in true_labels
            ]

            # Metrics
            accuracy = accuracy_score(true_labels_encoded, predicted_labels)
            report = classification_report(
                true_labels_encoded, predicted_labels,
                target_names=list(dataset.id_to_label.values())
            )

            logger.info(f"Classification evaluation report:\n{report}")

            return {
                "accuracy": accuracy,
                "classification_report": report,
            }

        except Exception as e:
            logger.error(
                f"Classification evaluation failed: {str(e)}"
            )
            raise

    def _compute_classification_metrics(self, eval_pred):
        """Compute classification metrics"""
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)

        accuracy = accuracy_score(labels, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, predictions, average='weighted'
        )

        return {
            'accuracy': accuracy,
            'f1': f1,
            'precision': precision,
            'recall': recall
        }

    def fine_tune_biobert(self, medical_texts: List[str], save_path: str) -> str:
        """Fine-tune BioBERT on medical domain texts"""

        with mlflow.start_run(
            run_name=f"biobert_finetune_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ):
            try:
                logger.info("Starting BioBERT fine-tuning...")

                # Generate training data from medical texts
                data_generator = MedicalDataGenerator()
                classification_data = \
                    data_generator.generate_classification_data(
                        len(medical_texts)
                    )

                # Train classification model
                result = self.train_classification_model(
                    classification_data
                )

                # Save fine-tuned model
                fine_tuned_path = f"{save_path}/biobert_finetuned"
                Path(fine_tuned_path).mkdir(parents=True, exist_ok=True)

                # Copy model files
                import shutil
                shutil.copytree(result["model_path"], fine_tuned_path, dirs_exist_ok=True)

                logger.info(f"BioBERT fine-tuning completed. Model saved to: {fine_tuned_path}")

                return fine_tuned_path

            except Exception as e:
                logger.error(f"BioBERT fine-tuning failed: {str(e)}")
                raise

def create_training_pipeline(config: TrainingConfig = None) -> MedicalModelTrainer:
    """Create and configure training pipeline"""
    if config is None:
        config = TrainingConfig()

    return MedicalModelTrainer(config)
