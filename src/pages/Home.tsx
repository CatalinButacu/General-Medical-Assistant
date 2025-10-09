import { useNavigate } from 'react-router-dom';
import { Camera, MessageCircle, Shield, Package, Heart, AlertTriangle } from 'lucide-react';

export default function Home() {
  const navigate = useNavigate();

  const quickActions = [
    {
      icon: Camera,
      title: 'Scan Medicine',
      description: 'Take a photo to identify medicine',
      color: 'bg-green-500',
      action: () => navigate('/scanner')
    },
    {
      icon: MessageCircle,
      title: 'Ask AI Assistant',
      description: 'Get personalized medicine advice',
      color: 'bg-purple-500',
      action: () => navigate('/chat')
    },
    {
      icon: Package,
      title: 'Medicine Cabinet',
      description: 'Manage your medicine inventory',
      color: 'bg-orange-500',
      action: () => navigate('/cabinet')
    },
    {
      icon: Shield,
      title: 'Safety Check',
      description: 'Check medicine safety for you',
      color: 'bg-red-500',
      action: () => navigate('/profile')
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-md mx-auto px-4 py-6">
          <div className="flex items-center justify-center mb-2">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mr-3">
              <Heart className="text-white" size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">MedAssist</h1>
              <p className="text-sm text-gray-600">Your Personal AI Pharmacist</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-md mx-auto px-4 py-6">
        {/* Safety Alert */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <div className="flex items-start">
            <AlertTriangle className="text-amber-600 mr-3 mt-0.5" size={20} />
            <div>
              <h3 className="font-semibold text-amber-800 mb-1">Safety First</h3>
              <p className="text-sm text-amber-700">
                Always consult healthcare professionals for serious medical concerns. This app provides guidance only.
              </p>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mb-8">
          <h2 className="text-xl font-bold text-gray-800 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-4">
            {quickActions.map((action, index) => {
              const Icon = action.icon;
              return (
                <button
                  key={index}
                  onClick={action.action}
                  className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-all duration-200 active:scale-95"
                >
                  <div className={`w-12 h-12 ${action.color} rounded-lg flex items-center justify-center mb-3 mx-auto`}>
                    <Icon className="text-white" size={24} />
                  </div>
                  <h3 className="font-semibold text-gray-800 mb-1 text-sm">{action.title}</h3>
                  <p className="text-xs text-gray-600 leading-relaxed">{action.description}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Features Overview */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-bold text-gray-800 mb-4">How It Works</h2>
          <div className="space-y-4">
            <div className="flex items-start">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3 mt-0.5">
                <span className="text-blue-600 font-bold text-sm">1</span>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800 text-sm">Photo Recognition</h4>
                <p className="text-xs text-gray-600">Take photos of medicines for instant identification</p>
              </div>
            </div>
            <div className="flex items-start">
              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mr-3 mt-0.5">
                <span className="text-green-600 font-bold text-sm">2</span>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800 text-sm">Personalized Safety</h4>
                <p className="text-xs text-gray-600">Get warnings based on your health profile</p>
              </div>
            </div>
            <div className="flex items-start">
              <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center mr-3 mt-0.5">
                <span className="text-purple-600 font-bold text-sm">3</span>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800 text-sm">AI Assistance</h4>
                <p className="text-xs text-gray-600">Chat with AI for medicine questions and advice</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}