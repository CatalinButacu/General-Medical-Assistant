import { useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import { Camera, MessageCircle, Shield, Package, Heart, AlertTriangle, LogIn, LogOut, User as UserIcon } from 'lucide-react';

export default function Home() {
  const navigate = useNavigate();
  const { loginWithRedirect, logout, user, isAuthenticated, isLoading } = useAuth0();

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
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-md mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mr-3">
                <Heart className="text-white" size={20} />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-800">MedAssist</h1>
                <p className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">AI Pharmacist</p>
              </div>
            </div>

            {isLoading ? (
              <div className="w-8 h-8 rounded-full bg-gray-100 animate-pulse" />
            ) : isAuthenticated ? (
              <div className="flex items-center space-x-3">
                <button
                  onClick={() => navigate('/profile')}
                  className="flex items-center space-x-2 p-1 pr-3 bg-gray-50 rounded-full border hover:bg-gray-100 transition-colors"
                >
                  <img src={user?.picture} alt={user?.name} className="w-7 h-7 rounded-full" />
                  <span className="text-xs font-semibold text-gray-700 truncate max-w-[80px]">{user?.given_name || 'Profile'}</span>
                </button>
                <button
                  onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
                  className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                >
                  <LogOut size={18} />
                </button>
              </div>
            ) : (
              <button
                onClick={() => loginWithRedirect()}
                className="flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors shadow-sm"
              >
                <LogIn size={16} />
                <span>Login</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Educational Disclaimer */}
      <div className="bg-indigo-600 text-white px-4 py-2 text-center text-[10px] font-bold uppercase tracking-[0.2em]">
        Educational Demo Purposes Only • Not Medical Advice
      </div>

      <div className="max-w-md mx-auto px-4 py-6">
        {!isAuthenticated && (
          <div className="bg-white rounded-2xl p-6 shadow-md border border-blue-100 mb-8 text-center bg-gradient-to-br from-white to-blue-50">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <UserIcon className="text-blue-600" size={24} />
            </div>
            <h2 className="text-lg font-bold text-gray-800 mb-2">Save Your Progress</h2>
            <p className="text-sm text-gray-600 mb-6">
              Log in to save your health profile and keep track of your medicine cabinet across all devices.
            </p>
            <button
              onClick={() => loginWithRedirect()}
              className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold shadow-lg shadow-blue-200 hover:bg-blue-700 transition-all active:scale-[0.98]"
            >
              Sign In to Start
            </button>
          </div>
        )}

        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-8">
          <div className="flex items-start">
            <AlertTriangle className="text-amber-600 mr-3 mt-0.5" size={20} />
            <div>
              <h3 className="font-semibold text-amber-800 mb-1 text-sm">Safety First</h3>
              <p className="text-xs text-amber-700 opacity-80">
                Always consult healthcare professionals for serious medical concerns. This app provides guidance only.
              </p>
            </div>
          </div>
        </div>

        <div className="mb-10">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-800 tracking-tight">Quick Actions</h2>
            <div className="h-[2px] w-12 bg-blue-200 rounded-full"></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {quickActions.map((action, index) => {
              const Icon = action.icon;
              return (
                <button
                  key={index}
                  onClick={action.action}
                  className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group"
                >
                  <div className={`w-12 h-12 ${action.color} rounded-xl flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 transition-transform`}>
                    <Icon className="text-white" size={24} />
                  </div>
                  <h3 className="font-bold text-gray-800 mb-1 text-sm">{action.title}</h3>
                  <p className="text-[10px] text-gray-500 leading-relaxed font-medium uppercase tracking-tighter">Click to open</p>
                </button>
              );
            })}
          </div>
        </div>

        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 mb-10">
          <h2 className="text-lg font-bold text-gray-800 mb-6 flex items-center">
            <div className="w-1 h-5 bg-blue-500 rounded-full mr-3"></div>
            How It Works
          </h2>
          <div className="space-y-6">
            {[
              { num: 1, title: 'Photo Recognition', desc: 'Take photos of medicines for instant identification', bg: 'bg-blue-50', text: 'text-blue-600' },
              { num: 2, title: 'Personalized Safety', desc: 'Get warnings based on your health profile', bg: 'bg-green-50', text: 'text-green-600' },
              { num: 3, title: 'AI Assistance', desc: 'Chat with AI for medicine questions and advice', bg: 'bg-purple-50', text: 'text-purple-600' }
            ].map((step) => (
              <div key={step.num} className="flex items-start">
                <div className={`w-10 h-10 ${step.bg} rounded-xl flex-shrink-0 flex items-center justify-center mr-4 mt-0.5`}>
                  <span className={`${step.text} font-bold text-sm`}>{step.num}</span>
                </div>
                <div>
                  <h4 className="font-bold text-gray-800 text-sm mb-1">{step.title}</h4>
                  <p className="text-xs text-gray-500 font-medium leading-relaxed">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
