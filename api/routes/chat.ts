import express from 'express';
import { OpenAI } from 'openai';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const router = express.Router();

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// In-memory storage for chat sessions (in production, use a proper database)
const chatSessions = new Map();

// Mock medicine database for RAG context
const MEDICINE_DATABASE = [
  {
    id: 1,
    name: "Paracetamol",
    genericName: "Acetaminophen",
    dosage: "500mg",
    uses: ["pain relief", "fever reduction", "headache"],
    contraindications: ["liver disease", "alcohol dependency"],
    pregnancySafe: true,
    sideEffects: ["nausea", "skin rash"],
    maxDailyDose: "4000mg"
  },
  {
    id: 2,
    name: "Ibuprofen",
    genericName: "Ibuprofen",
    dosage: "400mg",
    uses: ["pain relief", "inflammation", "fever reduction"],
    contraindications: ["stomach ulcers", "kidney disease", "heart disease"],
    pregnancySafe: false,
    sideEffects: ["stomach upset", "dizziness", "headache"],
    maxDailyDose: "1200mg"
  },
  {
    id: 3,
    name: "Aspirin",
    genericName: "Acetylsalicylic acid",
    dosage: "325mg",
    uses: ["pain relief", "fever reduction", "blood thinning"],
    contraindications: ["bleeding disorders", "stomach ulcers", "children under 16"],
    pregnancySafe: false,
    sideEffects: ["stomach irritation", "bleeding", "tinnitus"],
    maxDailyDose: "4000mg"
  },
  {
    id: 4,
    name: "Loratadine",
    genericName: "Loratadine",
    dosage: "10mg",
    uses: ["allergies", "hay fever", "hives"],
    contraindications: ["severe liver disease"],
    pregnancySafe: true,
    sideEffects: ["drowsiness", "dry mouth", "headache"],
    maxDailyDose: "10mg"
  },
  {
    id: 5,
    name: "Omeprazole",
    genericName: "Omeprazole",
    dosage: "20mg",
    uses: ["acid reflux", "heartburn", "stomach ulcers"],
    contraindications: ["severe liver disease"],
    pregnancySafe: true,
    sideEffects: ["headache", "nausea", "diarrhea"],
    maxDailyDose: "40mg"
  }
];

// RAG search function
function searchMedicineDatabase(query: string, userProfile?: Record<string, unknown>) {
  const searchTerms = query.toLowerCase().split(' ');
  const results = MEDICINE_DATABASE.filter(medicine => {
    const searchableText = `${medicine.name} ${medicine.genericName} ${medicine.uses.join(' ')} ${medicine.contraindications.join(' ')}`.toLowerCase();
    return searchTerms.some(term => searchableText.includes(term));
  });

  // Filter based on user profile if available
  if (userProfile) {
    return results.filter(medicine => {
      // Filter out medicines not safe for pregnancy
      if (userProfile.isPregnant && !medicine.pregnancySafe) {
        return false;
      }
      
      // Filter out medicines with contraindications matching user conditions
      if (userProfile.conditions && Array.isArray(userProfile.conditions) && userProfile.conditions.length > 0) {
        const hasContraindication = medicine.contraindications.some(contra =>
          (userProfile.conditions as string[]).some((condition: string) =>
            contra.toLowerCase().includes(condition.toLowerCase())
          )
        );
        if (hasContraindication) {
          return false;
        }
      }
      
      return true;
    });
  }

  return results;
}

