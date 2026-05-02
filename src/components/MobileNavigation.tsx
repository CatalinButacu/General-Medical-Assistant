import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import { Home, Camera, User, Package, MessageCircle } from 'lucide-react';
import { cn } from '../lib/utils';

// Routes that take over the full viewport with their own dismiss UX —
// rendering the bottom nav on top of them covers content (e.g. the chat input).
const FULLSCREEN_ROUTES = new Set(['/chat', '/scanner']);

export default function MobileNavigation() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth0();

  if (FULLSCREEN_ROUTES.has(location.pathname)) return null;

  const navigationItems = [
    {
      path: '/',
      icon: Home,
      label: 'Home',
      color: 'text-blue-600'
    },
    {
      path: '/scanner',
      icon: Camera,
      label: 'Scanner',
      color: 'text-green-600'
    },
    {
      path: '/chat',
      icon: MessageCircle,
      label: 'Chat',
      color: 'text-purple-600'
    },
    {
      path: '/cabinet',
      icon: Package,
      label: 'Cabinet',
      color: 'text-orange-600'
    },
    {
      path: '/profile',
      icon: User,
      label: 'Profile',
      color: 'text-red-600',
      customIcon: isAuthenticated && user?.picture ? (
        <img src={user.picture} alt="Profile" className="w-6 h-6 rounded-full border border-gray-200" />
      ) : null
    }
  ];

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white/80 backdrop-blur-lg border-t border-gray-100 px-4 py-3 pb-6 z-50">
      <div className="flex justify-around items-center max-w-md mx-auto">
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={cn(
                "flex flex-col items-center justify-center p-1 rounded-2xl transition-all duration-300 min-w-[64px]",
                isActive
                  ? "scale-110"
                  : "hover:bg-gray-50 active:scale-95 opacity-50"
              )}
            >
              <div className={cn(
                "p-2 rounded-xl transition-all duration-300",
                isActive ? "bg-white shadow-lg shadow-blue-100 mb-1" : ""
              )}>
                {item.customIcon ? (
                  <div className={cn("transition-transform duration-300", isActive ? "scale-110" : "")}>
                    {item.customIcon}
                  </div>
                ) : (
                  <Icon
                    size={22}
                    className={cn(
                      "transition-colors duration-200",
                      isActive ? item.color : "text-gray-400"
                    )}
                  />
                )}
              </div>
              <span
                className={cn(
                  "text-[10px] font-bold uppercase tracking-tighter transition-colors duration-200",
                  isActive ? item.color : "text-gray-400"
                )}
              >
                {item.label}
              </span>
              {isActive && (
                <div className={cn("w-1 h-1 rounded-full mt-1", item.color.replace('text', 'bg'))} />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
