import asyncio
import argparse
import logging
import json
import sys

from .base import Document, StrategyConfig
from .config import get_config
from .runner import ExperimentRunner
from .local_llm import get_llm, set_llm, MinistralLLM, TinyLlamaLLM
from .loader import load_documents
from .data_sources import create_sample_knowledge_base

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_documents():
    from pathlib import Path
    data_dir = Path(__file__).parent / "data"
    
    # Try comprehensive database first
    comprehensive = data_dir / "comprehensive_medicines.json"
    if comprehensive.exists():
        from .loader import load_documents
        return load_documents(comprehensive)
    
    # Fallback to leaflets
    leaflets = data_dir / "ro_leaflets.json"
    if leaflets.exists():
        from .loader import load_documents
        return load_documents(leaflets)
    
    # Last fallback
    try:
        from .loader import load_documents
        return load_documents()
    except Exception:
        from .data_sources import create_sample_knowledge_base
        create_sample_knowledge_base()
        from .loader import load_documents
        return load_documents()


SAMPLE_DOCUMENTS = [
    Document(
        content="""# Aspirin (Acetylsalicylic Acid)

## Overview
Aspirin is a nonsteroidal anti-inflammatory drug (NSAID) used to reduce pain, fever, and inflammation.

## Common Uses
- Pain relief (headaches, muscle pain)
- Fever reduction
- Anti-inflammatory treatment
- Cardiovascular protection (low-dose)

## Side Effects
- Stomach irritation and ulcers
- Increased bleeding risk
- Allergic reactions (rare)
- Tinnitus at high doses

## Interactions
- Blood thinners (warfarin): increased bleeding risk
- Other NSAIDs: increased side effects
- Methotrexate: increased toxicity""",
        title="Aspirin Drug Information",
        source="medical_db"
    ),
    Document(
        content="""# Metformin

## Overview
Metformin is the first-line medication for type 2 diabetes treatment.

## Mechanism
Works by reducing glucose production in the liver and improving insulin sensitivity.

## Dosage
- Starting dose: 500mg once daily
- Maximum: 2550mg daily in divided doses
- Take with meals to reduce GI effects

## Side Effects
- Gastrointestinal upset (common initially)
- Vitamin B12 deficiency (long-term)
- Lactic acidosis (rare but serious)

## Contraindications
- Severe kidney disease
- Liver disease
- Before contrast imaging procedures""",
        title="Metformin Drug Information",
        source="medical_db"
    )
]


async def run_interactive(use_medical: bool = False, model: str = "tinyllama"):
    print("=" * 60)
    print("RAG Strategies Experiment - Local Models")
    print("=" * 60)

    print(f"\nLoading {model} model (this may take a moment)...")

    if model == "ministral":
        set_llm(MinistralLLM())
    else:
        set_llm(TinyLlamaLLM())

    get_llm()
    print("LLM loaded!")

    runner = ExperimentRunner(use_medical=use_medical)

    print("\nLoading strategies (rerank only for faster startup)...")
    await runner.initialize(["rerank"])

    print("Preparing EU medicines knowledge base...")
    documents = get_documents()
    chunks = await runner.prepare_chunks(documents)
    print(f"Ready with {len(chunks)} chunks")
    print()

    print("Available strategies: rerank")
    print("Commands: 'quit'")
    print()

    while True:
        try:
            user_input = input("Query: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                break

            print(f"\nSearching...")
            result = await runner.run_strategy("rerank", user_input, chunks)

            print(f"\nResults ({result.result_count} found, {result.latency_ms:.0f}ms):")
            print(f"  Top score: {result.top_score:.4f}")
            print(f"  Avg score: {result.avg_score:.4f}")
            print()

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    await runner.cleanup()
    print("\nGoodbye!")


async def run_comparison(query: str, strategies: list, use_medical: bool = False):
    runner = ExperimentRunner(use_medical=use_medical)
    await runner.initialize(strategies if strategies else None)

    chunks = await runner.prepare_chunks(SAMPLE_DOCUMENTS)

    report = await runner.compare_strategies(query, chunks, strategies)
    print(json.dumps(report.to_dict(), indent=2))

    await runner.cleanup()


def main():
    parser = argparse.ArgumentParser(description="RAG Strategies Experiment CLI (Local Models)")
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Query to test"
    )
    parser.add_argument(
        "--strategy", "-s",
        type=str,
        choices=["multi_query", "rerank", "agentic", "self_reflective"],
        help="Strategy to use"
    )
    parser.add_argument(
        "--compare", "-c",
        action="store_true",
        help="Compare all strategies"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Interactive mode"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        choices=["ministral", "tinyllama"],
        default="tinyllama",
        help="LLM model to use (default: tinyllama for faster loading)"
    )
    parser.add_argument(
        "--medical",
        action="store_true",
        help="Use medical-domain embeddings"
    )

    args = parser.parse_args()

    if args.interactive or (not args.query and not args.compare):
        asyncio.run(run_interactive(args.medical, args.model))
    elif args.compare and args.query:
        asyncio.run(run_comparison(args.query, None, args.medical))
    elif args.query:
        strategies = [args.strategy] if args.strategy else None
        asyncio.run(run_comparison(args.query, strategies, args.medical))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
