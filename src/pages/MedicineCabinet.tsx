import { useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import {
  Package, Plus, Search, Calendar, AlertTriangle,
  Trash2, Edit3, X, Clock, CheckCircle, Sparkles
} from 'lucide-react';
import { toast } from 'sonner';
import { useUserApi } from '../hooks/useUserApi';
import { userPaths, type CabinetItemDTO } from '../services/userApi';
import type { CabinetAddState } from '../types';
import { Button, FormField, TextInput, Textarea, Select } from '../components/ui';
import {
  fireExpiryNotifications,
  hasAskedForPermission,
  requestNotificationPermission,
} from '../lib/cabinetExpiry';
import { Bell } from 'lucide-react';

// Local UI shape: server fields from CabinetItemDTO normalized to camelCase +
// derived isExpired / daysUntilExpiration for the row badge. Lives next to the
// only consumer so the API DTO stays the canonical contract.
interface CabinetItemView {
  id: string;
  name: string;
  genericName?: string;
  dosage?: string;
  type?: string;
  quantity: number;
  expirationDate: string;
  addedDate: string;
  notes?: string;
  isExpired?: boolean;
  daysUntilExpiration?: number;
}

function dtoToItem(d: CabinetItemDTO): CabinetItemView {
  const today = new Date();
  const exp = new Date(d.expiration_date);
  const days = Math.ceil((exp.getTime() - today.getTime()) / (1000 * 3600 * 24));
  return {
    id: d.id ?? '',
    name: d.name,
    genericName: d.generic_name ?? undefined,
    dosage: d.dosage ?? undefined,
    type: d.item_type ?? 'tablet',
    quantity: d.quantity,
    expirationDate: d.expiration_date,
    addedDate: d.added_date ?? new Date().toISOString().split('T')[0],
    notes: d.notes ?? undefined,
    isExpired: days < 0,
    daysUntilExpiration: days,
  };
}

export default function MedicineCabinet() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth0();
  const medicineToAdd = location.state?.addMedicine as CabinetAddState | undefined;
  const fromScanner = Boolean(location.state?.fromScanner);

  const [medicines, setMedicines] = useState<CabinetItemView[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'expired' | 'expiring' | 'active'>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingMedicine, setEditingMedicine] = useState<CabinetItemView | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    genericName: '',
    dosage: '',
    type: 'tablet',
    quantity: 1,
    expirationDate: '',
    notes: ''
  });

  const apiCall = useUserApi();

  const reloadCabinet = useCallback(async () => {
    if (!user?.sub) return;
    try {
      const items = await apiCall<CabinetItemDTO[]>(userPaths.cabinet);
      setMedicines(items.map(dtoToItem));
    } catch (err) {
      console.error('cabinet load failed', err);
      toast.error('Încărcarea cabinetului a eșuat');
    } finally {
      setIsLoading(false);
    }
  }, [apiCall, user?.sub]);

  useEffect(() => {
    if (!user?.sub) return;
    reloadCabinet();
  }, [user?.sub, reloadCabinet]);

  // Fire any pending expiry notifications whenever the cabinet list changes.
  // The library is deduped per (item, day) so re-renders don't spam the user.
  useEffect(() => {
    if (medicines.length === 0) return;
    void fireExpiryNotifications(medicines.map(m => ({
      id: m.id,
      name: m.name,
      daysUntilExpiration: m.daysUntilExpiration,
      isExpired: m.isExpired,
    })));
  }, [medicines]);

  const [notifPrompt, setNotifPrompt] = useState(
    () => !hasAskedForPermission() && typeof Notification !== 'undefined' && Notification.permission === 'default'
  );
  const handleEnableNotifications = async () => {
    const result = await requestNotificationPermission();
    setNotifPrompt(false);
    if (result === 'granted') {
      toast.success('Notificările sunt activate');
    } else if (result === 'denied') {
      toast.info('Notificările au fost refuzate — le poți activa din setările browserului.');
    }
  };

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
      toast.error('Completează câmpurile obligatorii');
      return;
    }

    const payload: CabinetItemDTO = {
      name: formData.name,
      generic_name: formData.genericName || null,
      dosage: formData.dosage || null,
      item_type: formData.type,
      quantity: formData.quantity,
      expiration_date: formData.expirationDate,
      notes: formData.notes || null,
    };

    try {
      if (editingMedicine) {
        await apiCall<CabinetItemDTO>(userPaths.cabinetItem(editingMedicine.id), {
          method: 'PUT',
          body: JSON.stringify(payload),
        });
        toast.success('Medicament actualizat');
      } else {
        await apiCall<CabinetItemDTO>(userPaths.cabinet, {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        toast.success('Medicament adăugat');
      }
      setShowAddForm(false);
      setEditingMedicine(null);
      resetForm();
      await reloadCabinet();
    } catch (e) {
      console.error('save medicine failed', e);
      toast.error('Salvare eșuată');
    }
  };

  const resetForm = () => setFormData({ name: '', genericName: '', dosage: '', type: 'tablet', quantity: 1, expirationDate: '', notes: '' });

  const startEdit = (item: CabinetItemView) => {
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
      await apiCall<void>(userPaths.cabinetItem(id), { method: 'DELETE' });
      toast.success('Eliminat din cabinet');
      await reloadCabinet();
    } catch (e) {
      console.error('delete medicine failed', e);
      toast.error('Ștergere eșuată');
    }
  };

  const getStatus = (item: CabinetItemView) => {
    if (item.isExpired) return { color: 'text-red-600 bg-red-50', label: 'Expirat', icon: AlertTriangle };
    if ((item.daysUntilExpiration ?? 100) <= 30) return { color: 'text-orange-600 bg-orange-50', label: 'Expiră curând', icon: Clock };
    return { color: 'text-green-600 bg-green-50', label: 'Activ', icon: CheckCircle };
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
            <h1 className="text-lg font-semibold">Cabinet medicamente</h1>
            <button onClick={() => setShowAddForm(true)} className="bg-blue-600 text-white p-2 rounded-lg"><Plus size={20} /></button>
          </div>
        </div>
      </div>

      <div className="max-w-md mx-auto p-4">
        {notifPrompt && (
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
            <Bell className="text-blue-600 mt-0.5 flex-shrink-0" size={20} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-blue-900">Vrei notificări pentru expirări?</p>
              <p className="text-xs text-blue-700 mt-1 leading-relaxed">
                Te anunțăm când un medicament din cabinet se apropie de data expirării.
                Notificările sunt locale și nu părăsesc dispozitivul.
              </p>
              <div className="flex gap-2 mt-3">
                <button
                  onClick={handleEnableNotifications}
                  className="bg-blue-600 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-sm hover:bg-blue-700"
                >
                  Activează
                </button>
                <button
                  onClick={() => setNotifPrompt(false)}
                  className="text-blue-700 text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-blue-100"
                >
                  Mai târziu
                </button>
              </div>
            </div>
          </div>
        )}

        {(expiredCount > 0 || expiringCount > 0) && (
          <div className="mb-6 space-y-2">
            {expiredCount > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center">
                <AlertTriangle className="text-red-600 mr-3" size={20} />
                <span className="text-red-800 font-semibold">{expiredCount} medicament{expiredCount > 1 ? 'e' : ''} expirat{expiredCount > 1 ? 'e' : ''}</span>
              </div>
            )}
            {expiringCount > 0 && (
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 flex items-center">
                <Clock className="text-orange-600 mr-3" size={20} />
                <span className="text-orange-800 font-semibold">{expiringCount} medicament{expiringCount > 1 ? 'e' : ''} expiră curând</span>
              </div>
            )}
          </div>
        )}

        <div className="mb-6 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text" placeholder="Caută medicamente…" value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
            />
          </div>

          <div className="flex space-x-2 overflow-x-auto pb-1 no-scrollbar">
            {([
              { key: 'all', label: 'Toate' },
              { key: 'active', label: 'Active' },
              { key: 'expiring', label: 'Expiră curând' },
              { key: 'expired', label: 'Expirate' },
            ] as const).map(({ key, label }) => (
              <button
                key={key} onClick={() => setFilterType(key)}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all whitespace-nowrap ${filterType === key ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-gray-600 border border-gray-200'}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          {isLoading ? (
            <div className="text-center py-20">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-500 font-medium">Sincronizare cu cloud…</p>
            </div>
          ) : filteredMedicines.length === 0 ? (
            <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-gray-300">
              <Package className="mx-auto mb-4 text-gray-300" size={48} />
              <p className="text-gray-500 font-medium">Niciun medicament</p>
              <button onClick={() => setShowAddForm(true)} className="mt-4 text-blue-600 font-bold">Adaugă primul medicament</button>
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
                        <span className="px-2 py-0.5 bg-gray-50 text-gray-600 text-[10px] font-bold rounded uppercase tracking-wider">Cant: {med.quantity}</span>
                      </div>
                    </div>
                    <div className="flex -mr-2">
                      <button onClick={() => startEdit(med)} className="p-2 text-gray-400 hover:text-blue-600 transition-colors"><Edit3 size={18} /></button>
                      <button onClick={() => deleteMedicine(med.id)} className="p-2 text-gray-400 hover:text-red-600 transition-colors"><Trash2 size={18} /></button>
                    </div>
                  </div>
                  <div className={`inline-flex items-center px-3 py-1 rounded-full text-[11px] font-bold border ${status.color}`}>
                    <StatusIcon size={12} className="mr-1.5" /> {status.label} {!med.isExpired && med.daysUntilExpiration !== undefined && `(${med.daysUntilExpiration} zile rămase)`}
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-gray-400 mt-4 pt-4 border-t border-gray-50">
                    <div className="flex items-center font-medium"><Calendar size={12} className="mr-1.5" /> Expiră: {med.expirationDate}</div>
                    <div className="font-medium">Adăugat: {med.addedDate}</div>
                  </div>
                  {med.notes && <div className="mt-3 p-3 bg-gray-50 rounded-xl text-xs text-gray-600 italic">"{med.notes}"</div>}
                </div>
              );
            })
          )}
        </div>
      </div>

      {showAddForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-end justify-center z-[60] p-4">
          <div className="bg-white w-full max-w-md rounded-3xl p-6 shadow-2xl animate-in slide-in-from-bottom duration-300 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-xl font-bold text-gray-800">{editingMedicine ? 'Editează medicament' : 'Adaugă în cabinet'}</h2>
              <button onClick={() => { setShowAddForm(false); setEditingMedicine(null); resetForm(); }} className="p-2 bg-gray-100 rounded-full hover:bg-gray-200 transition-colors"><X size={20} /></button>
            </div>
            {fromScanner && !editingMedicine && (
              <div className="flex items-center gap-2 mb-3 px-3 py-2 bg-blue-50 border border-blue-100 rounded-xl text-[11px] font-semibold text-blue-700">
                <Sparkles size={12} />
                <span>Date precompletate din scaner — verifică și ajustează dacă e cazul.</span>
              </div>
            )}
            {fromScanner && !editingMedicine && !formData.expirationDate && (
              <div className="flex items-start gap-2 mb-6 px-3 py-2 bg-amber-50 border border-amber-200 rounded-xl text-[11px] font-semibold text-amber-800">
                <AlertTriangle size={12} className="mt-0.5 flex-shrink-0" />
                <span>Data expirării nu a fost detectată în imagine — completează-o manual mai jos.</span>
              </div>
            )}
            {!fromScanner && <div className="mb-6" />}
            <div className="space-y-5">
              <FormField label="Denumire">
                <TextInput placeholder="ex: Paracetamol" value={formData.name} onChange={e => setFormData(p => ({ ...p, name: e.target.value }))} />
              </FormField>
              <FormField label="Substanță activă (DCI)">
                <TextInput placeholder="ex: Paracetamolum" value={formData.genericName} onChange={e => setFormData(p => ({ ...p, genericName: e.target.value }))} />
              </FormField>
              <div className="grid grid-cols-2 gap-4">
                <FormField label="Concentrație">
                  <TextInput placeholder="500mg" value={formData.dosage} onChange={e => setFormData(p => ({ ...p, dosage: e.target.value }))} />
                </FormField>
                <FormField label="Formă">
                  <Select value={formData.type} onChange={e => setFormData(p => ({ ...p, type: e.target.value }))}>
                    {[
                      { v: 'tablet', l: 'Comprimat' },
                      { v: 'capsule', l: 'Capsulă' },
                      { v: 'liquid', l: 'Sirop / soluție' },
                      { v: 'cream', l: 'Cremă / unguent' },
                      { v: 'injection', l: 'Injectabil' },
                      { v: 'other', l: 'Alta' },
                    ].map(({ v, l }) => <option key={v} value={v}>{l}</option>)}
                  </Select>
                </FormField>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <FormField label="Cantitate">
                  <TextInput type="number" value={formData.quantity} onChange={e => setFormData(p => ({ ...p, quantity: parseInt(e.target.value) || 1 }))} />
                </FormField>
                <FormField label="Data expirării">
                  <TextInput
                    type="date"
                    value={formData.expirationDate}
                    onChange={e => setFormData(p => ({ ...p, expirationDate: e.target.value }))}
                    className={fromScanner && !editingMedicine && !formData.expirationDate ? 'ring-2 ring-amber-400 bg-amber-50' : ''}
                  />
                </FormField>
              </div>
              <FormField label="Notițe personale">
                <Textarea placeholder="ex: De luat după mese" value={formData.notes} onChange={e => setFormData(p => ({ ...p, notes: e.target.value }))} rows={2} />
              </FormField>
              <Button onClick={saveMedicine} variant="primary" size="lg" fullWidth className="mt-4 uppercase tracking-widest">
                {editingMedicine ? 'Actualizează' : 'Adaugă în cabinet'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
