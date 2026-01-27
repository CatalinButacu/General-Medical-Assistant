"""
Romanian Medicine Leaflets Database with Full Prospectus Information
Contains detailed medical information for symptom-based search
"""

MEDICINE_LEAFLETS = [
    # PAIN & FEVER
    {
        "name": "Nurofen 400mg",
        "active": "Ibuprofen 400mg",
        "category": "Analgezice/Antiinflamatoare",
        "rx": False,
        "price": 15.50,
        "symptoms": ["durere de cap", "migrena", "dureri menstruale", "dureri musculare", "dureri articulare", "febra", "dureri dentare", "raceala"],
        "indications": "Tratamentul simptomatic al durerii ușoare până la moderată, precum dureri de cap, dureri menstruale, dureri dentare, dureri musculare și articulare. Reducerea febrei.",
        "contraindications": "Hipersensibilitate la ibuprofen sau AINS. Ulcer gastroduodenal activ. Insuficiență cardiacă severă. Trimestrul 3 de sarcină. Insuficiență renală sau hepatică severă.",
        "side_effects": "Tulburări gastrointestinale (greață, vărsături, diaree, dureri abdominale). Reacții alergice cutanate. Cefalee, amețeli. Rareori: ulcer gastric, sângerări GI.",
        "dosage": "Adulți: 1 comprimat (400mg) la 4-6 ore. Maximum 3 comprimate/zi. A se lua cu alimente pentru a reduce iritația gastrică.",
        "interactions": "Anticoagulante (risc crescut de sângerare). Alte AINS. Metotrexat. Litiu. Antihipertensive (efect redus).",
        "warnings": "Nu depășiți doza recomandată. Nu utilizați mai mult de 3 zile fără consult medical. Evitați alcoolul.",
        "url": "https://www.catena.ro/nurofen-400mg"
    },
    {
        "name": "Paracetamol 500mg",
        "active": "Paracetamol 500mg",
        "category": "Analgezice/Antipiretice",
        "rx": False,
        "price": 8.90,
        "symptoms": ["durere de cap", "febra", "dureri musculare", "raceala", "gripa", "dureri dentare"],
        "indications": "Tratamentul simptomatic al durerii ușoare până la moderată și al febrei. Indicat în răceală, gripă, dureri de cap, dureri dentare.",
        "contraindications": "Hipersensibilitate la paracetamol. Insuficiență hepatică severă.",
        "side_effects": "Rar: reacții alergice cutanate. Foarte rar: tulburări ale formulei sanguine. Supradozaj: leziuni hepatice grave.",
        "dosage": "Adulți: 500-1000mg la 4-6 ore. Maximum 4g/zi. Copii: doza adaptată greutății corporale.",
        "interactions": "Alcool (risc hepatotoxicitate). Warfarină (efect anticoagulant crescut). Carbamazepină.",
        "warnings": "Nu depășiți 4g/zi. Evitați alcoolul. Consultați medicul dacă simptomele persistă peste 3 zile.",
        "url": "https://www.catena.ro/paracetamol-500mg"
    },
    {
        "name": "Algocalmin 500mg",
        "active": "Metamizol sodic 500mg",
        "category": "Analgezice",
        "rx": False,
        "price": 12.30,
        "symptoms": ["durere de cap severa", "colici", "dureri postoperatorii", "dureri intense", "febra mare"],
        "indications": "Dureri intense când alte analgezice nu sunt suficiente. Colici biliare și renale. Febră înaltă neresponsivă la alte antipiretice.",
        "contraindications": "Disfuncții ale măduvei osoase. Deficit de glucozo-6-fosfat dehidrogenază. Porfirie hepatică. Sarcina trimestrul 3.",
        "side_effects": "Rar: agranulocitoză (foarte gravă). Reacții alergice. Hipotensiune. Colorare roșiatică a urinei.",
        "dosage": "Adulți: 500-1000mg până la 4 ori/zi. Maximum 4g/zi.",
        "interactions": "Metotrexat. Ciclosporină. Anticoagulante orale.",
        "warnings": "Utilizare pe termen scurt! Consultați medicul la primul semn de febră sau răni bucale (posibil agranulocitoză).",
        "url": "https://www.catena.ro/algocalmin-500mg"
    },
    # DIGESTIVE
    {
        "name": "Omez 20mg",
        "active": "Omeprazol 20mg",
        "category": "Antiacide/IPP",
        "rx": False,
        "price": 24.50,
        "symptoms": ["arsuri gastrice", "reflux", "aciditate", "ulcer", "dureri de stomac", "regurgitare acida", "GERD"],
        "indications": "Boala de reflux gastroesofagian (GERD). Ulcer gastric și duodenal. Esofagită de reflux. Sindrom Zollinger-Ellison.",
        "contraindications": "Hipersensibilitate la omeprazol sau alți IPP. Utilizare concomitentă cu nelfinavir.",
        "side_effects": "Cefalee. Dureri abdominale, constipație, diaree, greață. Utilizare prelungită: risc de fracturi, deficit B12, hipomagneziemie.",
        "dosage": "Adulți: 20mg o dată/zi, dimineața, înainte de masă. Pentru ulcer: 4-8 săptămâni. Pentru reflux: până la rezoluția simptomelor.",
        "interactions": "Clopidogrel (efect antiagregant redus). Metotrexat. Ketoconazol (absorbție redusă).",
        "warnings": "Nu utilizați mai mult de 14 zile fără consult medical. Excludeți malignitatea gastrică înainte de tratament.",
        "url": "https://www.catena.ro/omez-20mg"
    },
    {
        "name": "Smecta",
        "active": "Diosmectită 3g",
        "category": "Antidiareice",
        "rx": False,
        "price": 19.90,
        "symptoms": ["diaree", "diaree acuta", "colita", "dureri abdominale", "intoxicatie alimentara", "gastroenterita"],
        "indications": "Tratamentul simptomatic al diareei acute la adulți și copii. Tratamentul durerii asociate afecțiunilor esofago-gastro-duodenale și colonului.",
        "contraindications": "Intoleranță la fructoză. Malabsorbție de glucoză-galactoză. Deficit de zaharază-izomaltază.",
        "side_effects": "Constipație (rar). Meteorism.",
        "dosage": "Adulți: 3 plicuri/zi, între mese. Copii: 1-2 plicuri/zi în funcție de vârstă. Se dizolvă în apă.",
        "interactions": "Poate reduce absorbția altor medicamente. Administrați alte medicamente la 2 ore distanță.",
        "warnings": "Dacă diareea nu se ameliorează în 2 zile, consultați medicul. Mențineți hidratarea adecvată.",
        "url": "https://www.catena.ro/smecta"
    },
    {
        "name": "Imodium 2mg",
        "active": "Loperamidă 2mg",
        "category": "Antidiareice",
        "rx": False,
        "price": 22.50,
        "symptoms": ["diaree", "diaree calatori", "diaree acuta", "scaune lichide frecvente"],
        "indications": "Tratamentul simptomatic al diareei acute. Diareea călătorilor.",
        "contraindications": "Copii sub 6 ani. Distensie abdominală. Megacolon toxic. Colită ulceroasă acută. Dizenterie bacteriană.",
        "side_effects": "Constipație. Dureri abdominale. Greață. Flatulență. Rar: ileus paralitic.",
        "dosage": "Adulți: 2 capsule inițial, apoi 1 capsulă după fiecare scaun diareic. Maximum 8 capsule/zi.",
        "interactions": "Poate masca simptomele infecțiilor bacteriene.",
        "warnings": "Nu utilizați în cazul febrei sau scaunelor cu sânge! Opriți tratamentul dacă constipația persistă.",
        "url": "https://www.catena.ro/imodium"
    },
    {
        "name": "No-Spa 40mg",
        "active": "Drotaverină 40mg",
        "category": "Antispastice",
        "rx": False,
        "price": 16.00,
        "symptoms": ["crampe abdominale", "colici", "dureri menstruale", "spasme intestinale", "spasme biliare", "spasme urinare"],
        "indications": "Spasme ale musculaturii netede din tractul gastro-intestinal, biliar, urinar. Dismenoree.",
        "contraindications": "Insuficiență hepatică sau renală severă. Insuficiență cardiacă severă. Hipersensibilitate.",
        "side_effects": "Rar: cefalee, amețeli, palpitații, greață, constipație. Foarte rar: hipotensiune.",
        "dosage": "Adulți: 1-2 comprimate de 3 ori/zi. Maximum 240mg/zi.",
        "interactions": "Levodopa (efect antiparkinsonian redus).",
        "warnings": "Nu utilizați pentru dureri abdominale de cauză neidentificată fără consult medical.",
        "url": "https://www.catena.ro/no-spa-40mg"
    },
    # RESPIRATORY
    {
        "name": "ACC 600mg",
        "active": "Acetilcisteină 600mg",
        "category": "Mucolitice/Expectorante",
        "rx": False,
        "price": 32.00,
        "symptoms": ["tuse productiva", "mucus", "bronsita", "sinuzita", "tuse cu flegma", "secretii bronhice"],
        "indications": "Terapia secretolitică în afecțiuni acute și cronice ale bronhiilor și plămânilor cu secreție mucoasă vâscoasă. Bronșită, sinuzită, laringită.",
        "contraindications": "Ulcer gastroduodenal activ. Copii sub 2 ani. Hipersensibilitate la acetilcisteină.",
        "side_effects": "Rar: greață, vărsături, diaree. Foarte rar: bronhospasm, reacții alergice.",
        "dosage": "Adulți: 600mg o dată/zi sau 200mg de 3 ori/zi. Se dizolvă în apă. Se administrează după masă.",
        "interactions": "Nu administrați concomitent cu antitusive (blocarea reflexului de tuse)! Tetracicline (la 2h distanță).",
        "warnings": "Asigurați hidratare adecvată pentru a facilita expectorația. Dacă tusea persistă peste 1 săptămână, consultați medicul.",
        "url": "https://www.catena.ro/acc-600mg"
    },
    {
        "name": "Mucosolvan 30mg",
        "active": "Ambroxol 30mg",
        "category": "Mucolitice/Expectorante",
        "rx": False,
        "price": 19.90,
        "symptoms": ["tuse productiva", "bronsita", "mucus", "tuse cu flegma", "secretii vascose"],
        "indications": "Tratamentul afecțiunilor respiratorii acute și cronice asociate cu secreții bronșice vâscoase.",
        "contraindications": "Hipersensibilitate la ambroxol. Intoleranță la lactoză.",
        "side_effects": "Rar: greață, dureri abdominale, diaree. Foarte rar: reacții cutanate severe.",
        "dosage": "Adulți: 1 comprimat de 2-3 ori/zi. Copii: sirop adaptat vârstei.",
        "interactions": "Poate crește concentrația antibioticelor în țesutul pulmonar.",
        "warnings": "Opriți tratamentul la primele semne de reacție cutanată! Nu utilizați cu antitusive.",
        "url": "https://www.catena.ro/mucosolvan"
    },
    {
        "name": "Strepsils",
        "active": "Amilmetacrezol + Alcool diclorbenzilic",
        "category": "Antiseptice orale",
        "rx": False,
        "price": 21.50,
        "symptoms": ["durere in gat", "faringita", "amigdalita", "infectii gat", "iritatii gat"],
        "indications": "Tratamentul simptomatic al infecțiilor minore ale cavității bucale și faringelui.",
        "contraindications": "Copii sub 6 ani. Hipersensibilitate la componente.",
        "side_effects": "Rar: iritație locală, reacții alergice.",
        "dosage": "Adulți și copii peste 6 ani: 1 pastilă la 2-3 ore. Maximum 8 pastile/zi.",
        "interactions": "Nu sunt cunoscute interacțiuni semnificative.",
        "warnings": "Dacă simptomele persistă peste 3 zile, consultați medicul.",
        "url": "https://www.catena.ro/strepsils"
    },
    {
        "name": "Olynth 0.1%",
        "active": "Xilometazolină 0.1%",
        "category": "Decongestionante nazale",
        "rx": False,
        "price": 14.50,
        "symptoms": ["nas infundat", "congestie nazala", "raceala", "sinuzita", "rinita"],
        "indications": "Decongestionarea mucoasei nazale în rinită acută, rinită alergică, sinuzită.",
        "contraindications": "Rinită atrofică. Glaucom cu unghi închis. Hipertensiune arterială severă. Hipertiroidism.",
        "side_effects": "Uscăciune nazală. Strănut. Senzație de arsură. La utilizare prelungită: rinită medicamentoasă.",
        "dosage": "Adulți: 1 puf în fiecare nară de 2-3 ori/zi. Maximum 7 zile de utilizare continuă!",
        "interactions": "IMAO și antidepresive triciclice (risc de criză hipertensivă).",
        "warnings": "NU utilizați mai mult de 7 zile! Poate provoca dependență nazală.",
        "url": "https://www.catena.ro/olynth"
    },
    {
        "name": "Theraflu",
        "active": "Paracetamol + Fenilefrină + Vitamina C",
        "category": "Antigripale",
        "rx": False,
        "price": 28.50,
        "symptoms": ["raceala", "gripa", "febra", "congestie nazala", "durere de cap", "frisoane", "dureri musculare"],
        "indications": "Ameliorarea simptomelor răcelii și gripei: febră, dureri, congestie nazală.",
        "contraindications": "Hipertensiune severă. Boli cardiace. Hipertiroidism. Glaucom. Tratament cu IMAO.",
        "side_effects": "Nervozitate, insomnie. Greață. Palpitații. Uscăciunea gurii.",
        "dosage": "Adulți: 1 plic la 4-6 ore. Maximum 4 plicuri/zi. Se dizolvă în apă caldă.",
        "interactions": "Nu combinați cu alte medicamente ce conțin paracetamol! IMAO. Beta-blocante.",
        "warnings": "Nu depășiți 4 plicuri/zi. Evitați alcoolul. Nu utilizați mai mult de 5 zile.",
        "url": "https://www.catena.ro/theraflu"
    },
    # ALLERGIES
    {
        "name": "Claritine 10mg",
        "active": "Loratadină 10mg",
        "category": "Antihistaminice",
        "rx": False,
        "price": 24.00,
        "symptoms": ["alergie", "rinita alergica", "urticarie", "mancarimi", "stranut", "ochi rosii", "alergie polen"],
        "indications": "Rinită alergică sezonieră și perenă. Urticarie cronică idiopatică.",
        "contraindications": "Hipersensibilitate la loratadină sau desloratadină.",
        "side_effects": "Adulți: cefalee. Copii: cefalee, nervozitate, oboseală. Rar: somnolență.",
        "dosage": "Adulți și copii peste 12 ani: 10mg o dată/zi. Copii 2-12 ani: 5mg/zi.",
        "interactions": "Eritromicină, ketoconazol (cresc nivelul plasmatic).",
        "warnings": "Non-sedativ, dar unele persoane pot experimenta somnolență. Prudență la condus.",
        "url": "https://www.catena.ro/claritine"
    },
    {
        "name": "Zyrtec 10mg",
        "active": "Cetirizină 10mg",
        "category": "Antihistaminice",
        "rx": False,
        "price": 28.00,
        "symptoms": ["alergie", "rinita alergica", "urticarie", "mancarimi", "conjunctivita alergica"],
        "indications": "Rinită alergică sezonieră și perenă. Urticarie cronică. Conjunctivită alergică.",
        "contraindications": "Insuficiență renală severă. Hipersensibilitate la cetirizină sau hidroxizină.",
        "side_effects": "Somnolență, cefalee, gură uscată. Rar: agitație, confuzie.",
        "dosage": "Adulți: 10mg o dată/zi, seara. Copii 6-12 ani: 5mg de 2 ori/zi.",
        "interactions": "Alcool (sedare crescută). Teofilină (clearance redus).",
        "warnings": "Poate provoca somnolență. Evitați alcoolul și activitățile ce necesită vigilență.",
        "url": "https://www.catena.ro/zyrtec"
    },
    # CARDIOVASCULAR
    {
        "name": "Aspenter 75mg",
        "active": "Acid acetilsalicilic 75mg",
        "category": "Antiagregante plachetare",
        "rx": False,
        "price": 12.00,
        "symptoms": ["prevenție cardiovasculara", "infarct", "AVC", "tromboze"],
        "indications": "Prevenția secundară a infarctului miocardic și AVC. Prevenția trombozelor la pacienți cu risc cardiovascular.",
        "contraindications": "Ulcer gastroduodenal activ. Hemofilie. Trimestrul 3 de sarcină. Alergie la aspirină.",
        "side_effects": "Sângerări GI. Dispepsie. Reacții alergice.",
        "dosage": "Adulți: 75-100mg o dată/zi, cu alimente.",
        "interactions": "Anticoagulante (risc sângerare). AINS. Metotrexat.",
        "warnings": "Nu întrerupeți tratamentul fără consult medical! Opriți înainte de intervenții chirurgicale.",
        "url": "https://www.catena.ro/aspenter-75mg"
    },
    {
        "name": "Detralex 500mg",
        "active": "Fracție flavonoidică purificată",
        "category": "Venotonice",
        "rx": False,
        "price": 48.00,
        "symptoms": ["varice", "picioare grele", "insuficienta venoasa", "hemoroizi", "edeme", "crampe nocturne picioare"],
        "indications": "Insuficiență venoasă cronică (picioare grele, dureroase, edeme). Criză hemoroidală.",
        "contraindications": "Hipersensibilitate la compuși.",
        "side_effects": "Rar: tulburări digestive ușoare, cefalee, vertij.",
        "dosage": "Insuficiență venoasă: 2 comprimate/zi. Hemoroizi: 6 comp/zi 4 zile, apoi 4 comp/zi 3 zile.",
        "interactions": "Nu sunt cunoscute interacțiuni semnificative.",
        "warnings": "Nu înlocuiește alte măsuri: ciorapi compresivi, evitarea statului prelungit în picioare.",
        "url": "https://www.catena.ro/detralex"
    },
    # DIABETES
    {
        "name": "Siofor 850mg",
        "active": "Metformină 850mg",
        "category": "Antidiabetice orale",
        "rx": True,
        "price": 22.00,
        "symptoms": ["diabet tip 2", "glicemie crescuta", "rezistenta la insulina"],
        "indications": "Diabet zaharat tip 2, în special la pacienți supraponderali, când dieta și exercițiul fizic nu asigură controlul glicemic.",
        "contraindications": "Cetoacidoză diabetică. Insuficiență renală. Insuficiență hepatică. Insuficiență cardiacă decompensată. Alcoolism acut.",
        "side_effects": "Greață, vărsături, diaree, dureri abdominale (frecvente inițial). Rar: acidoză lactică (gravă!).",
        "dosage": "Inițial 850mg o dată/zi cu masa. Creștere treptată până la 850mg x 2-3/zi.",
        "interactions": "Contrast iodat (suspendați 48h înainte/după). Alcool. Diuretice.",
        "warnings": "OPRIȚI înainte de proceduri imagistice cu contrast! Monitorizați funcția renală.",
        "url": "https://www.catena.ro/siofor-850mg"
    },
    # VITAMINS
    {
        "name": "Vitamina D3 2000UI",
        "active": "Colecalciferol 2000UI",
        "category": "Vitamine",
        "rx": False,
        "price": 35.00,
        "symptoms": ["deficit vitamina D", "osteoporoza", "imunitate scazuta", "oboseala", "dureri osoase"],
        "indications": "Prevenirea și tratamentul deficitului de vitamina D. Suport pentru sănătatea oaselor și sistemului imunitar.",
        "contraindications": "Hipercalcemie. Hipervitaminoză D. Calculi renali.",
        "side_effects": "La doze excesive: hipercalcemie, greață, slăbiciune, calculi renali.",
        "dosage": "Adulți: 1000-2000UI/zi. În deficit sever: doze mai mari conform indicației medicale.",
        "interactions": "Digitala (hipercalcemia crește toxicitatea). Diuretice tiazidice.",
        "warnings": "Nu depășiți 4000UI/zi fără supraveghere medicală. Verificați periodic calciul seric.",
        "url": "https://www.catena.ro/vitamina-d3"
    },
    {
        "name": "Vitamina C 1000mg",
        "active": "Acid ascorbic 1000mg",
        "category": "Vitamine",
        "rx": False,
        "price": 22.00,
        "symptoms": ["raceala", "imunitate scazuta", "oboseala", "gripa", "stres oxidativ"],
        "indications": "Prevenirea și tratamentul deficitului de vitamina C. Suport imunitar. Antioxidant.",
        "contraindications": "Calculi renali oxalați. Hemocromatoză.",
        "side_effects": "Doze mari: diaree, greață, crampe abdominale. Calculi renali la utilizare prelungită.",
        "dosage": "Adulți: 500-1000mg/zi. În răceală: până la 2000mg/zi pe termen scurt.",
        "interactions": "Poate crește absorbția fierului. Interfere cu anumite teste de laborator.",
        "warnings": "Doze foarte mari pot cauza probleme digestive și renale.",
        "url": "https://www.catena.ro/vitamina-c-1000mg"
    },
    {
        "name": "Magneziu + B6",
        "active": "Citrat de magneziu 400mg + Vitamina B6 5mg",
        "category": "Minerale",
        "rx": False,
        "price": 32.00,
        "symptoms": ["crampe musculare", "oboseala", "stres", "anxietate", "insomnie usoara", "nervozitate"],
        "indications": "Deficit de magneziu manifestat prin: crampe, oboseală, nervozitate, tulburări de somn.",
        "contraindications": "Insuficiență renală severă. Miastenia gravis.",
        "side_effects": "Diaree (la doze mari). Greață.",
        "dosage": "Adulți: 300-400mg magneziu/zi, în 2-3 prize, cu alimente.",
        "interactions": "Reduce absorbția tetraciclinelor și bifosfonaților (administrați la 2h distanță).",
        "warnings": "Pacienții cu insuficiență renală trebuie să consulte medicul.",
        "url": "https://www.catena.ro/magneziu-b6"
    },
    # DERMATOLOGY
    {
        "name": "Voltaren Emulgel",
        "active": "Diclofenac gel 1%",
        "category": "Antiinflamatoare topice",
        "rx": False,
        "price": 32.00,
        "symptoms": ["dureri musculare", "dureri articulare", "entorse", "contuzii", "tendinite"],
        "indications": "Tratamentul local al durerii și inflamației în: traumatisme, entorse, tendinite, artralgii.",
        "contraindications": "Piele lezată. Trimestrul 3 de sarcină. Copii sub 14 ani. Alergie la AINS.",
        "side_effects": "Local: eritem, prurit, uscăciune. Rar: reacții alergice.",
        "dosage": "Aplicați 2-4g (mărimea unei cireșe) de 3-4 ori/zi pe zona afectată. Masați ușor.",
        "interactions": "Evitați utilizarea concomitentă cu alte AINS topice.",
        "warnings": "Nu aplicați pe răni deschise sau mucoase. Spălați mâinile după aplicare.",
        "url": "https://www.catena.ro/voltaren-emulgel"
    },
    {
        "name": "Bepanthen",
        "active": "Dexpantenol 5%",
        "category": "Cicatrizante/Regenerante",
        "rx": False,
        "price": 45.00,
        "symptoms": ["piele iritata", "arsuri usoare", "rani superficiale", "crăpat", "eczeme usoare", "fese iritatii bebe"],
        "indications": "Cicatrizarea rănilor superficiale. Arsuri ușoare. Prevenirea și tratamentul iritațiilor cutanate. Îngrijirea mameloanelor în alăptare.",
        "contraindications": "Hipersensibilitate la dexpantenol.",
        "side_effects": "Foarte rar: reacții alergice locale.",
        "dosage": "Aplicați un strat subțire de 1-2 ori/zi pe zona afectată.",
        "interactions": "Nu sunt cunoscute.",
        "warnings": "Doar uz extern. Nu aplicați pe răni infectate.",
        "url": "https://www.catena.ro/bepanthen"
    },
    {
        "name": "Canesten cremă",
        "active": "Clotrimazol 1%",
        "category": "Antifungice topice",
        "rx": False,
        "price": 28.00,
        "symptoms": ["ciuperca picior", "micoze", "intertrigo", "candidoze cutanate", "mancarimi piele"],
        "indications": "Infecții fungice ale pielii: dermatofitoze, candidoze cutanate, pitiriazis versicolor.",
        "contraindications": "Hipersensibilitate la clotrimazol sau alte imidazole.",
        "side_effects": "Rar: iritație locală, arsură, prurit.",
        "dosage": "Aplicați un strat subțire de 2-3 ori/zi. Durata: 2-4 săptămâni (continuați 2 săpt. după vindecare).",
        "interactions": "Reduce eficacitatea prezervativelor din latex!",
        "warnings": "Dacă nu se ameliorează în 4 săptămâni, consultați medicul. Mențineți zona curată și uscată.",
        "url": "https://www.catena.ro/canesten-crema"
    },
]


