import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Package, Plus, Search, Calendar, AlertTriangle,
  Trash2, Camera, Edit3, X, Clock, CheckCircle
} from 'lucide-react';
import { toast } from 'sonner';
import type { Medicine } from '../types';

interface CabinetItem extends Medicine {
  id: string;
  quantity: number;
  expirationDate: string;
  addedDate: string;
  isExpired: boolean;
  daysUntilExpiration: number;
}

export default function MedicineCabinet() {
  const navigate = useNavigate();
  const location = useLocation();
  const medicineToAdd = location.state?.addMedicine as Medicine;

  const [medicines, setMedicines] = useState<CabinetItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'expired' | 'expiring' | 'active'>('all');
  const [isLoading, setIsLoading] = useState(false);
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
    loadMedicines();
    if (medicineToAdd) {
      setFormData({
        name: medicineToAdd.name,
        genericName: medicineToAdd.genericName || '',
        dosage: medicineToAdd.dosage || '',
        type: medicineToAdd.type || 'tablet',
        quantity: 1,
        expirationDate: '',
        notes: ''
      });
      setShowAddForm(true);
    }
  }, [medicineToAdd]);

  const loadMedicines = async () => {
    setIsLoading(true);
    try {
      const mockMedicines: Partial<CabinetItem>[] = [
        {
          id: '1',
          name: 'Ibuprofen',
          genericName: 'Ibuprofen',
          dosage: '200mg',
          type: 'tablet',
          quantity: 24,
          expirationDate: '2024-12-31',
          addedDate: '2024-01-15'
        },
        {
          id: '2',
          name: 'Vitamin D3',
          genericName: 'Cholecalciferol',
          dosage: '1000 IU',
          type: 'capsule',
          quantity: 60,
          expirationDate: '2024-06-15',
          addedDate: '2024-01-10'
        },
        {
          id: '3',
          name: 'Expired Aspirin',
          genericName: 'Acetylsalicylic acid',
          dosage: '325mg',
          type: 'tablet',
          quantity: 12,
          expirationDate: '2023-12-01',
          addedDate: '2023-06-01'
        }
      ];

      const today = new Date();
      const processed = mockMedicines.map(med => {
        const expDate = new Date(med.expirationDate!);
        const daysDiff = Math.ceil((expDate.getTime() - today.getTime()) / (1000 * 3600 * 24));
        return { ...med, isExpired: daysDiff < 0, daysUntilExpiration: daysDiff } as CabinetItem;
      });

      setMedicines(processed);
    } catch (error) {
      toast.error('Failed to load medicine cabinet');
    } finally {
      setIsLoading(false);
    }
  };

  const saveMedicine = () => {
    if (!formData.name || !formData.expirationDate) {
      toast.error('Name and expiration date are required');
      return;
    }

    const today = new Date();
    const expDate = new Date(formData.expirationDate);
    const daysDiff = Math.ceil((expDate.getTime() - today.getTime()) / (1000 * 3600 * 24));

    const item: CabinetItem = {
      id: editingMedicine?.id || Date.now().toString(),
      name: formData.name,
      genericName: formData.genericName,
      dosage: formData.dosage,
      type: formData.type,
      quantity: formData.quantity,
      expirationDate: formData.expirationDate,
      addedDate: editingMedicine?.addedDate || new Date().toISOString().split('T')[0],
      notes: formData.notes,
      isExpired: daysDiff < 0,
      daysUntilExpiration: daysDiff
    };

    if (editingMedicine) {
      setMedicines(prev => prev.map(m => m.id === item.id ? item : m));
      toast.success('Medicine updated');
    } else {
      setMedicines(prev => [...prev, item]);
      toast.success('Medicine added');
    }

    setShowAddForm(false);
    setEditingMedicine(null);
    resetForm();
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

  const getStatus = (item: CabinetItem) => {
    if (item.isExpired) return { color: 'text-red-600 bg-red-50', label: 'Expired', icon: AlertTriangle };
    if (item.daysUntilExpiration <= 30) return { color: 'text-orange-600 bg-orange-50', label: 'Expiring Soon', icon: Clock };
    return { color: 'text-green-600 bg-green-50', label: 'Active', icon: CheckCircle };
  };

  const deleteMedicine = (id: string) => {
    setMedicines(prev => prev.filter(m => m.id !== id));
    toast.success('Removed from cabinet');
  };

  const filteredMedicines = medicines.filter(med => {
    const query = searchQuery.toLowerCase();
    const matchesSearch = med.name.toLowerCase().includes(query) || med.genericName?.toLowerCase().includes(query);
    const matchesFilter = filterType === 'expired' ? med.isExpired :
      filterType === 'expiring' ? (!med.isExpired && (med.daysUntilExpiration ?? 0) <= 30) :
        filterType === 'active' ? (!med.isExpired && (med.daysUntilExpiration ?? 0) > 30) : true;
    return matchesSearch && matchesFilter;
  });

  const expiredCount = medicines.filter(m => m.isExpired).length;
  const expiringCount = medicines.filter(m => !m.isExpired && (m.daysUntilExpiration ?? 0) <= 30).length;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow-sm">
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
                <AlertTriangle className="text-red-600 mr-2" size={20} />
                <span className="text-red-800 font-semibold">{expiredCount} medicine{expiredCount > 1 ? 's' : ''} expired</span>
              </div>
            )}
            {expiringCount > 0 && (
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 flex items-center">
                <Clock className="text-orange-600 mr-2" size={20} />
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
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex space-x-2 overflow-x-auto">
            {['all', 'active', 'expiring', 'expired'].map(key => (
              <button
                key={key} onClick={() => setFilterType(key as any)}
                className={`px-4 py-2 rounded-lg text-sm font-medium ${filterType === key ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border border-gray-300'}`}
              >
                {key.charAt(0).toUpperCase() + key.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          {isLoading ? <div className="text-center py-8"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div></div> :
            filteredMedicines.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Package className="mx-auto mb-4 opacity-50" size={48} />
                <p>No medicines found.</p>
                <button onClick={() => setShowAddForm(true)} className="mt-4 text-blue-600 font-semibold">Add Medicine</button>
              </div>
            ) : (
              filteredMedicines.map(med => {
                const status = getStatus(med);
                const StatusIcon = status.icon;
                return (
                  <div key={med.id} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-800">{med.name}</h3>
                        {med.genericName && <p className="text-gray-600 text-sm">Generic: {med.genericName}</p>}
                        <div className="flex items-center space-x-2 text-sm text-gray-500 mt-1">
                          <span>{med.dosage}</span><span>•</span><span className="capitalize">{med.type}</span><span>•</span><span>Qty: {med.quantity}</span>
                        </div>
                      </div>
                      <div className="flex space-x-1">
                        <button onClick={() => startEdit(med)} className="p-2 text-gray-400 hover:text-blue-600"><Edit3 size={16} /></button>
                        <button onClick={() => deleteMedicine(med.id)} className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"><Trash2 size={16} /></button>
                      </div>
                    </div>
                    <div className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${status.color}`}>
                      <StatusIcon size={12} className="mr-1" /> {status.label} {!med.isExpired && `(${med.daysUntilExpiration} days)`}
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-gray-400 mt-3 pt-3 border-t">
                      <div className="flex items-center"><Calendar size={12} className="mr-1" /> Expires: {med.expirationDate}</div>
                      <div>Added: {med.addedDate}</div>
                    </div>
                    {med.notes && <div className="mt-2 p-2 bg-gray-50 rounded text-xs text-gray-600">{med.notes}</div>}
                  </div>
                );
              })
            )}
        </div>
      </div>

      {showAddForm && (
        <div className="fixed inset-0 bg-black/50 flex items-end justify-center z-50">
          <div className="bg-white w-full max-w-md rounded-t-2xl p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold">{editingMedicine ? 'Edit Medicine' : 'Add Medicine'}</h2>
              <button onClick={() => { setShowAddForm(false); setEditingMedicine(null); resetForm(); }} className="p-2"><X size={20} /></button>
            </div>
            <div className="space-y-4">
              <input type="text" placeholder="Name" value={formData.name} onChange={e => setFormData(p => ({ ...p, name: e.target.value }))} className="w-full p-3 border rounded-lg" />
              <input type="text" placeholder="Generic Name" value={formData.genericName} onChange={e => setFormData(p => ({ ...p, genericName: e.target.value }))} className="w-full p-3 border rounded-lg" />
              <div className="grid grid-cols-2 gap-4">
                <input type="text" placeholder="Dosage" value={formData.dosage} onChange={e => setFormData(p => ({ ...p, dosage: e.target.value }))} className="w-full p-3 border rounded-lg" />
                <select value={formData.type} onChange={e => setFormData(p => ({ ...p, type: e.target.value }))} className="w-full p-3 border rounded-lg">
                  {['tablet', 'capsule', 'liquid', 'cream', 'injection', 'other'].map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <input type="number" value={formData.quantity} onChange={e => setFormData(p => ({ ...p, quantity: parseInt(e.target.value) || 1 }))} className="w-full p-3 border rounded-lg" />
                <input type="date" value={formData.expirationDate} onChange={e => setFormData(p => ({ ...p, expirationDate: e.target.value }))} className="w-full p-3 border rounded-lg" />
              </div>
              <textarea placeholder="Notes" value={formData.notes} onChange={e => setFormData(p => ({ ...p, notes: e.target.value }))} rows={2} className="w-full p-3 border rounded-lg" />
              <button onClick={saveMedicine} className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold">{editingMedicine ? 'Update' : 'Add'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
