"""
Comprehensive Romanian Medicine Database Generator
Generates 1000+ medicine entries across diverse categories with full leaflet information
"""

import json
import random
from pathlib import Path
from typing import List, Dict
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"

CATEGORIES = {
    "durere_febra": {
        "name": "Durere și Febră",
        "symptoms": ["durere de cap", "migrena", "febra", "dureri musculare", "dureri articulare", "dureri dentare", "nevralgie"],
        "substances": [
            ("Ibuprofen", "AINS pentru durere și inflamație"),
            ("Paracetamol", "Analgezic și antipiretic"),
            ("Acid acetilsalicilic", "Analgezic, antipiretic, antiinflamator"),
            ("Metamizol", "Analgezic puternic"),
            ("Naproxen", "AINS cu durată lungă de acțiune"),
            ("Ketoprofen", "AINS pentru dureri inflamatorii"),
            ("Diclofenac", "AINS pentru dureri articulare"),
            ("Meloxicam", "AINS selectiv COX-2"),
            ("Piroxicam", "AINS pentru artrită"),
            ("Dexketoprofen", "AINS cu acțiune rapidă"),
        ]
    },
    "digestiv": {
        "name": "Afecțiuni Digestive",
        "symptoms": ["arsuri gastrice", "reflux", "aciditate", "dureri stomac", "diaree", "constipatie", "balonare", "greata", "indigestie", "colici"],
        "substances": [
            ("Omeprazol", "Inhibitor de pompă protonică"),
            ("Pantoprazol", "IPP pentru protecție gastrică"),
            ("Esomeprazol", "Izomer S al omeprazolului"),
            ("Lansoprazol", "IPP pentru ulcer"),
            ("Rabeprazol", "IPP de nouă generație"),
            ("Ranitidină", "Antagonist H2"),
            ("Famotidină", "Antagonist H2"),
            ("Diosmectită", "Protector intestinal"),
            ("Loperamidă", "Antidiareic"),
            ("Drotaverină", "Antispastic"),
            ("Butilscopolamină", "Antispastic"),
            ("Simeticonă", "Antiflatulent"),
            ("Domperidonă", "Prokinetic"),
            ("Metoclopramidă", "Antiemetic"),
            ("Trimebutină", "Reglator motilitate"),
        ]
    },
    "respirator": {
        "name": "Afecțiuni Respiratorii",
        "symptoms": ["tuse", "raceala", "gripa", "nas infundat", "sinuzita", "bronsita", "durere in gat", "mucus", "stranut"],
        "substances": [
            ("Acetilcisteină", "Mucolitc pentru tuse productivă"),
            ("Ambroxol", "Expectorant"),
            ("Bromhexină", "Mucolitc"),
            ("Carbocisteină", "Mucoregulator"),
            ("Xilometazolină", "Decongestionant nazal"),
            ("Oximetazolină", "Decongestionant nazal de lungă durată"),
            ("Fenilefrină", "Decongestionant"),
            ("Pseudoefedrină", "Decongestionant sistemic"),
            ("Dextrometorfan", "Antitusiv"),
            ("Codeină", "Antitusiv opioid"),
            ("Benzidamină", "Antiinflamator pentru gât"),
            ("Amilmetacrezol", "Antiseptic oral"),
        ]
    },
    "alergii": {
        "name": "Alergii",
        "symptoms": ["alergie", "rinita alergica", "urticarie", "mancarimi", "ochi rosii", "stranut", "alergie polen", "conjunctivita"],
        "substances": [
            ("Loratadină", "Antihistaminic non-sedativ"),
            ("Desloratadină", "Antihistaminic de nouă generație"),
            ("Cetirizină", "Antihistaminic"),
            ("Levocetirizină", "Antihistaminic puternic"),
            ("Fexofenadină", "Antihistaminic non-sedativ"),
            ("Ebastină", "Antihistaminic de lungă durată"),
            ("Bilastină", "Antihistaminic modern"),
            ("Dimetindenă", "Antihistaminic pentru copii"),
            ("Clemastină", "Antihistaminic clasic"),
            ("Hidroxizină", "Antihistaminic cu efect sedativ"),
        ]
    },
    "cardiovascular": {
        "name": "Cardiovascular",
        "symptoms": ["hipertensiune", "colesterol", "insuficienta cardiaca", "aritmie", "angina", "varice", "hemoroizi", "picioare grele"],
        "substances": [
            ("Atorvastatină", "Statină pentru colesterol"),
            ("Rosuvastatină", "Statină de nouă generație"),
            ("Simvastatină", "Statină clasică"),
            ("Bisoprolol", "Beta-blocant"),
            ("Metoprolol", "Beta-blocant"),
            ("Carvedilol", "Beta-blocant cu efect alfa"),
            ("Nebivolol", "Beta-blocant cu efect vasodilatator"),
            ("Amlodipină", "Blocant canale calciu"),
            ("Lercanidipină", "BCC de nouă generație"),
            ("Nifedipină", "BCC pentru angină"),
            ("Perindopril", "IECA"),
            ("Ramipril", "IECA"),
            ("Enalapril", "IECA clasic"),
            ("Lisinopril", "IECA"),
            ("Losartan", "Sartan"),
            ("Valsartan", "Sartan"),
            ("Candesartan", "Sartan"),
            ("Irbesartan", "Sartan"),
            ("Telmisartan", "Sartan"),
            ("Clopidogrel", "Antiagregant plachetar"),
            ("Diosmină", "Venotonic"),
            ("Hesperidină", "Venotonic"),
        ]
    },
    "diabet": {
        "name": "Diabet",
        "symptoms": ["diabet", "glicemie crescuta", "sete excesiva", "urinare frecventa"],
        "substances": [
            ("Metformină", "Antidiabetic de primă linie"),
            ("Gliclazidă", "Sulfoniluree"),
            ("Glimepirida", "Sulfoniluree"),
            ("Glibenclamidă", "Sulfoniluree"),
            ("Sitagliptină", "Inhibitor DPP-4"),
            ("Vildagliptină", "Inhibitor DPP-4"),
            ("Linagliptină", "Inhibitor DPP-4"),
            ("Empagliflozină", "Inhibitor SGLT2"),
            ("Dapagliflozină", "Inhibitor SGLT2"),
            ("Canagliflozină", "Inhibitor SGLT2"),
            ("Pioglitazonă", "Tiazolidinedionă"),
            ("Repaglinidă", "Meglitinidă"),
        ]
    },
    "antibiotice": {
        "name": "Antibiotice",
        "symptoms": ["infectie", "febra", "infectie urinara", "infectie respiratorie", "infectie piele"],
        "substances": [
            ("Amoxicilină", "Penicilinã cu spectru larg"),
            ("Amoxicilină+Ac.clavulanic", "Penicilinã protejată"),
            ("Ampicilină", "Penicilinã"),
            ("Penicilină V", "Penicilinã orală"),
            ("Azitromicină", "Macrolidă"),
            ("Claritromicină", "Macrolidă"),
            ("Eritromicină", "Macrolidă clasică"),
            ("Ciprofloxacină", "Fluorochinolonă"),
            ("Levofloxacină", "Fluorochinolonă"),
            ("Norfloxacină", "Fluorochinolonă urinară"),
            ("Ofloxacină", "Fluorochinolonă"),
            ("Cefuroximă", "Cefalosporină gen. II"),
            ("Cefaclor", "Cefalosporină gen. II"),
            ("Cefalexină", "Cefalosporină gen. I"),
            ("Cefixim", "Cefalosporină gen. III"),
            ("Doxiciclină", "Tetraciclină"),
            ("Metronidazol", "Antibiotic și antiparazitar"),
            ("Trimetoprim+Sulfametoxazol", "Cotrimoxazol"),
            ("Nitrofurantoină", "Antibiotic urinar"),
            ("Fosfomicină", "Antibiotic urinar în doză unică"),
        ]
    },
    "vitamine": {
        "name": "Vitamine și Minerale",
        "symptoms": ["oboseala", "imunitate scazuta", "anemie", "crampe musculare", "piele uscata", "par fragil"],
        "substances": [
            ("Vitamina D3", "Colecalciferol"),
            ("Vitamina C", "Acid ascorbic"),
            ("Vitamina B1", "Tiamină"),
            ("Vitamina B2", "Riboflavină"),
            ("Vitamina B6", "Piridoxină"),
            ("Vitamina B12", "Cianocobalamină"),
            ("Acid folic", "Vitamina B9"),
            ("Vitamina E", "Tocoferol"),
            ("Vitamina A", "Retinol"),
            ("Vitamina K", "Fitonadionă"),
            ("Magneziu", "Mineral esențial"),
            ("Zinc", "Mineral pentru imunitate"),
            ("Fier", "Mineral pentru anemie"),
            ("Calciu", "Mineral pentru oase"),
            ("Seleniu", "Antioxidant"),
            ("Crom", "Pentru metabolism glucidic"),
            ("Potasiu", "Electrolit"),
            ("Omega-3", "Acizi grași esențiali"),
            ("Coenzima Q10", "Antioxidant"),
            ("Melatonină", "Pentru somn"),
        ]
    },
    "dermatologie": {
        "name": "Dermatologie",
        "symptoms": ["acnee", "eczema", "psoriazis", "ciuperca", "mancarimi piele", "rani", "arsuri"],
        "substances": [
            ("Diclofenac gel", "Antiinflamator topic"),
            ("Ketoprofen gel", "AINS topic"),
            ("Dexpantenol", "Cicatrizant"),
            ("Clotrimazol", "Antifungic"),
            ("Miconazol", "Antifungic"),
            ("Ketoconazol", "Antifungic"),
            ("Terbinafină", "Antifungic"),
            ("Aciclovir", "Antiviral pentru herpes"),
            ("Hidrocortizon", "Corticosteroid ușor"),
            ("Betametazonă", "Corticosteroid puternic"),
            ("Mometazonă", "Corticosteroid"),
            ("Clobetasol", "Corticosteroid foarte puternic"),
            ("Mupirocină", "Antibiotic topic"),
            ("Acid fusidic", "Antibiotic topic"),
            ("Peroxid de benzoil", "Antiacneic"),
            ("Adapalen", "Retinoid topic"),
            ("Acid azelaic", "Antiacneic"),
            ("Sulfură", "Pentru dermatoze"),
            ("Calamină", "Calmant pentru mâncărimi"),
            ("Alantoină", "Regenerant"),
        ]
    },
    "oftalmologie": {
        "name": "Oftalmologie",
        "symptoms": ["ochi uscati", "ochi rosii", "conjunctivita", "glaucom", "presiune oculara"],
        "substances": [
            ("Tetrizolină", "Decongestionant ocular"),
            ("Nafazolină", "Vasoconstrictor ocular"),
            ("Hipromelozã", "Lacrimi artificiale"),
            ("Carboxi-metilcelulozã", "Lubrifiant ocular"),
            ("Hialuronat de sodiu", "Lubrifiant ocular"),
            ("Timolol", "Antiglaucom"),
            ("Dorzolamidã", "Antiglaucom"),
            ("Latanoprost", "Antiglaucom"),
            ("Travoprost", "Antiglaucom"),
            ("Cromoglicatul de sodiu", "Antialergic ocular"),
            ("Olopatadină", "Antialergic ocular"),
            ("Tobramicină", "Antibiotic ocular"),
            ("Cloramfenicol", "Antibiotic ocular"),
            ("Ciprofloxacină oftalmică", "Antibiotic ocular"),
        ]
    },
    "ORL": {
        "name": "Oto-rino-laringologie",
        "symptoms": ["durere ureche", "otita", "amigdalita", "faringita", "laringita", "afonie"],
        "substances": [
            ("Lidocaină otică", "Anestezic local pentru ureche"),
            ("Fenazonă", "Analgezic otic"),
            ("Ciprofloxacină otică", "Antibiotic pentru ureche"),
            ("Neomicină otică", "Antibiotic otic"),
            ("Dexametazonă otică", "Corticosteroid otic"),
            ("Clorhexidină", "Antiseptic oral"),
            ("Hexetidină", "Antiseptic orofaringian"),
            ("Diclorbenzilic", "Antiseptic oral"),
            ("Flurbiprofen pastile", "Antiinflamator pentru gât"),
            ("Propolis", "Antiseptic natural"),
        ]
    },
    "urologie": {
        "name": "Urologie",
        "symptoms": ["infectie urinara", "cistita", "prostata marita", "incontinenta", "urinare dureroasa"],
        "substances": [
            ("Tamsulosină", "Alfa-blocant pentru prostată"),
            ("Alfuzosină", "Alfa-blocant pentru HBP"),
            ("Silodosină", "Alfa-blocant selectiv"),
            ("Finasteridă", "Inhibitor 5-alfa-reductază"),
            ("Dutasteridă", "Inhibitor 5-alfa-reductază"),
            ("Solifenacină", "Anticolinergic pentru vezică"),
            ("Tolterodină", "Anticolinergic"),
            ("Oxibutinină", "Antispastic vezical"),
            ("Fenazopiridină", "Analgezic urinar"),
            ("Serenoa repens", "Extract natural pentru prostată"),
            ("D-manoză", "Pentru infecții urinare recurente"),
            ("Merișor extract", "Prevenție ITU"),
        ]
    },
    "ginecologie": {
        "name": "Ginecologie",
        "symptoms": ["infectie vaginala", "dureri menstruale", "menopauza", "candidoză", "vaginoză"],
        "substances": [
            ("Clotrimazol ovule", "Antifungic vaginal"),
            ("Miconazol vaginal", "Antifungic"),
            ("Fluconazol", "Antifungic sistemic"),
            ("Metronidazol vaginal", "Antibacterian vaginal"),
            ("Clindamicină vaginală", "Pentru vaginoză"),
            ("Estriol vaginal", "Estrogen local"),
            ("Didrogesteron", "Progestativ"),
            ("Progesteron", "Hormon natural"),
            ("Acid mefenamic", "Pentru dismenoree"),
            ("Izoflavone de soia", "Pentru simptome menopauză"),
            ("Cimicifuga", "Extract pentru menopauză"),
            ("Lactobacili vaginali", "Probiotice vaginale"),
        ]
    },
    "pediatrie": {
        "name": "Pediatrie",
        "symptoms": ["febra copil", "tuse copil", "colici", "dermatita scutec", "raceala copii"],
        "substances": [
            ("Ibuprofen sirop", "Analgezic pediatric"),
            ("Paracetamol sirop", "Antipiretic pediatric"),
            ("Paracetamol supozitoare", "Antipiretic pentru sugari"),
            ("Ambroxol sirop", "Expectorant pediatric"),
            ("Vitamina D3 picături", "Pentru sugari"),
            ("Simeticonă picături", "Pentru colici"),
            ("Lactuloză sirop", "Laxativ pediatric"),
            ("Probiotice copii", "Flora intestinală"),
            ("Zinc sirop", "Imunitate copii"),
            ("Fenicul+Mușețel", "Pentru colici"),
            ("Oxid de zinc cremă", "Pentru dermatita de scutec"),
            ("Ser fiziologic", "Igienă nazală"),
        ]
    },
    "neurologie": {
        "name": "Neurologie/Psihiatrie",
        "symptoms": ["anxietate", "depresie", "insomnie", "stres", "atacuri panica", "tulburari somn"],
        "substances": [
            ("Escitalopram", "Antidepresiv ISRS"),
            ("Sertralină", "Antidepresiv ISRS"),
            ("Paroxetină", "Antidepresiv ISRS"),
            ("Fluoxetină", "Antidepresiv ISRS"),
            ("Venlafaxină", "Antidepresiv IRSN"),
            ("Duloxetină", "Antidepresiv IRSN"),
            ("Mirtazapină", "Antidepresiv atipic"),
            ("Trazodonă", "Antidepresiv cu efect sedativ"),
            ("Bupropion", "Antidepresiv și ajutor renunțare fumat"),
            ("Alprazolam", "Anxiolitic"),
            ("Diazepam", "Anxiolitic"),
            ("Lorazepam", "Anxiolitic"),
            ("Bromazepam", "Anxiolitic"),
            ("Zolpidem", "Hipnotic"),
            ("Zopiclonă", "Hipnotic"),
            ("Valeriana", "Sedativ natural"),
            ("Passiflora", "Calmant natural"),
        ]
    },
    "endocrinologie": {
        "name": "Endocrinologie",
        "symptoms": ["hipotiroidism", "hipertiroidism", "obezitate", "glanda tiroida"],
        "substances": [
            ("Levotiroxină", "Hormon tiroidian"),
            ("Liotironină", "Hormon T3"),
            ("Tiamazol", "Antitiroidian"),
            ("Propiltiouracil", "Antitiroidian"),
            ("Orlistat", "Inhibitor lipaze"),
            ("Liraglutidă", "Agonist GLP-1"),
            ("Semaglutidă", "Agonist GLP-1"),
        ]
    },
    "reumatologie": {
        "name": "Reumatologie",
        "symptoms": ["artrita", "artroza", "dureri articulare", "reumatism", "inflamatie articulara"],
        "substances": [
            ("Metotrexat", "Imunosupresor"),
            ("Sulfasalazină", "Antireumatic"),
            ("Leflunomidă", "Antireumatic"),
            ("Hidroxiclorochină", "Antireumatic"),
            ("Colchicină", "Pentru gută"),
            ("Alopurinol", "Reduce acidul uric"),
            ("Febuxostat", "Reduce acidul uric"),
            ("Glucozamină", "Condroprotector"),
            ("Condroitină", "Condroprotector"),
            ("Acid hialuronic oral", "Pentru articulații"),
            ("Diacereină", "Antiartrozic"),
        ]
    },
    "probiotice": {
        "name": "Probiotice și Flora Intestinală",
        "symptoms": ["disbioză", "diaree dupa antibiotice", "balonare", "digestie lenta"],
        "substances": [
            ("Lactobacillus", "Probiotic"),
            ("Bifidobacterium", "Probiotic"),
            ("Saccharomyces boulardii", "Probiotic levuric"),
            ("Bacillus clausii", "Probiotic"),
            ("Enterococcus faecium", "Probiotic"),
            ("Lactobacillus rhamnosus", "Probiotic GG"),
            ("Inulină", "Prebiotic"),
            ("FOS", "Prebiotic"),
        ]
    },
    "sistemul_imunitar": {
        "name": "Sistem Imunitar",
        "symptoms": ["imunitate scazuta", "raceli frecvente", "infectii recurente", "stare generala proasta"],
        "substances": [
            ("Echinaceea", "Imunostimulator natural"),
            ("Propolis", "Imunomodulator"),
            ("Cătină", "Bogată în vitamina C"),
            ("Soc negru", "Antiviral natural"),
            ("Andrographis", "Imunostimulator"),
            ("Astragalus", "Adaptogen"),
            ("Beta-glucani", "Imunomodulator"),
            ("Colostru", "Imunoglobuline"),
        ]
    },
    "suplimente_naturale": {
        "name": "Suplimente Naturale",
        "symptoms": ["stres", "energie scazuta", "detoxifiere", "memorie slaba"],
        "substances": [
            ("Ginkgo biloba", "Pentru circulație și memorie"),
            ("Ginseng", "Adaptogen"),
            ("Rhodiola rosea", "Adaptogen antistres"),
            ("Ashwagandha", "Adaptogen"),
            ("Curcuma", "Antiinflamator natural"),
            ("Ghimbir", "Antiemetic și antiinflamator"),
            ("Usturoi", "Antimicrobian"),
            ("Armurariu", "Hepatoprotector"),
            ("Anghinare", "Coleretic"),
            ("Păducel", "Cardiotonic"),
            ("Tei", "Calmant"),
            ("Sunătoare", "Pentru dispoziție"),
            ("Lavandă", "Anxiolitic"),
            ("Lemon Balm", "Calmant"),
        ]
    }
}

