import asyncio
import aiohttp
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"


@dataclass
class DrugInfo:
    name: str
    active_substance: str
    therapeutic_area: str
    indication: str
    administration_route: str
    authorization_status: str
    marketing_holder: str
    side_effects: List[str]
    contraindications: List[str]
    interactions: List[str]
    dosage_info: str
    source: str

    def to_document(self) -> Dict[str, Any]:
        content = f"""# {self.name}

## Overview
Active substance: {self.active_substance}
Therapeutic area: {self.therapeutic_area}
Route of administration: {self.administration_route}
Marketing authorization holder: {self.marketing_holder}
Authorization status: {self.authorization_status}

## Indication
{self.indication}

## Dosage
{self.dosage_info}

## Side Effects
{chr(10).join(f'- {s}' for s in self.side_effects) if self.side_effects else 'No significant side effects reported.'}

## Contraindications
{chr(10).join(f'- {c}' for c in self.contraindications) if self.contraindications else 'None reported.'}

## Drug Interactions
{chr(10).join(f'- {i}' for i in self.interactions) if self.interactions else 'No significant interactions reported.'}
"""
        return {
            "content": content,
            "title": f"{self.name} - Drug Information",
            "source": self.source,
            "metadata": {
                "active_substance": self.active_substance,
                "therapeutic_area": self.therapeutic_area,
                "authorization_status": self.authorization_status
            }
        }


class EMADataFetcher:
    EMA_MEDICINES_URL = "https://www.ema.europa.eu/en/medicines/download-medicine-data"
    EMA_JSON_URL = "https://www.ema.europa.eu/sites/default/files/ema_website_data_all_english.json"
    EPAR_BASE_URL = "https://www.ema.europa.eu/en/medicines/human/EPAR"

    def __init__(self, output_dir: Path = DATA_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_ema_json(self) -> List[Dict[str, Any]]:
        logger.info("Fetching EMA medicine data JSON...")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    self.EMA_JSON_URL,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Fetched {len(data)} entries from EMA")

                        output_file = self.output_dir / "ema_raw.json"
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)

                        return data
                    else:
                        logger.error(f"EMA fetch failed: {response.status}")
                        return []
            except Exception as e:
                logger.error(f"EMA fetch error: {e}")
                return []

    def parse_medicines(self, raw_data: List[Dict]) -> List[DrugInfo]:
        medicines = []

        for entry in raw_data:
            if not self._is_medicine_entry(entry):
                continue

            try:
                drug = DrugInfo(
                    name=entry.get("title", "Unknown"),
                    active_substance=self._extract_field(entry, "active_substance"),
                    therapeutic_area=self._extract_field(entry, "therapeutic_area"),
                    indication=self._extract_field(entry, "condition", "therapeutic_indication"),
                    administration_route=self._extract_field(entry, "route_of_administration"),
                    authorization_status=self._extract_field(entry, "authorisation_status", "status"),
                    marketing_holder=self._extract_field(entry, "marketing_authorisation_holder"),
                    side_effects=self._extract_list(entry, "side_effects", "adverse_reactions"),
                    contraindications=self._extract_list(entry, "contraindications"),
                    interactions=self._extract_list(entry, "interactions", "drug_interactions"),
                    dosage_info=self._extract_field(entry, "dosage", "posology"),
                    source="EMA"
                )
                medicines.append(drug)
            except Exception as e:
                logger.warning(f"Failed to parse entry: {e}")

        return medicines

    def _is_medicine_entry(self, entry: Dict) -> bool:
        title = entry.get("title", "").lower()
        content_type = entry.get("type", "").lower()
        return "medicine" in content_type or entry.get("active_substance")

    def _extract_field(self, entry: Dict, *field_names: str) -> str:
        for field in field_names:
            if field in entry and entry[field]:
                val = entry[field]
                if isinstance(val, list):
                    return ", ".join(str(v) for v in val)
                return str(val)
        return "Not specified"

    def _extract_list(self, entry: Dict, *field_names: str) -> List[str]:
        for field in field_names:
            if field in entry and entry[field]:
                val = entry[field]
                if isinstance(val, list):
                    return [str(v) for v in val]
                return [str(val)]
        return []

    def save_documents(self, medicines: List[DrugInfo]) -> Path:
        documents = [m.to_document() for m in medicines]

        output_file = self.output_dir / "ema_medicines.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(documents)} medicine documents to {output_file}")
        return output_file


