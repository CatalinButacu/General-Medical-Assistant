import { useLocation, useNavigate } from 'react-router-dom';
import { Home, Camera, User, Package, MessageCircle } from 'lucide-react';
import { cn } from '../lib/utils';

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
    color: 'text-red-600'
  }
];

export default function MobileNavigation() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 px-4 py-2 z-50">
      <div className="flex justify-around items-center max-w-md mx-auto">
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={cn(
                "flex flex-col items-center justify-center p-2 rounded-lg transition-all duration-200 min-w-[60px]",
                isActive 
                  ? "bg-blue-50 scale-105" 
                  : "hover:bg-gray-50 active:scale-95"
              )}
            >
              <Icon 
                size={24} 
                className={cn(
                  "transition-colors duration-200",
                  isActive ? item.color : "text-gray-400"
                )} 
              />
              <span 
                className={cn(
                  "text-xs mt-1 font-medium transition-colors duration-200",
                  isActive ? item.color : "text-gray-400"
                )}
              >
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}