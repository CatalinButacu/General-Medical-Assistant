import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Any
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

from .config import get_config

logger = logging.getLogger(__name__)


class LocalLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        pass

    @abstractmethod
    def generate_batch(self, prompts: List[str], max_tokens: int = 256) -> List[str]:
        pass


class MinistralLLM(LocalLLM):
    def __init__(
        self,
        model_id: str = "mistralai/Ministral-3b-instruct",
        device: Optional[str] = None,
        torch_dtype: Any = torch.bfloat16
    ):
        self.model_id = model_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.torch_dtype = torch_dtype
        self._model = None
        self._tokenizer = None
        self._pipeline = None
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return

        logger.info(f"Loading {self.model_id} on {self.device}...")

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)

        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=self.torch_dtype,
            device_map="auto" if self.device == "cuda" else None,
            low_cpu_mem_usage=True
        )

        if self.device == "cpu":
            self._model = self._model.to(self.device)

        self._pipeline = pipeline(
            "text-generation",
            model=self._model,
            tokenizer=self._tokenizer,
            device=None if self.device == "cuda" else -1
        )

        self._initialized = True
        logger.info(f"{self.model_id} loaded successfully")

    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        if not self._initialized:
            self.initialize()

        messages = [{"role": "user", "content": prompt}]

        formatted = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        output = self._pipeline(
            formatted,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=self._tokenizer.pad_token_id,
            return_full_text=False
        )

        return output[0]["generated_text"].strip()

    def generate_batch(self, prompts: List[str], max_tokens: int = 256) -> List[str]:
        return [self.generate(p, max_tokens) for p in prompts]

    def cleanup(self) -> None:
        if self._model is not None:
            del self._model
            del self._tokenizer
            del self._pipeline
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            self._initialized = False


class TinyLlamaLLM(LocalLLM):
    def __init__(
        self,
        model_id: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        device: Optional[str] = None
    ):
        self.model_id = model_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._pipeline = None
        self._tokenizer = None
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return

        logger.info(f"Loading {self.model_id} on {self.device}...")

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)

        self._pipeline = pipeline(
            "text-generation",
            model=self.model_id,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None
        )

        self._initialized = True
        logger.info(f"{self.model_id} loaded successfully")

    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        if not self._initialized:
            self.initialize()

        messages = [{"role": "user", "content": prompt}]

        formatted = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        output = self._pipeline(
            formatted,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=0.7,
            return_full_text=False
        )

        return output[0]["generated_text"].strip()

    def generate_batch(self, prompts: List[str], max_tokens: int = 256) -> List[str]:
        return [self.generate(p, max_tokens) for p in prompts]


_llm_instance: Optional[LocalLLM] = None


def get_llm(model_type: str = "ministral") -> LocalLLM:
    global _llm_instance

    if _llm_instance is None:
        if model_type == "ministral":
            _llm_instance = MinistralLLM()
        elif model_type == "tinyllama":
            _llm_instance = TinyLlamaLLM()
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        _llm_instance.initialize()

    return _llm_instance


def set_llm(llm: LocalLLM) -> None:
    global _llm_instance
    _llm_instance = llm