def build_leaflet_document(med: dict) -> dict:
    rx_status = "⚠️ **NECESITĂ REȚETĂ MEDICALĂ**" if med["rx"] else "✅ Disponibil fără rețetă"
    symptoms_text = ", ".join(med["symptoms"])

    content = f"""# {med["name"]}

## Informații Generale
- **Substanță activă**: {med["active"]}
- **Categorie**: {med["category"]}
- **Status**: {rx_status}
- **Preț orientativ**: {med["price"]} RON

## Pentru ce simptome este recomandat
{symptoms_text}

## Indicații Terapeutice
{med["indications"]}

## Mod de Administrare și Dozaj
{med["dosage"]}

## Contraindicații (NU se administrează în)
{med["contraindications"]}

## Reacții Adverse Posibile
{med["side_effects"]}

## Interacțiuni Medicamentoase
{med["interactions"]}

## Atenționări Speciale
⚠️ {med["warnings"]}

## Cumpărare Online
🛒 [Cumpără de la Catena]({med["url"]})
"""
    return {
        "content": content,
        "title": f"{med['name']} - Prospect Complet",
        "source": "Catena.ro",
        "metadata": {
            "active_substance": med["active"],
            "category": med["category"],
            "prescription_required": med["rx"],
            "price": med["price"],
            "symptoms": med["symptoms"],
            "url": med["url"]
        }
    }


def get_leaflet_documents():
    return [build_leaflet_document(med) for med in MEDICINE_LEAFLETS]


def get_symptom_index():
    index = {}
    for med in MEDICINE_LEAFLETS:
        for symptom in med["symptoms"]:
            symptom_lower = symptom.lower()
            if symptom_lower not in index:
                index[symptom_lower] = []
            index[symptom_lower].append({
                "name": med["name"],
                "rx": med["rx"],
                "price": med["price"],
                "url": med["url"]
            })
    return index


def save_leaflet_database():
    import json
    from pathlib import Path

    DATA_DIR = Path(__file__).parent / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    documents = get_leaflet_documents()
    output_file = DATA_DIR / "ro_leaflets.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)

    symptom_index = get_symptom_index()
    index_file = DATA_DIR / "symptom_index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(symptom_index, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(documents)} medicine leaflets to {output_file}")
    print(f"Saved symptom index ({len(symptom_index)} symptoms) to {index_file}")
    return output_file


if __name__ == "__main__":
    save_leaflet_database()