// Start a new chat session
router.post('/start', (req, res) => {
  try {
    const { userId, userProfile } = req.body;
    
    const sessionId = `chat_${userId}_${Date.now()}`;
    const session = {
      sessionId,
      userId,
      userProfile: userProfile || null,
      messages: [],
      createdAt: new Date().toISOString(),
      lastActivity: new Date().toISOString()
    };
    
    chatSessions.set(sessionId, session);
    
    res.json({
      sessionId,
      message: 'Chat session started successfully',
      welcomeMessage: userProfile?.isPregnant 
        ? "Hello! I'm your medical assistant. I see you're pregnant, so I'll be extra careful with medication recommendations. How can I help you today?"
        : "Hello! I'm your medical assistant. I can help you with medication questions, safety checks, and health advice. How can I help you today?"
    });
  } catch (error) {
    console.error('Start chat error:', error);
    res.status(500).json({ error: 'Failed to start chat session' });
  }
});

// Send a message in chat
router.post('/:sessionId/message', async (req: express.Request & { io?: { to: (room: string) => { emit: (event: string, data: unknown) => void } } }, res) => {
  try {
    const { sessionId } = req.params;
    const { message, userProfile } = req.body;
    
    const session = chatSessions.get(sessionId);
    if (!session) {
      return res.status(404).json({ error: 'Chat session not found' });
    }
    
    // Update user profile if provided
    if (userProfile) {
      session.userProfile = userProfile;
    }
    
    // Add user message to session
    const userMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };
    session.messages.push(userMessage);
    
    // Perform RAG search
    const relevantMedicines = searchMedicineDatabase(message, session.userProfile);
    
    // Build context for AI
    let context = "You are a helpful medical assistant. Use the following medicine information to answer the user's question:\n\n";
    
    if (relevantMedicines.length > 0) {
      context += "Relevant medicines from database:\n";
      relevantMedicines.forEach(med => {
        context += `- ${med.name} (${med.genericName}): Used for ${med.uses.join(', ')}. `;
        context += `Pregnancy safe: ${med.pregnancySafe ? 'Yes' : 'No'}. `;
        context += `Contraindications: ${med.contraindications.join(', ')}.\n`;
      });
    } else {
      context += "No specific medicines found in database for this query.\n";
    }
    
    // Add user profile context
    if (session.userProfile) {
      context += "\nUser profile:\n";
      if (session.userProfile.isPregnant) {
        context += "- User is pregnant (provide extra safety warnings)\n";
      }
      if (session.userProfile.allergies && session.userProfile.allergies.length > 0) {
        context += `- Allergies: ${session.userProfile.allergies.join(', ')}\n`;
      }
      if (session.userProfile.conditions && session.userProfile.conditions.length > 0) {
        context += `- Medical conditions: ${session.userProfile.conditions.join(', ')}\n`;
      }
      if (session.userProfile.currentMedications && session.userProfile.currentMedications.length > 0) {
        context += `- Current medications: ${session.userProfile.currentMedications.join(', ')}\n`;
      }
    }
    
    context += "\nIMPORTANT: Always recommend consulting a healthcare professional for serious medical concerns. Provide safety warnings when appropriate.";
    
    // Get AI response
    const completion = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: [
        {
          role: "system",
          content: context
        },
        ...session.messages.slice(-5).map(msg => ({
          role: msg.role as 'user' | 'assistant',
          content: msg.content
        }))
      ],
      max_tokens: 500,
      temperature: 0.7
    });
    
    const aiResponse = completion.choices[0]?.message?.content || "I'm sorry, I couldn't process your request right now.";
    
    // Add AI response to session
    const assistantMessage = {
      id: `msg_${Date.now() + 1}`,
      role: 'assistant',
      content: aiResponse,
      timestamp: new Date().toISOString(),
      relevantMedicines: relevantMedicines.slice(0, 3) // Include top 3 relevant medicines
    };
    session.messages.push(assistantMessage);
    
    // Update session activity
    session.lastActivity = new Date().toISOString();
    chatSessions.set(sessionId, session);
    
    // Emit real-time update if socket.io is available
    if (req.io && session.userId) {
      req.io.to(`user_${session.userId}`).emit('new_message', assistantMessage);
    }
    
    res.json({
      message: assistantMessage,
      relevantMedicines: relevantMedicines.slice(0, 3),
      sessionId
    });
  } catch (error) {
    console.error('Send message error:', error);
    res.status(500).json({ 
      error: 'Failed to process message',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Get chat history
router.get('/:sessionId/history', (req, res) => {
  try {
    const { sessionId } = req.params;
    const { limit = 50 } = req.query;
    
    const session = chatSessions.get(sessionId);
    if (!session) {
      return res.status(404).json({ error: 'Chat session not found' });
    }
    
    const messages = session.messages.slice(-Number(limit));
    
    res.json({
      sessionId,
      messages,
      totalMessages: session.messages.length,
      lastActivity: session.lastActivity
    });
  } catch (error) {
    console.error('Get chat history error:', error);
    res.status(500).json({ error: 'Failed to get chat history' });
  }
});

// Get user's chat sessions
router.get('/user/:userId/sessions', (req, res) => {
  try {
    const { userId } = req.params;
    
    const userSessions = Array.from(chatSessions.values())
      .filter(session => session.userId === userId)
      .map(session => ({
        sessionId: session.sessionId,
        createdAt: session.createdAt,
        lastActivity: session.lastActivity,
        messageCount: session.messages.length,
        lastMessage: session.messages[session.messages.length - 1]?.content?.substring(0, 100) || ''
      }))
      .sort((a, b) => new Date(b.lastActivity).getTime() - new Date(a.lastActivity).getTime());
    
    res.json({
      sessions: userSessions,
      total: userSessions.length
    });
  } catch (error) {
    console.error('Get user sessions error:', error);
    res.status(500).json({ error: 'Failed to get user sessions' });
  }
});

// Delete chat session
router.delete('/:sessionId', (req, res) => {
  try {
    const { sessionId } = req.params;
    
    if (!chatSessions.has(sessionId)) {
      return res.status(404).json({ error: 'Chat session not found' });
    }
    
    chatSessions.delete(sessionId);
    
    res.json({ message: 'Chat session deleted successfully' });
  } catch (error) {
    console.error('Delete chat session error:', error);
    res.status(500).json({ error: 'Failed to delete chat session' });
  }
});

// Emergency medicine query (for urgent questions)
router.post('/emergency-query', async (req, res) => {
  try {
    const { query, userProfile } = req.body;
    
    if (!query) {
      return res.status(400).json({ error: 'Query is required' });
    }
    
    // Perform RAG search
    const relevantMedicines = searchMedicineDatabase(query, userProfile);
    
    // Build emergency context
    let context = "You are an emergency medical assistant. Provide immediate, safe guidance. ALWAYS recommend seeking immediate medical attention for emergencies.\n\n";
    
    if (relevantMedicines.length > 0) {
      context += "Relevant medicines:\n";
      relevantMedicines.forEach(med => {
        context += `- ${med.name}: ${med.uses.join(', ')}. Max daily: ${med.maxDailyDose}. `;
        context += `Pregnancy safe: ${med.pregnancySafe ? 'Yes' : 'No'}.\n`;
      });
    }
    
    if (userProfile?.isPregnant) {
      context += "\nIMPORTANT: User is pregnant - provide extra safety warnings and recommend consulting healthcare provider immediately.";
    }
    
    const completion = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: [
        {
          role: "system",
          content: context
        },
        {
          role: "user",
          content: query
        }
      ],
      max_tokens: 300,
      temperature: 0.3 // Lower temperature for more consistent emergency responses
    });
    
    const response = completion.choices[0]?.message?.content || "Please seek immediate medical attention.";
    
    res.json({
      response,
      relevantMedicines: relevantMedicines.slice(0, 2),
      emergencyWarning: "This is not a substitute for professional medical advice. Seek immediate medical attention for emergencies.",
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Emergency query error:', error);
    res.status(500).json({ 
      error: 'Failed to process emergency query',
      emergencyWarning: "Please contact emergency services or your healthcare provider immediately."
    });
  }
});

export default router;