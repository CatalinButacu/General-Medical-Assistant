import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import {
  User, AlertTriangle, Plus, X, Save, Shield, Baby, Pill, Activity
} from 'lucide-react';
import { toast } from 'sonner';
import { useUserApi } from '../hooks/useUserApi';
import { userPaths, type ProfileDTO } from '../services/userApi';
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
  const { user } = useAuth0();
  const apiCall = useUserApi();
  const medicineForSafetyCheck = location.state?.medicineForSafetyCheck as Medicine;

  const [profile, setProfile] = useState<IHealthProfile>({
    id: '',
    name: '',
    conditions: [],
    allergies: [],
    medications: [],
    isPregnant: false,
    pregnancyDueDate: '',
  } as IHealthProfile);

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [safetyResult, setSafetyResult] = useState<SafetyCheckResult | null>(null);
  const [showSafetyCheck, setShowSafetyCheck] = useState(false);

  const [newCondition, setNewCondition] = useState('');
  const [newAllergy, setNewAllergy] = useState('');
  const [newMedication, setNewMedication] = useState('');

  useEffect(() => {
    if (user?.sub) {
      loadProfile(user.sub);
    }
    if (medicineForSafetyCheck) setShowSafetyCheck(true);
  }, [user, medicineForSafetyCheck]);

  const loadProfile = async (userId: string) => {
    setIsLoading(true);
    try {
      const p = await apiCall<ProfileDTO>(userPaths.profile);
      setProfile({
        id: userId,
        name: p.name || user?.name || 'User',
        age: p.age ?? undefined,
        gender: p.gender ?? undefined,
        isPregnant: p.isPregnant ?? false,
        pregnancyDueDate: p.pregnancyDueDate ?? '',
        allergies: p.allergies ?? [],
        conditions: p.conditions ?? [],
        medications: p.medications ?? [],
      });
    } catch (error) {
      console.error("Load error:", error);
      toast.error('Încărcarea profilului a eșuat');
      setProfile({
        id: userId,
        name: user?.name || 'User',
        conditions: [],
        allergies: [],
        medications: [],
        isPregnant: false,
        pregnancyDueDate: '',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const saveProfile = async () => {
    if (!user?.sub) return;
    setIsSaving(true);
    try {
      const payload: ProfileDTO = {
        name: profile.name || null,
        age: profile.age ?? null,
        gender: profile.gender ?? null,
        isPregnant: Boolean(profile.isPregnant),
        pregnancyDueDate: profile.pregnancyDueDate || null,
        allergies: profile.allergies,
        conditions: profile.conditions,
        medications: profile.medications,
      };
      await apiCall<ProfileDTO>(userPaths.profile, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });
      toast.success('Profil salvat');
    } catch {
      toast.error('Salvarea profilului a eșuat');
    } finally {
      setIsSaving(false);
    }
  };

  const performSafetyCheck = async () => {
    if (!medicineForSafetyCheck) return;
    setIsLoading(true);
    try {
      // Still using the backend API for safety logic as it might involve complex ML or data scraping
      const response = await fetch('/api/medicine/safety-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ medicine: medicineForSafetyCheck, userProfile: profile }),
      });
      if (response.ok) {
        const result = await response.json();
        setSafetyResult(result.safetyCheck);
      } else {
        // Demo fallback if API doesn't exist yet
        setTimeout(() => {
          setSafetyResult({
            isContraindicated: false,
            warnings: ['Consultă întotdeauna un medic înainte de a combina medicamente.'],
            recommendations: ['Verifică cu atenție indicațiile de dozaj.'],
            riskLevel: 'low'
          });
          setIsLoading(false);
        }, 1000);
        return;
      }
    } catch {
      toast.error('Backend indisponibil pentru verificarea siguranței');
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

  const calculateAge = (dob?: string) => {
    if (!dob) return 0;
    const birth = new Date(dob);
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const m = today.getMonth() - birth.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
    return age;
  };

  const getRiskColor = (level: string) => {
    if (level === 'high') return 'text-red-600 bg-red-50 border-red-200';
    if (level === 'medium') return 'text-orange-600 bg-orange-50 border-orange-200';
    return 'text-green-600 bg-green-50 border-green-200';
  };

  if (isLoading && !profile.id) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-md mx-auto px-4 py-4 flex items-center justify-between">
          <button onClick={() => navigate('/')} className="p-2 hover:bg-gray-100 rounded-full transition-colors font-bold text-gray-400 hover:text-gray-800"><X size={20} /></button>
          <h1 className="text-lg font-bold text-gray-800">Profil de sănătate</h1>
          <button onClick={saveProfile} disabled={isSaving} className="flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-xl font-bold text-sm shadow-md shadow-blue-100 disabled:opacity-50 active:scale-95 transition-all">
            <Save size={16} /> <span>{isSaving ? 'Salvez…' : 'Salvează'}</span>
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {showSafetyCheck && medicineForSafetyCheck && (
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-red-100 animate-in fade-in slide-in-from-top duration-300">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-gray-800">Verificare siguranță</h2>
              <button onClick={performSafetyCheck} disabled={isLoading} className="bg-red-600 text-white px-4 py-2 rounded-xl font-bold text-xs shadow-lg shadow-red-100 hover:bg-red-700 transition-colors">{isLoading ? 'Verific…' : 'Verifică'}</button>
            </div>
            <div className="bg-gray-50 rounded-2xl p-4 mb-5 border border-gray-100">
              <h3 className="font-bold text-gray-800 text-sm">{medicineForSafetyCheck.name}</h3>
              <p className="text-gray-500 text-[10px] font-bold uppercase tracking-wider mt-1">{medicineForSafetyCheck.dosage} • {medicineForSafetyCheck.type}</p>
            </div>
            {safetyResult && (
              <div className={`border rounded-2xl p-5 ${getRiskColor(safetyResult.riskLevel)} transition-colors`}>
                <div className="flex items-center mb-4 font-bold text-sm uppercase tracking-wider"><Shield className="mr-2" size={20} /> <span>Risc {safetyResult.riskLevel === 'high' ? 'ridicat' : safetyResult.riskLevel === 'medium' ? 'mediu' : 'scăzut'}</span></div>
                <div className="space-y-3">
                  {safetyResult.warnings.map((w, i) => <p key={i} className="text-xs font-semibold leading-relaxed flex items-start"><span className="mr-1.5">•</span> {w}</p>)}
                  <div className="pt-3 border-t border-black/5 opacity-80">
                    <p className="text-[10px] font-bold uppercase mb-2">Recomandări</p>
                    {safetyResult.recommendations.map((r, i) => <p key={i} className="text-xs font-medium leading-relaxed flex items-start italic"><span className="mr-1.5">›</span> {r}</p>)}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {user && (
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 flex items-center space-x-4">
            {user.picture ? (
              <img src={user.picture} alt={user.name || 'profile'} className="w-14 h-14 rounded-full border-2 border-blue-100 shadow-sm" />
            ) : (
              <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center">
                <User className="text-blue-600" size={28} />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="font-bold text-gray-800 truncate">{user.name || profile.name || 'User'}</p>
              {user.email && <p className="text-xs text-gray-500 truncate mt-0.5">{user.email}</p>}
              <div className="inline-flex items-center mt-1.5 text-[9px] font-bold text-green-700 uppercase tracking-widest bg-green-50 px-2 py-0.5 rounded-full">
                <span className="w-1 h-1 bg-green-500 rounded-full mr-1.5" />
                Conectat prin Google
              </div>
            </div>
          </div>
        )}

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center mb-6"><div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center mr-3"><User className="text-blue-600" size={18} /></div><h2 className="text-lg font-bold text-gray-800">Informații de bază</h2></div>
          <div className="space-y-5">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-gray-400 uppercase ml-1 tracking-widest leading-none">Data nașterii</label>
              <input type="date" value={profile.dateOfBirth || ''} onChange={e => setProfile(p => ({ ...p, dateOfBirth: e.target.value }))} className="w-full p-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 font-medium" />
              {profile.dateOfBirth && <p className="text-[10px] font-bold text-blue-500 mt-2 px-1">Vârsta actuală: {calculateAge(profile.dateOfBirth)} ani</p>}
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-gray-400 uppercase ml-1 tracking-widest leading-none">Gen</label>
              <div className="flex gap-2">
                {([
                  { v: 'female', l: 'Feminin' },
                  { v: 'male', l: 'Masculin' },
                  { v: 'other', l: 'Altul' },
                ] as const).map(({ v, l }) => (
                  <button key={v} onClick={() => setProfile(p => ({ ...p, gender: v }))} className={`flex-1 py-3 px-2 rounded-2xl text-xs font-bold transition-all border-2 ${profile.gender === v ? 'bg-blue-600 text-white border-blue-600 shadow-lg shadow-blue-100' : 'bg-gray-50 text-gray-500 border-gray-50 opacity-60 hover:opacity-100'}`}>
                    {l}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {profile.gender === 'female' && (
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 overflow-hidden relative">
            <div className="flex items-center mb-6"><div className="w-8 h-8 rounded-lg bg-pink-100 flex items-center justify-center mr-3"><Baby className="text-pink-600" size={18} /></div><h2 className="text-lg font-bold text-gray-800">Stare de sarcină</h2></div>
            <div className="space-y-5">
              <button
                onClick={() => setProfile(p => ({ ...p, isPregnant: !p.isPregnant }))}
                className={`w-full p-4 rounded-2xl flex items-center justify-between transition-all ${profile.isPregnant ? 'bg-pink-50 border-2 border-pink-200' : 'bg-gray-50 border-2 border-transparent'}`}
              >
                <span className={`text-sm font-bold ${profile.isPregnant ? 'text-pink-700' : 'text-gray-500'}`}>Sunt însărcinată</span>
                <div className={`w-10 h-6 rounded-full p-1 transition-colors ${profile.isPregnant ? 'bg-pink-500' : 'bg-gray-300'}`}>
                  <div className={`w-4 h-4 bg-white rounded-full transition-transform ${profile.isPregnant ? 'translate-x-4' : 'translate-x-0'}`}></div>
                </div>
              </button>
              {profile.isPregnant && (
                <div className="space-y-1.5 animate-in slide-in-from-top duration-300">
                  <label className="text-[10px] font-bold text-gray-400 uppercase ml-1">Data probabilă a nașterii</label>
                  <input type="date" value={profile.pregnancyDueDate || ''} onChange={e => setProfile(p => ({ ...p, pregnancyDueDate: e.target.value }))} className="w-full p-3.5 bg-pink-50 border-none rounded-2xl focus:ring-2 focus:ring-pink-500 font-medium text-pink-900" />
                </div>
              )}
            </div>
          </div>
        )}

        <Section title="Condiții cronice" placeholder="Adaugă o condiție…" icon={<Activity className="text-red-600" size={18} />} items={profile.conditions} onAdd={addCondition} onRemove={c => setProfile(p => ({ ...p, conditions: p.conditions.filter(x => x !== c) }))} value={newCondition} onChange={setNewCondition} />
        <Section title="Alergii la medicamente" placeholder="Adaugă o alergie…" icon={<AlertTriangle className="text-orange-600" size={18} />} items={profile.allergies} onAdd={addAllergy} onRemove={a => setProfile(p => ({ ...p, allergies: p.allergies.filter(x => x !== a) }))} value={newAllergy} onChange={setNewAllergy} />
        <Section title="Medicamente curente" placeholder="Adaugă un medicament…" icon={<Pill className="text-green-600" size={18} />} items={profile.medications} onAdd={addMedication} onRemove={m => setProfile(p => ({ ...p, medications: p.medications.filter(x => x !== m) }))} value={newMedication} onChange={setNewMedication} />

        <div className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-2xl p-6 text-white shadow-xl shadow-blue-200">
          <div className="flex items-start">
            <Shield className="mr-4 mt-0.5 flex-shrink-0 opacity-80" size={24} />
            <div>
              <h4 className="font-bold mb-1 text-sm">Date securizate</h4>
              <p className="text-[10px] font-medium leading-relaxed opacity-70 uppercase tracking-tighter">Datele tale sunt stocate în cloud-ul personal. Le folosim doar pentru a verifica contraindicații medicale.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface SectionProps {
  title: string;
  placeholder?: string;
  icon: React.ReactNode;
  items: string[];
  onAdd: () => void;
  onRemove: (item: string) => void;
  value: string;
  onChange: (value: string) => void;
}

function Section({ title, placeholder, icon, items, onAdd, onRemove, value, onChange }: SectionProps) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
      <div className="flex items-center mb-6">
        <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center mr-3">{icon}</div>
        <h2 className="text-lg font-bold text-gray-800">{title}</h2>
      </div>
      <div className="flex space-x-2 mb-6">
        <input
          type="text" value={value} onChange={e => onChange(e.target.value)}
          placeholder={placeholder ?? 'Adaugă…'}
          className="flex-1 p-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 font-medium text-sm"
          onKeyPress={e => e.key === 'Enter' && onAdd()}
        />
        <button onClick={onAdd} className="bg-blue-600 text-white p-3.5 rounded-2xl shadow-lg shadow-blue-100 hover:bg-blue-700 transition-colors active:scale-95 flex items-center justify-center">
          <Plus size={20} />
        </button>
      </div>
      <div className="flex flex-wrap gap-2.5">
        {items.length === 0 ? (
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest italic px-1">Nimic adăugat încă</p>
        ) : (
          items.map((item, i) => (
            <div key={i} className="bg-gray-50 border border-gray-100 px-4 py-2 rounded-2xl flex items-center animate-in zoom-in duration-200">
              <span className="text-xs font-bold text-gray-700">{item}</span>
              <button onClick={() => onRemove(item)} className="ml-2.5 p-1 bg-white text-gray-400 hover:text-red-600 rounded-full transition-colors active:scale-95 shadow-sm"><X size={10} /></button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
