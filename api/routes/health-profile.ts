import express from 'express';

const router = express.Router();

// In-memory storage for MVP (in production, use a proper database)
const userProfiles = new Map();

// Get user health profile
router.get('/:userId', (req, res) => {
  try {
    const { userId } = req.params;
    const profile = userProfiles.get(userId);
    
    if (!profile) {
      return res.status(404).json({ error: 'Health profile not found' });
    }
    
    res.json(profile);
  } catch (error) {
    console.error('Get health profile error:', error);
    res.status(500).json({ error: 'Failed to get health profile' });
  }
});

// Create or update user health profile
router.post('/:userId', (req, res) => {
  try {
    const { userId } = req.params;
    const profileData = req.body;
    
    // Validate required fields
    const requiredFields = ['dateOfBirth', 'gender'];
    const missingFields = requiredFields.filter(field => !profileData[field]);
    
    if (missingFields.length > 0) {
      return res.status(400).json({ 
        error: 'Missing required fields', 
        missingFields 
      });
    }

    const profile = {
      userId,
      ...profileData,
      updatedAt: new Date().toISOString(),
      createdAt: userProfiles.has(userId) ? userProfiles.get(userId).createdAt : new Date().toISOString()
    };
    
    userProfiles.set(userId, profile);
    
    res.json({
      message: 'Health profile updated successfully',
      profile
    });
  } catch (error) {
    console.error('Update health profile error:', error);
    res.status(500).json({ error: 'Failed to update health profile' });
  }
});

// Update specific health conditions
router.patch('/:userId/conditions', (req, res) => {
  try {
    const { userId } = req.params;
    const { conditions } = req.body;
    
    const profile = userProfiles.get(userId);
    if (!profile) {
      return res.status(404).json({ error: 'Health profile not found' });
    }
    
    profile.conditions = conditions || [];
    profile.updatedAt = new Date().toISOString();
    
    userProfiles.set(userId, profile);
    
    res.json({
      message: 'Health conditions updated successfully',
      conditions: profile.conditions
    });
  } catch (error) {
    console.error('Update conditions error:', error);
    res.status(500).json({ error: 'Failed to update health conditions' });
  }
});

// Update pregnancy status
router.patch('/:userId/pregnancy', (req, res) => {
  try {
    const { userId } = req.params;
    const { isPregnant, dueDate } = req.body;
    
    const profile = userProfiles.get(userId);
    if (!profile) {
      return res.status(404).json({ error: 'Health profile not found' });
    }
    
    profile.isPregnant = isPregnant;
    if (isPregnant && dueDate) {
      profile.dueDate = dueDate;
    } else if (!isPregnant) {
      delete profile.dueDate;
    }
    profile.updatedAt = new Date().toISOString();
    
    userProfiles.set(userId, profile);
    
    res.json({
      message: 'Pregnancy status updated successfully',
      isPregnant: profile.isPregnant,
      dueDate: profile.dueDate
    });
  } catch (error) {
    console.error('Update pregnancy status error:', error);
    res.status(500).json({ error: 'Failed to update pregnancy status' });
  }
});

// Update allergies
router.patch('/:userId/allergies', (req, res) => {
  try {
    const { userId } = req.params;
    const { allergies } = req.body;
    
    const profile = userProfiles.get(userId);
    if (!profile) {
      return res.status(404).json({ error: 'Health profile not found' });
    }
    
    profile.allergies = allergies || [];
    profile.updatedAt = new Date().toISOString();
    
    userProfiles.set(userId, profile);
    
    res.json({
      message: 'Allergies updated successfully',
      allergies: profile.allergies
    });
  } catch (error) {
    console.error('Update allergies error:', error);
    res.status(500).json({ error: 'Failed to update allergies' });
  }
});

// Update current medications
router.patch('/:userId/medications', (req, res) => {
  try {
    const { userId } = req.params;
    const { medications } = req.body;
    
    const profile = userProfiles.get(userId);
    if (!profile) {
      return res.status(404).json({ error: 'Health profile not found' });
    }
    
    profile.currentMedications = medications || [];
    profile.updatedAt = new Date().toISOString();
    
    userProfiles.set(userId, profile);
    
    res.json({
      message: 'Current medications updated successfully',
      medications: profile.currentMedications
    });
  } catch (error) {
    console.error('Update medications error:', error);
    res.status(500).json({ error: 'Failed to update current medications' });
  }
});

// Get safety summary for user
router.get('/:userId/safety-summary', (req, res) => {
  try {
    const { userId } = req.params;
    const profile = userProfiles.get(userId);
    
    if (!profile) {
      return res.status(404).json({ error: 'Health profile not found' });
    }
    
    const summary = {
      userId,
      riskFactors: [],
      safetyAlerts: [],
      recommendations: []
    };
    
    // Check for high-risk conditions
    if (profile.isPregnant) {
      summary.riskFactors.push('pregnancy');
      summary.safetyAlerts.push('Extra caution needed during pregnancy');
      summary.recommendations.push('Always consult healthcare provider before taking any medication');
    }
    
    if (profile.allergies && profile.allergies.length > 0) {
      summary.riskFactors.push('allergies');
      summary.safetyAlerts.push(`Known allergies: ${profile.allergies.join(', ')}`);
      summary.recommendations.push('Always check medication ingredients for allergens');
    }
    
    if (profile.conditions && profile.conditions.length > 0) {
      summary.riskFactors.push('medical_conditions');
      summary.safetyAlerts.push(`Medical conditions: ${profile.conditions.join(', ')}`);
      summary.recommendations.push('Check for drug interactions with your conditions');
    }
    
    if (profile.currentMedications && profile.currentMedications.length > 0) {
      summary.riskFactors.push('drug_interactions');
      summary.safetyAlerts.push(`Currently taking ${profile.currentMedications.length} medication(s)`);
      summary.recommendations.push('Check for drug-drug interactions');
    }
    
    // Calculate overall risk level
    const riskLevel = summary.riskFactors.length === 0 ? 'low' : 
                     summary.riskFactors.length <= 2 ? 'medium' : 'high';
    
    (summary as any).riskLevel = riskLevel;
    (summary as any).lastUpdated = profile.updatedAt;
    
    res.json(summary);
  } catch (error) {
    console.error('Get safety summary error:', error);
    res.status(500).json({ error: 'Failed to get safety summary' });
  }
});

// Delete health profile
router.delete('/:userId', (req, res) => {
  try {
    const { userId } = req.params;
    
    if (!userProfiles.has(userId)) {
      return res.status(404).json({ error: 'Health profile not found' });
    }
    
    userProfiles.delete(userId);
    
    res.json({ message: 'Health profile deleted successfully' });
  } catch (error) {
    console.error('Delete health profile error:', error);
    res.status(500).json({ error: 'Failed to delete health profile' });
  }
});

export default router;