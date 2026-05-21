import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import { Camera, MessageCircle, Shield, Package, Heart, AlertTriangle, LogIn, LogOut, User as UserIcon } from 'lucide-react';
import { useUserApi } from '../hooks/useUserApi';
import { userPaths, type ProfileDTO } from '../services/userApi';
import { OnboardingTour } from '../components/OnboardingTour';
import { shouldShowOnboarding } from '../lib/onboarding';

export default function Home() {
  const navigate = useNavigate();
  const { loginWithRedirect, logout, user, isAuthenticated, isLoading } = useAuth0();
  const apiCall = useUserApi();
  const [showTour, setShowTour] = useState(false);

  useEffect(() => {
    // Fire the first-launch tour for any visitor (auth or not) who hasn't
    // seen it yet. The tour itself sets the localStorage flag on dismiss.
    setShowTour(shouldShowOnboarding());
  }, []);

  useEffect(() => {
    if (!isAuthenticated || !user?.sub) return;
    let cancelled = false;
    (async () => {
      try {
        const p = await apiCall<ProfileDTO>(userPaths.profile);
        if (cancelled) return;
        if (!p.onboarded) navigate('/onboarding', { replace: true });
      } catch (err) {
        console.warn('onboarding-check failed', err);
      }
    })();
    return () => { cancelled = true; };
  }, [isAuthenticated, user?.sub, navigate, apiCall]);

  const quickActions = [
    {
      icon: Camera,
      title: 'Scanează medicament',
      description: 'Fă o poză pentru identificare',
      color: 'bg-green-500',
      action: () => navigate('/scanner')
    },
    {
      icon: MessageCircle,
      title: 'Asistent AI',
      description: 'Sfaturi personalizate de farmacie',
      color: 'bg-purple-500',
      action: () => navigate('/chat')
    },
    {
      icon: Package,
      title: 'Cabinet medicamente',
      description: 'Inventarul tău de medicamente',
      color: 'bg-orange-500',
      action: () => navigate('/cabinet')
    },
    {
      icon: Shield,
      title: 'Verificare siguranță',
      description: 'Verifică un medicament pentru tine',
      color: 'bg-red-500',
      action: () => navigate('/profile')
    }
  ];

  return (
    <div className="min-h-full">
      {showTour && <OnboardingTour onDone={() => setShowTour(false)} />}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-md mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mr-3">
                <Heart className="text-white" size={20} />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-800">MedAssist</h1>
                <p className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">Asistent farmaceutic AI</p>
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
                  <span className="text-xs font-semibold text-gray-700 truncate max-w-[80px]">{user?.given_name || 'Profil'}</span>
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
                <span>Autentificare</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Educational Disclaimer */}
      <div className="bg-indigo-600 text-white px-4 py-2 text-center text-[10px] font-bold uppercase tracking-[0.2em]">
        Demo educativ • Nu este sfat medical
      </div>

      <div className="max-w-md mx-auto px-4 py-6">
        {!isAuthenticated && (
          <div className="bg-white rounded-2xl p-6 shadow-md border border-blue-100 mb-8 text-center bg-gradient-to-br from-white to-blue-50">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <UserIcon className="text-blue-600" size={24} />
            </div>
            <h2 className="text-lg font-bold text-gray-800 mb-2">Salvează-ți progresul</h2>
            <p className="text-sm text-gray-600 mb-6">
              Autentifică-te pentru a-ți salva profilul de sănătate și cabinetul de medicamente pe toate dispozitivele.
            </p>
            <button
              onClick={() => loginWithRedirect()}
              className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold shadow-lg shadow-blue-200 hover:bg-blue-700 transition-all active:scale-[0.98]"
            >
              Autentifică-te
            </button>
          </div>
        )}

        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-8">
          <div className="flex items-start">
            <AlertTriangle className="text-amber-600 mr-3 mt-0.5" size={20} />
            <div>
              <h3 className="font-semibold text-amber-800 mb-1 text-sm">Siguranța pe primul loc</h3>
              <p className="text-xs text-amber-700 opacity-80">
                Pentru probleme medicale serioase, consultă întotdeauna un medic sau farmacist. Aplicația oferă doar îndrumare.
              </p>
            </div>
          </div>
        </div>

        {isAuthenticated && (
          <div className="mb-10">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-800 tracking-tight">Acțiuni rapide</h2>
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
                    <p className="text-[10px] text-gray-500 leading-relaxed font-medium uppercase tracking-tighter">Apasă pentru a deschide</p>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 mb-10">
          <h2 className="text-lg font-bold text-gray-800 mb-6 flex items-center">
            <div className="w-1 h-5 bg-blue-500 rounded-full mr-3"></div>
            Cum funcționează
          </h2>
          <div className="space-y-6">
            {[
              { num: 1, title: 'Recunoaștere foto', desc: 'Fă o poză cutiei pentru identificare instantă', bg: 'bg-blue-50', text: 'text-blue-600' },
              { num: 2, title: 'Siguranță personalizată', desc: 'Avertizări pe baza profilului tău de sănătate', bg: 'bg-green-50', text: 'text-green-600' },
              { num: 3, title: 'Asistență AI', desc: 'Discută cu AI-ul pentru întrebări și sfaturi', bg: 'bg-purple-50', text: 'text-purple-600' }
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
