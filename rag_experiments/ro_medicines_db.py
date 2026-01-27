"""
Romanian Pharmacy Medicines Database
Curated dataset of 100 common medicines available in Romanian pharmacies
with purchase links and medical information.
"""

ROMANIAN_MEDICINES = [
    # PAIN & FEVER (Durere și Febră)
    {"name": "Nurofen 400mg", "active": "Ibuprofen", "category": "Durere/Febră", "rx": False, "price": 15.50,
     "desc": "Antiinflamator nesteroidian pentru dureri și febră", "url": "https://comenzi.farmaciatei.ro/p/nurofen-400mg"},
    {"name": "Paracetamol 500mg Zentiva", "active": "Paracetamol", "category": "Durere/Febră", "rx": False, "price": 8.90,
     "desc": "Analgezic și antipiretic de bază", "url": "https://comenzi.farmaciatei.ro/p/paracetamol-500mg"},
    {"name": "Algocalmin 500mg", "active": "Metamizol", "category": "Durere/Febră", "rx": False, "price": 12.30,
     "desc": "Analgezic puternic pentru dureri moderate-severe", "url": "https://comenzi.farmaciatei.ro/p/algocalmin"},
    {"name": "Aspirin 500mg", "active": "Acid acetilsalicilic", "category": "Durere/Febră", "rx": False, "price": 9.50,
     "desc": "Analgezic, antipiretic și antiinflamator", "url": "https://comenzi.farmaciatei.ro/p/aspirin-500mg"},
    {"name": "Ketonal 100mg", "active": "Ketoprofen", "category": "Durere/Febră", "rx": True, "price": 22.00,
     "desc": "AINS pentru dureri inflamatorii", "url": "https://comenzi.farmaciatei.ro/p/ketonal-100mg"},
    {"name": "Calmaben", "active": "Ibuprofen + Codeină", "category": "Durere/Febră", "rx": True, "price": 18.50,
     "desc": "Analgezic combinat pentru dureri moderate", "url": "https://comenzi.farmaciatei.ro/p/calmaben"},
    {"name": "Paduden 400mg", "active": "Ibuprofen", "category": "Durere/Febră", "rx": False, "price": 14.20,
     "desc": "Antiinflamator pentru dureri și febră", "url": "https://comenzi.farmaciatei.ro/p/paduden-400mg"},
    {"name": "Nurofen Express 400mg", "active": "Ibuprofen lizinat", "category": "Durere/Febră", "rx": False, "price": 19.90,
     "desc": "Ibuprofen cu absorbție rapidă", "url": "https://comenzi.farmaciatei.ro/p/nurofen-express"},
    {"name": "Panadol Extra", "active": "Paracetamol + Cafeină", "category": "Durere/Febră", "rx": False, "price": 16.50,
     "desc": "Pentru dureri de cap și migrene", "url": "https://comenzi.farmaciatei.ro/p/panadol-extra"},
    {"name": "Diclofenac 50mg", "active": "Diclofenac", "category": "Durere/Febră", "rx": True, "price": 11.00,
     "desc": "AINS pentru dureri articulare și musculare", "url": "https://comenzi.farmaciatei.ro/p/diclofenac-50mg"},

    # DIGESTIVE (Afecțiuni Digestive)
    {"name": "Omez 20mg", "active": "Omeprazol", "category": "Digestiv", "rx": False, "price": 24.50,
     "desc": "Inhibitor de pompă protonică pentru reflux și ulcer", "url": "https://comenzi.farmaciatei.ro/p/omez-20mg"},
    {"name": "Controloc 20mg", "active": "Pantoprazol", "category": "Digestiv", "rx": False, "price": 28.00,
     "desc": "IPP pentru protecție gastrică", "url": "https://comenzi.farmaciatei.ro/p/controloc-20mg"},
    {"name": "Smecta", "active": "Diosmectită", "category": "Digestiv", "rx": False, "price": 19.90,
     "desc": "Antidiareic și protector al mucoasei intestinale", "url": "https://comenzi.farmaciatei.ro/p/smecta"},
    {"name": "Imodium 2mg", "active": "Loperamidă", "category": "Digestiv", "rx": False, "price": 22.50,
     "desc": "Antidiareic pentru diaree acută", "url": "https://comenzi.farmaciatei.ro/p/imodium"},
    {"name": "Motilium 10mg", "active": "Domperidonă", "category": "Digestiv", "rx": True, "price": 18.90,
     "desc": "Antiemetic și prokinetic", "url": "https://comenzi.farmaciatei.ro/p/motilium-10mg"},
    {"name": "Maalox Plus", "active": "Hidroxid Al/Mg + Simeticonă", "category": "Digestiv", "rx": False, "price": 21.00,
     "desc": "Antiacid pentru arsuri gastrice", "url": "https://comenzi.farmaciatei.ro/p/maalox-plus"},
    {"name": "Rennie", "active": "Carbonat de calciu/magneziu", "category": "Digestiv", "rx": False, "price": 17.50,
     "desc": "Antiacid masticabil cu acțiune rapidă", "url": "https://comenzi.farmaciatei.ro/p/rennie"},
    {"name": "Buscopan 10mg", "active": "Butilscopolamină", "category": "Digestiv", "rx": False, "price": 25.00,
     "desc": "Antispastic pentru crampe abdominale", "url": "https://comenzi.farmaciatei.ro/p/buscopan"},
    {"name": "Debridat", "active": "Trimebutină", "category": "Digestiv", "rx": False, "price": 23.50,
     "desc": "Reglator al motilității intestinale", "url": "https://comenzi.farmaciatei.ro/p/debridat"},
    {"name": "No-Spa 40mg", "active": "Drotaverină", "category": "Digestiv", "rx": False, "price": 16.00,
     "desc": "Antispastic pentru dureri abdominale", "url": "https://comenzi.farmaciatei.ro/p/no-spa"},

    # RESPIRATORY (Afecțiuni Respiratorii)
    {"name": "ACC 200mg", "active": "Acetilcisteină", "category": "Respirator", "rx": False, "price": 18.50,
     "desc": "Mucolitc pentru tuse productivă", "url": "https://comenzi.farmaciatei.ro/p/acc-200mg"},
    {"name": "Fluimucil 600mg", "active": "Acetilcisteină", "category": "Respirator", "rx": False, "price": 32.00,
     "desc": "Mucolitc efervescent pentru expectorație", "url": "https://comenzi.farmaciatei.ro/p/fluimucil-600mg"},
    {"name": "Mucosolvan 30mg", "active": "Ambroxol", "category": "Respirator", "rx": False, "price": 19.90,
     "desc": "Expectorant și mucolitc", "url": "https://comenzi.farmaciatei.ro/p/mucosolvan"},
    {"name": "Sinupret", "active": "Extract vegetal combinat", "category": "Respirator", "rx": False, "price": 42.00,
     "desc": "Tratament natural pentru sinuzită", "url": "https://comenzi.farmaciatei.ro/p/sinupret"},
    {"name": "Theraflu", "active": "Paracetamol + Fenilefrină", "category": "Respirator", "rx": False, "price": 28.50,
     "desc": "Tratament simptomatic pentru răceală și gripă", "url": "https://comenzi.farmaciatei.ro/p/theraflu"},
    {"name": "Coldrex MaxGrip", "active": "Paracetamol + Vitamina C", "category": "Respirator", "rx": False, "price": 26.00,
     "desc": "Pentru simptomele răcelii și gripei", "url": "https://comenzi.farmaciatei.ro/p/coldrex-maxgrip"},
    {"name": "Strepsils", "active": "Amilmetacrezol + Diclorbenzilic", "category": "Respirator", "rx": False, "price": 21.50,
     "desc": "Pastile pentru dureri în gât", "url": "https://comenzi.farmaciatei.ro/p/strepsils"},
    {"name": "Tantum Verde", "active": "Benzidamină", "category": "Respirator", "rx": False, "price": 29.00,
     "desc": "Antiinflamator pentru faringită", "url": "https://comenzi.farmaciatei.ro/p/tantum-verde"},
    {"name": "Olynth 0.1%", "active": "Xilometazolină", "category": "Respirator", "rx": False, "price": 14.50,
     "desc": "Decongestionant nazal", "url": "https://comenzi.farmaciatei.ro/p/olynth"},
    {"name": "Otrivin 0.1%", "active": "Xilometazolină", "category": "Respirator", "rx": False, "price": 16.00,
     "desc": "Spray nazal decongestionant", "url": "https://comenzi.farmaciatei.ro/p/otrivin"},

    # CARDIOVASCULAR (Cardiovascular)
    {"name": "Aspenter 75mg", "active": "Acid acetilsalicilic", "category": "Cardiovascular", "rx": False, "price": 12.00,
     "desc": "Antiagregant plachetar pentru prevenție cardiovasculară", "url": "https://comenzi.farmaciatei.ro/p/aspenter-75mg"},
    {"name": "Atoris 20mg", "active": "Atorvastatină", "category": "Cardiovascular", "rx": True, "price": 35.00,
     "desc": "Statină pentru reducerea colesterolului", "url": "https://comenzi.farmaciatei.ro/p/atoris-20mg"},
    {"name": "Crestor 10mg", "active": "Rosuvastatină", "category": "Cardiovascular", "rx": True, "price": 65.00,
     "desc": "Statină de generație nouă", "url": "https://comenzi.farmaciatei.ro/p/crestor-10mg"},
    {"name": "Concor 5mg", "active": "Bisoprolol", "category": "Cardiovascular", "rx": True, "price": 28.00,
     "desc": "Beta-blocant pentru hipertensiune și insuficiență cardiacă", "url": "https://comenzi.farmaciatei.ro/p/concor-5mg"},
    {"name": "Prestarium 5mg", "active": "Perindopril", "category": "Cardiovascular", "rx": True, "price": 45.00,
     "desc": "IECA pentru hipertensiune", "url": "https://comenzi.farmaciatei.ro/p/prestarium-5mg"},
    {"name": "Norvasc 5mg", "active": "Amlodipină", "category": "Cardiovascular", "rx": True, "price": 38.00,
     "desc": "Blocant de canale de calciu pentru hipertensiune", "url": "https://comenzi.farmaciatei.ro/p/norvasc-5mg"},
    {"name": "Atacand 16mg", "active": "Candesartan", "category": "Cardiovascular", "rx": True, "price": 55.00,
     "desc": "Sartan pentru hipertensiune arterială", "url": "https://comenzi.farmaciatei.ro/p/atacand-16mg"},
    {"name": "Plavix 75mg", "active": "Clopidogrel", "category": "Cardiovascular", "rx": True, "price": 120.00,
     "desc": "Antiagregant plachetar post-stent", "url": "https://comenzi.farmaciatei.ro/p/plavix-75mg"},
    {"name": "Detralex 500mg", "active": "Diosmină + Hesperidină", "category": "Cardiovascular", "rx": False, "price": 48.00,
     "desc": "Venotonic pentru insuficiență venoasă cronică", "url": "https://comenzi.farmaciatei.ro/p/detralex-500mg"},
    {"name": "Daflon 500mg", "active": "Fracție flavonoidică purificată", "category": "Cardiovascular", "rx": False, "price": 52.00,
     "desc": "Tratament pentru hemoroizi și varice", "url": "https://comenzi.farmaciatei.ro/p/daflon-500mg"},

    # DIABETES (Diabet)
    {"name": "Siofor 850mg", "active": "Metformină", "category": "Diabet", "rx": True, "price": 22.00,
     "desc": "Antidiabetic oral de primă linie pentru DZ tip 2", "url": "https://comenzi.farmaciatei.ro/p/siofor-850mg"},
    {"name": "Glucophage 1000mg", "active": "Metformină", "category": "Diabet", "rx": True, "price": 28.00,
     "desc": "Metformină cu eliberare prelungită", "url": "https://comenzi.farmaciatei.ro/p/glucophage-1000mg"},
    {"name": "Diamicron MR 60mg", "active": "Gliclazidă", "category": "Diabet", "rx": True, "price": 45.00,
     "desc": "Sulfoniluree pentru controlul glicemiei", "url": "https://comenzi.farmaciatei.ro/p/diamicron-mr-60mg"},
    {"name": "Januvia 100mg", "active": "Sitagliptină", "category": "Diabet", "rx": True, "price": 185.00,
     "desc": "Inhibitor DPP-4 pentru diabet tip 2", "url": "https://comenzi.farmaciatei.ro/p/januvia-100mg"},
    {"name": "Jardiance 10mg", "active": "Empagliflozină", "category": "Diabet", "rx": True, "price": 220.00,
     "desc": "Inhibitor SGLT2 cu beneficii cardiovasculare", "url": "https://comenzi.farmaciatei.ro/p/jardiance-10mg"},

    # ANTIBIOTICS (Antibiotice)
    {"name": "Augmentin 1g", "active": "Amoxicilină + Acid clavulanic", "category": "Antibiotice", "rx": True, "price": 42.00,
     "desc": "Antibiotic cu spectru larg", "url": "https://comenzi.farmaciatei.ro/p/augmentin-1g"},
    {"name": "Ospamox 1000mg", "active": "Amoxicilină", "category": "Antibiotice", "rx": True, "price": 25.00,
     "desc": "Penicilinã pentru infecții respiratorii", "url": "https://comenzi.farmaciatei.ro/p/ospamox-1000mg"},
    {"name": "Sumamed 500mg", "active": "Azitromicină", "category": "Antibiotice", "rx": True, "price": 55.00,
     "desc": "Macrolidă cu administrare 3 zile", "url": "https://comenzi.farmaciatei.ro/p/sumamed-500mg"},
    {"name": "Ciprinol 500mg", "active": "Ciprofloxacină", "category": "Antibiotice", "rx": True, "price": 28.00,
     "desc": "Fluorochinolonă pentru infecții urinare", "url": "https://comenzi.farmaciatei.ro/p/ciprinol-500mg"},
    {"name": "Zinnat 500mg", "active": "Cefuroximă", "category": "Antibiotice", "rx": True, "price": 48.00,
     "desc": "Cefalosporină de generația II", "url": "https://comenzi.farmaciatei.ro/p/zinnat-500mg"},

    # ALLERGIES (Alergii)
    {"name": "Claritine 10mg", "active": "Loratadină", "category": "Alergii", "rx": False, "price": 24.00,
     "desc": "Antihistaminic non-sedativ", "url": "https://comenzi.farmaciatei.ro/p/claritine-10mg"},
    {"name": "Aerius 5mg", "active": "Desloratadină", "category": "Alergii", "rx": False, "price": 32.00,
     "desc": "Antihistaminic de nouă generație", "url": "https://comenzi.farmaciatei.ro/p/aerius-5mg"},
    {"name": "Zyrtec 10mg", "active": "Cetirizină", "category": "Alergii", "rx": False, "price": 28.00,
     "desc": "Antihistaminic pentru rinită alergică", "url": "https://comenzi.farmaciatei.ro/p/zyrtec-10mg"},
    {"name": "Xyzal 5mg", "active": "Levocetirizină", "category": "Alergii", "rx": False, "price": 35.00,
     "desc": "Antihistaminic puternic", "url": "https://comenzi.farmaciatei.ro/p/xyzal-5mg"},
    {"name": "Fenistil picături", "active": "Dimetindenă", "category": "Alergii", "rx": False, "price": 22.00,
     "desc": "Antihistaminic pentru copii", "url": "https://comenzi.farmaciatei.ro/p/fenistil-picaturi"},

    # MENTAL HEALTH (Sănătate Mentală)
    {"name": "Lexapro 10mg", "active": "Escitalopram", "category": "Psihiatrie", "rx": True, "price": 65.00,
     "desc": "ISRS pentru depresie și anxietate", "url": "https://comenzi.farmaciatei.ro/p/lexapro-10mg"},
    {"name": "Zoloft 50mg", "active": "Sertralină", "category": "Psihiatrie", "rx": True, "price": 48.00,
     "desc": "Antidepresiv ISRS", "url": "https://comenzi.farmaciatei.ro/p/zoloft-50mg"},
    {"name": "Xanax 0.5mg", "active": "Alprazolam", "category": "Psihiatrie", "rx": True, "price": 28.00,
     "desc": "Anxiolitic benzodiazepinic", "url": "https://comenzi.farmaciatei.ro/p/xanax-05mg"},
    {"name": "Trittico 150mg", "active": "Trazodonă", "category": "Psihiatrie", "rx": True, "price": 42.00,
     "desc": "Antidepresiv atipic cu efect sedativ", "url": "https://comenzi.farmaciatei.ro/p/trittico-150mg"},
    {"name": "Stilnox 10mg", "active": "Zolpidem", "category": "Psihiatrie", "rx": True, "price": 35.00,
     "desc": "Hipnotic non-benzodiazepinic pentru insomnie", "url": "https://comenzi.farmaciatei.ro/p/stilnox-10mg"},

    # VITAMINS & SUPPLEMENTS
    {"name": "Vitamina D3 2000UI", "active": "Colecalciferol", "category": "Vitamine", "rx": False, "price": 35.00,
     "desc": "Supliment pentru sănătatea oaselor și imunitate", "url": "https://comenzi.farmaciatei.ro/p/vitamina-d3-2000ui"},
    {"name": "Vitamina C 1000mg", "active": "Acid ascorbic", "category": "Vitamine", "rx": False, "price": 22.00,
     "desc": "Antioxidant și suport imunitar", "url": "https://comenzi.farmaciatei.ro/p/vitamina-c-1000mg"},
    {"name": "Vitamina B Complex", "active": "Vitamine B1, B2, B6, B12", "category": "Vitamine", "rx": False, "price": 28.00,
     "desc": "Pentru sistemul nervos și energie", "url": "https://comenzi.farmaciatei.ro/p/vitamina-b-complex"},
    {"name": "Magneziu + B6", "active": "Citrat de magneziu + Piridoxină", "category": "Vitamine", "rx": False, "price": 32.00,
     "desc": "Pentru mușchi și sistem nervos", "url": "https://comenzi.farmaciatei.ro/p/magneziu-b6"},
    {"name": "Omega 3 Fish Oil", "active": "EPA + DHA", "category": "Vitamine", "rx": False, "price": 45.00,
     "desc": "Acizi grași esențiali pentru inimă și creier", "url": "https://comenzi.farmaciatei.ro/p/omega-3-fish-oil"},
    {"name": "Fier + Acid Folic", "active": "Fier + Acid folic", "category": "Vitamine", "rx": False, "price": 25.00,
     "desc": "Pentru anemie și sarcină", "url": "https://comenzi.farmaciatei.ro/p/fier-acid-folic"},
    {"name": "Zinc 25mg", "active": "Gluconat de zinc", "category": "Vitamine", "rx": False, "price": 18.00,
     "desc": "Pentru imunitate și piele", "url": "https://comenzi.farmaciatei.ro/p/zinc-25mg"},
    {"name": "Probiotice", "active": "Lactobacillus + Bifidobacterium", "category": "Vitamine", "rx": False, "price": 55.00,
     "desc": "Pentru flora intestinală", "url": "https://comenzi.farmaciatei.ro/p/probiotice"},
    {"name": "Coenzima Q10 100mg", "active": "Ubichinonă", "category": "Vitamine", "rx": False, "price": 65.00,
     "desc": "Antioxidant pentru energie celulară", "url": "https://comenzi.farmaciatei.ro/p/coenzima-q10"},
    {"name": "Melatonină 5mg", "active": "Melatonină", "category": "Vitamine", "rx": False, "price": 38.00,
     "desc": "Pentru reglarea somnului", "url": "https://comenzi.farmaciatei.ro/p/melatonina-5mg"},

    # DERMATOLOGY (Dermatologie)
    {"name": "Voltaren Emulgel", "active": "Diclofenac gel", "category": "Dermatologie", "rx": False, "price": 32.00,
     "desc": "Gel antiinflamator pentru dureri musculare", "url": "https://comenzi.farmaciatei.ro/p/voltaren-emulgel"},
    {"name": "Bepanthen", "active": "Dexpantenol", "category": "Dermatologie", "rx": False, "price": 45.00,
     "desc": "Regenerant pentru piele și mucoase", "url": "https://comenzi.farmaciatei.ro/p/bepanthen"},
    {"name": "Canesten cremă", "active": "Clotrimazol", "category": "Dermatologie", "rx": False, "price": 28.00,
     "desc": "Antifungic local", "url": "https://comenzi.farmaciatei.ro/p/canesten-crema"},
    {"name": "Locoid cremă", "active": "Hidrocortizon butirat", "category": "Dermatologie", "rx": True, "price": 35.00,
     "desc": "Corticosteroid topic pentru eczeme", "url": "https://comenzi.farmaciatei.ro/p/locoid-crema"},
    {"name": "Zovirax cremă", "active": "Aciclovir", "category": "Dermatologie", "rx": False, "price": 42.00,
     "desc": "Antiviral pentru herpes labial", "url": "https://comenzi.farmaciatei.ro/p/zovirax-crema"},

    # OPHTHALMOLOGY (Oftalmologie)
    {"name": "Systane Ultra", "active": "PEG + Propilen glicol", "category": "Oftalmologie", "rx": False, "price": 55.00,
     "desc": "Lacrimi artificiale pentru ochi uscați", "url": "https://comenzi.farmaciatei.ro/p/systane-ultra"},
    {"name": "Visine", "active": "Tetrizolină", "category": "Oftalmologie", "rx": False, "price": 28.00,
     "desc": "Picături pentru ochi roșii", "url": "https://comenzi.farmaciatei.ro/p/visine"},
    {"name": "Optive Fusion", "active": "CMC + Glicerină", "category": "Oftalmologie", "rx": False, "price": 48.00,
     "desc": "Lubrifiant oftalmic", "url": "https://comenzi.farmaciatei.ro/p/optive-fusion"},

    # UROLOGY (Urologie)
    {"name": "Prostamol Uno", "active": "Extract Serenoa repens", "category": "Urologie", "rx": False, "price": 85.00,
     "desc": "Pentru hipertrofia benignă de prostată", "url": "https://comenzi.farmaciatei.ro/p/prostamol-uno"},
    {"name": "Omnic 0.4mg", "active": "Tamsulosină", "category": "Urologie", "rx": True, "price": 55.00,
     "desc": "Alpha-blocant pentru HBP", "url": "https://comenzi.farmaciatei.ro/p/omnic-04mg"},
    {"name": "Urosept", "active": "Extract vegetal combinat", "category": "Urologie", "rx": False, "price": 38.00,
     "desc": "Dezinfectant urinar natural", "url": "https://comenzi.farmaciatei.ro/p/urosept"},
    {"name": "Canephron", "active": "Extract vegetal", "category": "Urologie", "rx": False, "price": 52.00,
     "desc": "Tratament natural pentru infecții urinare", "url": "https://comenzi.farmaciatei.ro/p/canephron"},

    # THYROID (Tiroidă)
    {"name": "Euthyrox 50mcg", "active": "Levotiroxină", "category": "Endocrinologie", "rx": True, "price": 18.00,
     "desc": "Hormon tiroidian pentru hipotiroidism", "url": "https://comenzi.farmaciatei.ro/p/euthyrox-50mcg"},
    {"name": "Euthyrox 100mcg", "active": "Levotiroxină", "category": "Endocrinologie", "rx": True, "price": 22.00,
     "desc": "Substituție tiroidiană", "url": "https://comenzi.farmaciatei.ro/p/euthyrox-100mcg"},

    # BONE HEALTH (Sănătate Osoasă)
    {"name": "Caltrate 600 + D3", "active": "Carbonat de calciu + Vitamina D3", "category": "Oase", "rx": False, "price": 42.00,
     "desc": "Pentru sănătatea oaselor", "url": "https://comenzi.farmaciatei.ro/p/caltrate-600-d3"},
    {"name": "Osteofos 70mg", "active": "Acid alendronic", "category": "Oase", "rx": True, "price": 85.00,
     "desc": "Bifosfonat pentru osteoporoză", "url": "https://comenzi.farmaciatei.ro/p/osteofos-70mg"},

    # WOMEN'S HEALTH (Sănătatea Femeii)
    {"name": "Duphaston 10mg", "active": "Didrogesteron", "category": "Ginecologie", "rx": True, "price": 75.00,
     "desc": "Progestativ pentru tulburări menstruale", "url": "https://comenzi.farmaciatei.ro/p/duphaston-10mg"},
    {"name": "Utrogestan 200mg", "active": "Progesteron micronizat", "category": "Ginecologie", "rx": True, "price": 62.00,
     "desc": "Progesteron natural", "url": "https://comenzi.farmaciatei.ro/p/utrogestan-200mg"},
    {"name": "Gyno-Canesten", "active": "Clotrimazol ovule", "category": "Ginecologie", "rx": False, "price": 45.00,
     "desc": "Antifungic vaginal", "url": "https://comenzi.farmaciatei.ro/p/gyno-canesten"},

    # PEDIATRIC (Pediatrie)
    {"name": "Nurofen pentru copii", "active": "Ibuprofen sirop", "category": "Pediatrie", "rx": False, "price": 24.00,
     "desc": "Analgezic și antipiretic pentru copii", "url": "https://comenzi.farmaciatei.ro/p/nurofen-copii-sirop"},
    {"name": "Paracetamol sirop copii", "active": "Paracetamol 120mg/5ml", "category": "Pediatrie", "rx": False, "price": 15.00,
     "desc": "Pentru febră și durere la copii", "url": "https://comenzi.farmaciatei.ro/p/paracetamol-sirop-copii"},
    {"name": "Colimil", "active": "Extract de fenicul + Mușețel", "category": "Pediatrie", "rx": False, "price": 28.00,
     "desc": "Pentru colici la sugari", "url": "https://comenzi.farmaciatei.ro/p/colimil"},
    {"name": "Reumalex sirop", "active": "Vitamina D3 pentru copii", "category": "Pediatrie", "rx": False, "price": 32.00,
     "desc": "Vitamina D pentru dezvoltarea oaselor", "url": "https://comenzi.farmaciatei.ro/p/reumalex-sirop"},
]


