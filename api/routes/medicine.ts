import express from 'express';
import multer from 'multer';
import { OpenAI } from 'openai';
import dotenv from 'dotenv';

const router = express.Router();

// Load environment variables
dotenv.config();

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Mock medicine database for MVP
const MEDICINE_DATABASE = [
  {
    id: 1,
    name: "Paracetamol",
    genericName: "Acetaminophen",
    dosage: "500mg",
    type: "tablet",
    uses: ["pain relief", "fever reduction", "headache"],
    contraindications: ["liver disease", "alcohol dependency"],
    pregnancySafe: true,
    sideEffects: ["nausea", "skin rash"],
    maxDailyDose: "4000mg",
    description: "Common pain reliever and fever reducer"
  },
  {
    id: 2,
    name: "Ibuprofen",
    genericName: "Ibuprofen",
    dosage: "400mg",
    type: "tablet",
    uses: ["pain relief", "inflammation", "fever reduction"],
    contraindications: ["stomach ulcers", "kidney disease", "heart disease"],
    pregnancySafe: false,
    sideEffects: ["stomach upset", "dizziness", "headache"],
    maxDailyDose: "1200mg",
    description: "Anti-inflammatory pain reliever"
  },
  {
    id: 3,
    name: "Aspirin",
    genericName: "Acetylsalicylic acid",
    dosage: "325mg",
    type: "tablet",
    uses: ["pain relief", "fever reduction", "blood thinning"],
    contraindications: ["bleeding disorders", "stomach ulcers", "children under 16"],
    pregnancySafe: false,
    sideEffects: ["stomach irritation", "bleeding", "tinnitus"],
    maxDailyDose: "4000mg",
    description: "Pain reliever and blood thinner"
  },
  {
    id: 4,
    name: "Loratadine",
    genericName: "Loratadine",
    dosage: "10mg",
    type: "tablet",
    uses: ["allergies", "hay fever", "hives"],
    contraindications: ["severe liver disease"],
    pregnancySafe: true,
    sideEffects: ["drowsiness", "dry mouth", "headache"],
    maxDailyDose: "10mg",
    description: "Antihistamine for allergies"
  },
  {
    id: 5,
    name: "Omeprazole",
    genericName: "Omeprazole",
    dosage: "20mg",
    type: "capsule",
    uses: ["acid reflux", "heartburn", "stomach ulcers"],
    contraindications: ["severe liver disease"],
    pregnancySafe: true,
    sideEffects: ["headache", "nausea", "diarrhea"],
    maxDailyDose: "40mg",
    description: "Proton pump inhibitor for acid reduction"
  }
];

