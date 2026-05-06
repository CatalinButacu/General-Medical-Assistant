import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import { Auth0Provider } from '@auth0/auth0-react';
import { Toaster } from 'sonner';
import { auth0Config } from './config/auth0';
import Home from './pages/Home';
import CameraScanner from './pages/CameraScanner';
import HealthProfile from './pages/HealthProfile';
import MedicineCabinet from './pages/MedicineCabinet';
import Chat from './pages/Chat';
import Onboarding from './pages/Onboarding';
import MobileNavigation from './components/MobileNavigation';
import AuthGuard from './components/AuthGuard';
import './index.css';

function App() {
  return (
    <Auth0Provider {...auth0Config}>
      <Router>
        <div className="h-[100dvh] flex flex-col bg-gradient-to-br from-blue-50 to-indigo-100 overflow-hidden">
          <main className="flex-1 overflow-y-auto pb-24 relative">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/scanner" element={
                <AuthGuard>
                  <CameraScanner />
                </AuthGuard>
              } />
              <Route path="/profile" element={
                <AuthGuard>
                  <HealthProfile />
                </AuthGuard>
              } />
              <Route path="/cabinet" element={
                <AuthGuard>
                  <MedicineCabinet />
                </AuthGuard>
              } />
              <Route path="/chat" element={
                <AuthGuard>
                  <Chat />
                </AuthGuard>
              } />
              <Route path="/onboarding" element={
                <AuthGuard>
                  <Onboarding />
                </AuthGuard>
              } />
            </Routes>
          </main>

          <MobileNavigation />

          <Toaster
            position="top-center"
            richColors
            closeButton
            toastOptions={{
              style: {
                fontSize: '14px',
                padding: '12px',
                borderRadius: '16px',
              }
            }}
          />
        </div>
      </Router>
    </Auth0Provider>
  );
}

export default App;