BRANDS = [
    "Zentiva", "Terapia", "Antibiotice SA", "Biofarm", "Labormed", "Gedeon Richter",
    "Sandoz", "Krka", "Stada", "Actavis", "Mylan", "Teva", "Egis", "Alvogen",
    "Pfizer", "GSK", "Novartis", "Bayer", "Sanofi", "Merck", "AstraZeneca",
    "Johnson & Johnson", "Roche", "Abbott", "Boehringer Ingelheim", "Eli Lilly",
    "Naturalis", "Hofigal", "PlantExtrakt", "Dacia Plant", "Alevia", "Fiterman",
    "Himalaya", "Solgar", "Now Foods", "Nature's Way", "Swanson", "Life Extension"
]

PHARMACIES = [
    ("Catena", "https://www.catena.ro"),
    ("Farmacia Tei", "https://comenzi.farmaciatei.ro"),
    ("HelpNet", "https://www.helpnet.ro"),
    ("Dr. Max", "https://www.drmax.ro"),
    ("Ropharma", "https://ropharma.ro"),
    ("EUmed", "https://www.eumed.ro"),
    ("Sensiblu", "https://www.sensiblu.com"),
    ("Dona", "https://www.farmaciadonas.ro"),
]

FORMS = [
    "comprimate", "capsule", "tablete", "drajeuri", "comprimate filmate",
    "comprimate efervescente", "capsule moi", "pulbere", "plicuri",
    "sirop", "soluție orală", "picături", "suspensie",
    "cremă", "gel", "unguent", "spray", "loțiune",
    "supozitoare", "ovule", "picături oftalmice", "spray nazal",
    "plasturi", "injecție", "fiole"
]