// Photo medicine identification endpoint
router.post('/identify', async (req, res) => {
  try {
    const { image, userQuery } = req.body;
    
    if (!image) {
      return res.status(400).json({ error: 'Image is required' });
    }

    // For MVP, we'll use OpenAI Vision API to analyze the image
    const response = await openai.chat.completions.create({
      model: "gpt-4-vision-preview",
      messages: [
        {
          role: "user",
          content: [
            {
              type: "text",
              text: `Analyze this medicine image and identify the medication. Look for:
              1. Medicine name on packaging or pills
              2. Dosage information
              3. Type (tablet, capsule, liquid, etc.)
              4. Any visible brand names or generic names
              5. Shape, color, and markings on pills
              
              Respond with a JSON object containing:
              - name: medicine name
              - dosage: dosage strength
              - type: medication type
              - confidence: confidence level (0-100)
              - description: brief description
              
              If you cannot identify the medicine clearly, set confidence to 0 and explain why.`
            },
            {
              type: "image_url",
              image_url: {
                url: image
              }
            }
          ]
        }
      ],
      max_tokens: 500
    });

    const aiResponse = response.choices[0]?.message?.content;
    
    // Try to parse AI response as JSON, fallback to text analysis
    let identificationResult;
    try {
      identificationResult = JSON.parse(aiResponse || '{}');
    } catch {
      // Fallback: extract information from text response
      identificationResult = {
        name: "Unknown Medicine",
        dosage: "Unknown",
        type: "Unknown",
        confidence: 0,
        description: aiResponse || "Could not identify medicine from image"
      };
    }

    // Try to match with our database
    const matchedMedicine = MEDICINE_DATABASE.find(med => 
      med.name.toLowerCase().includes(identificationResult.name?.toLowerCase() || '') ||
      med.genericName.toLowerCase().includes(identificationResult.name?.toLowerCase() || '')
    );

    const result = {
      identification: identificationResult,
      medicineInfo: matchedMedicine || null,
      userQuery: userQuery || null,
      timestamp: new Date().toISOString()
    };

    res.json(result);
  } catch (error) {
    console.error('Medicine identification error:', error);
    res.status(500).json({ 
      error: 'Failed to identify medicine',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Search medicines by name or symptoms
router.get('/search', (req, res) => {
  try {
    const { query, symptom } = req.query;
    
    if (!query && !symptom) {
      return res.status(400).json({ error: 'Query or symptom parameter is required' });
    }

    let results = MEDICINE_DATABASE;

    if (query) {
      const searchTerm = (query as string).toLowerCase();
      results = results.filter(med => 
        med.name.toLowerCase().includes(searchTerm) ||
        med.genericName.toLowerCase().includes(searchTerm) ||
        med.description.toLowerCase().includes(searchTerm)
      );
    }

    if (symptom) {
      const symptomTerm = (symptom as string).toLowerCase();
      results = results.filter(med =>
        med.uses.some(use => use.toLowerCase().includes(symptomTerm))
      );
    }

    res.json({
      results,
      total: results.length,
      query: query || symptom
    });
  } catch (error) {
    console.error('Medicine search error:', error);
    res.status(500).json({ error: 'Failed to search medicines' });
  }
});

// Get medicine details by ID
router.get('/:id', (req, res) => {
  try {
    const medicineId = parseInt(req.params.id);
    const medicine = MEDICINE_DATABASE.find(med => med.id === medicineId);
    
    if (!medicine) {
      return res.status(404).json({ error: 'Medicine not found' });
    }
    
    res.json(medicine);
  } catch (error) {
    console.error('Get medicine error:', error);
    res.status(500).json({ error: 'Failed to get medicine details' });
  }
});

// Safety check endpoint
router.post('/safety-check', (req, res) => {
  try {
    const { medicineId, userProfile } = req.body;
    
    if (!medicineId || !userProfile) {
      return res.status(400).json({ error: 'Medicine ID and user profile are required' });
    }

    const medicine = MEDICINE_DATABASE.find(med => med.id === medicineId);
    if (!medicine) {
      return res.status(404).json({ error: 'Medicine not found' });
    }

    const warnings = [];
    const recommendations = [];

    // Check pregnancy safety
    if (userProfile.isPregnant && !medicine.pregnancySafe) {
      warnings.push({
        type: 'pregnancy',
        severity: 'high',
        message: `${medicine.name} is not recommended during pregnancy. Consult your doctor.`
      });
    }

    // Check allergies
    if (userProfile.allergies && userProfile.allergies.length > 0) {
      const allergyMatch = userProfile.allergies.some((allergy: string) =>
        medicine.name.toLowerCase().includes(allergy.toLowerCase()) ||
        medicine.genericName.toLowerCase().includes(allergy.toLowerCase())
      );
      
      if (allergyMatch) {
        warnings.push({
          type: 'allergy',
          severity: 'critical',
          message: `You may be allergic to ${medicine.name}. Do not take this medication.`
        });
      }
    }

    // Check contraindications
    if (userProfile.conditions && userProfile.conditions.length > 0) {
      userProfile.conditions.forEach((condition: string) => {
        if (medicine.contraindications.some(contra => 
          contra.toLowerCase().includes(condition.toLowerCase())
        )) {
          warnings.push({
            type: 'contraindication',
            severity: 'high',
            message: `${medicine.name} may not be suitable for ${condition}. Consult your doctor.`
          });
        }
      });
    }

    // Generate recommendations
    if (warnings.length === 0) {
      recommendations.push(`${medicine.name} appears safe based on your profile.`);
      recommendations.push(`Maximum daily dose: ${medicine.maxDailyDose}`);
    } else {
      recommendations.push('Consider consulting a healthcare professional before taking this medication.');
      
      // Suggest alternatives if available
      const alternatives = MEDICINE_DATABASE.filter(med => 
        med.id !== medicineId &&
        med.uses.some(use => medicine.uses.includes(use)) &&
        (userProfile.isPregnant ? med.pregnancySafe : true)
      );
      
      if (alternatives.length > 0) {
        recommendations.push(`Alternative options: ${alternatives.slice(0, 2).map(alt => alt.name).join(', ')}`);
      }
    }

    res.json({
      medicine,
      warnings,
      recommendations,
      safetyScore: Math.max(0, 100 - (warnings.length * 25)),
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Safety check error:', error);
    res.status(500).json({ error: 'Failed to perform safety check' });
  }
});

export default router;