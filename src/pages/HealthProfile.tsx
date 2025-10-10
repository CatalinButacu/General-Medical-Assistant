import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  User, 
  AlertTriangle, 
  Plus, 
  X, 
  Save, 
  Shield,
  Baby,
  Pill,
  Activity
} from 'lucide-react';
import { toast } from 'sonner';

interface HealthProfile {
  userId: string;
  dateOfBirth: string;
  gender: 'male' | 'female' | 'other';
  conditions: string[];
  allergies: string[];
  currentMedications: string[];
  isPregnant: boolean;
  pregnancyDueDate?: string;
  emergencyContact?: {
    name: string;
    phone: string;
  };
}

interface MedicineForSafetyCheck {
  id: string;
  name: string;
  genericName: string;
  dosage: string;
  type: string;
}

interface SafetyCheckResult {
  isContraindicated: boolean;
  warnings: string[];
  recommendations: string[];
  riskLevel: 'low' | 'medium' | 'high';
}

export default function HealthProfile() {
  const navigate = useNavigate();
  const location = useLocation();
  const medicineForSafetyCheck = location.state?.medicineForSafetyCheck as MedicineForSafetyCheck;

  const [profile, setProfile] = useState<HealthProfile>({
    userId: 'user-1', // Mock user ID
    dateOfBirth: '',
    gender: 'female',
    conditions: [],
    allergies: [],
    currentMedications: [],
    isPregnant: false,
    pregnancyDueDate: '',
  });

  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [safetyResult, setSafetyResult] = useState<SafetyCheckResult | null>(null);
  const [showSafetyCheck, setShowSafetyCheck] = useState(false);

  // Form states
  const [newCondition, setNewCondition] = useState('');
  const [newAllergy, setNewAllergy] = useState('');
  const [newMedication, setNewMedication] = useState('');

  useEffect(() => {
    const loadProfileData = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`/api/health-profile/${profile.userId}`);
        if (response.ok) {
          const data = await response.json();
          if (data.profile) {
            setProfile(data.profile);
          }
        }
      } catch (error) {
        console.error('Error loading profile:', error);
        toast.error('Failed to load health profile');
      } finally {
        setIsLoading(false);
      }
    };
    
    loadProfileData();
    if (medicineForSafetyCheck) {
      setShowSafetyCheck(true);
    }
  }, [medicineForSafetyCheck, profile.userId]);



  const saveProfile = async () => {
    setIsSaving(true);
    try {
      const response = await fetch(`/api/health-profile/${profile.userId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(profile),
      });

      if (response.ok) {
        toast.success('Profile saved successfully');
      } else {
        throw new Error('Failed to save profile');
      }
    } catch (error) {
      console.error('Error saving profile:', error);
      toast.error('Failed to save profile');
    } finally {
      setIsSaving(false);
    }
  };

  const performSafetyCheck = async () => {
    if (!medicineForSafetyCheck) return;

    setIsLoading(true);
    try {
      const response = await fetch('/api/medicine/safety-check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          medicine: medicineForSafetyCheck,
          userProfile: profile,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setSafetyResult(result.safetyCheck);
      } else {
        throw new Error('Safety check failed');
      }
    } catch (error) {
      console.error('Error performing safety check:', error);
      toast.error('Safety check failed');
    } finally {
      setIsLoading(false);
    }
  };

  const addCondition = () => {
    if (newCondition.trim() && !profile.conditions.includes(newCondition.trim())) {
      setProfile(prev => ({
        ...prev,
        conditions: [...prev.conditions, newCondition.trim()]
      }));
      setNewCondition('');
    }
  };

  const removeCondition = (condition: string) => {
    setProfile(prev => ({
      ...prev,
      conditions: prev.conditions.filter(c => c !== condition)
    }));
  };

  const addAllergy = () => {
    if (newAllergy.trim() && !profile.allergies.includes(newAllergy.trim())) {
      setProfile(prev => ({
        ...prev,
        allergies: [...prev.allergies, newAllergy.trim()]
      }));
      setNewAllergy('');
    }
  };

  const removeAllergy = (allergy: string) => {
    setProfile(prev => ({
      ...prev,
      allergies: prev.allergies.filter(a => a !== allergy)
    }));
  };

  const addMedication = () => {
    if (newMedication.trim() && !profile.currentMedications.includes(newMedication.trim())) {
      setProfile(prev => ({
        ...prev,
        currentMedications: [...prev.currentMedications, newMedication.trim()]
      }));
      setNewMedication('');
    }
  };

  const removeMedication = (medication: string) => {
    setProfile(prev => ({
      ...prev,
      currentMedications: prev.currentMedications.filter(m => m !== medication)
    }));
  };

  const calculateAge = (dateOfBirth: string) => {
    if (!dateOfBirth) return 0;
    const today = new Date();
    const birthDate = new Date(dateOfBirth);
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age;
  };

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'high': return 'text-red-600 bg-red-50 border-red-200';
      case 'medium': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'low': return 'text-green-600 bg-green-50 border-green-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-md mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => navigate('/')}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <X size={20} />
            </button>
            <h1 className="text-lg font-semibold">Health Profile</h1>
            <button
              onClick={saveProfile}
              disabled={isSaving}
              className="flex items-center space-x-1 bg-blue-600 text-white px-3 py-2 rounded-lg disabled:opacity-50"
            >
              <Save size={16} />
              <span className="text-sm">{isSaving ? 'Saving...' : 'Save'}</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-md mx-auto p-4 space-y-6">
        {/* Safety Check Result */}
        {showSafetyCheck && medicineForSafetyCheck && (
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-800">Safety Check</h2>
              <button
                onClick={performSafetyCheck}
                disabled={isLoading}
                className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
              >
                {isLoading ? 'Checking...' : 'Check Safety'}
              </button>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <h3 className="font-semibold text-gray-800 mb-1">{medicineForSafetyCheck.name}</h3>
              <p className="text-gray-600 text-sm">{medicineForSafetyCheck.dosage} • {medicineForSafetyCheck.type}</p>
            </div>

            {safetyResult && (
              <div className={`border rounded-lg p-4 ${getRiskLevelColor(safetyResult.riskLevel)}`}>
                <div className="flex items-center mb-3">
                  <Shield className="mr-2" size={20} />
                  <span className="font-semibold capitalize">
                    {safetyResult.riskLevel} Risk Level
                  </span>
                </div>

                {safetyResult.warnings.length > 0 && (
                  <div className="mb-3">
                    <h4 className="font-semibold mb-2">⚠️ Warnings:</h4>
                    <ul className="space-y-1">
                      {safetyResult.warnings.map((warning, index) => (
                        <li key={index} className="text-sm">• {warning}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {safetyResult.recommendations.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">💡 Recommendations:</h4>
                    <ul className="space-y-1">
                      {safetyResult.recommendations.map((rec, index) => (
                        <li key={index} className="text-sm">• {rec}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Basic Information */}
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center mb-4">
            <User className="text-blue-600 mr-2" size={20} />
            <h2 className="text-lg font-bold text-gray-800">Basic Information</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Date of Birth
              </label>
              <input
                type="date"
                value={profile.dateOfBirth}
                onChange={(e) => setProfile(prev => ({ ...prev, dateOfBirth: e.target.value }))}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {profile.dateOfBirth && (
                <p className="text-sm text-gray-600 mt-1">Age: {calculateAge(profile.dateOfBirth)} years</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Gender
              </label>
              <select
                value={profile.gender}
                onChange={(e) => setProfile(prev => ({ ...prev, gender: e.target.value as 'male' | 'female' | 'other' }))}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
        </div>

        {/* Pregnancy Status */}
        {profile.gender === 'female' && (
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="flex items-center mb-4">
              <Baby className="text-pink-600 mr-2" size={20} />
              <h2 className="text-lg font-bold text-gray-800">Pregnancy Status</h2>
            </div>

            <div className="space-y-4">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="pregnant"
                  checked={profile.isPregnant}
                  onChange={(e) => setProfile(prev => ({ ...prev, isPregnant: e.target.checked }))}
                  className="w-4 h-4 text-pink-600 border-gray-300 rounded focus:ring-pink-500"
                />
                <label htmlFor="pregnant" className="ml-2 text-gray-700">
                  I am currently pregnant
                </label>
              </div>

              {profile.isPregnant && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Expected Due Date
                  </label>
                  <input
                    type="date"
                    value={profile.pregnancyDueDate || ''}
                    onChange={(e) => setProfile(prev => ({ ...prev, pregnancyDueDate: e.target.value }))}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Medical Conditions */}
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center mb-4">
            <Activity className="text-red-600 mr-2" size={20} />
            <h2 className="text-lg font-bold text-gray-800">Medical Conditions</h2>
          </div>

          <div className="space-y-3">
            <div className="flex space-x-2">
              <input
                type="text"
                value={newCondition}
                onChange={(e) => setNewCondition(e.target.value)}
                placeholder="Add a medical condition"
                className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                onKeyPress={(e) => e.key === 'Enter' && addCondition()}
              />
              <button
                onClick={addCondition}
                className="bg-red-600 text-white p-3 rounded-lg hover:bg-red-700"
              >
                <Plus size={16} />
              </button>
            </div>

            <div className="flex flex-wrap gap-2">
              {profile.conditions.map((condition, index) => (
                <div key={index} className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 flex items-center">
                  <span className="text-red-800 text-sm">{condition}</span>
                  <button
                    onClick={() => removeCondition(condition)}
                    className="ml-2 text-red-600 hover:text-red-800"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Allergies */}
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center mb-4">
            <AlertTriangle className="text-orange-600 mr-2" size={20} />
            <h2 className="text-lg font-bold text-gray-800">Allergies</h2>
          </div>

          <div className="space-y-3">
            <div className="flex space-x-2">
              <input
                type="text"
                value={newAllergy}
                onChange={(e) => setNewAllergy(e.target.value)}
                placeholder="Add an allergy"
                className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                onKeyPress={(e) => e.key === 'Enter' && addAllergy()}
              />
              <button
                onClick={addAllergy}
                className="bg-orange-600 text-white p-3 rounded-lg hover:bg-orange-700"
              >
                <Plus size={16} />
              </button>
            </div>

            <div className="flex flex-wrap gap-2">
              {profile.allergies.map((allergy, index) => (
                <div key={index} className="bg-orange-50 border border-orange-200 rounded-lg px-3 py-2 flex items-center">
                  <span className="text-orange-800 text-sm">{allergy}</span>
                  <button
                    onClick={() => removeAllergy(allergy)}
                    className="ml-2 text-orange-600 hover:text-orange-800"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Current Medications */}
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center mb-4">
            <Pill className="text-green-600 mr-2" size={20} />
            <h2 className="text-lg font-bold text-gray-800">Current Medications</h2>
          </div>

          <div className="space-y-3">
            <div className="flex space-x-2">
              <input
                type="text"
                value={newMedication}
                onChange={(e) => setNewMedication(e.target.value)}
                placeholder="Add current medication"
                className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                onKeyPress={(e) => e.key === 'Enter' && addMedication()}
              />
              <button
                onClick={addMedication}
                className="bg-green-600 text-white p-3 rounded-lg hover:bg-green-700"
              >
                <Plus size={16} />
              </button>
            </div>

            <div className="flex flex-wrap gap-2">
              {profile.currentMedications.map((medication, index) => (
                <div key={index} className="bg-green-50 border border-green-200 rounded-lg px-3 py-2 flex items-center">
                  <span className="text-green-800 text-sm">{medication}</span>
                  <button
                    onClick={() => removeMedication(medication)}
                    className="ml-2 text-green-600 hover:text-green-800"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Safety Notice */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <div className="flex items-start">
            <Shield className="text-blue-600 mr-2 mt-0.5" size={20} />
            <div>
              <h3 className="font-semibold text-blue-800 mb-1">Privacy &amp; Safety</h3>
              <p className="text-blue-700 text-sm">
                Your health information is stored securely and used only to provide personalized safety warnings and recommendations. Always consult healthcare professionals for medical decisions.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}