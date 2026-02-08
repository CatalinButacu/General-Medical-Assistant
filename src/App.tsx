import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import { Auth0Provider } from '@auth0/auth0-react';
import { Toaster } from 'sonner';
import { auth0Config } from './config/auth0';
import Home from './pages/Home';
import CameraScanner from './pages/CameraScanner';
import HealthProfile from './pages/HealthProfile';
import MedicineCabinet from './pages/MedicineCabinet';
import Chat from './pages/Chat';
import MobileNavigation from './components/MobileNavigation';
import AuthGuard from './components/AuthGuard';
import './index.css';

function App() {
  return (
    <Auth0Provider {...auth0Config}>
      <Router>
        <div className="min-h-screen bg-gray-50 pb-20">
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
          </Routes>
          <MobileNavigation />
          <Toaster
            position="top-center"
            richColors
            closeButton
            toastOptions={{
              style: {
                fontSize: '16px',
                padding: '16px',
              }
            }}
          />
        </div>
      </Router>
    </Auth0Provider>
  );
}

export default App;