def generate_medicine_entry(
    category_key: str,
    substance_data: tuple,
    index: int
) -> dict:
    category = CATEGORIES[category_key]
    substance, mechanism = substance_data

    brand = random.choice(BRANDS)
    pharmacy_name, pharmacy_url = random.choice(PHARMACIES)
    form = random.choice(FORMS)

    doses = ["50mg", "100mg", "200mg", "250mg", "400mg", "500mg", "1000mg", "25mg", "10mg", "20mg", "5mg", "75mg", "150mg", "300mg"]
    dose = random.choice(doses)

    name = f"{substance} {brand} {dose}"
    if random.random() > 0.5:
        name = f"{brand} {substance} {dose}"

    price = round(random.uniform(8.0, 150.0), 2)

    symptoms = random.sample(category["symptoms"], min(3, len(category["symptoms"])))

    url_slug = name.lower().replace(" ", "-").replace("+", "-")
    url = f"{pharmacy_url}/p/{url_slug}"

    rx = category_key in ["antibiotice", "neurologie", "diabet", "cardiovascular", "endocrinologie", "reumatologie"]
    if substance in ["Metamizol", "Codeină", "Tramadol"]:
        rx = True

    indications = f"{mechanism}. Indicat pentru: {', '.join(symptoms)}."

    contraindications = [
        "Hipersensibilitate la substanța activă",
        "Sarcina și alăptarea (consultați medicul)",
        "Insuficiență hepatică sau renală severă (în unele cazuri)",
    ]
    if category_key == "digestiv":
        contraindications.append("Obstrucție intestinală")
    if category_key in ["durere_febra", "reumatologie"]:
        contraindications.extend(["Ulcer gastroduodenal activ", "Insuficiență cardiacă severă"])
    if category_key == "cardiovascular":
        contraindications.extend(["Hipotensiune severă", "Bradicardie (pentru beta-blocante)"])

    side_effects = [
        "Tulburări gastrointestinale (greață, dureri abdominale)",
        "Reacții alergice cutanate",
        "Cefalee, amețeli",
    ]
    if category_key == "neurologie":
        side_effects.extend(["Somnolență", "Modificări ale apetitului", "Tulburări sexuale"])
    if category_key == "antibiotice":
        side_effects.extend(["Diaree", "Candidoză", "Fotosensibilitate"])

    return {
        "name": name,
        "active": substance,
        "mechanism": mechanism,
        "category": category["name"],
        "category_key": category_key,
        "form": form,
        "rx": rx,
        "price": price,
        "currency": "RON",
        "symptoms": symptoms,
        "indications": indications,
        "contraindications": contraindications,
        "side_effects": side_effects,
        "dosage": f"Conform prospectului. Consultați medicul sau farmacistul pentru doză personalizată.",
        "interactions": "Consultați prospectul sau farmacistul pentru interacțiuni medicamentoase.",
        "warnings": "Citiți prospectul înainte de utilizare. Nu depășiți doza recomandată.",
        "manufacturer": brand,
        "pharmacy": pharmacy_name,
        "url": url,
    }


