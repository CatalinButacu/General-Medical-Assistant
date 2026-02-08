import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  User, AlertTriangle, Plus, X, Save, Shield, Baby, Pill, Activity
} from 'lucide-react';
import { toast } from 'sonner';
import type { HealthProfile as IHealthProfile, Medicine } from '../types';

interface SafetyCheckResult {
  isContraindicated: boolean;
  warnings: string[];
  recommendations: string[];
  riskLevel: 'low' | 'medium' | 'high';
}

export default function HealthProfile() {
  const navigate = useNavigate();
  const location = useLocation();
  const medicineForSafetyCheck = location.state?.medicineForSafetyCheck as Medicine;

  const [profile, setProfile] = useState<IHealthProfile>({
    id: 'user-1',
    name: 'Test User',
    dateOfBirth: '',
    gender: 'female',
    conditions: [],
    allergies: [],
    medications: [],
    isPregnant: false,
    pregnancyDueDate: '',
  } as any);

  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [safetyResult, setSafetyResult] = useState<SafetyCheckResult | null>(null);
  const [showSafetyCheck, setShowSafetyCheck] = useState(false);

  const [newCondition, setNewCondition] = useState('');
  const [newAllergy, setNewAllergy] = useState('');
  const [newMedication, setNewMedication] = useState('');

  useEffect(() => {
    loadProfile();
    if (medicineForSafetyCheck) setShowSafetyCheck(true);
  }, [medicineForSafetyCheck]);

  const loadProfile = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/health-profile/${profile.id}`);
      if (response.ok) {
        const data = await response.json();
        if (data.profile) setProfile(data.profile);
      }
    } catch (error) {
      toast.error('Failed to load health profile');
    } finally {
      setIsLoading(false);
    }
  };

  const saveProfile = async () => {
    setIsSaving(true);
    try {
      const response = await fetch(`/api/health-profile/${profile.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile),
      });
      if (response.ok) toast.success('Profile saved');
      else throw new Error();
    } catch (error) {
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ medicine: medicineForSafetyCheck, userProfile: profile }),
      });
      if (response.ok) {
        const result = await response.json();
        setSafetyResult(result.safetyCheck);
      }
    } catch (error) {
      toast.error('Safety check failed');
    } finally {
      setIsLoading(false);
    }
  };

  const addCondition = () => {
    if (newCondition.trim() && !profile.conditions.includes(newCondition.trim())) {
      setProfile(prev => ({ ...prev, conditions: [...prev.conditions, newCondition.trim()] }));
      setNewCondition('');
    }
  };

  const addAllergy = () => {
    if (newAllergy.trim() && !profile.allergies.includes(newAllergy.trim())) {
      setProfile(prev => ({ ...prev, allergies: [...prev.allergies, newAllergy.trim()] }));
      setNewAllergy('');
    }
  };

  const addMedication = () => {
    if (newMedication.trim() && !profile.medications.includes(newMedication.trim())) {
      setProfile(prev => ({ ...prev, medications: [...prev.medications, newMedication.trim()] }));
      setNewMedication('');
    }
  };

  const calculateAge = (dob: string) => {
    if (!dob) return 0;
    const birth = new Date(dob);
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    if (today.getMonth() < birth.getMonth() || (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())) age--;
    return age;
  };

  const getRiskColor = (level: string) => {
    if (level === 'high') return 'text-red-600 bg-red-50 border-red-200';
    if (level === 'medium') return 'text-orange-600 bg-orange-50 border-orange-200';
    return 'text-green-600 bg-green-50 border-green-200';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow-sm">
        <div className="max-w-md mx-auto px-4 py-4 flex items-center justify-between">
          <button onClick={() => navigate('/')} className="p-2 hover:bg-gray-100 rounded-lg"><X size={20} /></button>
          <h1 className="text-lg font-semibold">Health Profile</h1>
          <button onClick={saveProfile} disabled={isSaving} className="flex items-center space-x-1 bg-blue-600 text-white px-3 py-2 rounded-lg disabled:opacity-50">
            <Save size={16} /> <span className="text-sm">{isSaving ? 'Saving...' : 'Save'}</span>
          </button>
        </div>
      </div>

      <div className="max-w-md mx-auto p-4 space-y-6">
        {showSafetyCheck && medicineForSafetyCheck && (
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold">Safety Check</h2>
              <button onClick={performSafetyCheck} disabled={isLoading} className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm">{isLoading ? 'Checking...' : 'Check Safety'}</button>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <h3 className="font-semibold">{medicineForSafetyCheck.name}</h3>
              <p className="text-gray-600 text-sm">{medicineForSafetyCheck.dosage} • {medicineForSafetyCheck.type}</p>
            </div>
            {safetyResult && (
              <div className={`border rounded-lg p-4 ${getRiskColor(safetyResult.riskLevel)}`}>
                <div className="flex items-center mb-3 font-semibold"><Shield className="mr-2" size={20} /> <span className="capitalize">{safetyResult.riskLevel} Risk</span></div>
                {safetyResult.warnings.map((w, i) => <p key={i} className="text-sm">• {w}</p>)}
                {safetyResult.recommendations.map((r, i) => <p key={i} className="text-sm mt-2">• {r}</p>)}
              </div>
            )}
          </div>
        )}

        <div className="bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center mb-4"><User className="text-blue-600 mr-2" size={20} /><h2 className="text-lg font-bold">Basic Info</h2></div>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-gray-400 uppercase mb-2">Date of Birth</label>
              <input type="date" value={(profile as any).dateOfBirth} onChange={e => setProfile(p => ({ ...p, dateOfBirth: e.target.value } as any))} className="w-full p-3 border rounded-lg" />
              {(profile as any).dateOfBirth && <p className="text-xs text-gray-500 mt-2">Age: {calculateAge((profile as any).dateOfBirth)} years</p>}
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-400 uppercase mb-2">Gender</label>
              <select value={profile.gender} onChange={e => setProfile(p => ({ ...p, gender: e.target.value as any }))} className="w-full p-3 border rounded-lg">
                <option value="female">Female</option><option value="male">Male</option><option value="other">Other</option>
              </select>
            </div>
          </div>
        </div>

        {profile.gender === 'female' && (
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="flex items-center mb-4"><Baby className="text-pink-600 mr-2" size={20} /><h2 className="text-lg font-bold">Pregnancy</h2></div>
            <div className="space-y-4">
              <label className="flex items-center space-x-2">
                <input type="checkbox" checked={profile.isPregnant} onChange={e => setProfile(p => ({ ...p, isPregnant: e.target.checked }))} className="w-4 h-4 rounded text-pink-600" />
                <span>Currently pregnant</span>
              </label>
              {profile.isPregnant && <input type="date" value={profile.pregnancyDueDate} onChange={e => setProfile(p => ({ ...p, pregnancyDueDate: e.target.value }))} className="w-full p-3 border rounded-lg" />}
            </div>
          </div>
        )}

        <Section title="Conditions" icon={<Activity className="text-red-600" size={20} />} items={profile.conditions} onAdd={addCondition} onRemove={c => setProfile(p => ({ ...p, conditions: p.conditions.filter(x => x !== c) }))} value={newCondition} onChange={setNewCondition} />
        <Section title="Allergies" icon={<AlertTriangle className="text-orange-600" size={20} />} items={profile.allergies} onAdd={addAllergy} onRemove={a => setProfile(p => ({ ...p, allergies: p.allergies.filter(x => x !== a) }))} value={newAllergy} onChange={setNewAllergy} />
        <Section title="Medications" icon={<Pill className="text-green-600" size={20} />} items={profile.medications} onAdd={addMedication} onRemove={m => setProfile(p => ({ ...p, medications: p.medications.filter(x => x !== m) }))} value={newMedication} onChange={setNewMedication} />

        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-start">
          <Shield className="text-blue-600 mr-2 mt-0.5 flex-shrink-0" size={20} />
          <p className="text-blue-700 text-xs font-medium">Your data is stored securely. Always consult a professional for medical decisions.</p>
        </div>
      </div>
    </div>
  );
}

function Section({ title, icon, items, onAdd, onRemove, value, onChange }: any) {
  return (
    <div className="bg-white rounded-xl p-6 shadow-sm">
      <div className="flex items-center mb-4">{icon}<h2 className="text-lg font-bold ml-2">{title}</h2></div>
      <div className="flex space-x-2 mb-4">
        <input type="text" value={value} onChange={e => onChange(e.target.value)} placeholder={`Add ${title.toLowerCase()}...`} className="flex-1 p-3 border rounded-lg text-sm" onKeyPress={e => e.key === 'Enter' && onAdd()} />
        <button onClick={onAdd} className="bg-gray-800 text-white p-3 rounded-lg"><Plus size={16} /></button>
      </div>
      <div className="flex flex-wrap gap-2">
        {items.map((item: string, i: number) => (
          <div key={i} className="bg-gray-100 px-3 py-1.5 rounded-full flex items-center text-sm">
            <span>{item}</span>
            <button onClick={() => onRemove(item)} className="ml-2 text-gray-400 hover:text-red-600"><X size={14} /></button>
          </div>
        ))}
      </div>
    </div>
  );
}