SAMPLE_EU_MEDICINES = [
    DrugInfo(
        name="Paracetamol (Acetaminophen)",
        active_substance="Paracetamol",
        therapeutic_area="Pain and fever",
        indication="Relief of mild to moderate pain and fever reduction",
        administration_route="Oral, rectal, intravenous",
        authorization_status="Authorized",
        marketing_holder="Various",
        side_effects=[
            "Rare allergic reactions",
            "Liver damage at high doses",
            "Skin reactions (very rare)"
        ],
        contraindications=[
            "Severe hepatic impairment",
            "Known hypersensitivity to paracetamol"
        ],
        interactions=[
            "Warfarin: may enhance anticoagulant effect",
            "Alcohol: increased hepatotoxicity risk",
            "Carbamazepine: may increase hepatotoxicity risk"
        ],
        dosage_info="Adults: 500-1000mg every 4-6 hours, max 4g/day",
        source="EU Common Medicines"
    ),
    DrugInfo(
        name="Ibuprofen",
        active_substance="Ibuprofen",
        therapeutic_area="Pain and inflammation",
        indication="Treatment of mild to moderate pain, fever, and inflammatory conditions",
        administration_route="Oral, topical",
        authorization_status="Authorized",
        marketing_holder="Various",
        side_effects=[
            "Gastrointestinal irritation and ulcers",
            "Increased cardiovascular risk with prolonged use",
            "Renal impairment",
            "Allergic reactions"
        ],
        contraindications=[
            "History of GI bleeding or peptic ulcer",
            "Severe heart failure",
            "Third trimester of pregnancy",
            "Severe renal or hepatic impairment"
        ],
        interactions=[
            "Aspirin: reduced cardioprotective effect",
            "ACE inhibitors: reduced antihypertensive effect",
            "Lithium: increased lithium levels",
            "Methotrexate: increased toxicity"
        ],
        dosage_info="Adults: 200-400mg every 4-6 hours, max 1200mg/day (OTC) or 2400mg/day (prescription)",
        source="EU Common Medicines"
    ),
    DrugInfo(
        name="Omeprazole",
        active_substance="Omeprazole",
        therapeutic_area="Gastroenterology",
        indication="Treatment of gastric and duodenal ulcers, GERD, and Zollinger-Ellison syndrome",
        administration_route="Oral",
        authorization_status="Authorized",
        marketing_holder="Various (Losec by AstraZeneca)",
        side_effects=[
            "Headache",
            "Nausea and diarrhea",
            "Vitamin B12 deficiency (long-term)",
            "Increased fracture risk (long-term)",
            "Hypomagnesemia"
        ],
        contraindications=[
            "Known hypersensitivity to proton pump inhibitors"
        ],
        interactions=[
            "Clopidogrel: reduced antiplatelet effect",
            "Methotrexate: increased methotrexate levels",
            "Ketoconazole: reduced absorption"
        ],
        dosage_info="20-40mg once daily, typically before breakfast",
        source="EU Common Medicines"
    ),
    DrugInfo(
        name="Amoxicillin",
        active_substance="Amoxicillin",
        therapeutic_area="Antibiotics",
        indication="Bacterial infections including respiratory, urinary, and skin infections",
        administration_route="Oral",
        authorization_status="Authorized",
        marketing_holder="Various",
        side_effects=[
            "Diarrhea",
            "Nausea and vomiting",
            "Skin rash",
            "Allergic reactions (including anaphylaxis)"
        ],
        contraindications=[
            "Penicillin allergy",
            "History of amoxicillin-associated jaundice"
        ],
        interactions=[
            "Methotrexate: increased toxicity",
            "Warfarin: enhanced anticoagulant effect",
            "Oral contraceptives: potentially reduced efficacy"
        ],
        dosage_info="Adults: 250-500mg every 8 hours or 500-875mg every 12 hours",
        source="EU Common Medicines"
    ),
    DrugInfo(
        name="Atorvastatin",
        active_substance="Atorvastatin",
        therapeutic_area="Cardiovascular",
        indication="Hypercholesterolemia and prevention of cardiovascular events",
        administration_route="Oral",
        authorization_status="Authorized",
        marketing_holder="Pfizer (Lipitor) and generics",
        side_effects=[
            "Muscle pain and weakness (myalgia)",
            "Elevated liver enzymes",
            "Headache",
            "Gastrointestinal disturbances",
            "Rhabdomyolysis (rare)"
        ],
        contraindications=[
            "Active liver disease",
            "Pregnancy and breastfeeding",
            "Unexplained persistent transaminase elevation"
        ],
        interactions=[
            "Cyclosporine: increased statin levels",
            "Gemfibrozil: increased myopathy risk",
            "CYP3A4 inhibitors (clarithromycin, itraconazole): increased toxicity",
            "Grapefruit juice: increased statin levels"
        ],
        dosage_info="10-80mg once daily, can be taken at any time",
        source="EU Common Medicines"
    ),
    DrugInfo(
        name="Metformin",
        active_substance="Metformin hydrochloride",
        therapeutic_area="Diabetes",
        indication="Type 2 diabetes mellitus, particularly in overweight patients",
        administration_route="Oral",
        authorization_status="Authorized",
        marketing_holder="Various (Glucophage by Merck)",
        side_effects=[
            "Gastrointestinal upset (nausea, diarrhea, abdominal pain)",
            "Metallic taste",
            "Vitamin B12 deficiency (long-term)",
            "Lactic acidosis (rare but serious)"
        ],
        contraindications=[
            "Severe renal impairment (eGFR <30)",
            "Acute conditions with risk of tissue hypoxia",
            "Diabetic ketoacidosis",
            "Before contrast imaging procedures"
        ],
        interactions=[
            "Alcohol: increased lactic acidosis risk",
            "Iodinated contrast agents: acute kidney injury risk",
            "ACE inhibitors: may enhance hypoglycemic effect"
        ],
        dosage_info="Starting: 500mg once or twice daily with meals. Max: 2000-3000mg/day in divided doses",
        source="EU Common Medicines"
    ),
    DrugInfo(
        name="Losartan",
        active_substance="Losartan potassium",
        therapeutic_area="Cardiovascular",
        indication="Hypertension, heart failure, diabetic nephropathy protection",
        administration_route="Oral",
        authorization_status="Authorized",
        marketing_holder="MSD (Cozaar) and generics",
        side_effects=[
            "Dizziness",
            "Hypotension",
            "Hyperkalemia",
            "Fatigue"
        ],
        contraindications=[
            "Pregnancy (especially 2nd and 3rd trimester)",
            "Bilateral renal artery stenosis",
            "Co-administration with aliskiren in diabetics"
        ],
        interactions=[
            "NSAIDs: reduced antihypertensive effect",
            "Potassium supplements: hyperkalemia risk",
            "Lithium: increased lithium levels"
        ],
        dosage_info="50mg once daily, may increase to 100mg. Take consistently with or without food",
        source="EU Common Medicines"
    ),
    DrugInfo(
        name="Salbutamol (Albuterol)",
        active_substance="Salbutamol",
        therapeutic_area="Respiratory",
        indication="Relief and prevention of bronchospasm in asthma and COPD",
        administration_route="Inhalation, oral, intravenous",
        authorization_status="Authorized",
        marketing_holder="Various (Ventolin by GSK)",
        side_effects=[
            "Tremor",
            "Tachycardia",
            "Headache",
            "Hypokalemia (with high doses)"
        ],
        contraindications=[
            "Hypersensitivity to salbutamol"
        ],
        interactions=[
            "Beta-blockers: mutual antagonism",
            "Diuretics: enhanced hypokalemia",
            "MAO inhibitors: enhanced cardiovascular effects"
        ],
        dosage_info="Inhalation: 100-200mcg (1-2 puffs) as needed, max 8 puffs/day",
        source="EU Common Medicines"
    ),
    DrugInfo(
        name="Sertraline",
        active_substance="Sertraline hydrochloride",
        therapeutic_area="Mental health",
        indication="Depression, panic disorder, OCD, PTSD, social anxiety disorder",
        administration_route="Oral",
        authorization_status="Authorized",
        marketing_holder="Pfizer (Zoloft) and generics",
        side_effects=[
            "Nausea",
            "Diarrhea",
            "Insomnia",
            "Sexual dysfunction",
            "Headache",
            "Serotonin syndrome (rare)"
        ],
        contraindications=[
            "Concurrent MAO inhibitor use",
            "Concurrent pimozide use",
            "Known hypersensitivity"
        ],
        interactions=[
            "MAO inhibitors: serotonin syndrome risk (14-day washout required)",
            "Warfarin: increased bleeding risk",
            "Tramadol: seizure risk",
            "Alcohol: enhanced CNS depression"
        ],
        dosage_info="Starting: 50mg/day. May increase by 50mg increments weekly. Max: 200mg/day",
        source="EU Common Medicines"
    ),
    DrugInfo(
        name="Levothyroxine",
        active_substance="Levothyroxine sodium",
        therapeutic_area="Endocrinology",
        indication="Hypothyroidism, thyroid hormone replacement",
        administration_route="Oral",
        authorization_status="Authorized",
        marketing_holder="Various",
        side_effects=[
            "Symptoms of hyperthyroidism if overdosed (tachycardia, tremor, weight loss)",
            "Headache",
            "Insomnia",
            "Bone density reduction (with excess doses)"
        ],
        contraindications=[
            "Untreated adrenal insufficiency",
            "Acute myocardial infarction",
            "Thyrotoxicosis"
        ],
        interactions=[
            "Calcium/iron supplements: reduced absorption (separate by 4 hours)",
            "Warfarin: enhanced anticoagulant effect",
            "Antacids: reduced absorption",
            "Carbamazepine: increased levothyroxine metabolism"
        ],
        dosage_info="25-50mcg daily initially, increase every 4-6 weeks. Typical maintenance: 100-200mcg/day. Take on empty stomach",
        source="EU Common Medicines"
    )
]


def create_sample_knowledge_base() -> Path:
    output_dir = DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    documents = [m.to_document() for m in SAMPLE_EU_MEDICINES]

    output_file = output_dir / "eu_medicines.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)

    logger.info(f"Created sample knowledge base with {len(documents)} medicines at {output_file}")
    return output_file


async def fetch_and_build_knowledge_base() -> Path:
    fetcher = EMADataFetcher()

    raw_data = await fetcher.fetch_ema_json()

    if raw_data:
        medicines = fetcher.parse_medicines(raw_data)
        if medicines:
            return fetcher.save_documents(medicines)

    logger.info("Using sample EU medicines data as fallback")
    return create_sample_knowledge_base()


if __name__ == "__main__":
    sample_path = create_sample_knowledge_base()
    print(f"Created: {sample_path}")