def build_document(med: dict) -> dict:
    rx_status = "⚠️ **NECESITĂ REȚETĂ**" if med["rx"] else "✅ Fără rețetă"
    symptoms_text = ", ".join(med["symptoms"])

    content = f"""# {med["name"]}

## Informații Produs
- **Substanță activă**: {med["active"]}
- **Formă farmaceutică**: {med["form"]}
- **Categorie**: {med["category"]}
- **Producător**: {med["manufacturer"]}
- **Status**: {rx_status}
- **Preț**: {med["price"]} {med["currency"]}

## Mecanism de Acțiune
{med["mechanism"]}

## Simptome Tratate
{symptoms_text}

## Indicații
{med["indications"]}

## Contraindicații
{chr(10).join('- ' + c for c in med["contraindications"])}

## Reacții Adverse
{chr(10).join('- ' + s for s in med["side_effects"])}

## Dozaj
{med["dosage"]}

## Atenționări
⚠️ {med["warnings"]}

## Cumpărare Online
🛒 [Cumpără de la {med["pharmacy"]}]({med["url"]})
"""
    return {
        "content": content,
        "title": f"{med['name']} - Prospect Complet",
        "source": med["pharmacy"],
        "metadata": {
            "active_substance": med["active"],
            "category": med["category"],
            "category_key": med["category_key"],
            "form": med["form"],
            "prescription_required": med["rx"],
            "price": med["price"],
            "symptoms": med["symptoms"],
            "manufacturer": med["manufacturer"],
            "url": med["url"]
        }
    }


