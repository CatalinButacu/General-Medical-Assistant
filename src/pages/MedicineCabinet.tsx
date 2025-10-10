import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  Package, 
  Plus, 
  Search, 
  Calendar, 
  AlertTriangle, 
  Trash2, 
  Camera,
  Edit3,
  X,
  Clock,
  CheckCircle
} from 'lucide-react';
import { toast } from 'sonner';

interface MedicineItem {
  id: string;
  name: string;
  genericName?: string;
  dosage: string;
  type: string;
  quantity: number;
  expirationDate: string;
  addedDate: string;
  imageUrl?: string;
  notes?: string;
  isExpired: boolean;
  daysUntilExpiration: number;
}

interface MedicineToAdd {
  id: string;
  name: string;
  genericName: string;
  dosage: string;
  type: string;
}

export default function MedicineCabinet() {
  const navigate = useNavigate();
  const location = useLocation();
  const medicineToAdd = location.state?.addMedicine as MedicineToAdd;

  const [medicines, setMedicines] = useState<MedicineItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'expired' | 'expiring' | 'active'>('all');
  const [isLoading, setIsLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingMedicine, setEditingMedicine] = useState<MedicineItem | null>(null);

  // Form state
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
        dosage: medicineToAdd.dosage,
        type: medicineToAdd.type,
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
      // Mock data for MVP - in real app, this would be an API call
      const mockMedicines: MedicineItem[] = [
        {
          id: '1',
          name: 'Ibuprofen',
          genericName: 'Ibuprofen',
          dosage: '200mg',
          type: 'tablet',
          quantity: 24,
          expirationDate: '2024-12-31',
          addedDate: '2024-01-15',
          isExpired: false,
          daysUntilExpiration: 365,
          notes: 'For headaches and pain relief'
        },
        {
          id: '2',
          name: 'Vitamin D3',
          genericName: 'Cholecalciferol',
          dosage: '1000 IU',
          type: 'capsule',
          quantity: 60,
          expirationDate: '2024-06-15',
          addedDate: '2024-01-10',
          isExpired: false,
          daysUntilExpiration: 150,
          notes: 'Daily supplement'
        },
        {
          id: '3',
          name: 'Expired Aspirin',
          genericName: 'Acetylsalicylic acid',
          dosage: '325mg',
          type: 'tablet',
          quantity: 12,
          expirationDate: '2023-12-01',
          addedDate: '2023-06-01',
          isExpired: true,
          daysUntilExpiration: -30,
          notes: 'Needs to be disposed of'
        }
      ];

      // Calculate expiration status
      const today = new Date();
      const processedMedicines = mockMedicines.map(med => {
        const expDate = new Date(med.expirationDate);
        const timeDiff = expDate.getTime() - today.getTime();
        const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));
        
        return {
          ...med,
          isExpired: daysDiff < 0,
          daysUntilExpiration: daysDiff
        };
      });

      setMedicines(processedMedicines);
    } catch (error) {
      console.error('Error loading medicines:', error);
      toast.error('Failed to load medicine cabinet');
    } finally {
      setIsLoading(false);
    }
  };

  const addMedicine = async () => {
    if (!formData.name || !formData.expirationDate) {
      toast.error('Please fill in required fields');
      return;
    }

    const newMedicine: MedicineItem = {
      id: Date.now().toString(),
      name: formData.name,
      genericName: formData.genericName,
      dosage: formData.dosage,
      type: formData.type,
      quantity: formData.quantity,
      expirationDate: formData.expirationDate,
      addedDate: new Date().toISOString().split('T')[0],
      notes: formData.notes,
      isExpired: false,
      daysUntilExpiration: 0
    };

    // Calculate expiration status
    const today = new Date();
    const expDate = new Date(newMedicine.expirationDate);
    const timeDiff = expDate.getTime() - today.getTime();
    const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));
    
    newMedicine.isExpired = daysDiff < 0;
    newMedicine.daysUntilExpiration = daysDiff;

    setMedicines(prev => [...prev, newMedicine]);
    setShowAddForm(false);
    resetForm();
    toast.success('Medicine added to cabinet');
  };

  const updateMedicine = async () => {
    if (!editingMedicine || !formData.name || !formData.expirationDate) {
      toast.error('Please fill in required fields');
      return;
    }

    const updatedMedicine: MedicineItem = {
      ...editingMedicine,
      name: formData.name,
      genericName: formData.genericName,
      dosage: formData.dosage,
      type: formData.type,
      quantity: formData.quantity,
      expirationDate: formData.expirationDate,
      notes: formData.notes
    };

    // Calculate expiration status
    const today = new Date();
    const expDate = new Date(updatedMedicine.expirationDate);
    const timeDiff = expDate.getTime() - today.getTime();
    const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));
    
    updatedMedicine.isExpired = daysDiff < 0;
    updatedMedicine.daysUntilExpiration = daysDiff;

    setMedicines(prev => prev.map(med => med.id === editingMedicine.id ? updatedMedicine : med));
    setEditingMedicine(null);
    resetForm();
    toast.success('Medicine updated');
  };

  const deleteMedicine = async (id: string) => {
    setMedicines(prev => prev.filter(med => med.id !== id));
    toast.success('Medicine removed from cabinet');
  };

  const resetForm = () => {
    setFormData({
      name: '',
      genericName: '',
      dosage: '',
      type: 'tablet',
      quantity: 1,
      expirationDate: '',
      notes: ''
    });
  };

  const startEdit = (medicine: MedicineItem) => {
    setEditingMedicine(medicine);
    setFormData({
      name: medicine.name,
      genericName: medicine.genericName || '',
      dosage: medicine.dosage,
      type: medicine.type,
      quantity: medicine.quantity,
      expirationDate: medicine.expirationDate,
      notes: medicine.notes || ''
    });
    setShowAddForm(true);
  };

  const getExpirationStatus = (medicine: MedicineItem) => {
    if (medicine.isExpired) {
      return { color: 'text-red-600 bg-red-50 border-red-200', label: 'Expired', icon: AlertTriangle };
    } else if (medicine.daysUntilExpiration <= 30) {
      return { color: 'text-orange-600 bg-orange-50 border-orange-200', label: 'Expiring Soon', icon: Clock };
    } else {
      return { color: 'text-green-600 bg-green-50 border-green-200', label: 'Active', icon: CheckCircle };
    }
  };

  const filteredMedicines = medicines.filter(medicine => {
    const matchesSearch = medicine.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         (medicine.genericName?.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const matchesFilter = (() => {
      switch (filterType) {
        case 'expired': return medicine.isExpired;
        case 'expiring': return !medicine.isExpired && medicine.daysUntilExpiration <= 30;
        case 'active': return !medicine.isExpired && medicine.daysUntilExpiration > 30;
        default: return true;
      }
    })();

    return matchesSearch && matchesFilter;
  });

  const expiredCount = medicines.filter(m => m.isExpired).length;
  const expiringCount = medicines.filter(m => !m.isExpired && m.daysUntilExpiration <= 30).length;

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
            <h1 className="text-lg font-semibold">Medicine Cabinet</h1>
            <button
              onClick={() => setShowAddForm(true)}
              className="bg-blue-600 text-white p-2 rounded-lg"
            >
              <Plus size={20} />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-md mx-auto p-4">
        {/* Alerts */}
        {(expiredCount > 0 || expiringCount > 0) && (
          <div className="mb-6 space-y-2">
            {expiredCount > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center">
                  <AlertTriangle className="text-red-600 mr-2" size={20} />
                  <span className="text-red-800 font-semibold">
                    {expiredCount} medicine{expiredCount > 1 ? 's' : ''} expired
                  </span>
                </div>
              </div>
            )}
            {expiringCount > 0 && (
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                <div className="flex items-center">
                  <Clock className="text-orange-600 mr-2" size={20} />
                  <span className="text-orange-800 font-semibold">
                    {expiringCount} medicine{expiringCount > 1 ? 's' : ''} expiring soon
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Search and Filter */}
        <div className="mb-6 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search medicines..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="flex space-x-2 overflow-x-auto">
            {[
              { key: 'all', label: 'All', count: medicines.length },
              { key: 'active', label: 'Active', count: medicines.filter(m => !m.isExpired && m.daysUntilExpiration > 30).length },
              { key: 'expiring', label: 'Expiring', count: expiringCount },
              { key: 'expired', label: 'Expired', count: expiredCount }
            ].map(filter => (
              <button
                key={filter.key}
                onClick={() => setFilterType(filter.key as 'all' | 'expired' | 'expiring')}
                className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap ${
                  filterType === filter.key
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 border border-gray-300'
                }`}
              >
                {filter.label} ({filter.count})
              </button>
            ))}
          </div>
        </div>

        {/* Medicine List */}
        <div className="space-y-4">
          {isLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-gray-600 mt-2">Loading medicines...</p>
            </div>
          ) : filteredMedicines.length === 0 ? (
            <div className="text-center py-8">
              <Package className="mx-auto text-gray-400 mb-4" size={48} />
              <h3 className="text-lg font-semibold text-gray-800 mb-2">
                {searchQuery || filterType !== 'all' ? 'No medicines found' : 'Cabinet is empty'}
              </h3>
              <p className="text-gray-600 mb-4">
                {searchQuery || filterType !== 'all' 
                  ? 'Try adjusting your search or filter'
                  : 'Add medicines to start tracking your inventory'
                }
              </p>
              {!searchQuery && filterType === 'all' && (
                <div className="space-y-2">
                  <button
                    onClick={() => setShowAddForm(true)}
                    className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold"
                  >
                    Add Medicine
                  </button>
                  <br />
                  <button
                    onClick={() => navigate('/scanner')}
                    className="bg-green-600 text-white px-6 py-3 rounded-lg font-semibold"
                  >
                    Scan Medicine
                  </button>
                </div>
              )}
            </div>
          ) : (
            filteredMedicines.map(medicine => {
              const status = getExpirationStatus(medicine);
              const StatusIcon = status.icon;
              
              return (
                <div key={medicine.id} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-800 mb-1">{medicine.name}</h3>
                      {medicine.genericName && (
                        <p className="text-gray-600 text-sm mb-1">Generic: {medicine.genericName}</p>
                      )}
                      <div className="flex items-center space-x-4 text-sm text-gray-600">
                        <span>{medicine.dosage}</span>
                        <span>•</span>
                        <span className="capitalize">{medicine.type}</span>
                        <span>•</span>
                        <span>Qty: {medicine.quantity}</span>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => startEdit(medicine)}
                        className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                      >
                        <Edit3 size={16} />
                      </button>
                      <button
                        onClick={() => deleteMedicine(medicine.id)}
                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>

                  <div className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${status.color} mb-3`}>
                    <StatusIcon size={12} className="mr-1" />
                    {status.label}
                    {!medicine.isExpired && (
                      <span className="ml-1">
                        ({medicine.daysUntilExpiration} days)
                      </span>
                    )}
                  </div>

                  <div className="flex items-center justify-between text-sm text-gray-600">
                    <div className="flex items-center">
                      <Calendar size={14} className="mr-1" />
                      <span>Expires: {new Date(medicine.expirationDate).toLocaleDateString()}</span>
                    </div>
                    <span>Added: {new Date(medicine.addedDate).toLocaleDateString()}</span>
                  </div>

                  {medicine.notes && (
                    <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-700">{medicine.notes}</p>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Quick Actions */}
        <div className="mt-8 bg-white rounded-xl p-6 shadow-sm">
          <h3 className="font-semibold text-gray-800 mb-4">Quick Actions</h3>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => navigate('/scanner')}
              className="flex items-center justify-center space-x-2 bg-green-50 text-green-700 py-3 px-4 rounded-lg border border-green-200 hover:bg-green-100"
            >
              <Camera size={16} />
              <span className="text-sm font-medium">Scan Medicine</span>
            </button>
            <button
              onClick={() => setShowAddForm(true)}
              className="flex items-center justify-center space-x-2 bg-blue-50 text-blue-700 py-3 px-4 rounded-lg border border-blue-200 hover:bg-blue-100"
            >
              <Plus size={16} />
              <span className="text-sm font-medium">Add Manually</span>
            </button>
          </div>
        </div>
      </div>

      {/* Add/Edit Medicine Modal */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black/50 flex items-end justify-center z-50">
          <div className="bg-white w-full max-w-md rounded-t-2xl p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold">
                {editingMedicine ? 'Edit Medicine' : 'Add Medicine'}
              </h2>
              <button
                onClick={() => {
                  setShowAddForm(false);
                  setEditingMedicine(null);
                  resetForm();
                }}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Medicine Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., Ibuprofen"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Generic Name
                </label>
                <input
                  type="text"
                  value={formData.genericName}
                  onChange={(e) => setFormData(prev => ({ ...prev, genericName: e.target.value }))}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., Ibuprofen"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Dosage
                  </label>
                  <input
                    type="text"
                    value={formData.dosage}
                    onChange={(e) => setFormData(prev => ({ ...prev, dosage: e.target.value }))}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="e.g., 200mg"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Type
                  </label>
                  <select
                    value={formData.type}
                    onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value }))}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="tablet">Tablet</option>
                    <option value="capsule">Capsule</option>
                    <option value="liquid">Liquid</option>
                    <option value="cream">Cream</option>
                    <option value="injection">Injection</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Quantity
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={formData.quantity}
                    onChange={(e) => setFormData(prev => ({ ...prev, quantity: parseInt(e.target.value) || 1 }))}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Expiration Date *
                  </label>
                  <input
                    type="date"
                    value={formData.expirationDate}
                    onChange={(e) => setFormData(prev => ({ ...prev, expirationDate: e.target.value }))}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Notes
                </label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                  rows={3}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Any additional notes..."
                />
              </div>

              <button
                onClick={editingMedicine ? updateMedicine : addMedicine}
                className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700"
              >
                {editingMedicine ? 'Update Medicine' : 'Add Medicine'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}