import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';
import Home from './pages/Home';
import CameraScanner from './pages/CameraScanner';
import HealthProfile from './pages/HealthProfile';
import MedicineCabinet from './pages/MedicineCabinet';
import Chat from './pages/Chat';
import MobileNavigation from './components/MobileNavigation';
import './index.css';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50 pb-20">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/scanner" element={<CameraScanner />} />
          <Route path="/profile" element={<HealthProfile />} />
          <Route path="/cabinet" element={<MedicineCabinet />} />
          <Route path="/chat" element={<Chat />} />
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
  );
}

export default App;
