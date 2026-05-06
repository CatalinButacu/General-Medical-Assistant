import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import {
  collection, query, where, onSnapshot,
  addDoc, updateDoc, deleteDoc, doc,
  serverTimestamp
} from 'firebase/firestore';
import { db } from '../config/firebase';
import {
  Package, Plus, Search, Calendar, AlertTriangle,
  Trash2, Camera, Edit3, X, Clock, CheckCircle, Sparkles
} from 'lucide-react';
import { toast } from 'sonner';
import type { CabinetItem, Medicine } from '../types';

export default function MedicineCabinet() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth0();
  const medicineToAdd = location.state?.addMedicine as (Medicine & { expirationDate?: string }) | undefined;
  const fromScanner = Boolean(location.state?.fromScanner);

  const [medicines, setMedicines] = useState<CabinetItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'expired' | 'expiring' | 'active'>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingMedicine, setEditingMedicine] = useState<CabinetItem | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    genericName: '',
    dosage: '',
    type: 'tablet',
    quantity: 1,
    expirationDate: '',
    notes: ''
  });

  useEffect(() => {
    if (!user?.sub) return;

    const q = query(
      collection(db, 'medicine_cabinets'),
      where('userId', '==', user.sub)
    );

    const unsubscribe = onSnapshot(q, (snapshot) => {
      const today = new Date();
      const items = snapshot.docs.map(doc => {
        const data = doc.data();
        const expDate = new Date(data.expirationDate);
        const daysDiff = Math.ceil((expDate.getTime() - today.getTime()) / (1000 * 3600 * 24));
        return {
          id: doc.id,
          ...data,
          isExpired: daysDiff < 0,
          daysUntilExpiration: daysDiff
        } as CabinetItem;
      });
      setMedicines(items);
      setIsLoading(false);
    }, (error) => {
      console.error("Firestore error:", error);
      toast.error('Failed to sync cabinet data');
      setIsLoading(false);
    });

    return () => unsubscribe();
  }, [user]);

  useEffect(() => {
    if (medicineToAdd) {
      setFormData({
        name: medicineToAdd.name,
        genericName: medicineToAdd.genericName || '',
        dosage: medicineToAdd.dosage || '',
        type: medicineToAdd.type || 'tablet',
        quantity: 1,
        expirationDate: medicineToAdd.expirationDate || '',
        notes: ''
      });
      setShowAddForm(true);
    }
  }, [medicineToAdd]);

  const saveMedicine = async () => {
    if (!formData.name || !formData.expirationDate || !user?.sub) {
      toast.error('Missing required fields');
      return;
    }

    const payload = {
      userId: user.sub,
      name: formData.name,
      genericName: formData.genericName,
      dosage: formData.dosage,
      type: formData.type,
      quantity: formData.quantity,
      expirationDate: formData.expirationDate,
      addedDate: editingMedicine?.addedDate || new Date().toISOString().split('T')[0],
      notes: formData.notes,
      updatedAt: serverTimestamp()
    };

    try {
      if (editingMedicine) {
        await updateDoc(doc(db, 'medicine_cabinets', editingMedicine.id), payload);
        toast.success('Medicine updated');
      } else {
        await addDoc(collection(db, 'medicine_cabinets'), payload);
        toast.success('Medicine added');
      }
      setShowAddForm(false);
      setEditingMedicine(null);
      resetForm();
    } catch (e) {
      toast.error('Failed to save medicine');
    }
  };

  const resetForm = () => setFormData({ name: '', genericName: '', dosage: '', type: 'tablet', quantity: 1, expirationDate: '', notes: '' });

  const startEdit = (item: CabinetItem) => {
    setEditingMedicine(item);
    setFormData({
      name: item.name,
      genericName: item.genericName || '',
      dosage: item.dosage || '',
      type: item.type || 'tablet',
      quantity: item.quantity,
      expirationDate: item.expirationDate,
      notes: item.notes || ''
    });
    setShowAddForm(true);
  };

  const deleteMedicine = async (id: string) => {
    try {
      await deleteDoc(doc(db, 'medicine_cabinets', id));
      toast.success('Removed from cabinet');
    } catch (e) {
      toast.error('Failed to delete');
    }
  };

  const getStatus = (item: CabinetItem) => {
    if (item.isExpired) return { color: 'text-red-600 bg-red-50', label: 'Expired', icon: AlertTriangle };
    if ((item.daysUntilExpiration ?? 100) <= 30) return { color: 'text-orange-600 bg-orange-50', label: 'Expiring Soon', icon: Clock };
    return { color: 'text-green-600 bg-green-50', label: 'Active', icon: CheckCircle };
  };

  const filteredMedicines = medicines.filter(med => {
    const queryStr = searchQuery.toLowerCase();
    const matchesSearch = med.name.toLowerCase().includes(queryStr) || med.genericName?.toLowerCase().includes(queryStr);
    const matchesFilter = filterType === 'expired' ? med.isExpired :
      filterType === 'expiring' ? (!med.isExpired && (med.daysUntilExpiration ?? 0) <= 30) :
        filterType === 'active' ? (!med.isExpired && (med.daysUntilExpiration ?? 0) > 30) : true;
    return matchesSearch && matchesFilter;
  });

  const expiredCount = medicines.filter(m => m.isExpired).length;
  const expiringCount = medicines.filter(m => !m.isExpired && (m.daysUntilExpiration ?? 0) <= 30).length;

  return (
    <div className="h-full flex flex-col">
      <div className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-md mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <button onClick={() => navigate('/')} className="p-2 hover:bg-gray-100 rounded-lg"><X size={20} /></button>
            <h1 className="text-lg font-semibold">Medicine Cabinet</h1>
            <button onClick={() => setShowAddForm(true)} className="bg-blue-600 text-white p-2 rounded-lg"><Plus size={20} /></button>
          </div>
        </div>
      </div>

      <div className="max-w-md mx-auto p-4">
        {(expiredCount > 0 || expiringCount > 0) && (
          <div className="mb-6 space-y-2">
            {expiredCount > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center">
                <AlertTriangle className="text-red-600 mr-3" size={20} />
                <span className="text-red-800 font-semibold">{expiredCount} medicine{expiredCount > 1 ? 's' : ''} expired</span>
              </div>
            )}
            {expiringCount > 0 && (
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 flex items-center">
                <Clock className="text-orange-600 mr-3" size={20} />
                <span className="text-orange-800 font-semibold">{expiringCount} medicine{expiringCount > 1 ? 's' : ''} expiring soon</span>
              </div>
            )}
          </div>
        )}

        <div className="mb-6 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text" placeholder="Search medicines..." value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
            />
          </div>

          <div className="flex space-x-2 overflow-x-auto pb-1 no-scrollbar">
            {['all', 'active', 'expiring', 'expired'].map(key => (
              <button
                key={key} onClick={() => setFilterType(key as any)}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all whitespace-nowrap ${filterType === key ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-gray-600 border border-gray-200'}`}
              >
                {key.charAt(0).toUpperCase() + key.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          {isLoading ? (
            <div className="text-center py-20">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-500 font-medium">Syncing with cloud...</p>
            </div>
          ) : filteredMedicines.length === 0 ? (
            <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-gray-300">
              <Package className="mx-auto mb-4 text-gray-300" size={48} />
              <p className="text-gray-500 font-medium">No medicines found</p>
              <button onClick={() => setShowAddForm(true)} className="mt-4 text-blue-600 font-bold">Add Your First Medicine</button>
            </div>
          ) : (
            filteredMedicines.map(med => {
              const status = getStatus(med);
              const StatusIcon = status.icon;
              return (
                <div key={med.id} className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <h3 className="font-bold text-gray-800 text-lg leading-tight">{med.name}</h3>
                      {med.genericName && <p className="text-gray-500 text-sm font-medium mt-1">{med.genericName}</p>}
                      <div className="flex items-center flex-wrap gap-2 mt-3">
                        <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-bold rounded uppercase tracking-wider">{med.dosage}</span>
                        <span className="px-2 py-0.5 bg-gray-50 text-gray-600 text-[10px] font-bold rounded uppercase tracking-wider">{med.type}</span>
                        <span className="px-2 py-0.5 bg-gray-50 text-gray-600 text-[10px] font-bold rounded uppercase tracking-wider">Qty: {med.quantity}</span>
                      </div>
                    </div>
                    <div className="flex -mr-2">
                      <button onClick={() => startEdit(med)} className="p-2 text-gray-400 hover:text-blue-600 transition-colors"><Edit3 size={18} /></button>
                      <button onClick={() => deleteMedicine(med.id)} className="p-2 text-gray-400 hover:text-red-600 transition-colors"><Trash2 size={18} /></button>
                    </div>
                  </div>
                  <div className={`inline-flex items-center px-3 py-1 rounded-full text-[11px] font-bold border ${status.color}`}>
                    <StatusIcon size={12} className="mr-1.5" /> {status.label} {!med.isExpired && med.daysUntilExpiration !== undefined && `(${med.daysUntilExpiration} days left)`}
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-gray-400 mt-4 pt-4 border-t border-gray-50">
                    <div className="flex items-center font-medium"><Calendar size={12} className="mr-1.5" /> Expires: {med.expirationDate}</div>
                    <div className="font-medium">Added: {med.addedDate}</div>
                  </div>
                  {med.notes && <div className="mt-3 p-3 bg-gray-50 rounded-xl text-xs text-gray-600 italic">"{med.notes}"</div>}
                </div>
              );
            })
          )}
        </div>
      </div>

      {showAddForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-end justify-center z-50 p-4">
          <div className="bg-white w-full max-w-md rounded-3xl p-6 shadow-2xl animate-in slide-in-from-bottom duration-300">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-xl font-bold text-gray-800">{editingMedicine ? 'Edit Medicine' : 'Add to Cabinet'}</h2>
              <button onClick={() => { setShowAddForm(false); setEditingMedicine(null); resetForm(); }} className="p-2 bg-gray-100 rounded-full hover:bg-gray-200 transition-colors"><X size={20} /></button>
            </div>
            {fromScanner && !editingMedicine && (
              <div className="flex items-center gap-2 mb-6 px-3 py-2 bg-blue-50 border border-blue-100 rounded-xl text-[11px] font-semibold text-blue-700">
                <Sparkles size={12} />
                <span>Date precompletate din scaner — verifică și ajustează dacă e cazul.</span>
              </div>
            )}
            {!fromScanner && <div className="mb-6" />}
            <div className="space-y-5">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-gray-400 uppercase ml-1">Medicine Name</label>
                <input type="text" placeholder="e.g. Paracetamol" value={formData.name} onChange={e => setFormData(p => ({ ...p, name: e.target.value }))} className="w-full p-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 font-medium" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-gray-400 uppercase ml-1">Generic / Active Ingredient</label>
                <input type="text" placeholder="e.g. Acetaminophen" value={formData.genericName} onChange={e => setFormData(p => ({ ...p, genericName: e.target.value }))} className="w-full p-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 font-medium" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-gray-400 uppercase ml-1">Dosage</label>
                  <input type="text" placeholder="500mg" value={formData.dosage} onChange={e => setFormData(p => ({ ...p, dosage: e.target.value }))} className="w-full p-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 font-medium" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-gray-400 uppercase ml-1">Form</label>
                  <select value={formData.type} onChange={e => setFormData(p => ({ ...p, type: e.target.value }))} className="w-full p-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 font-medium appearance-none">
                    {['tablet', 'capsule', 'liquid', 'cream', 'injection', 'other'].map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-gray-400 uppercase ml-1">Quantity</label>
                  <input type="number" value={formData.quantity} onChange={e => setFormData(p => ({ ...p, quantity: parseInt(e.target.value) || 1 }))} className="w-full p-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 font-medium" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-gray-400 uppercase ml-1">Expiry Date</label>
                  <input type="date" value={formData.expirationDate} onChange={e => setFormData(p => ({ ...p, expirationDate: e.target.value }))} className="w-full p-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 font-medium" />
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-gray-400 uppercase ml-1">Private Notes</label>
                <textarea placeholder="e.g. Take after meal" value={formData.notes} onChange={e => setFormData(p => ({ ...p, notes: e.target.value }))} rows={2} className="w-full p-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 font-medium resize-none" />
              </div>
              <button onClick={saveMedicine} className="w-full bg-blue-600 text-white py-4 rounded-2xl font-bold shadow-lg shadow-blue-100 hover:bg-blue-700 transition-all active:scale-[0.98] mt-4 uppercase tracking-widest text-sm">{editingMedicine ? 'Update Entry' : 'Add to Cabinet'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
