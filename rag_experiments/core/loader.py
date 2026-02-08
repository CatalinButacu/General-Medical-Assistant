import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

def load_json_data(path: Path) -> Any:
    if not path.exists():
        logger.warning(f"Data file not found: {path}")
        return [] if "medicines" in path.name else {}
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from {path}: {e}")
        return [] if "medicines" in path.name else {}

def load_medicines_db(
    data_dir: Optional[Path] = None,
    filename: str = "comprehensive_medicines.json"
) -> List[Dict[str, Any]]:
    data_dir = data_dir or DATA_DIR
    path = data_dir / filename
    
    medicines = load_json_data(path)
    if medicines:
        logger.info(f"Loaded {len(medicines)} medicines from {path}")
    return medicines

def load_symptom_index(
    data_dir: Optional[Path] = None,
    filename: str = "comprehensive_symptom_index.json"
) -> Dict[str, List[Dict[str, Any]]]:
    data_dir = data_dir or DATA_DIR
    path = data_dir / filename
    
    index = load_json_data(path)
    if index:
        logger.info(f"Loaded {len(index)} symptoms from {path}")
    return index

def save_json_data(data: Any, path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved data to {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save data to {path}: {e}")
        return False