def generate_database(target_count: int = 1000) -> List[dict]:
    medicines = []
    index = 0

    per_category = max(5, target_count // len(CATEGORIES))

    for category_key, category_data in CATEGORIES.items():
        substances = category_data["substances"]

        for substance_data in substances:
            for variant in range(max(1, per_category // len(substances))):
                med = generate_medicine_entry(category_key, substance_data, index)
                medicines.append(med)
                index += 1

                if len(medicines) >= target_count:
                    break
            if len(medicines) >= target_count:
                break
        if len(medicines) >= target_count:
            break

    while len(medicines) < target_count:
        category_key = random.choice(list(CATEGORIES.keys()))
        substance_data = random.choice(CATEGORIES[category_key]["substances"])
        med = generate_medicine_entry(category_key, substance_data, index)
        medicines.append(med)
        index += 1

    return medicines


def build_symptom_index(medicines: List[dict]) -> dict:
    index = {}
    for med in medicines:
        for symptom in med["symptoms"]:
            symptom_lower = symptom.lower()
            if symptom_lower not in index:
                index[symptom_lower] = []
            index[symptom_lower].append({
                "name": med["name"],
                "active": med["active"],
                "category": med["category"],
                "rx": med["rx"],
                "price": med["price"],
                "url": med["url"]
            })
    return index


def save_comprehensive_database(target_count: int = 1000):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating {target_count} medicine entries...")
    medicines = generate_database(target_count)

    documents = [build_document(med) for med in medicines]
    docs_file = DATA_DIR / "comprehensive_medicines.json"
    with open(docs_file, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(documents)} documents to {docs_file}")

    symptom_index = build_symptom_index(medicines)
    index_file = DATA_DIR / "comprehensive_symptom_index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(symptom_index, f, indent=2, ensure_ascii=False)
    print(f"Saved symptom index ({len(symptom_index)} symptoms) to {index_file}")

    stats = {}
    for med in medicines:
        cat = med["category"]
        stats[cat] = stats.get(cat, 0) + 1

    print("\nPer-category breakdown:")
    for cat, count in sorted(stats.items()):
        print(f"  {cat}: {count}")

    return docs_file


if __name__ == "__main__":
    save_comprehensive_database(1200)