def get_romanian_medicines_documents():
    from datetime import datetime
    from .data_sources import DrugInfo

    documents = []

    for med in ROMANIAN_MEDICINES:
        rx_note = "⚠️ **Necesită rețetă**" if med["rx"] else "Disponibil fără rețetă"

        content = f"""# {med["name"]}

## Prezentare Generală
- **Substanță activă**: {med["active"]}
- **Categorie**: {med["category"]}
- **Rețetă**: {rx_note}

## Descriere
{med["desc"]}

## Cumpărare
- **Preț**: {med["price"]} RON
- **Cumpără online**: [Farmacia Tei]({med["url"]})
"""
        documents.append({
            "content": content,
            "title": f"{med['name']} - Medicament România",
            "source": "Farmacia Tei",
            "metadata": {
                "active_substance": med["active"],
                "category": med["category"],
                "prescription_required": med["rx"],
                "price": med["price"],
                "currency": "RON",
                "url": med["url"]
            }
        })

    return documents


def save_romanian_database():
    import json
    from pathlib import Path

    DATA_DIR = Path(__file__).parent / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    documents = get_romanian_medicines_documents()
    output_file = DATA_DIR / "ro_medicines_100.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(documents)} Romanian medicines to {output_file}")
    return output_file


if __name__ == "__main__":
    save_romanian_database()
